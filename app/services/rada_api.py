"""
Service for working with Rada API
"""
import httpx
import asyncio
import json
from typing import Optional, Dict, List, Any
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class RadaAPIService:
    """Service for interacting with Rada API"""
    
    def __init__(self):
        self.base_url = settings.RADA_API_BASE_URL
        self.token = settings.RADA_API_TOKEN
        self.rate_limit = settings.RADA_API_RATE_LIMIT
        self.delay = settings.RADA_API_DELAY
        self.last_request_time = 0.0
    
    async def _rate_limit(self):
        """Rate limiting between requests"""
        import time
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.delay:
            await asyncio.sleep(self.delay - time_since_last)
        
        self.last_request_time = time.time()
    
    def _get_headers(self, use_token: bool = False) -> Dict[str, str]:
        """Get request headers"""
        if use_token and self.token:
            return {"User-Agent": self.token}
        return {"User-Agent": "OpenData"}
    
    async def get_token(self) -> Optional[str]:
        """Get API token from Rada"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/token",
                    timeout=30.0
                )
                if response.status_code == 200:
                    token = response.text.strip()
                    logger.info("Successfully obtained Rada API token")
                    return token
                else:
                    logger.error(f"Failed to get token: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error getting token: {e}")
            return None
    
    async def get_document_json(self, nreg: str) -> Optional[Dict[str, Any]]:
        """
        Get full document in JSON format
        Tries multiple URL formats and endpoints to find the correct one
        """
        await self._rate_limit()
        
        # Try to get token if not set
        if not self.token:
            logger.info("RADA_API_TOKEN not set, trying to get token automatically...")
            self.token = await self.get_token()
        
        from urllib.parse import quote
        
        # Prepare encoded nreg variants
        if '/' in nreg:
            parts = nreg.split('/')
            encoded_parts = [quote(part, safe='') for part in parts]
            encoded_nreg = '/'.join(encoded_parts)
            # Also try with %2F encoding
            encoded_nreg_full = quote(nreg, safe='')
        else:
            encoded_nreg = quote(nreg, safe='')
            encoded_nreg_full = encoded_nreg
        
        # List of URL formats to try (in order of preference)
        url_formats = [
            # Try card endpoint first (usually faster and more reliable)
            f"{self.base_url}/laws/card/{encoded_nreg}.json",
            # Try show endpoint
            f"{self.base_url}/laws/show/{encoded_nreg}.json",
            # Try with full encoding
            f"{self.base_url}/laws/card/{encoded_nreg_full}.json",
            f"{self.base_url}/laws/show/{encoded_nreg_full}.json",
            # Try without .json extension (some APIs return JSON by default)
            f"{self.base_url}/laws/card/{encoded_nreg}",
            f"{self.base_url}/laws/show/{encoded_nreg}",
        ]
        
        headers_with_token = self._get_headers(use_token=True)
        headers_no_token = self._get_headers(use_token=False)
        
        for url in url_formats:
            try:
                async with httpx.AsyncClient() as client:
                    # Try with token first
                    logger.debug(f"Trying URL: {url} (with token)")
                    response = await client.get(url, headers=headers_with_token, timeout=30.0)
                    
                    if response.status_code == 200:
                        content_type = response.headers.get("content-type", "").lower()
                        
                        # Check if it's actually JSON
                        if "application/json" in content_type or "text/json" in content_type:
                            try:
                                data = response.json()
                                if data and isinstance(data, dict):
                                    logger.info(f"Successfully retrieved JSON for {nreg} from {url}")
                                    return data
                            except json.JSONDecodeError:
                                logger.debug(f"Response from {url} is not valid JSON")
                        
                        # If HTML is returned, skip this URL format
                        if "text/html" in content_type:
                            logger.debug(f"URL {url} returned HTML, trying next format")
                            continue
                    
                    # If 403, try without token
                    elif response.status_code == 403:
                        logger.debug(f"Got 403 for {url}, trying without token")
                        response2 = await client.get(url, headers=headers_no_token, timeout=30.0)
                        if response2.status_code == 200:
                            content_type2 = response2.headers.get("content-type", "").lower()
                            if "application/json" in content_type2 or "text/json" in content_type2:
                                try:
                                    data = response2.json()
                                    if data and isinstance(data, dict):
                                        logger.info(f"Successfully retrieved JSON for {nreg} from {url} (no token)")
                                        return data
                                except json.JSONDecodeError:
                                    pass
                    
                    # If 404, try next format
                    elif response.status_code == 404:
                        logger.debug(f"URL {url} returned 404, trying next format")
                        continue
                    
            except Exception as e:
                logger.debug(f"Error trying {url}: {e}")
                continue
        
        # If all URL formats failed, try text format as fallback
        logger.info(f"All JSON URL formats failed for {nreg}, trying text format as fallback...")
        try:
            text = await self.get_document_text(nreg)
            if text:
                logger.info(f"Successfully retrieved text for {nreg}, creating minimal JSON structure")
                # Extract title from text (first line or first 200 chars)
                title = nreg
                if text:
                    lines = text.split('\n')
                    for line in lines[:10]:  # Check first 10 lines
                        line = line.strip()
                        if line and len(line) > 10 and len(line) < 200:
                            # Likely a title
                            title = line
                            break
                    if title == nreg and len(text) > 0:
                        # Use first 100 chars as title
                        title = text[:100].replace('\n', ' ').strip()
                
                return {
                    "nreg": nreg,
                    "title": title,
                    "text": text,
                    "source": "text_fallback"
                }
        except Exception as e:
            logger.debug(f"Text format also failed: {e}")
        
        # Last resort: check if document exists in list (but don't fetch full list for single check)
        logger.warning(f"Could not retrieve JSON or text for {nreg} using any URL format")
        return None
    
    async def get_document_card(self, nreg: str) -> Optional[Dict[str, Any]]:
        """
        Get document card in JSON format
        Uses the same multi-format approach as get_document_json
        """
        # Card endpoint is already tried first in get_document_json
        # So we can reuse that logic
        result = await self.get_document_json(nreg)
        if result:
            return result
        
        # If get_document_json failed, try card endpoint specifically
        await self._rate_limit()
        
        try:
            async with httpx.AsyncClient() as client:
                from urllib.parse import quote
                if '/' in nreg:
                    parts = nreg.split('/')
                    encoded_parts = [quote(part, safe='') for part in parts]
                    encoded_nreg = '/'.join(encoded_parts)
                else:
                    encoded_nreg = quote(nreg, safe='')
                
                url = f"{self.base_url}/laws/card/{encoded_nreg}.json"
                headers = self._get_headers(use_token=True)
                
                logger.debug(f"Requesting card: original nreg={nreg}, encoded={encoded_nreg}, url={url}")
                response = await client.get(url, headers=headers, timeout=30.0)
                
                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "").lower()
                    if "application/json" in content_type or "text/json" in content_type:
                        try:
                            return response.json()
                        except:
                            pass
                
                logger.warning(f"Card for {nreg} not found: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Exception getting card {nreg}: {e}")
            return None
    
    async def get_document_text(self, nreg: str) -> Optional[str]:
        """Get document as plain text"""
        await self._rate_limit()
        
        try:
            async with httpx.AsyncClient() as client:
                # URL encode the nreg properly (same as get_document_json)
                from urllib.parse import quote
                if '/' in nreg:
                    parts = nreg.split('/')
                    encoded_parts = [quote(part, safe='') for part in parts]
                    encoded_nreg = '/'.join(encoded_parts)
                else:
                    encoded_nreg = quote(nreg, safe='')
                
                url = f"{self.base_url}/laws/show/{encoded_nreg}.txt"
                headers = self._get_headers(use_token=False)  # TXT doesn't need token
                
                logger.debug(f"Requesting text: original nreg={nreg}, encoded={encoded_nreg}, url={url}")
                response = await client.get(url, headers=headers, timeout=60.0)
                
                if response.status_code == 200:
                    return response.text
                else:
                    logger.warning(f"Text for {nreg} not found: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Exception getting text {nreg}: {e}")
            return None
    
    async def get_updated_documents_list(self) -> List[str]:
        """Get list of updated document nregs"""
        await self._rate_limit()
        
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/laws/main/r"
                headers = self._get_headers(use_token=False)
                
                response = await client.get(url, headers=headers, timeout=30.0)
                
                if response.status_code == 200:
                    # Парсимо HTML для отримання списку nreg
                    # Це спрощена версія, може знадобитися більш складний парсинг
                    import re
                    nregs = re.findall(r'/laws/show/([^"]+)', response.text)
                    return list(set(nregs))
                else:
                    logger.error(f"Error getting updated list: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Exception getting updated list: {e}")
            return []
    
    async def get_new_documents_list(self, days: int = 30) -> List[str]:
        """Get list of new document nregs"""
        await self._rate_limit()
        
        try:
            async with httpx.AsyncClient() as client:
                if days == 1:
                    url = f"{self.base_url}/laws/main/nn"  # За день
                else:
                    url = f"{self.base_url}/laws/main/n"  # За 30 днів
                
                headers = self._get_headers(use_token=False)
                response = await client.get(url, headers=headers, timeout=30.0, follow_redirects=True)
                
                if response.status_code == 200:
                    import re
                    from bs4 import BeautifulSoup
                    from urllib.parse import unquote
                    
                    # Try BeautifulSoup first
                    soup = BeautifulSoup(response.text, 'html.parser')
                    nregs = []
                    
                    # Find all links to /laws/show/{nreg}
                    for link in soup.find_all('a', href=True):
                        href = link.get('href', '')
                        if '/laws/show/' in href:
                            match = re.search(r'/laws/show/([^"\s<>\.\?&#]+)', href)
                            if match:
                                nreg = match.group(1)
                                nreg = nreg.replace('.json', '').replace('.txt', '').replace('.html', '')
                                if '?' in nreg:
                                    nreg = nreg.split('?')[0]
                                if nreg and nreg not in nregs:
                                    try:
                                        decoded = unquote(nreg)
                                        nregs.append(decoded)
                                    except:
                                        nregs.append(nreg)
                    
                    # Fallback to regex if BeautifulSoup didn't find anything
                    if not nregs:
                        nregs = re.findall(r'/laws/show/([^"\s<>\.\?&#]+)', response.text)
                        # Decode and clean
                        decoded_nregs = []
                        for nreg in nregs:
                            try:
                                decoded = unquote(nreg)
                                decoded = decoded.replace('.json', '').replace('.txt', '').replace('.html', '')
                                if '?' in decoded:
                                    decoded = decoded.split('?')[0]
                                if decoded and decoded not in decoded_nregs:
                                    decoded_nregs.append(decoded)
                            except:
                                if nreg not in decoded_nregs:
                                    decoded_nregs.append(nreg)
                        nregs = decoded_nregs
                    
                    logger.info(f"Found {len(nregs)} documents from new documents list")
                    return list(set(nregs))  # Remove duplicates
                else:
                    logger.error(f"Error getting new list: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Exception getting new list: {e}", exc_info=True)
            return []
    
    async def get_all_documents_list(self, limit: Optional[int] = None) -> List[str]:
        """
        Get list of all document nregs from Rada API
        Tries multiple endpoints and methods to get the document list
        """
        all_nregs = []
        
        # Try different endpoints
        endpoints_to_try = [
            "/laws/main/r",  # Main listing page
            "/laws/main",    # Alternative main page
            "/laws",         # Laws root
        ]
        
        try:
            for endpoint in endpoints_to_try:
                logger.info(f"Trying endpoint: {endpoint}")
                await self._rate_limit()
                
                async with httpx.AsyncClient() as client:
                    url = f"{self.base_url}{endpoint}"
                    headers = self._get_headers(use_token=False)
                    response = await client.get(url, headers=headers, timeout=60.0, follow_redirects=True)
                    
                    if response.status_code == 200:
                        import re
                        from urllib.parse import unquote
                        from bs4 import BeautifulSoup
                        
                        # Parse HTML with BeautifulSoup for more reliable extraction
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Find all links to /laws/show/{nreg}
                        page_nregs = []
                        
                        # Method 1: Find all <a> tags with href containing /laws/show/
                        for link in soup.find_all('a', href=True):
                            href = link.get('href', '')
                            # Try both absolute and relative URLs
                            if '/laws/show/' in href or href.startswith('/laws/show/'):
                                # Extract NREG from href
                                match = re.search(r'/laws/show/([^"\s<>\.\?&#]+)', href)
                                if match:
                                    nreg = match.group(1)
                                    # Remove .json, .txt, .html extensions if present
                                    nreg = nreg.replace('.json', '').replace('.txt', '').replace('.html', '')
                                    # Remove query parameters
                                    if '?' in nreg:
                                        nreg = nreg.split('?')[0]
                                    if nreg and nreg not in page_nregs:
                                        page_nregs.append(nreg)
                        
                        # Method 2: Also check for data attributes or other patterns
                        # Some sites use data-nreg or similar attributes
                        for element in soup.find_all(attrs={'data-nreg': True}):
                            nreg = element.get('data-nreg')
                            if nreg and nreg not in page_nregs:
                                page_nregs.append(nreg)
                        
                        # Method 3: Regex fallback if BeautifulSoup didn't find anything
                        if not page_nregs:
                            # Try more flexible regex patterns
                            patterns = [
                                r'/laws/show/([^"\s<>\.\?&#]+)',  # Original pattern
                                r'/laws/show/([^"\s<>]+)',  # More permissive
                                r'href=["\']/laws/show/([^"\']+)["\']',  # With quotes
                                r'href=["\']https?://[^"\']*?/laws/show/([^"\']+)["\']',  # Full URL
                            ]
                            
                            for pattern in patterns:
                                matches = re.findall(pattern, response.text)
                                if matches:
                                    for match in matches:
                                        nreg = match.replace('.json', '').replace('.txt', '').replace('.html', '')
                                        if '?' in nreg:
                                            nreg = nreg.split('?')[0]
                                        if nreg and nreg not in page_nregs:
                                            page_nregs.append(nreg)
                                    if page_nregs:
                                        break
                        
                        if page_nregs:
                            logger.info(f"Found {len(page_nregs)} documents on {endpoint}")
                            all_nregs.extend(page_nregs)
                            break  # Success, no need to try other endpoints
                        else:
                            # Log more details for debugging
                            logger.warning(f"No documents found on {endpoint}")
                            # Count total links found
                            all_links = soup.find_all('a', href=True)
                            logger.info(f"Total <a> tags found: {len(all_links)}")
                            # Log sample hrefs
                            sample_hrefs = [link.get('href', '')[:100] for link in all_links[:10]]
                            logger.info(f"Sample hrefs: {sample_hrefs}")
                            
                            # Try to find any pattern that might contain NREG
                            # Look for common patterns in the HTML
                            import re
                            # Try to find any text that looks like NREG (e.g., "254к/96-ВР", "123/2023")
                            nreg_patterns = [
                                r'\b\d+[кК]?/\d+-?[ВВРР]?\b',  # Pattern like 254к/96-ВР
                                r'\b\d+/\d+\b',  # Simple pattern like 123/2023
                            ]
                            for pattern in nreg_patterns:
                                matches = re.findall(pattern, response.text)
                                if matches:
                                    logger.info(f"Found potential NREG patterns: {matches[:10]}")
                                    break
                            
                            # Log a snippet of the HTML to see structure
                            html_snippet = response.text[:2000] if len(response.text) > 2000 else response.text
                            logger.debug(f"HTML snippet (first 2000 chars): {html_snippet}")
                            
                            # If this is the first endpoint and we got HTML, try pagination
                            if endpoint == "/laws/main/r" and len(response.text) > 1000:
                                # Try pagination
                                logger.info("Trying pagination on /laws/main/r")
                                await self._try_pagination(client, headers, all_nregs, limit)
                                if all_nregs:
                                    break
                    else:
                        logger.warning(f"Endpoint {endpoint} returned status {response.status_code}")
            
            if not all_nregs:
                logger.error("No documents found on any endpoint. This might indicate:")
                logger.error("1. The website structure has changed")
                logger.error("2. Rate limiting is blocking requests")
                logger.error("3. Authentication is required")
                
                # Fallback: Try to use get_new_documents_list as alternative
                logger.info("Trying fallback: get_new_documents_list (new documents)")
                try:
                    new_nregs = await self.get_new_documents_list(days=365)  # Get all new from last year
                    if new_nregs:
                        logger.info(f"Fallback successful: found {len(new_nregs)} documents from new documents list")
                        # Apply limit if specified
                        if limit and len(new_nregs) > limit:
                            new_nregs = new_nregs[:limit]
                        return new_nregs
                except Exception as e:
                    logger.error(f"Fallback also failed: {e}")
                
                return []
            
            # Remove duplicates but preserve order (as they appear on the site)
            seen = set()
            unique_nregs = []
            for nreg in all_nregs:
                try:
                    from urllib.parse import unquote
                    decoded = unquote(nreg)
                    if decoded not in seen:
                        seen.add(decoded)
                        unique_nregs.append(decoded)
                except Exception:
                    if nreg not in seen:
                        seen.add(nreg)
                        unique_nregs.append(nreg)
            
            # Apply limit if specified
            if limit and len(unique_nregs) > limit:
                unique_nregs = unique_nregs[:limit]
                logger.info(f"Limited to {limit} documents")
            
            logger.info(f"Total unique documents found: {len(unique_nregs)}")
            return unique_nregs
            
        except Exception as e:
            logger.error(f"Exception getting all documents list: {e}", exc_info=True)
            return []
    
    async def _try_pagination(self, client: httpx.AsyncClient, headers: Dict[str, str], all_nregs: List[str], limit: Optional[int] = None):
        """Try to get documents using pagination"""
        page = 1
        max_pages = 10  # Limit pagination attempts
        
        while page <= max_pages:
            await self._rate_limit()
            
            url = f"{self.base_url}/laws/main/r"
            if page > 1:
                url = f"{self.base_url}/laws/main/r?page={page}"
            
            try:
                response = await client.get(url, headers=headers, timeout=60.0, follow_redirects=True)
                
                if response.status_code == 200:
                    from bs4 import BeautifulSoup
                    import re
                    from urllib.parse import unquote
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    page_nregs = []
                    
                    for link in soup.find_all('a', href=True):
                        href = link.get('href', '')
                        if '/laws/show/' in href:
                            match = re.search(r'/laws/show/([^"\s<>\.\?&#]+)', href)
                            if match:
                                nreg = match.group(1).replace('.json', '').replace('.txt', '').replace('.html', '')
                                if '?' in nreg:
                                    nreg = nreg.split('?')[0]
                                if nreg and nreg not in all_nregs and nreg not in page_nregs:
                                    page_nregs.append(nreg)
                    
                    if not page_nregs:
                        logger.info(f"No more documents on page {page}")
                        break
                    
                    # Decode and add
                    for nreg in page_nregs:
                        try:
                            decoded = unquote(nreg)
                            if decoded not in all_nregs:
                                all_nregs.append(decoded)
                        except Exception:
                            if nreg not in all_nregs:
                                all_nregs.append(nreg)
                    
                    logger.info(f"Page {page}: found {len(page_nregs)} documents (total: {len(all_nregs)})")
                    
                    if limit and len(all_nregs) >= limit:
                        break
                    
                    page += 1
                elif response.status_code == 404:
                    logger.info(f"No more pages (404 on page {page})")
                    break
                else:
                    logger.warning(f"Error on page {page}: {response.status_code}")
                    break
            except Exception as e:
                logger.error(f"Error fetching page {page}: {e}")
                break


# Singleton instance
rada_api = RadaAPIService()


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
        self.open_data_dataset_id = settings.RADA_OPEN_DATA_DATASET_ID
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
        Get list of ALL document nregs from Rada API
        Uses multiple strategies: open data API, pagination, new/updated lists
        """
        all_nregs = []
        seen_nregs = set()
        
        try:
            # Strategy 1: Try open data portal API first (fastest and most reliable)
            try:
                logger.info("Strategy 1: Trying open data portal API...")
                open_data_nregs = await self.get_all_nregs_from_open_data()
                if open_data_nregs and len(open_data_nregs) > 0:
                    logger.info(f"✅ Strategy 1 successful: found {len(open_data_nregs)} documents from open data portal")
                    if limit and len(open_data_nregs) > limit:
                        return open_data_nregs[:limit]
                    return open_data_nregs
            except Exception as e:
                logger.warning(f"Strategy 1 (open data API) failed: {e}")
            
            # Strategy 2: Use pagination to get all documents
            # Start with /laws/main/r and paginate through all pages
            logger.info("Strategy 2: Trying pagination method...")
            page = 1
            max_pages = 1000  # Safety limit
            consecutive_empty_pages = 0
            max_consecutive_empty = 3  # Stop after 3 empty pages in a row
            
            async with httpx.AsyncClient() as client:
                while page <= max_pages:
                    await self._rate_limit()
                    
                    # Try different URL formats for pagination
                    # API might use different pagination formats
                    if page == 1:
                        # Try multiple first page formats
                        urls_to_try = [
                            f"{self.base_url}/laws/main/r",
                            f"{self.base_url}/laws/main",
                            f"{self.base_url}/laws",
                        ]
                    else:
                        # Try different pagination formats
                        urls_to_try = [
                            f"{self.base_url}/laws/main/r?page={page}",
                            f"{self.base_url}/laws/main/r/{page}",
                            f"{self.base_url}/laws/main?page={page}",
                            f"{self.base_url}/laws?page={page}",
                        ]
                    
                    # Use first URL for now, but log all options
                    url = urls_to_try[0]
                    if page == 1 and len(urls_to_try) > 1:
                        logger.debug(f"Page {page}: Will try URLs: {urls_to_try}")
                    
                    headers = self._get_headers(use_token=False)
                    logger.info(f"Fetching page {page} from {url}")
                    
                    try:
                        response = await client.get(url, headers=headers, timeout=60.0, follow_redirects=True)
                        
                        if response.status_code == 200:
                            import re
                            from urllib.parse import unquote
                            from bs4 import BeautifulSoup
                            
                            # Log response length for debugging
                            response_length = len(response.text)
                            logger.debug(f"Page {page}: Response length: {response_length} bytes")
                            
                            # Check if response is actually HTML
                            if response_length < 100:
                                logger.warning(f"Page {page}: Response too short ({response_length} bytes), might be empty or error")
                            
                            soup = BeautifulSoup(response.text, 'html.parser')
                            page_nregs = []
                            
                            # Method 1: Find all <a> tags with href containing /laws/show/
                            links_found = 0
                            for link in soup.find_all('a', href=True):
                                href = link.get('href', '')
                                if '/laws/show/' in href:
                                    links_found += 1
                                    match = re.search(r'/laws/show/([^"\s<>\.\?&#]+)', href)
                                    if match:
                                        nreg = match.group(1)
                                        nreg = nreg.replace('.json', '').replace('.txt', '').replace('.html', '')
                                        if '?' in nreg:
                                            nreg = nreg.split('?')[0]
                                        if nreg:
                                            try:
                                                decoded = unquote(nreg)
                                                if decoded not in seen_nregs:
                                                    seen_nregs.add(decoded)
                                                    page_nregs.append(decoded)
                                            except:
                                                if nreg not in seen_nregs:
                                                    seen_nregs.add(nreg)
                                                    page_nregs.append(nreg)
                            
                            logger.debug(f"Page {page}: Found {links_found} links with /laws/show/, extracted {len(page_nregs)} unique nregs")
                            
                            # Method 2: Regex fallback (more aggressive)
                            if not page_nregs:
                                # Try multiple regex patterns
                                patterns = [
                                    r'/laws/show/([^"\s<>\.\?&#]+)',
                                    r'/laws/show/([^/]+)',
                                    r'href=["\']([^"\']*laws/show/([^"\']+))',
                                    r'"/laws/show/([^"]+)"',
                                ]
                                
                                for pattern in patterns:
                                    matches = re.findall(pattern, response.text)
                                    if matches:
                                        logger.debug(f"Page {page}: Regex pattern '{pattern}' found {len(matches)} matches")
                                        for match in matches:
                                            # Handle tuple matches (from groups)
                                            if isinstance(match, tuple):
                                                nreg = match[-1]  # Take last group
                                            else:
                                                nreg = match
                                            
                                            nreg = nreg.replace('.json', '').replace('.txt', '').replace('.html', '')
                                            if '?' in nreg:
                                                nreg = nreg.split('?')[0]
                                            if nreg and len(nreg) > 2:  # Filter out too short matches
                                                try:
                                                    decoded = unquote(nreg)
                                                    if decoded not in seen_nregs:
                                                        seen_nregs.add(decoded)
                                                        page_nregs.append(decoded)
                                                except:
                                                    if nreg not in seen_nregs:
                                                        seen_nregs.add(nreg)
                                                        page_nregs.append(nreg)
                                        
                                        if page_nregs:
                                            break  # Stop if we found something
                                
                                if not page_nregs:
                                    # Log sample of response for debugging
                                    sample = response.text[:500] if len(response.text) > 500 else response.text
                                    logger.warning(f"Page {page}: No nregs found. Response sample: {sample[:200]}...")
                            
                            if page_nregs:
                                all_nregs.extend(page_nregs)
                                logger.info(f"Page {page}: Found {len(page_nregs)} new documents (total: {len(all_nregs)})")
                                consecutive_empty_pages = 0
                                
                                # Check limit
                                if limit and len(all_nregs) >= limit:
                                    all_nregs = all_nregs[:limit]
                                    logger.info(f"Reached limit of {limit} documents")
                                    break
                            else:
                                consecutive_empty_pages += 1
                                logger.info(f"Page {page}: No documents found (consecutive empty: {consecutive_empty_pages})")
                                
                                if consecutive_empty_pages >= max_consecutive_empty:
                                    logger.info(f"Stopping after {consecutive_empty_pages} consecutive empty pages")
                                    break
                            
                            page += 1
                            
                        elif response.status_code == 404:
                            logger.info(f"Page {page} returned 404, no more pages")
                            break
                        else:
                            logger.warning(f"Page {page} returned status {response.status_code}")
                            consecutive_empty_pages += 1
                            if consecutive_empty_pages >= max_consecutive_empty:
                                break
                            page += 1
                            
                    except Exception as e:
                        logger.error(f"Error fetching page {page}: {e}")
                        consecutive_empty_pages += 1
                        if consecutive_empty_pages >= max_consecutive_empty:
                            break
                        page += 1
                        continue
            
            if not all_nregs:
                logger.warning("No documents found with pagination, trying fallback methods...")
                
                # Fallback 1: Try open data portal API (preferred method)
                try:
                    logger.info("Fallback: Trying open data portal API...")
                    open_data_nregs = await self.get_all_nregs_from_open_data()
                    if open_data_nregs:
                        logger.info(f"✅ Fallback successful: found {len(open_data_nregs)} documents from open data portal")
                        if limit and len(open_data_nregs) > limit:
                            open_data_nregs = open_data_nregs[:limit]
                        return open_data_nregs
                except Exception as e:
                    logger.warning(f"Fallback open data portal failed: {e}")
                
                # Fallback 2: Try get_new_documents_list with different time ranges
                for days in [365, 730, 1095]:  # Try 1 year, 2 years, 3 years
                    try:
                        logger.info(f"Fallback: Trying get_new_documents_list with {days} days")
                        new_nregs = await self.get_new_documents_list(days=days)
                        if new_nregs:
                            logger.info(f"Fallback successful: found {len(new_nregs)} documents from new documents list ({days} days)")
                            if limit and len(new_nregs) > limit:
                                new_nregs = new_nregs[:limit]
                            return new_nregs
                    except Exception as e:
                        logger.warning(f"Fallback get_new_documents_list ({days} days) failed: {e}")
                        continue
                
                # Fallback 3: Try get_updated_documents_list
                try:
                    logger.info("Fallback: Trying get_updated_documents_list")
                    updated_nregs = await self.get_updated_documents_list()
                    if updated_nregs:
                        logger.info(f"Fallback successful: found {len(updated_nregs)} documents from updated documents list")
                        if limit and len(updated_nregs) > limit:
                            updated_nregs = updated_nregs[:limit]
                        return updated_nregs
                except Exception as e:
                    logger.warning(f"Fallback get_updated_documents_list failed: {e}")
                
                logger.error("All fallback methods failed. Cannot retrieve document list from Rada API.")
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
    
    async def get_open_data_catalog(self) -> Optional[Dict[str, Any]]:
        """
        Get catalog of open data datasets from https://data.rada.gov.ua/ogd/
        Returns catalog metadata in JSON format
        """
        await self._rate_limit()
        
        try:
            async with httpx.AsyncClient() as client:
                # Try to get catalog in JSON format
                # The catalog might be at /ogd/ or /open/main/registry
                catalog_urls = [
                    "https://data.rada.gov.ua/ogd/registry.json",
                    "https://data.rada.gov.ua/open/main/registry.json",
                    "https://data.rada.gov.ua/ogd/catalog.json",
                ]
                
                headers = self._get_headers(use_token=False)
                
                for url in catalog_urls:
                    try:
                        logger.info(f"Trying to fetch catalog from {url}")
                        response = await client.get(url, headers=headers, timeout=30.0, follow_redirects=True)
                        
                        if response.status_code == 200:
                            content_type = response.headers.get("content-type", "").lower()
                            if "application/json" in content_type or "text/json" in content_type:
                                data = response.json()
                                logger.info(f"Successfully fetched catalog from {url}")
                                return data
                    except Exception as e:
                        logger.debug(f"Failed to fetch from {url}: {e}")
                        continue
                
                logger.warning("Could not fetch catalog in JSON format, trying HTML parsing")
                return None
        except Exception as e:
            logger.error(f"Error fetching open data catalog: {e}")
            return None
    
    async def get_open_data_dataset(self, dataset_id: str, format: str = "json") -> Optional[Dict[str, Any]]:
        """
        Get specific dataset from open data portal
        Format: json, csv, xml
        
        Supports multiple URL patterns:
        - https://data.rada.gov.ua/open/data/{dataset_id}.{format}
        - https://data.rada.gov.ua/ogd/zak/{dataset_id}/list.{format}
        """
        await self._rate_limit()
        
        try:
            async with httpx.AsyncClient() as client:
                # Try multiple URL patterns
                urls_to_try = [
                    f"https://data.rada.gov.ua/open/data/{dataset_id}.{format}",
                    f"https://data.rada.gov.ua/ogd/zak/{dataset_id}/list.{format}",
                    f"https://data.rada.gov.ua/ogd/zak/{dataset_id}.{format}",
                ]
                
                headers = self._get_headers(use_token=False)
                
                for url in urls_to_try:
                    try:
                        logger.debug(f"Trying to fetch dataset from {url}")
                        
                        # Add If-Modified-Since header if we have cached version
                        # (for future optimization)
                        
                        response = await client.get(url, headers=headers, timeout=60.0, follow_redirects=True)
                        
                        if response.status_code == 200:
                            if format == "json":
                                data = response.json()
                                logger.info(f"✅ Successfully fetched dataset {dataset_id} from {url}")
                                return data
                            elif format == "csv":
                                import csv
                                import io
                                # Parse CSV to list of dicts
                                text = response.text
                                reader = csv.DictReader(io.StringIO(text))
                                data = list(reader)
                                logger.info(f"✅ Successfully fetched dataset {dataset_id} from {url}")
                                return data
                            elif format == "xml":
                                # Return raw XML text for now
                                logger.info(f"✅ Successfully fetched dataset {dataset_id} from {url}")
                                return {"xml": response.text}
                            else:
                                logger.info(f"✅ Successfully fetched dataset {dataset_id} from {url}")
                                return {"text": response.text}
                        elif response.status_code == 304:
                            logger.info(f"Dataset {dataset_id} not modified (304)")
                            return None
                        elif response.status_code == 404:
                            logger.debug(f"URL {url} returned 404, trying next URL...")
                            continue
                        else:
                            logger.warning(f"URL {url} returned status {response.status_code}")
                            continue
                    except Exception as e:
                        logger.debug(f"Error fetching from {url}: {e}, trying next URL...")
                        continue
                
                logger.warning(f"Failed to fetch dataset {dataset_id} from all tried URLs")
                return None
        except Exception as e:
            logger.error(f"Error fetching dataset {dataset_id}: {e}")
            return None
    
    async def find_legal_acts_dataset_id(self) -> Optional[str]:
        """
        Find the dataset ID for legal acts database
        Searches in catalog for dataset containing legal acts
        """
        # Try multiple catalog URLs
        catalog_urls = [
            "https://data.rada.gov.ua/ogd/",
            "https://data.rada.gov.ua/open/main/",
            "https://data.rada.gov.ua/open/data/",
        ]
        
        keywords = ["законодавство", "нормативно-правові", "нпа", "закони", "база даних", "legal", "acts"]
        
        # First, try to get JSON catalog
        catalog = await self.get_open_data_catalog()
        
        if isinstance(catalog, dict):
            # Search for datasets with legal acts keywords
            datasets = (catalog.get("datasets", []) or 
                       catalog.get("data", []) or 
                       catalog.get("results", []) or
                       catalog.get("items", []) or [])
            
            logger.info(f"Searching in {len(datasets)} datasets from JSON catalog")
            
            for dataset in datasets:
                title = str(dataset.get("title", "") or dataset.get("name", "")).lower()
                description = str(dataset.get("description", "") or "").lower()
                
                if any(keyword in title or keyword in description for keyword in keywords):
                    dataset_id = (dataset.get("id") or 
                                 dataset.get("guid") or 
                                 dataset.get("identifier") or
                                 dataset.get("dataset_id"))
                    if dataset_id:
                        logger.info(f"✅ Found legal acts dataset ID: {dataset_id} (title: {title[:50]})")
                        return str(dataset_id)
        
        # If JSON catalog didn't work, try HTML parsing
        logger.info("JSON catalog search failed, trying HTML parsing...")
        for url in catalog_urls:
            await self._rate_limit()
            try:
                async with httpx.AsyncClient() as client:
                    headers = self._get_headers(use_token=False)
                    response = await client.get(url, headers=headers, timeout=30.0, follow_redirects=True)
                    
                    if response.status_code == 200:
                        from bs4 import BeautifulSoup
                        import re
                        
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Look for links to legal acts datasets
                        for link in soup.find_all('a', href=True):
                            href = link.get('href', '')
                            text = link.get_text().lower()
                            
                            # Check if link contains dataset ID and text matches keywords
                            if any(keyword in text for keyword in keywords):
                                # Try different URL patterns
                                patterns = [
                                    r'/open/data/(\d+)',
                                    r'/data/(\d+)',
                                    r'id[=:](\d+)',
                                    r'dataset[=:](\d+)',
                                ]
                                
                                for pattern in patterns:
                                    match = re.search(pattern, href)
                                    if match:
                                        dataset_id = match.group(1)
                                        logger.info(f"✅ Found potential legal acts dataset ID: {dataset_id} (from {url}, link: {text[:50]})")
                                        return dataset_id
            except Exception as e:
                logger.debug(f"Error searching {url}: {e}")
                continue
        
        logger.warning("❌ Could not find legal acts dataset ID in catalog. You may need to specify RADA_OPEN_DATA_DATASET_ID manually.")
        return None
    
    async def get_all_nregs_from_open_data(self, dataset_id: Optional[str] = None, limit: Optional[int] = None) -> List[str]:
        """
        Get all NREG identifiers from open data portal
        This is the preferred method as it uses structured API
        
        Args:
            dataset_id: Dataset ID (e.g., "laws", "docs", "dict"). If None, will try to find automatically
            limit: Optional limit on number of NREGs to return
        """
        if not dataset_id:
            # Try configured dataset ID first
            dataset_id = self.open_data_dataset_id
        
        if not dataset_id:
            logger.info("Dataset ID not provided, searching for legal acts dataset...")
            dataset_id = await self.find_legal_acts_dataset_id()
        
        if not dataset_id:
            logger.error("Could not find legal acts dataset ID")
            return []
        
        logger.info(f"Fetching legal acts from open data portal, dataset ID: {dataset_id}")
        
        # Special handling for "laws" registry - it contains sub-datasets
        # The actual documents are in "docs" sub-dataset
        if dataset_id == "laws":
            logger.info("Dataset 'laws' is a registry. Trying to fetch from 'docs' sub-dataset...")
            # Try "docs" sub-dataset which contains document cards
            docs_dataset = await self.get_open_data_dataset("docs", format="json")
            if docs_dataset:
                nregs = self._extract_nregs_from_dataset(docs_dataset)
                if nregs:
                    logger.info(f"✅ Successfully extracted {len(nregs)} NREGs from 'docs' dataset")
                    if limit and len(nregs) > limit:
                        return nregs[:limit]
                    return nregs
        
        # Try JSON format first
        dataset = await self.get_open_data_dataset(dataset_id, format="json")
        
        if dataset:
            nregs = self._extract_nregs_from_dataset(dataset)
            if nregs:
                logger.info(f"Found {len(nregs)} NREG identifiers from open data portal")
                if limit and len(nregs) > limit:
                    return nregs[:limit]
                return nregs
        
        # Fallback to CSV if JSON didn't work
        logger.info("JSON format didn't work, trying CSV...")
        dataset_csv = await self.get_open_data_dataset(dataset_id, format="csv")
        
        if dataset_csv:
            nregs = self._extract_nregs_from_dataset(dataset_csv)
            if nregs:
                logger.info(f"Found {len(nregs)} NREG identifiers from CSV format")
                if limit and len(nregs) > limit:
                    return nregs[:limit]
                return nregs
        
        logger.warning("Could not extract NREG identifiers from open data dataset")
        return []
    
    async def get_all_documents_from_dataset(self, dataset_id: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get ALL documents from open data dataset without filtering by NREG
        Returns full document records with all available fields
        
        Args:
            dataset_id: Dataset ID (e.g., "laws", "docs", "dict"). If None, will try to find automatically
            limit: Optional limit on number of documents to return
        
        Returns:
            List of document dictionaries with all fields from dataset
        """
        if not dataset_id:
            # Try configured dataset ID first
            dataset_id = self.open_data_dataset_id
        
        if not dataset_id:
            logger.info("Dataset ID not provided, searching for legal acts dataset...")
            dataset_id = await self.find_legal_acts_dataset_id()
        
        if not dataset_id:
            logger.error("Could not find legal acts dataset ID")
            return []
        
        logger.info(f"Fetching all documents from open data portal, dataset ID: {dataset_id}")
        
        # Special handling for "laws" registry - it contains sub-datasets
        if dataset_id == "laws":
            logger.info("Dataset 'laws' is a registry. Trying to fetch from 'docs' sub-dataset...")
            docs_dataset = await self.get_open_data_dataset("docs", format="json")
            if docs_dataset:
                documents = self._extract_all_documents_from_dataset(docs_dataset)
                if documents:
                    logger.info(f"✅ Successfully extracted {len(documents)} documents from 'docs' dataset")
                    if limit and len(documents) > limit:
                        return documents[:limit]
                    return documents
        
        # Try JSON format first
        dataset = await self.get_open_data_dataset(dataset_id, format="json")
        
        if dataset:
            documents = self._extract_all_documents_from_dataset(dataset)
            if documents:
                logger.info(f"Found {len(documents)} documents from open data portal")
                if limit and len(documents) > limit:
                    return documents[:limit]
                return documents
        
        # Fallback to CSV if JSON didn't work
        logger.info("JSON format didn't work, trying CSV...")
        dataset_csv = await self.get_open_data_dataset(dataset_id, format="csv")
        
        if dataset_csv:
            documents = self._extract_all_documents_from_dataset(dataset_csv)
            if documents:
                logger.info(f"Found {len(documents)} documents from CSV format")
                if limit and len(documents) > limit:
                    return documents[:limit]
                return documents
        
        logger.warning("Could not extract documents from open data dataset")
        return []
    
    def _extract_all_documents_from_dataset(self, dataset: Any) -> List[Dict[str, Any]]:
        """
        Extract ALL documents from dataset structure without filtering
        Returns full document records with all available fields
        
        Args:
            dataset: Dataset structure (list, dict, etc.)
        
        Returns:
            List of document dictionaries
        """
        documents = []
        
        # Extract documents from dataset
        items_to_process = []
        
        if isinstance(dataset, list):
            items_to_process = dataset
        elif isinstance(dataset, dict):
            # Try common keys that might contain list of documents
            for key in ["data", "items", "results", "documents", "acts", "docs", "list", "records"]:
                if key in dataset and isinstance(dataset[key], list):
                    items_to_process = dataset[key]
                    break
            
            # If no list found, the dict itself might be a single document
            if not items_to_process and len(dataset) > 0:
                # Check if it looks like a document (has common fields)
                if any(key in dataset for key in ["nreg", "NREG", "title", "name", "id", "number"]):
                    items_to_process = [dataset]
        
        # Process all items as documents
        for idx, item in enumerate(items_to_process):
            if isinstance(item, dict):
                # Keep all fields from the document - don't require NREG
                # NREG will be generated in API layer if needed
                # Just preserve any existing identifier fields
                pass  # Keep document as-is, no NREG extraction here
                
                # Add dataset metadata
                item["_dataset_id"] = getattr(self, 'open_data_dataset_id', None)
                item["_source"] = "open_data"
                
                documents.append(item)
        
        logger.info(f"Extracted {len(documents)} documents from dataset")
        return documents
    
    def _is_valid_nreg(self, nreg: str) -> bool:
        """
        Validate NREG format
        Valid NREG should contain '/' or '-' (typical Ukrainian format like 254к/96-вр)
        Exclude common invalid patterns like 'links-code', 'doc-dates', etc.
        """
        if not nreg or len(nreg) < 3:
            return False
        
        nreg_lower = nreg.lower()
        
        # Exclude common invalid patterns
        invalid_patterns = [
            'links-code', 'doc-dates', 'dict', 'proj', 'docs',
            'links', 'dates', 'code', 'id', 'guid', 'identifier',
            'ist', 'public', 'private', 'static', 'class', 'def',
            'list', 'data', 'items', 'results', 'documents', 'acts'
        ]
        
        if nreg_lower in invalid_patterns:
            return False
        
        # Exclude single words that are too short or look like code keywords
        if len(nreg) <= 3 and nreg.isalpha():
            return False
        
        # Valid NREG should contain '/' or '-' (typical format: 254к/96-вр)
        if '/' in nreg or '-' in nreg:
            # Additional validation: should have numbers
            import re
            if re.search(r'\d', nreg):
                return True
        
        # Also accept simple numeric IDs if they look like NREG
        # But exclude very short numbers
        if nreg.isdigit() and len(nreg) >= 4:
            return True
        
        return False
    
    def _extract_nregs_from_dataset(self, dataset: Any) -> List[str]:
        """
        Extract NREG identifiers from dataset structure
        Handles various data structures (list, dict, nested)
        Validates NREG format to exclude invalid values
        """
        nregs = []
        
        # Extract NREG identifiers from dataset
        # Structure might vary, try common patterns
        if isinstance(dataset, list):
            for item in dataset:
                if isinstance(item, dict):
                    # Try common field names for NREG (prioritize nreg field)
                    # Check all possible field names
                    nreg = None
                    for field_name in ["nreg", "NREG", "nreg_id", "document_id", "doc_id", 
                                      "number", "id", "identifier", "code", "nreg_number",
                                      "document_number", "act_number", "law_number"]:
                        if field_name in item:
                            value = item[field_name]
                            if value:
                                nreg_str = str(value).strip()
                                if self._is_valid_nreg(nreg_str):
                                    nregs.append(nreg_str)
                                    nreg = nreg_str  # Found valid NREG
                                    break
                    
                    # If no valid NREG found, log for debugging
                    if not nreg and len(item) > 0:
                        # Only log first few items to avoid spam
                        if len(nregs) < 3:
                            logger.debug(f"Item without valid NREG, keys: {list(item.keys())[:10]}, sample: {str(item)[:150]}")
        elif isinstance(dataset, dict):
            # If dataset is a dict, it might contain a list in a field
            for key in ["data", "items", "results", "documents", "acts", "docs", "list"]:
                if key in dataset and isinstance(dataset[key], list):
                    for item in dataset[key]:
                        if isinstance(item, dict):
                            # Try all possible field names
                            nreg = None
                            for field_name in ["nreg", "NREG", "nreg_id", "document_id", "doc_id", 
                                              "number", "id", "identifier", "code", "nreg_number",
                                              "document_number", "act_number", "law_number"]:
                                if field_name in item:
                                    value = item[field_name]
                                    if value:
                                        nreg_str = str(value).strip()
                                        if self._is_valid_nreg(nreg_str):
                                            nregs.append(nreg_str)
                                            nreg = nreg_str  # Found valid NREG
                                            break
                            
                            # If no valid NREG found, log for debugging (only first few)
                            if not nreg and len(nregs) < 3:
                                logger.debug(f"Item in '{key}' without valid NREG, keys: {list(item.keys())[:10]}")
            # Or the dict itself might have nreg
            nreg = (dataset.get("nreg") or dataset.get("NREG") or 
                   dataset.get("number") or dataset.get("id"))
            if nreg:
                nreg_str = str(nreg).strip()
                if self._is_valid_nreg(nreg_str):
                    nregs.append(nreg_str)
        
        # Remove duplicates and return
        unique_nregs = list(set(nregs))
        
        if not unique_nregs:
            # Log structure for debugging
            logger.warning("Could not extract NREG identifiers from dataset structure")
            if isinstance(dataset, dict):
                logger.debug(f"Dataset type: dict, keys: {list(dataset.keys())[:10]}")
                if len(dataset) > 0:
                    first_key = list(dataset.keys())[0]
                    first_value = dataset.get(first_key)
                    logger.debug(f"First key '{first_key}' type: {type(first_value)}")
                    if isinstance(first_value, list) and len(first_value) > 0:
                        first_item = first_value[0]
                        if isinstance(first_item, dict):
                            logger.debug(f"First item keys: {list(first_item.keys())[:10]}")
                            logger.debug(f"First item sample: {str(first_item)[:200]}")
                    elif isinstance(first_value, dict):
                        logger.debug(f"First value (dict) keys: {list(first_value.keys())[:10]}")
            elif isinstance(dataset, list):
                logger.debug(f"Dataset type: list, length: {len(dataset)}")
                if len(dataset) > 0:
                    first_item = dataset[0]
                    if isinstance(first_item, dict):
                        logger.debug(f"First item keys: {list(first_item.keys())[:10]}")
                        logger.debug(f"First item sample: {str(first_item)[:200]}")
                    else:
                        logger.debug(f"First item type: {type(first_item)}, value: {str(first_item)[:200]}")
            else:
                logger.debug(f"Dataset type: {type(dataset)}")
        
        return unique_nregs
    
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


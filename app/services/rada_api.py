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
                response = await client.get(url, headers=headers, timeout=30.0)
                
                if response.status_code == 200:
                    import re
                    nregs = re.findall(r'/laws/show/([^"]+)', response.text)
                    return list(set(nregs))
                else:
                    logger.error(f"Error getting new list: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Exception getting new list: {e}")
            return []
    
    async def get_all_documents_list(self, limit: Optional[int] = None) -> List[str]:
        """
        Get list of all document nregs from Rada API
        Uses pagination to get all documents from /laws/main/r
        """
        all_nregs = []
        page = 1
        max_pages = 100  # Safety limit to avoid infinite loops
        
        try:
            while page <= max_pages:
                await self._rate_limit()
                
                async with httpx.AsyncClient() as client:
                    # Main page with all documents
                    if page == 1:
                        url = f"{self.base_url}/laws/main/r"
                    else:
                        url = f"{self.base_url}/laws/main/r?page={page}"
                    
                    headers = self._get_headers(use_token=False)
                    response = await client.get(url, headers=headers, timeout=60.0)
                    
                    if response.status_code == 200:
                        import re
                        from urllib.parse import unquote
                        
                        # Find all links to /laws/show/{nreg}
                        # Pattern: /laws/show/{nreg} or /laws/show/{nreg}.json
                        page_nregs = re.findall(r'/laws/show/([^"\s<>\.]+)', response.text)
                        
                        if not page_nregs:
                            # No more documents found
                            logger.info(f"No more documents on page {page}")
                            break
                        
                        # Decode URL-encoded nregs and add to list
                        decoded_nregs = []
                        for nreg in page_nregs:
                            try:
                                decoded = unquote(nreg)
                                if decoded not in all_nregs:
                                    decoded_nregs.append(decoded)
                            except:
                                # If decoding fails, use as is
                                if nreg not in all_nregs:
                                    decoded_nregs.append(nreg)
                        
                        all_nregs.extend(decoded_nregs)
                        
                        logger.info(f"Page {page}: found {len(decoded_nregs)} new documents (total: {len(all_nregs)})")
                        
                        # Check if we've reached the limit
                        if limit and len(all_nregs) >= limit:
                            all_nregs = all_nregs[:limit]
                            logger.info(f"Reached limit of {limit} documents")
                            break
                        
                        # If we got fewer results than expected, might be last page
                        if len(decoded_nregs) < 20:  # Assuming ~20-50 per page
                            logger.info(f"Few results on page {page}, assuming last page")
                            break
                        
                        page += 1
                    elif response.status_code == 404:
                        # No more pages
                        logger.info(f"No more pages (404 on page {page})")
                        break
                    else:
                        logger.warning(f"Error getting page {page}: {response.status_code}")
                        break
                
                # Safety check to avoid infinite loops
                if page > max_pages:
                    logger.warning(f"Reached max pages limit ({max_pages})")
                    break
            
            # Remove duplicates and return
            unique_nregs = list(set(all_nregs))
            logger.info(f"Total unique documents found: {len(unique_nregs)}")
            return unique_nregs
            
        except Exception as e:
            logger.error(f"Exception getting all documents list: {e}", exc_info=True)
            return all_nregs  # Return what we have so far


# Singleton instance
rada_api = RadaAPIService()


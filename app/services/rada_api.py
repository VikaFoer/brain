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
        """Get full document in JSON format"""
        await self._rate_limit()
        
        # Try to get token if not set
        if not self.token:
            logger.info("RADA_API_TOKEN not set, trying to get token automatically...")
            self.token = await self.get_token()
        
        try:
            async with httpx.AsyncClient() as client:
                # URL encode the nreg properly
                # According to Rada API docs, / should be encoded as %2F
                # But we need to preserve the structure, so encode each part separately
                from urllib.parse import quote
                # Split by /, encode each part, then join with /
                if '/' in nreg:
                    parts = nreg.split('/')
                    encoded_parts = [quote(part, safe='') for part in parts]
                    encoded_nreg = '/'.join(encoded_parts)
                else:
                    encoded_nreg = quote(nreg, safe='')
                
                url = f"{self.base_url}/laws/show/{encoded_nreg}.json"
                headers = self._get_headers(use_token=True)
                
                logger.debug(f"Requesting document: original nreg={nreg}, encoded={encoded_nreg}, url={url}")
                response = await client.get(url, headers=headers, timeout=60.0)
                
                if response.status_code == 200:
                    # Check if response is actually JSON
                    content_type = response.headers.get("content-type", "").lower()
                    if "application/json" not in content_type and "text/json" not in content_type:
                        logger.warning(f"Response for {nreg} is not JSON (content-type: {content_type})")
                        
                        # If HTML is returned, try to extract basic info from HTML
                        if "text/html" in content_type:
                            logger.info(f"Received HTML instead of JSON for {nreg}, trying to extract info from HTML")
                            try:
                                from bs4 import BeautifulSoup
                                soup = BeautifulSoup(response.text, 'html.parser')
                                
                                # Try to extract title from HTML
                                title = None
                                title_tag = soup.find('title')
                                if title_tag:
                                    title = title_tag.get_text().strip()
                                    # Clean up title (remove "// Портал відкритих даних" etc)
                                    if '//' in title:
                                        title = title.split('//')[0].strip()
                                
                                # Try to find JSON data in script tags
                                scripts = soup.find_all('script', type='application/json')
                                for script in scripts:
                                    try:
                                        json_data = json.loads(script.string)
                                        if json_data:
                                            logger.info(f"Found JSON data in HTML script tag for {nreg}")
                                            return json_data
                                    except:
                                        pass
                                
                                # If we found title but no JSON, return minimal structure
                                if title:
                                    logger.info(f"Extracted title from HTML: {title}")
                                    return {
                                        "title": title,
                                        "nreg": nreg,
                                        "source": "html_parsed"
                                    }
                            except ImportError:
                                logger.warning("BeautifulSoup not available, cannot parse HTML")
                            except Exception as html_error:
                                logger.warning(f"Error parsing HTML: {html_error}")
                        
                        # Try to parse as JSON anyway
                        try:
                            return response.json()
                        except:
                            pass
                    
                    try:
                        return response.json()
                    except Exception as json_error:
                        logger.error(f"Failed to parse JSON for {nreg}: {json_error}")
                        logger.error(f"Response text (first 500 chars): {response.text[:500]}")
                        return None
                elif response.status_code == 404:
                    logger.warning(f"Document {nreg} not found (404)")
                    return None
                elif response.status_code == 403:
                    logger.warning(f"Access forbidden for {nreg} (403) - may need valid token")
                    # Try without token
                    headers_no_token = self._get_headers(use_token=False)
                    response2 = await client.get(url, headers=headers_no_token, timeout=60.0)
                    if response2.status_code == 200:
                        logger.info(f"Successfully retrieved {nreg} without token")
                        try:
                            return response2.json()
                        except Exception as json_error:
                            logger.error(f"Failed to parse JSON for {nreg} (no token): {json_error}")
                            return None
                    return None
                else:
                    logger.error(f"Error getting document {nreg}: {response.status_code} - {response.text[:200]}")
                    return None
        except Exception as e:
            logger.error(f"Exception getting document {nreg}: {e}", exc_info=True)
            return None
    
    async def get_document_card(self, nreg: str) -> Optional[Dict[str, Any]]:
        """Get document card in JSON format"""
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
                
                url = f"{self.base_url}/laws/card/{encoded_nreg}.json"
                headers = self._get_headers(use_token=True)
                
                logger.debug(f"Requesting card: original nreg={nreg}, encoded={encoded_nreg}, url={url}")
                response = await client.get(url, headers=headers, timeout=30.0)
                
                if response.status_code == 200:
                    return response.json()
                else:
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


"""
Service for working with Rada API
"""
import httpx
import asyncio
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
        
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/laws/show/{nreg}.json"
                headers = self._get_headers(use_token=True)
                
                response = await client.get(url, headers=headers, timeout=60.0)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    logger.warning(f"Document {nreg} not found")
                    return None
                else:
                    logger.error(f"Error getting document {nreg}: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Exception getting document {nreg}: {e}")
            return None
    
    async def get_document_card(self, nreg: str) -> Optional[Dict[str, Any]]:
        """Get document card in JSON format"""
        await self._rate_limit()
        
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/laws/card/{nreg}.json"
                headers = self._get_headers(use_token=True)
                
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
                url = f"{self.base_url}/laws/show/{nreg}.txt"
                headers = self._get_headers(use_token=False)  # TXT doesn't need token
                
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


# Singleton instance
rada_api = RadaAPIService()


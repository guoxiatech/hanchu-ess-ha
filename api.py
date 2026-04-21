"""API client for Hanchuess."""
import logging
import time
import aiohttp
import async_timeout

_LOGGER = logging.getLogger(__name__)

TOKEN_REFRESH_DAYS = 25
TOKEN_REFRESH_SECONDS = TOKEN_REFRESH_DAYS * 24 * 3600


class HanchuessApiClient:
    """Hanchuess API client."""

    def __init__(self, domain: str, token: str = None):
        self._domain = domain.rstrip("/")
        self._token = token
        self._token_time = time.time() if token else 0

    @property
    def token(self) -> str:
        return self._token

    def _headers(self) -> dict:
        headers = {
            "Content-Type": "application/json",
            "appPlat": "ha",
        }
        if self._token:
            headers["access-token"] = self._token
        return headers

    async def _request(self, path: str, data: dict) -> dict:
        url = f"{self._domain}{path}"
        try:
            async with async_timeout.timeout(10):
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url, json=data, headers=self._headers()
                    ) as response:
                        if response.status == 401:
                            return {"success": False, "code": 401}
                        if response.status == 200:
                            result = await response.json()
                            if result.get("code") == 401:
                                return {"success": False, "code": 401}
                            return result
        except TimeoutError:
            _LOGGER.error("Request timeout: %s", url)
        except aiohttp.ClientError as err:
            _LOGGER.error("Request error: %s - %s", url, err)
        return None

    async def async_login(self, account: str, password: str) -> str | None:
        result = await self._request(
            "/gateway/identify/auth/token",
            {"account": account, "pwd": password},
        )
        if result and result.get("success"):
            self._token = result.get("data")
            self._token_time = time.time()
            return self._token
        return None

    async def async_refresh_token(self) -> str | None:
        result = await self._request(
            "/gateway/identify/auth/token/refresh",
            {"token": self._token},
        )
        if result and result.get("success"):
            self._token = result.get("data")
            self._token_time = time.time()
            return self._token
        return None

    def should_refresh_token(self) -> bool:
        return (time.time() - self._token_time) >= TOKEN_REFRESH_SECONDS

    async def async_get_devices(self) -> list:
        result = await self._request(
            "/gateway/app/ha/getDeviceList", {}
        )
        if result and result.get("success"):
            return result.get("data", [])
        return []

    async def async_get_device_status(self, device_id: str, language: str = "en") -> dict | None:
        result = await self._request(
            "/gateway/app/ha/getDeviceStatus",
            {"deviceId": device_id, "language": language},
        )
        if result and result.get("code") == 401:
            return {"_token_expired": True}
        if result and result.get("success"):
            return result.get("data", {})
        return {}

    async def async_get_device_statistics(self, device_id: str, language: str = "en") -> dict | None:
        result = await self._request(
            "/gateway/app/ha/getDeviceStatistics",
            {"deviceId": device_id, "language": language},
        )
        if result and result.get("code") == 401:
            return {"_token_expired": True}
        if result and result.get("success"):
            return result.get("data", {})
        return {}

    async def async_device_control(self, device_id: str, value_map: dict) -> bool | str:
        result = await self._request(
            "/gateway/app/ha/deviceControl",
            {"deviceId": device_id, "valueMap": value_map},
        )
        if result and result.get("code") == 401:
            return "token_expired"
        return result is not None and result.get("success", False)

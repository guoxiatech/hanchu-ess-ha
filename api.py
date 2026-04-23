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

    def _headers(self, language: str = None) -> dict:
        headers = {
            "Content-Type": "application/json",
            "appPlat": "ha",
        }
        if self._token:
            headers["access-token"] = self._token
        if language:
            # HA returns zh-Hans/zh-Hant, server expects zh
            if language.startswith("zh"):
                language = "zh"
            headers["locale"] = language
        return headers

    async def _request(self, path: str, data: dict, language: str = None) -> dict:
        url = f"{self._domain}{path}"
        _LOGGER.debug("[HANCHUESS] request: %s token=%s", url, "yes" if self._token else "no")
        try:
            async with async_timeout.timeout(10):
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url, json=data, headers=self._headers(language)
                    ) as response:
                        response_text = await response.text()
                        _LOGGER.debug("[HANCHUESS] response: %s status=%s body=%s", path, response.status, response_text[:500])
                        if response.status == 401:
                            return {"success": False, "code": 401}
                        if response.status == 200:
                            result = await response.json(content_type=None)
                            if result.get("code") == 401:
                                return {"success": False, "code": 401}
                            return result
                        _LOGGER.error("[HANCHUESS] unexpected status: %s %s", response.status, response_text[:200])
        except TimeoutError:
            _LOGGER.error("[HANCHUESS] Request timeout: %s", url)
        except Exception as err:
            _LOGGER.error("[HANCHUESS] Request error: %s - %s", url, err)
        return None

    async def async_login(self, account: str, password: str) -> str | None:
        result = await self._request(
            "/gateway/identify/auth/token",
            {"account": account, "pwd": password},
        )
        _LOGGER.info("[HANCHUESS] login: %s", "success" if result and result.get("success") else "failed")
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
        _LOGGER.info("[HANCHUESS] getDeviceList: %d devices", len(result.get("data", [])) if result else 0)
        if result and result.get("success"):
            return result.get("data", [])
        return []

    async def async_get_device_status(self, sn: str, language: str = "en") -> dict | None:
        result = await self._request(
            "/gateway/app/ha/getDeviceStatus",
            {"sn": sn},
            language=language,
        )
        if result and result.get("code") == 401:
            return {"_token_expired": True}
        if result and result.get("success"):
            return result.get("data", {})
        return {}

    async def async_get_device_statistics(self, sn: str, language: str = "en") -> dict | None:
        result = await self._request(
            "/gateway/app/ha/getDeviceStatistics",
            {"sn": sn},
            language=language,
        )
        if result and result.get("code") == 401:
            return {"_token_expired": True}
        if result and result.get("success"):
            return result.get("data", {})
        return {}

    async def async_get_menu(self, sn: str, language: str = "en") -> dict:
        result = await self._request(
            "/gateway/app/ha/menu",
            {"sn": sn},
            language=language,
        )
        if result and result.get("code") == 200:
            return result
        return {}

    async def async_iot_get(self, sn: str, dev_type: str, keys: list) -> dict:
        result = await self._request(
            "/gateway/app/ha/iotGet",
            {"sn": sn, "devType": dev_type, "keys": keys},
        )
        if result and result.get("success"):
            return result.get("data", {})
        return {}

    async def async_fast_charge_discharge(self, sn: str, act: int, duration: int) -> dict:
        result = await self._request(
            "/gateway/app/ha/fastChargeDischarge",
            {"sn": sn, "act": act, "duration": duration},
        )
        if not result:
            return {"success": False, "msg": "Request failed"}
        if result.get("code") == 401:
            return {"success": False, "msg": "token_expired"}
        if result.get("code") == 100:
            return {"success": False, "msg": result.get("msg", "Device error")}
        if result.get("success"):
            return {"success": True, "data": result.get("data", {})}
        return {"success": False, "msg": result.get("msg", "Unknown error")}

    async def async_device_control(self, sn: str, dev_type: str, value: dict) -> dict:
        result = await self._request(
            "/gateway/app/ha/iotSet",
            {"sn": sn, "devType": dev_type, "value": value},
        )
        if result and result.get("code") == 401:
            return {"success": False, "msg": "token_expired"}
        if result and result.get("success"):
            return {"success": True, "data": result.get("data", {})}
        return {"success": False, "msg": result.get("msg", "Unknown error") if result else "Request failed"}

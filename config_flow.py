"""配置流程"""
import voluptuous as vol
import aiohttp
import logging
from homeassistant import config_entries
from .aes_util import encrypt_data

DOMAIN = "hanchuess"
_LOGGER = logging.getLogger(__name__)

class HanchuessConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        
        if user_input is not None:
            # 验证授权
            domain = user_input["domain"]
            device_id = user_input["device_id"]
            secret_key = user_input["secret_key"]
            language = self.hass.config.language or "en"
            
            url = f"{domain}/gateway/app/ha/auth"
            _LOGGER.info(f"Attempting auth to {url}")
            
            try:
                # 加密请求数据
                request_data = {
                    "language": language,
                    "domain": domain,
                    "deviceId": device_id,
                    "secretKey": secret_key
                }
                _LOGGER.info(f"Auth request data before encrypt: {request_data}")
                encrypted_data = encrypt_data(request_data)
                _LOGGER.info(f"Auth encrypted data: {encrypted_data}")
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url, 
                        data=encrypted_data,
                        headers={"Content-Type": "text/plain"}
                    ) as response:
                        _LOGGER.info(f"Auth response status: {response.status}")
                        response_text = await response.text()
                        _LOGGER.info(f"Auth response text: {response_text}")
                        if response.status == 200:
                            result = await response.json()
                            _LOGGER.info(f"Auth response json: {result}")
                            if result.get("success"):
                                return self.async_create_entry(
                                    title=f"Hanchuess {device_id}",
                                    data=user_input
                                )
                        errors["base"] = "auth_failed"
            except Exception as e:
                _LOGGER.error(f"Auth error: {e}")
                errors["base"] = "cannot_connect"
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("domain"): str,
                vol.Required("device_id"): str,
                vol.Required("secret_key"): str,
            }),
            errors=errors
        )

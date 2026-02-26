"""配置流程"""
import voluptuous as vol
import aiohttp
from homeassistant import config_entries
from homeassistant.core import callback

DOMAIN = "hanchuess"

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
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json={
                        "language": language,
                        "domain": domain,
                        "deviceId": device_id,
                        "secretKey": secret_key
                    }) as response:
                        if response.status == 200:
                            result = await response.json()
                            if result.get("success"):
                                return self.async_create_entry(
                                    title=f"Hanchuess {device_id}",
                                    data=user_input
                                )
                errors["base"] = "auth_failed"
            except:
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

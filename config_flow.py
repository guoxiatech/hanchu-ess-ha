"""配置流程"""
from homeassistant import config_entries

DOMAIN = "hanchuess"

class HanchuessConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Hanchuess", data={})
        
        return self.async_show_form(step_id="user")

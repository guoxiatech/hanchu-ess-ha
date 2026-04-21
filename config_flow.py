"""Config flow for Hanchuess."""
import logging
import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN, BASE_URL
from .api import HanchuessApiClient

_LOGGER = logging.getLogger(__name__)


class HanchuessConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._domain = None
        self._token = None
        self._devices = []

    async def async_step_user(self, user_input=None):
        """Step 1: Login."""
        # Check if already logged in
        existing = self.hass.data.get(DOMAIN, {})
        for entry_data in existing.values():
            if hasattr(entry_data, "client") and entry_data.client.token:
                self._token = entry_data.client.token
                self._domain = entry_data.entry.data["domain"]
                client = HanchuessApiClient(self._domain, self._token)
                self._devices = await client.async_get_devices()
                if self._devices:
                    return await self.async_step_select_device()

        errors = {}
        if user_input is not None:
            client = HanchuessApiClient(BASE_URL)
            token = await client.async_login(
                user_input["account"], user_input["password"]
            )
            if token:
                self._token = client.token
                self._devices = await client.async_get_devices()
                if self._devices:
                    return await self.async_step_select_device()
                errors["base"] = "no_devices"
            else:
                errors["base"] = "auth_failed"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("account"): str,
                vol.Required("password"): str,
            }),
            errors=errors,
        )

    async def async_step_select_device(self, user_input=None):
        """Step 2: Select device."""
        errors = {}
        if user_input is not None:
            device_id = user_input["device"]

            # Prevent duplicate
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()

            # Find device name
            device_name = device_id
            for device in self._devices:
                if device.get("deviceId") == device_id:
                    device_name = device.get("deviceName", device_id)
                    break

            return self.async_create_entry(
                title=f"Hanchuess {device_name}",
                data={
                    "device_id": device_id,
                    "token": self._token,
                },
            )

        device_options = {
            d["deviceId"]: d.get("deviceName", d["deviceId"])
            for d in self._devices
        }

        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema({
                vol.Required("device"): vol.In(device_options),
            }),
            errors=errors,
        )

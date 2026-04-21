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
            if isinstance(entry_data, dict) and "realtime" in entry_data:
                coordinator = entry_data["realtime"]
                if coordinator.client.token:
                    self._token = coordinator.client.token
                    client = HanchuessApiClient(BASE_URL, self._token)
                    self._devices = await client.async_get_devices()
                    if self._devices:
                        return await self.async_step_select_device()
                    break

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
            sn = user_input["device"]

            # Prevent duplicate
            await self.async_set_unique_id(sn)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"Hanchuess {sn}",
                data={
                    "device_id": sn,
                    "token": self._token,
                },
            )

        # Only show inverters (devType=2) for now
        device_options = {
            d["sn"]: d["sn"]
            for d in self._devices
            if d.get("devType") == "2"
        }

        if not device_options:
            return self.async_abort(reason="no_devices")

        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema({
                vol.Required("device"): vol.In(device_options),
            }),
            errors=errors,
        )

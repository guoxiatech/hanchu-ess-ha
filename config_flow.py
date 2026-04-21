"""Config flow for Hanchuess."""
import logging
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries
from .const import DOMAIN, BASE_URL
from .api import HanchuessApiClient

_LOGGER = logging.getLogger(__name__)


class HanchuessConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
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
        """Step 2: Select devices (multi-select)."""
        errors = {}
        if user_input is not None:
            # multi_select returns {sn: True/False}
            selected = [k for k, v in user_input.get("devices", {}).items() if v]
            if not selected:
                errors["base"] = "no_devices"
            else:
                # Create entry for the first device
                sn = selected[0]
                await self.async_set_unique_id(sn)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Hanchuess {sn}" if len(selected) == 1 else f"Hanchuess ({len(selected)} devices)",
                    data={
                        "device_id": sn,
                        "token": self._token,
                        "pending_devices": selected[1:] if len(selected) > 1 else [],
                    },
                )

        # Filter inverters and exclude already configured
        configured_ids = set()
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            configured_ids.add(entry.data.get("device_id"))

        available = {
            d["sn"]: d["sn"]
            for d in self._devices
            if d.get("devType") == "2" and d["sn"] not in configured_ids
        }

        if not available:
            return self.async_abort(reason="no_devices")

        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema({
                vol.Required("devices"): cv.multi_select(available),
            }),
            errors=errors,
        )

    async def async_step_import(self, data: dict):
        """Handle creation of additional devices from pending list."""
        sn = data["device_id"]
        await self.async_set_unique_id(sn)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=f"Hanchuess {sn}",
            data={
                "device_id": sn,
                "token": data["token"],
                "pending_devices": [],
            },
        )

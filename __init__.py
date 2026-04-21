"""Hanchuess Home Assistant integration."""
import logging
import os
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv
from .const import DOMAIN, PLATFORMS, BASE_URL
from .api import HanchuessApiClient
from .coordinator import HanchuessRealtimeCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_DEVICE_CONTROL = "device_control"
SERVICE_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Required("value_map"): dict,
})


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})

    # Register static path for custom card
    hass.http.register_static_path(
        "/hacsfiles/hanchuess",
        os.path.join(os.path.dirname(__file__), "www"),
        cache_headers=False,
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    client = HanchuessApiClient(
        domain=BASE_URL,
        token=entry.data.get("token"),
    )

    coordinator = HanchuessRealtimeCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "realtime": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register service for batch control
    async def handle_device_control(call: ServiceCall):
        device_id = call.data["device_id"]
        value_map = call.data["value_map"]
        _LOGGER.info("[HANCHUESS] service device_control: %s %s", device_id, value_map)
        target_client = None
        for eid, data in hass.data[DOMAIN].items():
            if isinstance(data, dict) and "realtime" in data:
                if data["realtime"].entry.data.get("device_id") == device_id:
                    target_client = data["realtime"].client
                    break
        if not target_client:
            _LOGGER.error("[HANCHUESS] device_control: device %s not found", device_id)
            return
        result = await target_client.async_device_control(device_id, value_map)
        if result is not True:
            _LOGGER.error("[HANCHUESS] device_control failed: %s", result)

    if not hass.services.has_service(DOMAIN, SERVICE_DEVICE_CONTROL):
        hass.services.async_register(
            DOMAIN, SERVICE_DEVICE_CONTROL, handle_device_control, schema=SERVICE_SCHEMA
        )

    # Auto-create entries for remaining selected devices
    pending = entry.data.get("pending_devices", [])
    if pending:
        for item in pending:
            await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "import"},
                data={
                    "device_id": item["sn"],
                    "dev_type": item.get("devType", "2"),
                    "token": entry.data["token"],
                },
            )
        new_data = {k: v for k, v in entry.data.items() if k != "pending_devices"}
        hass.config_entries.async_update_entry(entry, data=new_data)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok

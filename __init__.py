"""Hanchuess Home Assistant集成"""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import os

DOMAIN = "hanchuess"
PLATFORMS = ["sensor", "select"]

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    
    # 注册前端资源
    hass.http.register_static_path(
        "/hacsfiles/hanchuess",
        hass.config.path(f"custom_components/{DOMAIN}/www"),
        True
    )
    
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    # 先加载sensor创建coordinator
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    # 再加载select使用coordinator
    await hass.config_entries.async_forward_entry_setups(entry, ["select"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok

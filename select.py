"""设备控制选择器"""
import aiohttp
from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    async_add_entities([DeviceControlSelect()])

class DeviceControlSelect(SelectEntity):
    _attr_name = "设备控制"
    _attr_unique_id = "hanchuess_device_control"
    _attr_icon = "mdi:tune"
    _attr_options = ["开启充电", "开启放电", "逆变器开", "逆变器关"]
    
    def __init__(self):
        self._attr_current_option = None
    
    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={("hanchuess", "device_monitor")},
            name="Hanchuess设备",
            manufacturer="Hanchuess",
            model="ESS Device",
        )
    
    async def async_select_option(self, option: str):
        control_map = {
            "开启充电": {"controlType": 1, "controlValue": 1},
            "开启放电": {"controlType": 2, "controlValue": 1},
            "逆变器开": {"controlType": 3, "controlValue": 1},
            "逆变器关": {"controlType": 3, "controlValue": 0}
        }
        
        params = control_map.get(option)
        if params:
            url = "https://iess-international.hanchuess.net/gateway/app/ha/deviceControl"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=params) as response:
                        if response.status == 200:
                            self._attr_current_option = option
                            self.async_write_ha_state()
            except:
                pass

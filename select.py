"""设备控制选择器"""
import aiohttp
from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .aes_util import encrypt_data
import logging

DOMAIN = "hanchuess"
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    async_add_entities([DeviceControlSelect(coordinator, entry)])

class DeviceControlSelect(CoordinatorEntity, SelectEntity):
    _attr_name = "工作模式"
    _attr_icon = "mdi:tune"
    _attr_options = ["自发自用模式", "后备能源模式", "分时充放", "基于SOC", "馈网优先模式", "离网模式"]
    
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_work_mode"
    
    @property
    def current_option(self):
        """返回当前选中的选项"""
        value_to_name = {
            1: "自发自用模式",
            2: "后备能源模式",
            3: "分时充放",
            9: "基于SOC",
            10: "馈网优先模式",
            4: "离网模式"
        }
        work_mode = self.coordinator.data.get("workModeCmb")
        _LOGGER.info(f"[Select] workModeCmb value: {work_mode}, type: {type(work_mode)}")
        if work_mode is not None:
            result = value_to_name.get(work_mode)
            _LOGGER.info(f"[Select] mapped to: {result}")
            return result
        return None
    
    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=f"Hanchuess {self.entry.data['device_id']}",
            manufacturer="Hanchuess",
            model="ESS Device",
        )
    
    async def async_select_option(self, option: str):
        mode_map = {
            "自发自用模式": "1",
            "后备能源模式": "2",
            "分时充放": "3",
            "基于SOC": "9",
            "馈网优先模式": "10",
            "离网模式": "4"
        }
        
        value = mode_map.get(option)
        if value:
            domain = self.entry.data["domain"]
            device_id = self.entry.data["device_id"]
            url = f"{domain}/gateway/app/ha/deviceControl"
            
            try:
                request_data = {
                    "deviceId": device_id,
                    "valueMap": {"WORK_MODE_CMB": value}
                }
                encrypted_data = encrypt_data(request_data)
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url, 
                        data=encrypted_data,
                        headers={"Content-Type": "text/plain"}
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            if result.get("success"):
                                await self.coordinator.async_request_refresh()
            except Exception as e:
                _LOGGER.error(f"[Select] Error: {e}")

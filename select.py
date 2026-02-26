"""设备控制选择器"""
import aiohttp
from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from .aes_util import encrypt_data
import logging

DOMAIN = "hanchuess"
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    async_add_entities([DeviceControlSelect(entry, coordinator)])

class DeviceControlSelect(SelectEntity):
    _attr_name = "工作模式"
    _attr_icon = "mdi:tune"
    _attr_options = ["自发自用模式", "后备能源模式", "分时充放", "基于SOC", "馈网优先模式", "离网模式"]
    _attr_should_poll = False
    
    def __init__(self, entry, coordinator=None):
        self.entry = entry
        self.coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_work_mode"
        self._attr_current_option = None
    
    async def async_added_to_hass(self):
        """实体添加到HA时注册coordinator监听"""
        if self.coordinator:
            self.async_on_remove(
                self.coordinator.async_add_listener(self._handle_coordinator_update)
            )
    
    def _handle_coordinator_update(self):
        """处理coordinator数据更新"""
        self.async_write_ha_state()
    
    @property
    def current_option(self):
        """返回当前选中的选项"""
        if self.coordinator and self.coordinator.data:
            value_to_name = {
                "1": "自发自用模式",
                "2": "后备能源模式",
                "3": "分时充放",
                "9": "基于SOC",
                "10": "馈网优先模式",
                "4": "离网模式"
            }
            work_mode = self.coordinator.data.get("workModeCmb")
            if work_mode is not None:
                return value_to_name.get(str(work_mode))
        
        return self._attr_current_option
    
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
                                if self.coordinator:
                                    await self.coordinator.async_request_refresh()
                                else:
                                    self._attr_current_option = option
                                    self.async_write_ha_state()
            except Exception as e:
                _LOGGER.error(f"[Select] Error: {e}")

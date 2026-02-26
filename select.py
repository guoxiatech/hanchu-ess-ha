"""设备控制选择器"""
import aiohttp
from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from .aes_util import encrypt_data

DOMAIN = "hanchuess"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DeviceControlSelect(coordinator, entry)])

class DeviceControlSelect(SelectEntity):
    _attr_name = "工作模式"
    _attr_icon = "mdi:tune"
    _attr_options = ["自发自用模式", "后备能源模式", "分时充放", "基于SOC", "馈网优先模式", "离网模式"]
    _attr_should_poll = False
    
    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_control"
    
    async def async_added_to_hass(self):
        """实体添加到HA时注册coordinator监听"""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
    
    @property
    def available(self):
        """实体是否可用"""
        return self.coordinator.last_update_success
    
    @property
    def current_option(self):
        """返回当前选中的选项"""
        if not self.coordinator.data:
            return None
        
        value_to_name = {
            "1": "自发自用模式",
            "2": "后备能源模式",
            "3": "分时充放",
            "9": "基于SOC",
            "10": "馈网优先模式",
            "4": "离网模式"
        }
        work_mode = self.coordinator.data.get("workModeCmb")
        return value_to_name.get(str(work_mode)) if work_mode else None
    
    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=f"Hanchuess {self.entry.data['device_id']}",
            manufacturer="Hanchuess",
            model="ESS Device",
        )
    
    async def async_select_option(self, option: str):
        import logging
        _LOGGER = logging.getLogger(__name__)
        
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
            _LOGGER.info(f"[Select] Requesting {url}")
            
            try:
                # 加密请求数据
                request_data = {
                    "deviceId": device_id,
                    "valueMap": {"WORK_MODE_CMB": value}
                }
                _LOGGER.info(f"[Select] Request data before encrypt: {request_data}")
                encrypted_data = encrypt_data(request_data)
                _LOGGER.info(f"[Select] Encrypted data: {encrypted_data}")
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url, 
                        data=encrypted_data,
                        headers={"Content-Type": "text/plain"}
                    ) as response:
                        _LOGGER.info(f"[Select] Response status: {response.status}")
                        response_text = await response.text()
                        _LOGGER.info(f"[Select] Response text: {response_text}")
                        if response.status == 200:
                            result = await response.json()
                            _LOGGER.info(f"[Select] Response json: {result}")
                            if result.get("success"):
                                # 更新coordinator数据
                                await self.coordinator.async_request_refresh()
                                self.async_write_ha_state()
            except Exception as e:
                _LOGGER.error(f"[Select] Error: {e}")

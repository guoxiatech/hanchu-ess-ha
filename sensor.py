"""设备状态传感器"""
import aiohttp
import async_timeout
import logging
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .aes_util import encrypt_data

SCAN_INTERVAL = timedelta(seconds=30)
DOMAIN = "hanchuess"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator = DeviceDataCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    async_add_entities([DeviceStatusSensor(coordinator, entry)])

class DeviceDataCoordinator(DataUpdateCoordinator):
    """数据协调器"""
    def __init__(self, hass, entry):
        super().__init__(
            hass,
            logging.getLogger(__name__),
            name="hanchuess",
            update_interval=SCAN_INTERVAL
        )
        self.entry = entry
        
    async def _async_update_data(self):
        _LOGGER = logging.getLogger(__name__)
        
        domain = self.entry.data["domain"]
        device_id = self.entry.data["device_id"]
        language = self.hass.config.language or "en"
        
        url = f"{domain}/gateway/app/ha/getDeviceStatus"
        _LOGGER.info(f"[Sensor] Requesting {url}")
        
        try:
            async with async_timeout.timeout(10):
                # 加密请求数据
                request_data = {
                    "language": language,
                    "deviceId": device_id
                }
                _LOGGER.info(f"[Sensor] Request data before encrypt: {request_data}")
                encrypted_data = encrypt_data(request_data)
                _LOGGER.info(f"[Sensor] Encrypted data: {encrypted_data}")
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url, 
                        data=encrypted_data,
                        headers={"Content-Type": "text/plain"}
                    ) as response:
                        _LOGGER.info(f"[Sensor] Response status: {response.status}")
                        response_text = await response.text()
                        _LOGGER.info(f"[Sensor] Response text: {response_text}")
                        if response.status == 200:
                            result = await response.json()
                            _LOGGER.info(f"[Sensor] Response json: {result}")
                            if result.get("success"):
                                data = result.get("data", {})
                                dev_status = data.get("devStatus")
                                try:
                                    dev_status = int(dev_status)
                                except (ValueError, TypeError):
                                    dev_status = None
                                
                                if dev_status == 1:
                                    data["_status"] = "在线"
                                elif dev_status == 0:
                                    data["_status"] = "离线"
                                elif dev_status == 99:
                                    data["_status"] = "待接入"
                                else:
                                    data["_status"] = "未知"
                                return data
        except Exception as e:
            _LOGGER.error(f"[Sensor] Error: {e}")
        return {"_status": "离线"}

class DeviceStatusSensor(SensorEntity):
    _attr_name = "状态"
    _attr_icon = "mdi:check-circle"
    
    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_status"
    
    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=f"Hanchuess {self.coordinator.entry.data['device_id']}",
            manufacturer="Hanchuess",
            model="ESS Device",
        )
    
    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        soc = data.get("batSoc")
        if soc is not None:
            soc = f"{int(soc * 100)}%"
        
        return {
            "电池电量": soc,
            "电池功率": f"{data.get('batP', 0)} {data.get('batPUnit', 'W')}",
            "负载功率": f"{data.get('loadPwr', 0)} W",
            "光伏功率": f"{data.get('pvTtPwr', 0)} {data.get('pvTtPwrUnit', 'W')}",
            "电网功率": f"{data.get('meterPPwr', 0)} {data.get('meterPPwrUnit', 'W')}",
            "工作模式": data.get("deviceStatusDes", "-"),
            "设备序列号": data.get("sn", "-"),
        }

    async def async_update(self):
        await self.coordinator.async_request_refresh()
        self._attr_native_value = self.coordinator.data.get("_status", "未知")


"""设备状态传感器"""
import aiohttp
import async_timeout
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
    
    async_add_entities([
        DeviceStatusSensor(coordinator, entry),
        DeviceVersionSensor(coordinator, entry),
        DeviceBuildTimeSensor(coordinator, entry),
        DevicePodNameSensor(coordinator, entry),
        DeviceServiceNameSensor(coordinator, entry),
        DeviceStartTimeSensor(coordinator, entry),
        DeviceCurrentTimeSensor(coordinator, entry)
    ])

class DeviceDataCoordinator(DataUpdateCoordinator):
    """数据协调器"""
    def __init__(self, hass, entry):
        super().__init__(hass, None, "hanchuess", update_interval=SCAN_INTERVAL)
        self.entry = entry
        
    async def _async_update_data(self):
        domain = self.entry.data["domain"]
        device_id = self.entry.data["device_id"]
        language = self.hass.config.language or "en"
        
        url = f"{domain}/gateway/app/ha/getDeviceStatus"
        try:
            async with async_timeout.timeout(10):
                # 加密请求数据
                encrypted_data = encrypt_data({
                    "language": language,
                    "deviceId": device_id
                })
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json={"data": encrypted_data}) as response:
                        if response.status == 200:
                            result = await response.json()
                            if result.get("success"):
                                data = result.get("data", {})
                                data["_status"] = "在线"
                                return data
        except:
            pass
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

    async def async_update(self):
        await self.coordinator.async_request_refresh()
        self._attr_native_value = self.coordinator.data.get("_status", "未知")

class DeviceVersionSensor(SensorEntity):
    _attr_name = "版本号"
    _attr_icon = "mdi:tag"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_version"
    
    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=f"Hanchuess {self.coordinator.entry.data['device_id']}",
            manufacturer="Hanchuess",
            model="ESS Device",
        )

    async def async_update(self):
        self._attr_native_value = self.coordinator.data.get("tag", "未知")

class DeviceBuildTimeSensor(SensorEntity):
    _attr_name = "构建时间"
    _attr_icon = "mdi:hammer"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_build_time"
    
    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=f"Hanchuess {self.coordinator.entry.data['device_id']}",
            manufacturer="Hanchuess",
            model="ESS Device",
        )

    async def async_update(self):
        self._attr_native_value = self.coordinator.data.get("buildTime", "未知")

class DevicePodNameSensor(SensorEntity):
    _attr_name = "Pod名称"
    _attr_icon = "mdi:server"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_pod_name"
    
    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=f"Hanchuess {self.coordinator.entry.data['device_id']}",
            manufacturer="Hanchuess",
            model="ESS Device",
        )

    async def async_update(self):
        self._attr_native_value = self.coordinator.data.get("podName", "未知")

class DeviceServiceNameSensor(SensorEntity):
    _attr_name = "服务名称"
    _attr_icon = "mdi:application"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_service_name"
    
    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=f"Hanchuess {self.coordinator.entry.data['device_id']}",
            manufacturer="Hanchuess",
            model="ESS Device",
        )

    async def async_update(self):
        self._attr_native_value = self.coordinator.data.get("serviceName", "未知")

class DeviceStartTimeSensor(SensorEntity):
    _attr_name = "启动时间"
    _attr_icon = "mdi:clock-start"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_start_time"
    
    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=f"Hanchuess {self.coordinator.entry.data['device_id']}",
            manufacturer="Hanchuess",
            model="ESS Device",
        )

    async def async_update(self):
        self._attr_native_value = self.coordinator.data.get("startTime", "未知")

class DeviceCurrentTimeSensor(SensorEntity):
    _attr_name = "当前时间"
    _attr_icon = "mdi:clock"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_current_time"
    
    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=f"Hanchuess {self.coordinator.entry.data['device_id']}",
            manufacturer="Hanchuess",
            model="ESS Device",
        )

    async def async_update(self):
        self._attr_native_value = self.coordinator.data.get("currentTime", "未知")

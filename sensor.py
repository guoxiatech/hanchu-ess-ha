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

SCAN_INTERVAL = timedelta(seconds=30)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator = DeviceDataCoordinator(hass)
    await coordinator.async_refresh()
    
    async_add_entities([
        DeviceStatusSensor(coordinator),
        DeviceVersionSensor(coordinator),
        DeviceBuildTimeSensor(coordinator),
        DevicePodNameSensor(coordinator),
        DeviceServiceNameSensor(coordinator),
        DeviceStartTimeSensor(coordinator),
        DeviceCurrentTimeSensor(coordinator)
    ])

class DeviceDataCoordinator:
    """数据协调器"""
    def __init__(self, hass):
        self.hass = hass
        self.data = {}
        
    async def async_refresh(self):
        url = "https://iess-international.hanchuess.net/gateway/app/info"
        try:
            async with async_timeout.timeout(10):
                async with aiohttp.ClientSession() as session:
                    async with session.post(url) as response:
                        if response.status == 200:
                            result = await response.json()
                            if result.get("success"):
                                self.data = result.get("data", {})
                                self.data["_status"] = "在线"
                            else:
                                self.data = {"_status": "异常"}
                        else:
                            self.data = {"_status": "离线"}
        except:
            self.data = {"_status": "离线"}

class DeviceStatusSensor(SensorEntity):
    _attr_name = "状态"
    _attr_unique_id = "hanchuess_status"
    _attr_icon = "mdi:check-circle"
    
    def __init__(self, coordinator):
        self.coordinator = coordinator
    
    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={("hanchuess", "device_monitor")},
            name="Hanchuess设备",
            manufacturer="Hanchuess",
            model="ESS Device",
        )

    async def async_update(self):
        await self.coordinator.async_refresh()
        self._attr_native_value = self.coordinator.data.get("_status", "未知")

class DeviceVersionSensor(SensorEntity):
    _attr_name = "版本号"
    _attr_unique_id = "hanchuess_version"
    _attr_icon = "mdi:tag"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, coordinator):
        self.coordinator = coordinator
    
    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={("hanchuess", "device_monitor")},
            name="Hanchuess设备",
            manufacturer="Hanchuess",
            model="ESS Device",
        )

    async def async_update(self):
        self._attr_native_value = self.coordinator.data.get("tag", "未知")

class DeviceBuildTimeSensor(SensorEntity):
    _attr_name = "构建时间"
    _attr_unique_id = "hanchuess_build_time"
    _attr_icon = "mdi:hammer"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, coordinator):
        self.coordinator = coordinator
    
    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={("hanchuess", "device_monitor")},
            name="Hanchuess设备",
            manufacturer="Hanchuess",
            model="ESS Device",
        )

    async def async_update(self):
        self._attr_native_value = self.coordinator.data.get("buildTime", "未知")

class DevicePodNameSensor(SensorEntity):
    _attr_name = "Pod名称"
    _attr_unique_id = "hanchuess_pod_name"
    _attr_icon = "mdi:server"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, coordinator):
        self.coordinator = coordinator
    
    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={("hanchuess", "device_monitor")},
            name="Hanchuess设备",
            manufacturer="Hanchuess",
            model="ESS Device",
        )

    async def async_update(self):
        self._attr_native_value = self.coordinator.data.get("podName", "未知")

class DeviceServiceNameSensor(SensorEntity):
    _attr_name = "服务名称"
    _attr_unique_id = "hanchuess_service_name"
    _attr_icon = "mdi:application"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, coordinator):
        self.coordinator = coordinator
    
    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={("hanchuess", "device_monitor")},
            name="Hanchuess设备",
            manufacturer="Hanchuess",
            model="ESS Device",
        )

    async def async_update(self):
        self._attr_native_value = self.coordinator.data.get("serviceName", "未知")

class DeviceStartTimeSensor(SensorEntity):
    _attr_name = "启动时间"
    _attr_unique_id = "hanchuess_start_time"
    _attr_icon = "mdi:clock-start"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, coordinator):
        self.coordinator = coordinator
    
    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={("hanchuess", "device_monitor")},
            name="Hanchuess设备",
            manufacturer="Hanchuess",
            model="ESS Device",
        )

    async def async_update(self):
        self._attr_native_value = self.coordinator.data.get("startTime", "未知")

class DeviceCurrentTimeSensor(SensorEntity):
    _attr_name = "当前时间"
    _attr_unique_id = "hanchuess_current_time"
    _attr_icon = "mdi:clock"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, coordinator):
        self.coordinator = coordinator
    
    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={("hanchuess", "device_monitor")},
            name="Hanchuess设备",
            manufacturer="Hanchuess",
            model="ESS Device",
        )

    async def async_update(self):
        self._attr_native_value = self.coordinator.data.get("currentTime", "未知")

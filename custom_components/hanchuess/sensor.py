"""Sensor platform for Hanchuess."""
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfPower, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN

SENSORS = {
    "device_status": {
        "key": "devStatus",
        "icon": "mdi:check-circle",
    },
    "battery_soc": {
        "key": "batSoc",
        "device_class": SensorDeviceClass.BATTERY,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": PERCENTAGE,
        "icon": "mdi:battery",
        "scale": 100,
    },
    "battery_power": {
        "key": "batP",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.WATT,
        "icon": "mdi:battery-charging",
    },
    "pv_power": {
        "key": "pvTtPwr",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.WATT,
        "icon": "mdi:solar-power",
    },
    "grid_power": {
        "key": "meterPPwr",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.WATT,
        "icon": "mdi:transmission-tower",
    },
    "load_power": {
        "key": "loadPwr",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.WATT,
        "icon": "mdi:home-lightning-bolt",
    },
    "dg_power": {
        "key": "dgPAcTotal",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.WATT,
        "icon": "mdi:engine",
        "condition_key": "hasDg",
        "condition_value": True,
    },
}

STATISTICS_SENSORS = {
    "daily_load_energy": {
        "key": "load",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "icon": "mdi:home-lightning-bolt",
    },
    "daily_charge_energy": {
        "key": "batCharge",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "icon": "mdi:battery-plus",
    },
    "daily_discharge_energy": {
        "key": "batDisCharge",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "icon": "mdi:battery-minus",
    },
    "daily_pv_energy": {
        "key": "pv",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "icon": "mdi:solar-power",
    },
    "daily_grid_import": {
        "key": "gridImport",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "icon": "mdi:transmission-tower-import",
    },
    "daily_grid_export": {
        "key": "gridExport",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "icon": "mdi:transmission-tower-export",
    },
    "daily_dg_energy": {
        "key": "dgEp",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "icon": "mdi:engine",
        "condition_key": "hasDg",
        "condition_value": 1,
    },
}

STATUS_MAP = {
    0: "offline",
    1: "online",
    99: "pending",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    data = hass.data[DOMAIN][entry.entry_id]
    realtime = data["realtime"]
    statistics = data["statistics"]
    entities = []
    for sensor_key, config in SENSORS.items():
        cond_key = config.get("condition_key")
        if cond_key:
            if realtime.data.get(cond_key) != config.get("condition_value"):
                continue
        if config["key"] in realtime.data:
            entities.append(HanchueSensor(realtime, entry, sensor_key, config))
    for sensor_key, config in STATISTICS_SENSORS.items():
        cond_key = config.get("condition_key")
        if cond_key:
            if statistics.data.get(cond_key) != config.get("condition_value"):
                continue
        entities.append(HanchueSensor(statistics, entry, sensor_key, config))
    async_add_entities(entities)


class HanchueSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, sensor_key, config):
        super().__init__(coordinator)
        self._entry = entry
        self._sensor_key = sensor_key
        self._config = config
        self._attr_translation_key = sensor_key
        self._attr_unique_id = f"{entry.data['sn']}_{sensor_key}"
        self._attr_icon = config.get("icon")
        if "device_class" in config:
            self._attr_device_class = config["device_class"]
        if "state_class" in config:
            self._attr_state_class = config["state_class"]
        if "unit" in config:
            self._attr_native_unit_of_measurement = config["unit"]

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.data["sn"])},
            name=f"Hanchuess {self._entry.data['sn']}",
            manufacturer="Hanchuess",
            model="ESS Device",
        )

    @property
    def native_value(self):
        value = self.coordinator.data.get(self._config["key"])
        if value is None:
            return None
        if self._sensor_key == "device_status":
            try:
                return STATUS_MAP.get(int(value), "unknown")
            except (ValueError, TypeError):
                return "unknown"
        if "scale" in self._config:
            try:
                return round(float(value) * self._config["scale"], 1)
            except (ValueError, TypeError):
                return None
        return value

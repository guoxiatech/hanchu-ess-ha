"""Number platform for Hanchuess."""
import logging
from homeassistant.components.number import NumberEntity
from homeassistant.const import UnitOfPower, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

NUMBERS = {
    "charge_power_limit": {
        "key": "chargePowerLimit",
        "min_key": "chargeMinPower",
        "max_key": "chargeMaxPower",
        "control_key": "CHARGE_POWER_LIMIT",
        "unit": UnitOfPower.WATT,
        "icon": "mdi:battery-charging",
        "step": 100,
    },
    "discharge_power_limit": {
        "key": "dischargePowerLimit",
        "min_key": "dischargeMinPower",
        "max_key": "dischargeMaxPower",
        "control_key": "DISCHARGE_POWER_LIMIT",
        "unit": UnitOfPower.WATT,
        "icon": "mdi:battery-arrow-down",
        "step": 100,
    },
    "soc_min": {
        "key": "socMin",
        "min_key": "socMinLimit",
        "max_key": "socMaxLimit",
        "control_key": "SOC_MIN",
        "unit": PERCENTAGE,
        "icon": "mdi:battery-low",
        "step": 1,
    },
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    coordinators = hass.data[DOMAIN][entry.entry_id]
    coordinator = coordinators["realtime"]
    entities = []
    for number_key, config in NUMBERS.items():
        if config["key"] in coordinator.data:
            entities.append(HanchueNumber(coordinator, entry, number_key, config))
    async_add_entities(entities)


class HanchueNumber(CoordinatorEntity, NumberEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, number_key, config):
        super().__init__(coordinator)
        self._entry = entry
        self._config = config
        self._attr_translation_key = number_key
        self._attr_unique_id = f"{entry.entry_id}_{number_key}"
        self._attr_icon = config.get("icon")
        self._attr_native_unit_of_measurement = config.get("unit")
        self._attr_native_step = config.get("step", 1)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.data["device_id"])},
            name=f"Hanchuess {self._entry.data['device_id']}",
            manufacturer="Hanchuess",
            model="ESS Device",
        )

    @property
    def native_min_value(self) -> float:
        return self.coordinator.data.get(self._config["min_key"], 0)

    @property
    def native_max_value(self) -> float:
        return self.coordinator.data.get(self._config["max_key"], 100)

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get(self._config["key"])

    async def async_set_native_value(self, value: float) -> None:
        success = await self.coordinator.client.async_device_control(
            self._entry.data["device_id"],
            {self._config["control_key"]: str(int(value))},
        )
        if success:
            await self.coordinator.async_request_refresh()

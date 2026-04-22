"""Switch platform for Hanchuess."""
import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def _is_device_online(coordinator) -> bool:
    dev_status = coordinator.data.get("devStatus")
    try:
        return int(dev_status) == 1
    except (ValueError, TypeError):
        return False

SWITCHES = {
    "inverter_switch": {
        "key": "inverterOn",
        "control_key": "INVERTER_SWITCH",
        "icon": "mdi:power",
    },
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    coordinators = hass.data[DOMAIN][entry.entry_id]
    coordinator = coordinators["realtime"]
    entities = []
    for switch_key, config in SWITCHES.items():
        if config["key"] in coordinator.data:
            entities.append(HanchueSwitch(coordinator, entry, switch_key, config))
    async_add_entities(entities)


class HanchueSwitch(CoordinatorEntity, SwitchEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, switch_key, config):
        super().__init__(coordinator)
        self._entry = entry
        self._config = config
        self._attr_translation_key = switch_key
        self._attr_unique_id = f"{entry.data['sn']}_{switch_key}"
        self._attr_icon = config.get("icon")

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.data["sn"])},
            name=f"Hanchuess {self._entry.data['sn']}",
            manufacturer="Hanchuess",
            model="ESS Device",
        )

    @property
    def available(self) -> bool:
        return super().available and _is_device_online(self.coordinator)

    @property
    def is_on(self) -> bool | None:
        value = self.coordinator.data.get(self._config["key"])
        if value is None:
            return None
        return bool(value)

    async def async_turn_on(self, **kwargs) -> None:
        success = await self.coordinator.client.async_device_control(
            self._entry.data["sn"],
            {self._config["control_key"]: "1"},
        )
        if success:
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        success = await self.coordinator.client.async_device_control(
            self._entry.data["sn"],
            {self._config["control_key"]: "0"},
        )
        if success:
            await self.coordinator.async_request_refresh()

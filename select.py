"""Select platform for Hanchuess."""
import logging
from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    coordinators = hass.data[DOMAIN][entry.entry_id]
    coordinator = coordinators["realtime"]
    entities = []
    if "workModeOptions" in coordinator.data:
        entities.append(WorkModeSelect(coordinator, entry))
    async_add_entities(entities)


class WorkModeSelect(CoordinatorEntity, SelectEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "work_mode"
    _attr_icon = "mdi:tune"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_work_mode"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.data["device_id"])},
            name=f"Hanchuess {self._entry.data['device_id']}",
            manufacturer="Hanchuess",
            model="ESS Device",
        )

    @property
    def options(self) -> list[str]:
        opts = self.coordinator.data.get("workModeOptions", [])
        return [opt["label"] for opt in opts]

    @property
    def current_option(self) -> str | None:
        current = self.coordinator.data.get("workModeCmb")
        for opt in self.coordinator.data.get("workModeOptions", []):
            if opt["value"] == current:
                return opt["label"]
        return None

    async def async_select_option(self, option: str) -> None:
        for opt in self.coordinator.data.get("workModeOptions", []):
            if opt["label"] == option:
                value = opt["value"]
                break
        else:
            return

        success = await self.coordinator.client.async_device_control(
            self._entry.data["device_id"],
            {"WORK_MODE_CMB": str(value)},
        )
        if success:
            await self.coordinator.async_request_refresh()

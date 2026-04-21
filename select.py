"""Select platform for Hanchuess."""
import json
import logging
from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN
from .sensor import STATUS_MAP

_LOGGER = logging.getLogger(__name__)


def _is_device_online(coordinator) -> bool:
    dev_status = coordinator.data.get("devStatus")
    try:
        return int(dev_status) == 1
    except (ValueError, TypeError):
        return False


def _parse_work_mode_options(menu_data: dict) -> list:
    energy = menu_data.get("data", {}).get("energy", {})
    for group in energy.get("items", []):
        for item in group:
            if item.get("itemCode") == "work_mode" and item.get("itemType") == "3":
                try:
                    options = json.loads(item.get("optVal", "[]"))
                    return [
                        {"label": opt["name"], "value": opt["value"],
                         "signal": item.get("itemCodeSignal", "WORK_MODE_CMB")}
                        for opt in options
                    ]
                except (json.JSONDecodeError, KeyError):
                    _LOGGER.error("Failed to parse work mode options")
    return []


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["realtime"]
    async_add_entities([WorkModeSelect(coordinator, entry)])


class WorkModeSelect(CoordinatorEntity, SelectEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "work_mode"
    _attr_icon = "mdi:tune"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_work_mode"
        self._work_mode_options = []
        self._signal = "WORK_MODE_CMB"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.data["device_id"])},
            name=f"Hanchuess {self._entry.data['device_id']}",
            manufacturer="Hanchuess",
            model="ESS Device",
        )

    @property
    def available(self) -> bool:
        return super().available and _is_device_online(self.coordinator)

    @property
    def options(self) -> list[str]:
        if not self._work_mode_options:
            return []
        return [opt["label"] for opt in self._work_mode_options]

    @property
    def current_option(self) -> str | None:
        current = self.coordinator.data.get("workModeCmb")
        if current is None:
            return None
        current_str = str(current)
        for opt in self._work_mode_options:
            if str(opt["value"]) == current_str:
                return opt["label"]
        return None

    async def async_added_to_hass(self) -> None:
        """Called when entity is added to HA. Fetch menu on first load."""
        await super().async_added_to_hass()
        await self._refresh_menu()

    async def async_update(self) -> None:
        """Called every time HA UI requests entity state. Refresh menu."""
        await self._refresh_menu()
        await super().async_update()

    async def _refresh_menu(self) -> None:
        language = self.hass.config.language or "en"
        device_id = self._entry.data["device_id"]
        menu_data = await self.coordinator.client.async_get_menu(device_id, language)
        options = _parse_work_mode_options(menu_data)
        if options:
            self._work_mode_options = options
            self._signal = options[0].get("signal", "WORK_MODE_CMB")

    async def async_select_option(self, option: str) -> None:
        for opt in self._work_mode_options:
            if opt["label"] == option:
                value = opt["value"]
                break
        else:
            return

        success = await self.coordinator.client.async_device_control(
            self._entry.data["device_id"],
            {self._signal: str(value)},
        )
        if success is True:
            await self.coordinator.async_request_refresh()

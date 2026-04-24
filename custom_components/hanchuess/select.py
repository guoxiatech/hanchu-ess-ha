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

_LOGGER = logging.getLogger(__name__)


def _is_device_online(coordinator) -> bool:
    dev_status = coordinator.data.get("devStatus")
    try:
        return int(dev_status) == 1
    except (ValueError, TypeError):
        return False


def _parse_energy_menu(menu_data: dict) -> dict:
    """Parse energy menu into structured data for card."""
    result = {"work_mode_options": [], "fields": []}

    data = menu_data.get("data", {})
    # Find energy menu: try "energy" first, then look for key containing "energy"
    energy = data.get("energy")
    if not energy:
        for key, val in data.items():
            if isinstance(val, dict) and "energy" in key:
                energy = val
                break
    if not energy:
        return result

    for group in energy.get("items", []):
        for item in group:
            item_type = item.get("itemType")
            item_code = item.get("itemCode")
            signal = item.get("itemCodeSignal") or item.get("itemCode", "")

            # Work mode (select) - match by itemCode "work_mode" or "WORK_MODE_CMB"
            if item_code in ("work_mode", "WORK_MODE_CMB") and item_type == "3":
                try:
                    options = json.loads(item.get("optVal", "[]"))
                    result["work_mode_options"] = [
                        {"label": opt["name"], "value": opt["value"], "signal": signal}
                        for opt in options
                    ]
                except (json.JSONDecodeError, KeyError):
                    _LOGGER.error("Failed to parse work mode options")
                continue

            # Build field info
            field = {
                "code": item_code,
                "signal": signal,
                "type": item_type,
                "name": item.get("itemName", ""),
            }

            # Listener (show/hide based on work mode)
            listener = item.get("listener")

            # Number input (type=1)
            if item_type == "1":
                field["min"] = item.get("minVal", "")
                field["max"] = item.get("maxVal", "")

            # Select (type=3)
            if item_type == "3":
                try:
                    field["options"] = json.loads(item.get("optVal", "[]"))
                except (json.JSONDecodeError, KeyError):
                    field["options"] = []

            # Switch (type=4)
            if item_type == "4":
                field["onVal"] = item.get("onVal")
                field["offVal"] = item.get("offVal")

            # Time range (type=6)
            if item_type == "6":
                field["format"] = item.get("defFmt", "HH:mm")

            # Collapsible time period: has "structure" field (itemType may be 82/83/10 etc)
            if item.get("structure"):
                idx_map = {"charge_mode": 1, "chg_pwr_lmt": 2, "start_time": 3, "end_time": 4}
                children = []
                for child in item.get("structure"):
                    code = child.get("itemCode", "")
                    ct = child.get("itemType", "")
                    c = {
                        "code": code,
                        "type": ct if ct not in ("5", "6") else "5",
                        "name": child.get("itemName", ""),
                        "index": idx_map.get(code, 0),
                    }
                    if ct == "1":
                        dv = child.get("defVal", "")
                        try:
                            bounds = json.loads(dv) if dv else []
                            c["min"] = str(bounds[0]) if len(bounds) > 0 else child.get("minVal", "0")
                            c["max"] = str(bounds[1]) if len(bounds) > 1 else child.get("maxVal", "99999")
                        except (json.JSONDecodeError, ValueError):
                            c["min"] = child.get("minVal", "0")
                            c["max"] = child.get("maxVal", "99999")
                    if ct == "3":
                        try:
                            c["options"] = json.loads(child.get("optVal", "[]"))
                        except (json.JSONDecodeError, KeyError):
                            c["options"] = []
                    children.append(c)

                # Check if we need to expand (82/83 with itemCodeSignal) or use as-is (10 with individual items)
                if item_type in ("82", "83") and item.get("itemCodeSignal"):
                    # Expand to 3 slots
                    base_code = item_code.rstrip("0123456789")
                    base_name = field["name"].rstrip("0123456789").rstrip()
                    for i in range(3):
                        slot = {
                            "code": f"{base_code}{i}",
                            "signal": f"{signal}{i}" if not signal[-1].isdigit() else f"{signal[:-1]}{i}",
                            "type": "collapse",
                            "name": f"{base_name}{i + 1}",
                            "children": children,
                        }
                        if listener:
                            slot["listener_code"] = listener.get("code", "")
                            slot["listener_show"] = listener.get("show", "")
                        if item.get("hidden"):
                            slot["hidden"] = True
                        result["fields"].append(slot)
                else:
                    # Use as-is (itemType=10, already individual items)
                    field["type"] = "collapse"
                    field["children"] = children
                    if listener:
                        field["listener_code"] = listener.get("code", "")
                        field["listener_show"] = listener.get("show", "")
                    if item.get("hidden"):
                        field["hidden"] = True
                    result["fields"].append(field)
                continue

            # Listener for non-collapse fields
            if listener:
                field["listener_code"] = listener.get("code", "")
                field["listener_show"] = listener.get("show", "")

            # Hidden by default
            if item.get("hidden"):
                field["hidden"] = True

            result["fields"].append(field)

    return result


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
    _attr_entity_registry_visible_default = False

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.data['sn']}_work_mode"
        self._work_mode_options = []
        self._energy_fields = []
        self._signal = "WORK_MODE_CMB"
        self._menu_loaded = False

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.data["sn"])},
            name=f"Hanchuess {self._entry.data['sn']}",
            manufacturer="Hanchuess",
            model="ESS Device",
        )

    @property
    def extra_state_attributes(self):
        fast_chg = self.coordinator.data.get("deviceStatusOfTestFastChg")
        remain = self.coordinator.data.get("testTimeRemain")
        attrs = {
            "sn": self._entry.data["sn"],
            "energy_fields": self._energy_fields,
            "work_mode_options": self._work_mode_options,
        }
        if fast_chg is not None:
            attrs["fast_chg_status"] = fast_chg
        if remain is not None:
            attrs["fast_chg_remain"] = remain
        return attrs

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
        await super().async_added_to_hass()
        await self._refresh_menu()

    async def async_update(self) -> None:
        if not self._menu_loaded:
            await self._refresh_menu()
        await super().async_update()

    async def _refresh_menu(self) -> None:
        language = self.hass.config.language or "en"
        sn = self._entry.data["sn"]
        menu_data = await self.coordinator.client.async_get_menu(sn, language)
        parsed = _parse_energy_menu(menu_data)
        if parsed["work_mode_options"]:
            self._work_mode_options = parsed["work_mode_options"]
            self._signal = parsed["work_mode_options"][0].get("signal", "WORK_MODE_CMB")
            self._energy_fields = parsed["fields"]
            self._menu_loaded = True

    async def async_select_option(self, option: str) -> None:
        for opt in self._work_mode_options:
            if opt["label"] == option:
                value = opt["value"]
                break
        else:
            return

        success = await self.coordinator.client.async_device_control(
            self._entry.data["sn"],
            self._entry.data.get("dev_type", "2"),
            {self._signal: str(value)},
        )
        if success.get("success"):
            await self.coordinator.async_request_refresh()

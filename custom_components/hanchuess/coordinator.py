"""DataUpdateCoordinator for Hanchuess."""
import logging
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed
from .api import HanchuessApiClient, ReauthRequired

_LOGGER = logging.getLogger(__name__)

REALTIME_INTERVAL = timedelta(seconds=60)
STATISTICS_INTERVAL = timedelta(minutes=5)


class HanchuessRealtimeCoordinator(DataUpdateCoordinator):
    """Realtime data coordinator (30s)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: HanchuessApiClient):
        super().__init__(
            hass,
            _LOGGER,
            name="hanchuess_realtime",
            update_interval=REALTIME_INTERVAL,
        )
        self.entry = entry
        self.client = client

    async def _async_update_data(self) -> dict:
        sn = self.entry.data["sn"]
        language = self.hass.config.language or "en"

        try:
            if self.client.should_refresh_token():
                await self.client.async_refresh_token()
        except ReauthRequired:
            raise ConfigEntryAuthFailed("Token refresh returned 90076, reauth required")

        data = await self.client.async_get_device_status(sn, language)

        if data and data.get("_token_expired"):
            try:
                new_token = await self.client.async_refresh_token()
            except ReauthRequired:
                raise ConfigEntryAuthFailed("Token refresh returned 90076, reauth required")
            if new_token:
                self._update_entry_token(new_token)
                data = await self.client.async_get_device_status(sn, language)

        if data and data.get("_token_expired"):
            raise ConfigEntryAuthFailed("Token expired and refresh failed")

        if not data:
            raise UpdateFailed("Failed to get device status")
        return data

    def _update_entry_token(self, token: str):
        self.hass.config_entries.async_update_entry(
            self.entry, data={**self.entry.data, "token": token}
        )


class HanchuessStatisticsCoordinator(DataUpdateCoordinator):
    """Statistics data coordinator (5min)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: HanchuessApiClient):
        super().__init__(
            hass,
            _LOGGER,
            name="hanchuess_statistics",
            update_interval=STATISTICS_INTERVAL,
        )
        self.entry = entry
        self.client = client

    async def _async_update_data(self) -> dict:
        sn = self.entry.data["sn"]
        language = self.hass.config.language or "en"

        data = await self.client.async_get_device_statistics(sn, language)

        if data and data.get("_token_expired"):
            try:
                new_token = await self.client.async_refresh_token()
            except ReauthRequired:
                raise ConfigEntryAuthFailed("Token refresh returned 90076, reauth required")
            if new_token:
                self._update_entry_token(new_token)
                data = await self.client.async_get_device_statistics(sn, language)

        if data and data.get("_token_expired"):
            raise ConfigEntryAuthFailed("Token expired and refresh failed")

        if not data:
            raise UpdateFailed("Failed to get device statistics")
        return data

    def _update_entry_token(self, token: str):
        self.hass.config_entries.async_update_entry(
            self.entry, data={**self.entry.data, "token": token}
        )

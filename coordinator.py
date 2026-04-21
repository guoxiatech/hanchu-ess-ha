"""DataUpdateCoordinator for Hanchuess."""
import logging
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .api import HanchuessApiClient

_LOGGER = logging.getLogger(__name__)

REALTIME_INTERVAL = timedelta(seconds=30)
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
        device_id = self.entry.data["device_id"]
        language = self.hass.config.language or "en"

        if self.client.should_refresh_token():
            await self.client.async_refresh_token()

        data = await self.client.async_get_device_status(device_id, language)

        if data and data.get("_token_expired"):
            new_token = await self.client.async_refresh_token()
            if new_token:
                data = await self.client.async_get_device_status(device_id, language)

        if not data or data.get("_token_expired"):
            raise UpdateFailed("Failed to get device status")
        return data


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
        device_id = self.entry.data["device_id"]
        language = self.hass.config.language or "en"

        data = await self.client.async_get_device_statistics(device_id, language)

        if data and data.get("_token_expired"):
            new_token = await self.client.async_refresh_token()
            if new_token:
                data = await self.client.async_get_device_statistics(device_id, language)

        if not data or data.get("_token_expired"):
            raise UpdateFailed("Failed to get device statistics")
        return data

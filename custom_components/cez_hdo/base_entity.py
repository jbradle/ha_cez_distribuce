"""Base entity for CEZ HDO sensors."""
from __future__ import annotations
import json
import logging
import time
from datetime import timedelta, datetime, time as dt_time
from pathlib import Path
from typing import Any

import requests
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from homeassistant.helpers.event import async_track_time_interval

from . import downloader

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=86400)  # 24 hodin
_LOGGER = logging.getLogger(__name__)

DOMAIN = "cez_hdo"


class CezHdoBaseEntity(Entity):
    """Base class for CEZ HDO entities."""

    def __init__(self, ean: str, name: str, signal: str | None = None) -> None:
        """Initialize the sensor."""
        self.ean = ean
        self.signal = signal
        self._name = name
        self._response_data: dict[str, Any] | None = None
        self._last_update_success = False
        self._last_update_time = None
        self.update()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass, register for daily updates."""
        await super().async_added_to_hass()
        
        # Register this entity for daily refresh
        if DOMAIN not in self.hass.data:
            self.hass.data[DOMAIN] = {}
        if "entities" not in self.hass.data[DOMAIN]:
            self.hass.data[DOMAIN]["entities"] = []
        
        if self not in self.hass.data[DOMAIN]["entities"]:
            self.hass.data[DOMAIN]["entities"].append(self)

    async def async_will_remove_from_hass(self) -> None:
        """When entity is removed, unregister from daily updates."""
        if (DOMAIN in self.hass.data 
            and "entities" in self.hass.data[DOMAIN]
            and self in self.hass.data[DOMAIN]["entities"]):
            self.hass.data[DOMAIN]["entities"].remove(self)
        
        await super().async_will_remove_from_hass()

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{DOMAIN}_{self._name}"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return f"{DOMAIN}_{self._name}"

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state."""
        return True

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attributes = {}
        if self._response_data is not None:
            attributes["response_json"] = self._response_data
        return attributes

    @Throttle(MIN_TIME_BETWEEN_SCANS)
    def update(self) -> None:
        """Fetch new state data for the sensor with cache fallback."""
        # Pokusit se načíst z cache jako první priorita
        cache_paths = [
            "/config/www/cez_hdo/cez_hdo.json",
            "/config/www/cez_hdo_debug.json",
            "/mnt/ha-config/www/cez_hdo/cez_hdo.json",
            "/mnt/ha-config/www/cez_hdo_debug.json",
        ]

        # Nejdříve zkusit načíst z cache
        for cache_path in cache_paths:
            if self._load_from_cache(cache_path):
                _LOGGER.info("CEZ HDO: Loaded from cache: %s", cache_path)
                return

        # Pokud cache není dostupná, zkusit API se zkrácenými timeouty
        for attempt in range(2):  # Až 2 pokusy
            try:
                api_url = downloader.BASE_URL
                request_data = downloader.get_request_data(self.ean)

                _LOGGER.info(
                    "🌐 CEZ HDO: Cache not found, trying API (attempt %d/2) - URL: %s, EAN: %s",
                    attempt + 1,
                    api_url,
                    self.ean,
                )

                response = requests.post(
                    api_url,
                    json=request_data,
                    timeout=10,
                    headers={
                        "Accept": "application/json, text/plain, */*",
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    },
                )

                _LOGGER.info("CEZ HDO: HTTP Response status: %d", response.status_code)

                if response.status_code == 200:
                    try:
                        content_str = response.content.decode("utf-8")
                        _LOGGER.debug(
                            "CEZ HDO: Response content length: %d bytes",
                            len(content_str),
                        )

                        json_data = json.loads(content_str)

                        # Check if we have signals data
                        signals_count = len(
                            json_data.get("data", {}).get("signals", [])
                        )
                        _LOGGER.info(
                            "✅ CEZ HDO: API success, signals: %d", signals_count
                        )

                        if signals_count > 0:
                            self._response_data = json_data
                            self._last_update_success = True

                            # Uložit do cache
                            for cache_path in cache_paths:
                                try:
                                    cache_dir = Path(cache_path).parent
                                    cache_dir.mkdir(parents=True, exist_ok=True)
                                    with open(cache_path, "w", encoding="utf-8") as f:
                                        json.dump(
                                            json_data, f, ensure_ascii=False, indent=2
                                        )
                                    _LOGGER.info(
                                        "💾 CEZ HDO: Data saved to cache: %s",
                                        cache_path,
                                    )
                                    break
                                except Exception as cache_err:
                                    _LOGGER.warning(
                                        "CEZ HDO: Cache save failed for %s: %s",
                                        cache_path,
                                        cache_err,
                                    )
                            return
                        else:
                            _LOGGER.warning("CEZ HDO: API returned empty signals array")
                    except (json.JSONDecodeError, UnicodeDecodeError) as parse_err:
                        _LOGGER.error(
                            "CEZ HDO: Failed to parse API response: %s", parse_err
                        )
                elif response.status_code == 502:
                    _LOGGER.warning(
                        "CEZ HDO: Server error 502 - retrying in 3 seconds..."
                    )
                    if attempt == 0:  # Pouze při prvním pokusu čekej
                        time.sleep(3)
                        continue
                else:
                    _LOGGER.error(
                        "CEZ HDO: API request failed - Status: %d", response.status_code
                    )

            except requests.RequestException as req_err:
                _LOGGER.error(
                    "CEZ HDO: Network error (attempt %d/2): %s", attempt + 1, req_err
                )
                if attempt == 0:  # Pouze při prvním pokusu čekej
                    time.sleep(2)
                    continue
            except Exception as general_err:
                _LOGGER.error(
                    "CEZ HDO: Unexpected error during API call: %s", general_err
                )

            break  # Ukončit smyčku pokud nedošlo k 502 nebo network error

        # Pokud vše selže
        _LOGGER.warning("CEZ HDO: Both cache and API failed")
        self._last_update_success = False

    def _save_to_cache(self, cache_file: str, content: str) -> None:
        """Save content to cache file."""
        try:
            # Zajistit že složka existuje
            cache_dir = Path(cache_file).parent
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Uložit soubor
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(content)
            _LOGGER.debug("CEZ HDO: Data cached to %s", cache_file)
        except Exception as e:
            _LOGGER.warning("CEZ HDO: Cache save failed: %s", str(e)[:50])

    def _load_from_cache(self, cache_file: str) -> bool:
        """Load data from cache file. Returns True if successful."""
        try:
            if not Path(cache_file).exists():
                return False

            with open(cache_file, "r", encoding="utf-8") as f:
                content = f.read()

            json_data = json.loads(content)
            self._response_data = json_data
            self._last_update_success = True
            return True

        except Exception:
            return False

    def _get_hdo_data(self) -> tuple[bool, Any, Any, Any, bool, Any, Any, Any]:
        """Get HDO data from response."""
        if self._response_data is None or not self._last_update_success:
            _LOGGER.warning(
                "CEZ HDO: No data available for parsing (data=%s, success=%s)",
                self._response_data is not None,
                self._last_update_success,
            )
            return False, None, None, None, False, None, None, None

        try:
            # Pass signal parameter to isHdo if specified
            if self.signal:
                result = downloader.isHdo(
                    self._response_data, preferred_signal=self.signal
                )
            else:
                result = downloader.isHdo(self._response_data)
            _LOGGER.info("CEZ HDO: Parser result: %s", result)
            return result
        except (KeyError, TypeError) as err:
            _LOGGER.error("Error processing HDO data: %s", err)
            return False, None, None, None, False, None, None, None

    def get_low_tariff_remaining_seconds(self) -> int | None:
        """Get remaining seconds of current low tariff period."""
        hdo_data = self._get_hdo_data()
        low_tariff_active = hdo_data[0]
        low_tariff_end = hdo_data[2]

        if not low_tariff_active or low_tariff_end is None:
            return None

        now = datetime.now(tz=downloader.CEZ_TIMEZONE)
        end_today = datetime.combine(now.date(), low_tariff_end, tzinfo=downloader.CEZ_TIMEZONE)

        # Pokud je konec před současným časem, jedná se o konec zítra
        if end_today <= now:
            end_today = end_today.replace(day=end_today.day + 1)

        remaining = (end_today - now).total_seconds()
        return max(0, int(remaining))

    def get_high_tariff_remaining_seconds(self) -> int | None:
        """Get remaining seconds of current high tariff period."""
        hdo_data = self._get_hdo_data()
        high_tariff_active = hdo_data[4]
        high_tariff_end = hdo_data[6]

        if not high_tariff_active or high_tariff_end is None:
            return None

        now = datetime.now(tz=downloader.CEZ_TIMEZONE)
        end_today = datetime.combine(now.date(), high_tariff_end, tzinfo=downloader.CEZ_TIMEZONE)

        # Pokud je konec před současným časem, jedná se o konec zítra
        if end_today <= now:
            end_today = end_today.replace(day=end_today.day + 1)

        remaining = (end_today - now).total_seconds()
        return max(0, int(remaining))

    def get_next_low_tariff_seconds(self) -> int | None:
        """Get seconds until next low tariff period starts."""
        hdo_data = self._get_hdo_data()
        low_tariff_active = hdo_data[0]
        low_start = hdo_data[1]

        if low_tariff_active or low_start is None:
            return None

        now = datetime.now(tz=downloader.CEZ_TIMEZONE)
        start_today = datetime.combine(now.date(), low_start, tzinfo=downloader.CEZ_TIMEZONE)

        # Pokud je start před současným časem, jedná se o start zítra
        if start_today <= now:
            start_today = start_today.replace(day=start_today.day + 1)

        remaining = (start_today - now).total_seconds()
        return max(0, int(remaining))

    def get_next_high_tariff_seconds(self) -> int | None:
        """Get seconds until next high tariff period starts."""
        hdo_data = self._get_hdo_data()
        high_tariff_active = hdo_data[4]
        high_start = hdo_data[5]

        if high_tariff_active or high_start is None:
            return None

        now = datetime.now(tz=downloader.CEZ_TIMEZONE)
        start_today = datetime.combine(now.date(), high_start, tzinfo=downloader.CEZ_TIMEZONE)

        # Pokud je start před současným časem, jedná se o start zítra
        if start_today <= now:
            start_today = start_today.replace(day=start_today.day + 1)

        remaining = (start_today - now).total_seconds()
        return max(0, int(remaining))


class CezHdoFrequentUpdateEntity(CezHdoBaseEntity):
    """Entity that updates every second for time remaining displays."""

    def __init__(self, ean: str, name: str, signal: str | None = None) -> None:
        """Initialize the frequently updating entity."""
        super().__init__(ean, name, signal)
        self._update_interval_unsub = None

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass, start the update timer."""
        await super().async_added_to_hass()
        
        # Update every second for time remaining calculations
        self._update_interval_unsub = async_track_time_interval(
            self.hass, self._async_update_state, timedelta(seconds=1)
        )

    async def async_will_remove_from_hass(self) -> None:
        """When entity is removed, stop the update timer."""
        if self._update_interval_unsub:
            self._update_interval_unsub()
        await super().async_will_remove_from_hass()

    async def _async_update_state(self, now=None) -> None:
        """Update the entity state without fetching new data."""
        self.async_schedule_update_ha_state()

    @property
    def should_poll(self) -> bool:
        """These entities don't need traditional polling."""
        return False

    def update(self) -> None:
        """Override update to prevent throttling on frequent entities."""
        # Don't call the parent update() method as it's throttled
        # We rely on the existing data from the daily updates
        pass

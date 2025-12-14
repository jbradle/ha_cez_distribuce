"""Platform for sensor integration."""
from __future__ import annotations
import logging
from datetime import time
import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorEntity,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .base_entity import CezHdoBaseEntity, CezHdoFrequentUpdateEntity
from . import downloader

_LOGGER = logging.getLogger(__name__)

CONF_EAN = "ean"
CONF_SIGNAL = "signal"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_EAN): cv.string,
        vol.Optional(CONF_SIGNAL): cv.string,
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the CEZ HDO sensor platform."""
    ean = config[CONF_EAN]
    signal = config.get(CONF_SIGNAL)

    entities = [
        LowTariffStart(ean, signal),
        LowTariffEnd(ean, signal),
        LowTariffDuration(ean, signal),
        HighTariffStart(ean, signal),
        HighTariffEnd(ean, signal),
        HighTariffDuration(ean, signal),
        LowTariffRemaining(ean, signal),
        HighTariffRemaining(ean, signal),
        NextLowTariffCountdown(ean, signal),
        NextHighTariffCountdown(ean, signal),
    ]
    add_entities(entities, True)


class CezHdoSensor(CezHdoBaseEntity, SensorEntity):
    """Base class for CEZ HDO sensors."""

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:home-clock"


class LowTariffStart(CezHdoSensor):
    """Sensor for low tariff start time."""

    def __init__(self, ean: str, signal: str | None = None) -> None:
        """Initialize the sensor."""
        super().__init__(ean, "LowTariffStart", signal)

    @property
    def native_value(self) -> time | None:
        """Return the state of the sensor."""
        hdo_data = self._get_hdo_data()
        return hdo_data[1]  # low_tariff_start


class LowTariffEnd(CezHdoSensor):
    """Sensor for low tariff end time."""

    def __init__(self, ean: str, signal: str | None = None) -> None:
        """Initialize the sensor."""
        super().__init__(ean, "LowTariffEnd", signal)

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:home-clock-outline"

    @property
    def native_value(self) -> time | None:
        """Return the state of the sensor."""
        hdo_data = self._get_hdo_data()
        return hdo_data[2]  # low_tariff_end


class LowTariffDuration(CezHdoSensor):
    """Sensor for low tariff duration."""

    def __init__(self, ean: str, signal: str | None = None) -> None:
        """Initialize the sensor."""
        super().__init__(ean, "LowTariffDuration", signal)

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:timer"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        hdo_data = self._get_hdo_data()
        duration = hdo_data[3]  # low_tariff_duration
        if duration is None:
            return None
        return downloader.format_duration(duration)


class HighTariffStart(CezHdoSensor):
    """Sensor for high tariff start time."""

    def __init__(self, ean: str, signal: str | None = None) -> None:
        """Initialize the sensor."""
        super().__init__(ean, "HighTariffStart", signal)

    @property
    def native_value(self) -> time | None:
        """Return the state of the sensor."""
        hdo_data = self._get_hdo_data()
        return hdo_data[5]  # high_tariff_start


class HighTariffEnd(CezHdoSensor):
    """Sensor for high tariff end time."""

    def __init__(self, ean: str, signal: str | None = None) -> None:
        """Initialize the sensor."""
        super().__init__(ean, "HighTariffEnd", signal)

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:home-clock-outline"

    @property
    def native_value(self) -> time | None:
        """Return the state of the sensor."""
        hdo_data = self._get_hdo_data()
        return hdo_data[6]  # high_tariff_end


class HighTariffDuration(CezHdoSensor):
    """Sensor for high tariff duration."""

    def __init__(self, ean: str, signal: str | None = None) -> None:
        """Initialize the sensor."""
        super().__init__(ean, "HighTariffDuration", signal)

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:timer"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        hdo_data = self._get_hdo_data()
        duration = hdo_data[7]  # high_tariff_duration
        if duration is None:
            return None
        return downloader.format_duration(duration)


class CezHdoTimeRemainingSensor(CezHdoFrequentUpdateEntity, SensorEntity):
    """Base class for time remaining sensors with frequent updates."""

    def __init__(self, ean: str, name: str, signal: str | None = None) -> None:
        """Initialize the sensor."""
        super().__init__(ean, name, signal)

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:timer-sand"

    @property
    def device_class(self) -> str:
        """Return the device class."""
        return "duration"

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "s"


class LowTariffRemaining(CezHdoTimeRemainingSensor):
    """Sensor for remaining time in current low tariff period."""

    def __init__(self, ean: str, signal: str | None = None) -> None:
        """Initialize the sensor."""
        super().__init__(ean, "LowTariffRemaining", signal)

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:timer-sand"

    @property
    def native_value(self) -> int | None:
        """Return the remaining seconds in current low tariff period."""
        return self.get_low_tariff_remaining_seconds()

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        attrs = super().extra_state_attributes
        remaining_seconds = self.get_low_tariff_remaining_seconds()
        
        if remaining_seconds is not None:
            hours = remaining_seconds // 3600
            minutes = (remaining_seconds % 3600) // 60
            seconds = remaining_seconds % 60
            attrs["formatted_time"] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            attrs["display_text"] = f"Zbývá {hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            attrs["formatted_time"] = None
            attrs["display_text"] = "Není aktivní"
            
        return attrs


class HighTariffRemaining(CezHdoTimeRemainingSensor):
    """Sensor for remaining time in current high tariff period."""

    def __init__(self, ean: str, signal: str | None = None) -> None:
        """Initialize the sensor."""
        super().__init__(ean, "HighTariffRemaining", signal)

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:timer-sand"

    @property
    def native_value(self) -> int | None:
        """Return the remaining seconds in current high tariff period."""
        return self.get_high_tariff_remaining_seconds()

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        attrs = super().extra_state_attributes
        remaining_seconds = self.get_high_tariff_remaining_seconds()
        
        if remaining_seconds is not None:
            hours = remaining_seconds // 3600
            minutes = (remaining_seconds % 3600) // 60
            seconds = remaining_seconds % 60
            attrs["formatted_time"] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            attrs["display_text"] = f"Zbývá {hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            attrs["formatted_time"] = None
            attrs["display_text"] = "Není aktivní"
            
        return attrs


class NextLowTariffCountdown(CezHdoTimeRemainingSensor):
    """Sensor for countdown to next low tariff period."""

    def __init__(self, ean: str, signal: str | None = None) -> None:
        """Initialize the sensor."""
        super().__init__(ean, "NextLowTariffCountdown", signal)

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:clock-fast"

    @property
    def native_value(self) -> int | None:
        """Return the seconds until next low tariff period."""
        return self.get_next_low_tariff_seconds()

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        attrs = super().extra_state_attributes
        remaining_seconds = self.get_next_low_tariff_seconds()
        
        if remaining_seconds is not None:
            hours = remaining_seconds // 3600
            minutes = (remaining_seconds % 3600) // 60
            seconds = remaining_seconds % 60
            attrs["formatted_time"] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            attrs["display_text"] = f"Za {hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            attrs["formatted_time"] = None
            attrs["display_text"] = "Již aktivní"
            
        return attrs


class NextHighTariffCountdown(CezHdoTimeRemainingSensor):
    """Sensor for countdown to next high tariff period."""

    def __init__(self, ean: str, signal: str | None = None) -> None:
        """Initialize the sensor."""
        super().__init__(ean, "NextHighTariffCountdown", signal)

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:clock-fast"

    @property
    def native_value(self) -> int | None:
        """Return the seconds until next high tariff period."""
        return self.get_next_high_tariff_seconds()

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        attrs = super().extra_state_attributes
        remaining_seconds = self.get_next_high_tariff_seconds()
        
        if remaining_seconds is not None:
            hours = remaining_seconds // 3600
            minutes = (remaining_seconds % 3600) // 60
            seconds = remaining_seconds % 60
            attrs["formatted_time"] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            attrs["display_text"] = f"Za {hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            attrs["formatted_time"] = None
            attrs["display_text"] = "Již aktivní"
            
        return attrs

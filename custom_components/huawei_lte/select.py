"""Support for Huawei LTE selects."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging

from huawei_lte_api.enums.net import LTEBandEnum, NetworkModeEnum

from homeassistant.components.select import (
    DOMAIN as SELECT_DOMAIN,
    SelectEntity,
    SelectEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import UNDEFINED

from . import Router
from .const import DOMAIN, KEY_NET_NET_MODE
from .entity import HuaweiLteBaseEntityWithDevice
from .net_mode import (
    KEY_LTE_BAND,
    KEY_NETWORK_MODE,
    lte_band_configurable,
    read_lte_band,
    read_router_network_mode,
    set_net_mode,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class HuaweiSelectEntityDescription(SelectEntityDescription):
    """Class describing Huawei LTE select entities."""

    availability_fn: Callable[[], bool] | None
    setter_fn: Callable[[str], None]
    state_fn: Callable[[str], str] | None


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up from config entry."""
    router: Router = hass.data[DOMAIN].routers[config_entry.entry_id]
    selects: list[Entity] = []

    network_mode_desc = HuaweiSelectEntityDescription(
        key=KEY_NET_NET_MODE,
        entity_category=EntityCategory.CONFIG,
        name="Preferred network mode",
        translation_key="preferred_network_mode",
        options=[
            NetworkModeEnum.MODE_AUTO.name,
            NetworkModeEnum.MODE_4G_3G_AUTO.name,
            NetworkModeEnum.MODE_4G_2G_AUTO.name,
            NetworkModeEnum.MODE_4G_ONLY.name,
            NetworkModeEnum.MODE_3G_2G_AUTO.name,
            NetworkModeEnum.MODE_3G_ONLY.name,
            NetworkModeEnum.MODE_2G_ONLY.name,
        ],
        availability_fn=lambda: True,
        setter_fn=lambda mode: set_net_mode(router, network_mode=NetworkModeEnum[mode]),
        state_fn=lambda raw: NetworkModeEnum(raw).name,
    )
    selects.append(
        HuaweiLteSelectEntity(
            router,
            entity_description=network_mode_desc,
            key=network_mode_desc.key,
            item=KEY_NETWORK_MODE,
        )
    )

    lte_band_desc = HuaweiSelectEntityDescription(
        key=KEY_NET_NET_MODE,
        entity_category=EntityCategory.CONFIG,
        name="Preferred LTE band",
        translation_key="preferred_lte_band",
        options=[
            LTEBandEnum.ALL.name,
            LTEBandEnum.B20.name,
            LTEBandEnum.B8.name,
            LTEBandEnum.B3.name,
            LTEBandEnum.B1.name,
            LTEBandEnum.B40.name,
            LTEBandEnum.B7.name,
            LTEBandEnum.B38.name,
        ],
        availability_fn=lambda: lte_band_configurable(read_router_network_mode(router)),
        setter_fn=lambda band: set_net_mode(router, lte_band=LTEBandEnum[band]),
        state_fn=lambda raw: read_lte_band(raw).name,
    )
    selects.append(
        HuaweiLteSelectEntity(
            router,
            entity_description=lte_band_desc,
            key=lte_band_desc.key,
            item=KEY_LTE_BAND,
        )
    )

    async_add_entities(selects, True)


class HuaweiLteSelectEntity(HuaweiLteBaseEntityWithDevice, SelectEntity):
    """Huawei LTE select entity."""

    entity_description: HuaweiSelectEntityDescription
    _raw_state: str | None = None

    def __init__(
        self,
        router: Router,
        entity_description: HuaweiSelectEntityDescription,
        key: str,
        item: str,
    ) -> None:
        """Initialize."""
        super().__init__(router)
        self.entity_description = entity_description
        self.key = key
        self.item = item

        name = None
        if self.entity_description.name != UNDEFINED:
            name = self.entity_description.name
        self._attr_name = name or self.item

    def select_option(self, option: str) -> None:
        """Change the selected option."""
        self.entity_description.setter_fn(option)

    @property
    def current_option(self) -> str | None:
        """Return current option."""
        return self._raw_state

    @property
    def _device_unique_id(self) -> str:
        return f"{self.key}.{self.item}"

    async def async_added_to_hass(self) -> None:
        """Subscribe to needed data on add."""
        await super().async_added_to_hass()
        self.router.subscriptions[self.key].append(f"{SELECT_DOMAIN}/{self.item}")

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from needed data on remove."""
        await super().async_will_remove_from_hass()
        self.router.subscriptions[self.key].remove(f"{SELECT_DOMAIN}/{self.item}")

    async def async_update(self) -> None:
        """Update state."""
        if not self.entity_description.availability_fn():
            self._available = False
            return

        try:
            value = self.router.data[self.key][self.item]
        except KeyError:
            _LOGGER.debug("%s[%s] not in data", self.key, self.item)
            self._available = False
            return
        self._available = True
        self._raw_state = self.entity_description.state_fn(value)

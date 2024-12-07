"""Helper methods for things that use the net_mode endpoint."""

from __future__ import annotations

from huawei_lte_api.enums.net import LTEBandEnum, NetworkBandEnum, NetworkModeEnum

from . import Router
from .const import KEY_NET_NET_MODE

KEY_NETWORK_MODE = "NetworkMode"
KEY_LTE_BAND = "LTEBand"


def read_router_network_mode(router: Router):
    """Read network mode from router."""
    try:
        return NetworkModeEnum(router.data[KEY_NET_NET_MODE][KEY_NETWORK_MODE])
    except KeyError:
        return None


def lte_band_configurable(network_mode: NetworkModeEnum | None):
    """Return whether or not LTE band is configurable in this mode."""
    return network_mode and "03" in network_mode.value


def read_lte_band(raw: str):
    """Read LTE band from raw string."""
    value = int(raw, 16)
    if value in LTEBandEnum.__members__.values():
        return LTEBandEnum(value)
    return LTEBandEnum.ALL


def set_net_mode(
    router: Router,
    *,
    lte_band: LTEBandEnum | None = None,
    network_mode: NetworkModeEnum | None = None,
) -> None:
    """Set one property for net_mode on a router, preserving existing settings for other properties."""
    net_mode_data: dict[str, str] = router.data[KEY_NET_NET_MODE]

    if network_mode is None:
        network_mode = NetworkModeEnum(net_mode_data[KEY_NETWORK_MODE])

    if not lte_band_configurable(network_mode):
        lte_band = LTEBandEnum.ALL
    elif lte_band is None:
        lte_band = read_lte_band(net_mode_data[KEY_LTE_BAND])

    router.client.net.set_net_mode(lte_band, NetworkBandEnum.ALL, network_mode)

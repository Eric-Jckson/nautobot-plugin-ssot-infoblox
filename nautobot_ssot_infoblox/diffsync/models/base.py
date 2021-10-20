"""Base Shared Models for Infoblox integration with SSoT plugin."""

from typing import Optional, List
from diffsync import DiffSyncModel

from nautobot.ipam.models import IPAddress as OrmIPAddress
from nautobot.ipam.models import Prefix as OrmPrefix
from nautobot.extras.models import Status as OrmStatus


class Network(DiffSyncModel):
    """Network model for DiffSync"""

    _modelname = "prefix"
    _identifiers = ("network",)

    network: str


class IPAddress(DiffSyncModel):
    """IPAddress model for DiffSync"""

    _modelname = "ipaddress"
    _identifiers = ("address", "prefix")
    _shortname = ("address",)
    _attributes = ("status", "dns_name")

    address: str
    prefix: str
    status: Optional[str]
    dns_name: Optional[str]
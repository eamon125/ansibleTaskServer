# -*- coding:utf-8 -*-
from ansible.inventory.manager import InventoryManager
from ansible import constants as C
from ansible.errors import AnsibleError
from ansible.utils.path import unfrackpath
from ansible.utils.display import Display
from typing import NoReturn, Any, Dict, NamedTuple
from dataclasses import dataclass
from collections.abc import Mapping
from collections import namedtuple

display = Display()


@dataclass
class InventoryManagerFix(InventoryManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def parse_sources(self, cache: bool = False) -> NoReturn:
        ''' iterate over inventory sources and parse each one to populate it'''

        parsed = False
        # allow for multiple inventory parsing
        for source in self._sources:

            if source:
                if ',' not in source:
                    source = unfrackpath(source, follow=False)
                parse = self.parse_source(source, cache=cache)
                if parse and not parsed:
                    parsed = True

        if parsed:
            # do post processing
            self._inventory.reconcile_inventory()
        else:
            if C.INVENTORY_UNPARSED_IS_FAILED:
                raise AnsibleError(
                    "No inventory was parsed, please check your configuration and options.")
            else:
                # FIX: parser inventory from dict or list
                # display.warning("No inventory was parsed, only implicit localhost is available")
                pass


@dataclass
class CustomInventoryManager(Mapping):
    """Customized Inventory Manager.
    Args:
        loader: loader is InventoryData object, InventoryData no method name 'get_vars'.
        sources: sources is a inventory file path.
        resource:
            Example resource:
                {
                "group_name": {
                                "hosts": [{"hostname": "10.0.0.0", "port": "22",
                                           "username": "test", "password": "pass"}],
                                "vars": {"var1": value1, "var2": value2}
                            }
                }

                or:

                [{"hostname": "10.0.0.0", "port": "22", "username": "test", "password": "pass"}]
                or:
                {
                "group_name": {
                                "hosts": [{"hostname": "10.0.0.0", "port": "22",
                                           "username": "test", "password": "pass"}],
                                "vars": {"var1": value1, "var2": value2}
                            },
                "all": [{"hostname": "10.0.0.1", "port": "22",
                         "username": "test", "password": "pass"}]
                }
                or:
                {
                "group_name": {
                                "hosts": [{"hostname": "10.0.0.0", "port": "22",
                                           "username": "test", "password": "pass"}],
                                "vars": {"var1": value1, "var2": value2}
                            },
                "all": {
                                "hosts": [{"hostname": "10.0.0.1", "port": "22",
                                           "username": "test", "password": "pass"}],
                                "vars": {"var1": value1, "var2": value2}
                        }
                }

    """
    __slots__ = ("loader", "resource", "sources", "inventory")
    loader: Any
    resource: Any
    sources: str

    def __post_init__(self):
        setattr(self, "inventory", InventoryManagerFix(self.loader, sources=self.sources))
        getattr(self, "inventory").add_group("all")
        self.generate_inventory()

    def add_group_2(self, hosts: str, group_name: str, group_vars: Dict[str, str] = {}):
        """Add a group.
        Args:
            hosts: Host name.
            group_name: Group name.
            group_vars: Grouping variable.
        """
        if group_name != "all":
            getattr(self, "inventory").add_group(group_name)

        for host in hosts:
            if "hostname" not in list(host.keys()):
                continue
            hostname = host.get("hostname")
            getattr(self, "inventory").add_host(host=hostname, group=group_name)
            if group_name != "all":
                getattr(self, "inventory").add_host(host=hostname, group="all")

            host_info = getattr(self, "inventory").get_host(hostname=hostname)
            for k, v in host.items():
                if k != "hostname":
                    host_info.set_variable(k, v)

            if group_vars:
                group_info = getattr(self, "inventory").groups.get(group_name, None)
                if group_info:
                    for k, v in group_vars.items():
                        group_info.set_variable(k, v)

    def generate_inventory(self):
        """Generate a customized inventory list.
        """
        if isinstance(self.resource, list):
            self.add_group_2(self.resource, "all")
        elif isinstance(self.resource, dict):
            for group_name, hosts_vars in self.resource.items():
                if group_name == "all":
                    if isinstance(hosts_vars, list):
                        self.add_group_2(hosts_vars, "all")
                    elif isinstance(hosts_vars, dict):
                        self.add_group_2(hosts_vars["hosts"], "all", hosts_vars["vars"])
                else:
                    self.add_group_2(hosts_vars["hosts"], group_name, hosts_vars["vars"])

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __iter__(self):
        return iter([s.lstrip('_') for s in self.__slots__])

    def __len__(self) -> int:
        return len(self.__slots__)

    def __repr__(self) -> NamedTuple:
        named = namedtuple("Inventory", [s.lstrip('_') for s in self.__slots__])
        return named._make([str(getattr(self, attr.lstrip('_'))) for attr in self.__slots__])

    def __str__(self) -> str:
        return str(self.__repr__())


# -*- coding:utf-8 -*-
import os
import json
from dataclasses import dataclass
from collections.abc import Mapping
from collections import namedtuple
from typing import NamedTuple, Any, NoReturn, Dict
from configs import settings, ROOT_PATH, play_config
# from tools.ini2json import serializer
from pprint import pprint


@dataclass
class Playbook(Mapping):
    """Generate an Ansible Playbook object
    Args:
        name: Playbook's name.
    """
    __fields = ("name", 'inventory_json' "play_path", "play_file", "role_path",
                 "extra_vars")

    name: str
    inventory_json: str

    def __post_init__(self) -> NoReturn:
        play_path = os.path.join(os.path.join(
            ROOT_PATH, settings.play.playbook_path), self.name)
        play_file = os.path.join(play_path, "%s.yml" % self.name)
        extra_vars_file = os.path.join(play_path, "vars.yml")
        role_path = os.path.join(
            ROOT_PATH, settings.play.roles_path)
        if not os.path.exists(play_path) or not os.path.exists(role_path):
            raise FileNotFoundError(
                "Playbook {%s} does not exists!" % self.name)
        setattr(self, "play_path", play_path)
        setattr(self, "play_file", play_file)
        setattr(self, "role_path", role_path)
        setattr(self, "inventory_json", json.loads(self.inventory_json))
        setattr(self, "extra_vars", extra_vars_file)

    @property
    def inventory2json(self) -> Dict[str, Dict[str, Any]]:
        """ Format the host list as a json string.
        Returns:
            Inventory is converted to a dict in dict format.
            example:

                {'all': {'hosts': [{'ansible_ssh_pass': 'qwer1234',
                                    'ansible_ssh_user': 'root',
                                    'hostname': '10.25.18.145'},
                                {'ansible_ssh_pass': 'qwer1234',
                                    'ansible_ssh_user': 'root',
                                    'hostname': '10.25.18.143'},
                                {'ansible_ssh_pass': 'qwer1234',
                                    'ansible_ssh_user': 'root',
                                    'hostname': '10.25.18.144'}],
                        'vars': {}},
                'jdk': {'hosts': [{'ansible_ssh_pass': 'qwer1234',
                                    'ansible_ssh_user': 'root',
                                    'hostname': '10.25.18.145'},
                                {'ansible_ssh_pass': 'qwer1234',
                                    'ansible_ssh_user': 'root',
                                    'hostname': '10.25.18.143'},
                                {'ansible_ssh_pass': 'qwer1234',
                                    'ansible_ssh_user': 'root',
                                    'hostname': '10.25.18.144'}],
                        'vars': {}}}
        """
        return getattr(self, "inventory_json")

    def host2json(self, host: str = "all") -> Dict[str, Dict[str, Any]]:
        """Enter host (can be all, group or single host in inventory)
           return host variable information
        Args:
            host: can be all, group or single host in inventory.

        Returns:
            Host variable information.
            example:

                {'jdk': {'hosts': ['10.25.18.144'], 'vars': {'x': 2, 'y': 1}}}
        """
        if host == "all":
            host_json = self.inventory2json
        elif host in list(self.inventory2json.keys()):
            host_json = {host: self.inventory2json[host]}
            host_json[host]["vars"].update(self.inventory2json["all"]["vars"])
            return host_json
        else:
            for group, hosts_var in self.inventory2json.items():
                if group != "all":
                    host_json = {group: {'hosts': [],
                                         'vars': self.inventory2json[group]["vars"]}}
                    for host_info in hosts_var['hosts']:
                        if host_info['hostname'] == host:
                            host_json[group]["hosts"].append(host_info)
                            return host_json
                    host_json[group]["vars"].update(
                        self.inventory2json["all"]["vars"])
            return host_json

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __iter__(self):
        return iter([s.lstrip('_') for s in self.__slots__])

    def __len__(self) -> int:
        return len(self.__slots__)

    def __repr__(self) -> NamedTuple:
        named = namedtuple("Playbook", [s.lstrip('_') for s in self.__slots__])
        return named._make([str(getattr(self, attr.lstrip('_'))) for attr in self.__slots__])

    def __str__(self) -> str:
        return str(self.__repr__())

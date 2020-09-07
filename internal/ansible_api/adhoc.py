# -*- coding:utf-8 -*-
import os
import yaml
from collections import namedtuple
from typing import Any, NamedTuple, OrderedDict, List
from dataclasses import dataclass

from configs import adhoc_config, base_dir, settings
from internal.ansible_api.playbook import Playbook


@dataclass
class AdHoc(Playbook):
    __slots__ = ("name", "inventory_json", "play_path", "module_alias", "examples")
    name: str
    inventory_json: str

    def __post_init__(self):
        setattr(self, "inventory_json", self.inventory_json)
        module_info = eval("adhoc_config.%s" % self.name)
        setattr(self, "module_alias", module_info.alias)
        module_conf = os.path.join(base_dir, module_info.config)
        with open(module_conf, "r") as f:
            content = yaml.safe_load(f.read().strip())
        setattr(self, "examples", content)

    def __repr__(self) -> NamedTuple:
        named = namedtuple("AdHoc", [s.lstrip('_') for s in self.__slots__])
        return named._make([str(getattr(self, attr.lstrip('_'))) for attr in self.__slots__])

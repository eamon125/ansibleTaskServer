# -*- coding:utf-8 -*-
import traceback
import shutil
import os
from dataclasses import dataclass
from collections.abc import Mapping
from collections import namedtuple
from typing import Any, Callable, NoReturn, NamedTuple, Dict
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible import context
from ansible.module_utils.common.collections import ImmutableDict
import ansible.constants as C
from ansible.playbook.play import Play
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.executor.task_queue_manager import TaskQueueManager

from internal.ansible_api.playbook import Playbook
from internal.ansible_api.inventory import CustomInventoryManager
from internal.ansible_api.callback import CallbackDefault
from internal.ansible_api.adhoc import AdHoc
from configs import settings


@dataclass
class PlayAPI(Mapping):
    """ Ansible Playbook API.
    Args:
        service: Playbook's name.
        hosts: Remote host operating the playbook.
        callback: Specify the ansible callback plugin.
        fork: The number of processes opened by ansible at the same time.
    """
    __fields = ("service", "inventory_json", "host", "callback", "fork", "playbook", "ssh_connection",
                "loader", "inventory", "passwords", "variable_manager")

    service: str
    inventory_json: str
    job_id: str
    # callback: Callable[..., NoReturn] = CallbackDefault()
    host: str = ""
    fork: int = int(settings.play.fork)
    ssh_connection: str = settings.play.ssh_connection

    def __post_init__(self):
        playbook = Playbook(name=self.service, inventory_json=self.inventory_json)
        loader = DataLoader()
        inventory2json = playbook.inventory2json
        if self.host != "all":
            inventory2json = playbook.host2json(host=self.host)

        inventory_manager = CustomInventoryManager(
            loader=loader, sources=None, resource=inventory2json)
        inventory = getattr(inventory_manager, "inventory")
        passwords = dict(vault_pass="")
        variable_manager = VariableManager(loader=loader, inventory=inventory)
        if self.ssh_connection == "paramiko":
            variable_manager._extra_vars.update({'ansible_paramiko_host_key_checking': 'no'})

        setattr(self, "playbook", playbook)
        setattr(self, "loader", loader)
        setattr(self, "inventory", inventory)
        setattr(self, "passwords", passwords)
        setattr(self, "variable_manager", variable_manager)

    def execute(self, tag: Any = None, callback_default: bool = False) -> NoReturn:
        """Playbook actuator.
        Args:
            tag: The tag of the tasks, the string is a single tag,
                 and the other sequence types are multiple tags.
            callback_default: Whether to use Ansible's default callback' plugin.
        """
        if tag is not None:
            tags = [tag, ] if isinstance(tag, str) else tag
            getattr(self, "variable_manager").__dict__[
                '_options_vars'].update({"ansible_run_tags": tags})
            context.CLIARGS = ImmutableDict(connection=self.ssh_connection,
                                            forks=self.fork,
                                            become=None,
                                            become_method=None,
                                            become_user=None,
                                            check=False,
                                            diff=False,
                                            syntax=None,
                                            verbosity=5,
                                            start_at_task=None,
                                            tags=tag)
        else:
            context.CLIARGS = ImmutableDict(connection=self.ssh_connection,
                                            forks=self.fork,
                                            become=None,
                                            become_method=None,
                                            become_user=None,
                                            check=False,
                                            diff=False,
                                            syntax=None,
                                            verbosity=5,
                                            start_at_task=None)
        extra_file = getattr(self, "playbook").extra_vars
        extra_vars = getattr(self, "loader").load_from_file(extra_file)

        getattr(self, "variable_manager").__dict__['_options_vars'].update(
            {'ansible_version': {'major': 2, 'full': '2.8.3',
                                 'string': '2.8.3', 'minor': 8, 'revision': 3}})

        # role path
        role_path = getattr(self, "playbook").role_path
        C.DEFAULT_ROLES_PATH.append(role_path)
        # 关闭ssh key检查, 对ssh_connection=smart生效.
        C.HOST_KEY_CHECKING = False
        # playbook path
        play_file = getattr(self, "playbook").play_file

        try:
            # 将inventory变量信息导入variable_manager
            inventory = getattr(self, "inventory")
            variable_manager = getattr(self, "variable_manager")

            variable_manager.set_inventory(inventory)
            loader = getattr(self, "loader")
            passwords = getattr(self, "passwords")
            playbook = PlaybookExecutor(playbooks=[play_file, ], inventory=inventory,
                                        variable_manager=variable_manager,
                                        loader=loader, passwords=passwords)
            call = CallbackDefault(job_id=self.job_id, service_name=self.service)
            playbook._tqm._stdout_callback = "default" if callback_default else call
            playbook.run()
        except Exception:
            traceback.print_exc()
        else:
            if playbook._tqm:
                playbook._tqm.cleanup()
                playbook._tqm._cleanup_processes()
            if loader:
                loader.cleanup_all_tmp_files()

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __iter__(self):
        return iter([s.lstrip('_') for s in self.__fields])

    def __len__(self) -> int:
        return len(self.__fields)

    def __repr__(self) -> NamedTuple:
        named = namedtuple(self.__class__.__name__, [s.lstrip('_') for s in self.__fields])
        return named._make([str(getattr(self, attr.lstrip('_'))) for attr in self.__fields])

    def __str__(self) -> str:
        return str(self.__repr__())


@dataclass
class AdHocAPI(Mapping):
    __fields = ("module", "host", "inventory_json", "arguments", "callback", "fork",
                "ssh_connection", "adhoc", "loader", "inventory", "passwords", "variable_manager")
    module: str
    host: str
    inventory_json: str
    fork: int = int(settings.adhoc.fork)
    callback: str = "CallbackDefault"
    ssh_connection: str = settings.adhoc.ssh_connection

    def __post_init__(self):
        adhoc = AdHoc(self.module, self.inventory_json)
        setattr(self, "examples", getattr(adhoc, "examples"))
        loader = DataLoader()

        inventory2json = adhoc.inventory2json
        if self.host != "all":
            inventory2json = adhoc.host2json(host=self.host)
        inventory_manager = CustomInventoryManager(
            loader=loader, sources=None, resource=inventory2json)
        inventory = getattr(inventory_manager, "inventory")
        passwords = dict(vault_pass="")
        variable_manager = VariableManager(loader=loader, inventory=inventory)
        if self.ssh_connection == "paramiko":
            variable_manager._extra_vars.update({'ansible_paramiko_host_key_checking': 'no'})

        setattr(self, "adhoc", adhoc)
        setattr(self, "loader", loader)
        setattr(self, "inventory", inventory)
        setattr(self, "passwords", passwords)
        setattr(self, "variable_manager", variable_manager)
        setattr(self, "module_path", settings.adhoc.module_path)

    def execute(self, tasks: Dict[str, Dict[str, str]], callback_default: bool = False) -> NoReturn:
        """Adhoc actuator.
        Args:
            tasks: Dictionary format for Linux directives and their arguments.

        """
        # Ansible 上下文
        # since the API is constructed for CLI it expects certain
        # options to always be set in the context object
        base_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../'))
        context.CLIARGS = ImmutableDict(connection=self.ssh_connection,
                                        module_path=[os.path.join(base_dir, getattr(self, "module_path"))],
                                        forks=self.fork,
                                        become=None,
                                        become_method=None,
                                        become_user=None,
                                        verbosity=5,
                                        check=False,
                                        diff=False)
        print('=====', os.path.join(base_dir, getattr(self, "module_path")))
        # 关闭ssh key检查, 对ssh_connection=smart生效.
        C.HOST_KEY_CHECKING = False
        # create data structure that represents our play, including tasks,
        # this is basically what our
        # YAML loader does internally.
        # tasks like: dict(action=dict(module='shell', args='ls'), register='shell_out')
        play_source = dict(name="Ansible Ad-Hoc",
                           hosts=self.host,
                           gather_facts='yes',
                           tasks=[tasks])
        # Create play object, playbook objects use .load instead of init or new methods,
        # this will also automatically create the task objects from the info provided in play_source
        play = Play().load(play_source,
                           variable_manager=getattr(self, "variable_manager"),
                           loader=getattr(self, "loader"))

        # Run it - instantiate task queue manager, which takes care of forking and setting up all
        # objects to iterate over host list and tasks
        tqm = None
        callback_default = 'minimal' if callback_default else eval(self.callback)()
        try:
            tqm = TaskQueueManager(inventory=getattr(self, "inventory"),
                                   variable_manager=getattr(self, "variable_manager"),
                                   loader=getattr(self, "loader"),
                                   passwords=getattr(self, "passwords"),
                                   stdout_callback=callback_default)
            # most interesting data for a play is actually sent to the callback's methods
            tqm.run(play)
        except Exception:
            traceback.print_exc()
        finally:
            # we always need to cleanup child procs and
            # the structures we use to communicate with them
            if tqm is not None:
                tqm.cleanup()

            # Remove ansible tmpdir
            shutil.rmtree(C.DEFAULT_LOCAL_TMP, True)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __iter__(self):
        return iter([s.lstrip('_') for s in self.__fields])

    def __len__(self) -> int:
        return len(self.__fields)

    def __repr__(self) -> NamedTuple:
        named = namedtuple(self.__class__.__name__, [s.lstrip('_') for s in self.__fields])
        return named._make([str(getattr(self, attr.lstrip('_'))) for attr in self.__fields])

    def __str__(self) -> str:
        return str(self.__repr__())


if __name__ == "__main__":
    # api = PlayAPI("jdk", host="all")
    api = AdHocAPI(module="file", host="all")
    cmd = dict(action=dict(module='shell', args="ifconfig"), register='shell_out')
    api.execute(cmd, callback_default=True)

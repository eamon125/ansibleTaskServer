# -*- coding:utf-8 -*-
import os
from typing import NamedTuple
import configparser
import logging
import logging.config
from collections import namedtuple
from multiprocessing import Queue


base_dir = os.path.dirname(os.path.abspath(__file__))
ROOT_PATH = os.path.dirname(os.path.realpath(base_dir))


def gen_config(name: str, path: str) -> NamedTuple:
    config_file = os.path.join(base_dir, path)
    config = configparser.ConfigParser()
    config.read(config_file)

    sections = config.sections()
    settings = namedtuple(name, sections)

    setting_map = {s: "" for s in sections}
    global TASK_QUEUE

    for section in sections:
        ops = config.options(section)

        if not ops:
            raise KeyError("Configuration %s is not allowed to be empty" % section)
        np = namedtuple(section, ops)

        setting_map[section] = np._make([config.get(section, op) for op in ops])
        if section == "listner":
            TASK_QUEUE = Queue()

    return settings._make([setting_map[section] for section in sections])

log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logging.ini')

# create logger
logger = logging.getLogger('console')

settings = gen_config("settings", "settings.ini")
play_config = gen_config("play_config", "play.ini")
adhoc_config = gen_config("adhoc_config", "adhoc.ini")
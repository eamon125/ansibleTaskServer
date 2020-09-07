import os
import sys
import configparser
from collections import namedtuple

base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(base_dir, "configs"))
import logging
from pathlib import PureWindowsPath

from . import __platform__
from .console import run_cmd
from .errors import ConfigurerException
if __platform__ == 'win32':
    import winreg


class KeyNotFoundError(ConfigurerException):
    pass

class UndefinedRegValueType(ConfigurerException):
    pass

class KeyPath(PureWindowsPath):
    def __init__(self, *args):
        super().__init__(*args)
        self.base_key = None
        self.key_path = str(self)
        if len(self.parents) > 1:
            self.base_key = str(self.parents[-2])
        if self.base_key:
            self.key_path = str(self.relative_to(self.base_key))


def reg_add(path, name, data_type, value):
    return run_cmd(['reg', 'add', path, '/f', '/v', name, '/t', data_type, '/d', value])

# def create_key(path, name):
#     logging.debug(f"Creating key: {path=}\\{name=}")
#     kp = KeyPath(path)
#     with winreg.OpenKey(_encode_base(kp.base_key), kp.key_path, access=winreg.KEY_WRITE) as key:
#         logging.debug(f"Opened key in write mode at: {kp.base_key=}/{kp.key_path=}")
#         winreg.CreateKeyEx(key, name)

def create_key(path):
    logging.debug(f"Creating key: {path}")
    kp = KeyPath(path)
    with winreg.CreateKeyEx(_encode_base(kp.base_key), kp.key_path):
        pass

def ensure_key(path, name):
    logging.debug(f"Ensuring key: {path=}\\{name=}")
    kp = KeyPath(path)
    if not key_exists(kp.parent, kp.name):
        ensure_key(kp.parent, kp.name)
    if not key_exists(path, name):
        create_key(path, name)

def ensure_key_value(path, name, data_type, value):
    kp = KeyPath(path)
    with winreg.CreateKeyEx(_encode_base(kp.base_key), kp.key_path) as key:
        logging.debug(f"Created/opened key at: {path}")
        dtype = _encode_type(data_type)
        logging.debug(f"Setting entry: {name=}; {dtype=}; {value=}")
        winreg.SetValueEx(key, name, 0, dtype, value)

def get_key_value(path, name):
    logging.debug(f"Getting key value at {path}\\{name}")
    kp = KeyPath(path)
    try:
        with winreg.OpenKey(_encode_base(kp.base_key), kp.key_path) as key:
            logging.debug(f"Opened key in read mode at: {kp.base_key}\\{kp.key_path}")
            value = winreg.QueryValueEx(key, name)
    except FileNotFoundError:
        value = None
    logging.debug(f"{value=}")
    return value

def key_exists(path, name):
    logging.debug(f"Checking if key exists: {path}\\{name}")
    path = KeyPath(path) / name
    try:
        with winreg.OpenKey(_encode_base(path.base_key), path.key_path):
            pass
        logging.debug("Key exists")
        return True
    except FileNotFoundError:
        logging.debug("Key not found.")
        return False

def set_key_value(path, name, data_type, value):
    logging.debug(f"Setting key at {path=}\\{name=}, {data_type=}, to {value=}")
    kp = KeyPath(path)
    try:
        with winreg.OpenKey(_encode_base(kp.base_key), kp.key_path, access=winreg.KEY_WRITE) as key:
            logging.debug(f"Opened key in write mode at: {kp.base_key}\\{kp.key_path}")
            winreg.SetValueEx(key, name, 0, _encode_type(data_type), value)
    except FileNotFoundError:
        raise KeyNotFoundError(f"Clé non trouvée : {path}")

def _encode_base(input_base):
    hkey_bases = {
        winreg.HKEY_CURRENT_USER: ['HKEY_CURRENT_USER', 'HKCU'],
        winreg.HKEY_LOCAL_MACHINE: ['HKEY_LOCAL_MACHINE', 'HKLM'],
        winreg.HKEY_USERS: ['HKEY_USERS']
    }
    for winreg_base, user_bases in hkey_bases.items():
        if input_base in user_bases:
            return winreg_base

def _encode_type(input_type):
    data_types = {
        'REG_SZ': winreg.REG_SZ,
        'REG_DWORD': winreg.REG_DWORD,
    }
    encoded_type = data_types.get(input_type)
    if encoded_type is None:
        raise UndefinedRegValueType(f"Registry Value Type inconnu : {input_type}")
    return encoded_type

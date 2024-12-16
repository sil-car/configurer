import logging
from pathlib import Path

from . import __platform__
from .console import run_cmd
from .errors import ConfigurerException
if __platform__ == 'win32':
    import winreg


class KeyNotFoundError(ConfigurerException):
    pass


class UndefinedRegValueType(ConfigurerException):
    pass


def reg_add(path, name, data_type, value):
    return run_cmd(['reg', 'add', path, '/f', '/v', name, '/t', data_type, '/d', value])

def create_key(path, name):
    logging.debug(f"Creating key: {path=}/{name=}")
    base, key_path = split_base_from_path(path)
    with winreg.OpenKey(base, key_path, access=winreg.KEY_WRITE) as key:
        logging.debug(f"Opened key in write mode at: {base=}/{key_path}")
        winreg.CreateKey(key, name)

def encode_base(input_base):
    hkey_bases = {
        winreg.HKEY_CURRENT_USER: ['HKEY_CURRENT_USER', 'HKCU'],
        winreg.HKEY_LOCAL_MACHINE: ['HKEY_LOCAL_MACHINE', 'HKLM'],
        winreg.HKEY_USERS: ['HKEY_USERS']
    }
    for winreg_base, user_bases in hkey_bases.items():
        if input_base in user_bases:
            return winreg_base
            break

def encode_type(input_type):
    data_types = {
        'REG_SZ': winreg.REG_SZ,
        'REG_DWORD': winreg.REG_DWORD,
    }
    encoded_type = data_types.get(input_type)
    if encoded_type is None:
        raise UndefinedRegValueType(f"Registry Value Type inconnu : {input_type}")

def ensure_key(path, name):
    logging.debug(f"Ensuring key: {path=}/{name=}")
    parent = get_key_parent_path(path)
    if not key_exists(parent):
        ensure_key(parent)
    create_key(path, name)

def get_key_parent_path(path):
    parts = split_path(path)
    return '\\'.join(parts[:-1])

def get_key_value(full_path, name):
    logging.debug(f"Getting key value {name=} at {full_path=}")
    base, key_path = split_base_from_path(full_path)
    try:
        with winreg.OpenKey(base, key_path) as key:
            logging.debug(f"Opened key in read mode at: {base=}/{key_path}")
            value = winreg.QueryValueEx(key, name)
            logging.debug(f"{value=}")
            return value
    except FileNotFoundError:
        value = None
        logging.debug(f"{value=}")
        return None

def key_exists(path):
    logging.debug(f"Checking if key exists: {path=}")
    base, key_path = split_base_from_path(path)
    try:
        with winreg.OpenKey(base, key_path):
            pass
        logging.debug("Key exists")
        return True
    except FileNotFoundError:
        logging.debug("Key not found.")
        return False

def set_key_value(path, name, data_type, value):
    logging.debug(f"Setting key {value=} of {data_type=} at {path=}/{name=}")
    base, key_path = split_base_from_path(path)
    dtype = encode_type(data_type)
    try:
        with winreg.OpenKey(base, key_path, access=winreg.KEY_WRITE) as key:
            logging.debug(f"Opened key in write mode at: {base=}/{key_path}")
            winreg.SetValueEx(key, name, dtype, value)
    except FileNotFoundError:
        raise KeyNotFoundError(f"Clé non trouvée : {path}")

def split_path(input_path):
    return Path(input_path).parts

def split_base_from_path(input_path):
    parts = split_path(input_path)
    base = f"{parts[0]}"
    path = '\\'.join(parts[1:])
    logging.debug(f"{base=}; {path=}")
    return base, path
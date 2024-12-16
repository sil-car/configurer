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
    base, key_path = split_base_from_path(path)
    with winreg.OpenKey(base, key_path, access=winreg.KEY_WRITE) as key:
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
    parent = get_key_parent_path(path)
    if not key_exists(parent):
        ensure_key(parent)
    create_key(path, name)

def ensure_key_value(path, name, data_type, value):
    p = path
    while not key_exists(p):
        p = get_key_parent_path(p)
    
    try:
        set_key_value(path, name, data_type, value)
    except KeyNotFoundError:
        create_key(path, name)
        set_key_value(path, name, data_type, value)

def get_key_parent_path(path):
    parts = split_path(path)
    return '\\'.join(parts[:-1])

def get_key_value(full_path, name):
    base, key_path = split_base_from_path(full_path)
    try:
        with winreg.OpenKey(base, key_path) as key:
            return winreg.QueryValueEx(key, name)
    except FileNotFoundError:
        return None

def key_exists(path):
    base, key_path = split_base_from_path(path)
    try:
        with winreg.OpenKey(base, key_path):
            pass
        return True
    except FileNotFoundError:
        return False

def set_key_value(path, name, data_type, value):
    base, key_path = split_base_from_path(path)
    dtype = encode_type(data_type)
    try:
        with winreg.OpenKey(base, key_path, access=winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, name, dtype, value)
    except FileNotFoundError:
        raise KeyNotFoundError(f"Clé non trouvée : {path}")

def split_path(input_path):
    return Path(input_path).parts

def split_base_from_path(input_path):
    parts = split_path(input_path)
    return (f"{parts[0]}", '\\'.join(parts[1:]))
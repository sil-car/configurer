import logging
from pathlib import PureWindowsPath

from . import __platform__
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

def ensure_key_value(path, name, data_type, value):
    kp = KeyPath(path)
    logging.info(f"Setting entry in '{path}': {name}; {data_type}; {value}")
    try:
        with winreg.CreateKeyEx(_encode_base(kp.base_key), kp.key_path) as key:
            logging.debug(f"Created/opened key at: {path}")
            dtype = _encode_type(data_type)
            if dtype == winreg.REG_DWORD:
                # String value can't be converted to REG_DWORD by winreg.
                value = int(value)
            logging.debug(f"{dtype=}; {value=}")
            winreg.SetValueEx(key, name, 0, dtype, value)
            logging.info("Entry set successfully.")
    except Exception as e:
        logging.error("Entry not set:")
        logging.error(e)
        raise ConfigurerException(e)

def _encode_base(input_base):
    hkey_bases = {
        winreg.HKEY_CURRENT_USER: ['HKEY_CURRENT_USER', 'HKCU'],
        winreg.HKEY_LOCAL_MACHINE: ['HKEY_LOCAL_MACHINE', 'HKLM'],
        winreg.HKEY_USERS: ['HKEY_USERS']
    }
    for encoded_base, user_bases in hkey_bases.items():
        if input_base in user_bases:
            logging.debug(f"{input_base} -> {encoded_base}")
            return encoded_base

def _encode_type(input_type):
    data_types = {
        'REG_SZ': winreg.REG_SZ,
        'REG_DWORD': winreg.REG_DWORD,
    }
    encoded_type = data_types.get(input_type)
    logging.debug(f"{input_type} -> {encoded_type}")
    if encoded_type is None:
        raise UndefinedRegValueType(f"Registry Value Type inconnu : {input_type}")
    return encoded_type

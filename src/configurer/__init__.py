import sys

__appname__ = 'Configurer'
__version__ = '0.1.2'


def is_bundled():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return True
    else:
        return False

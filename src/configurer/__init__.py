import sys

def is_bundled():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return True
    else:
        return False

__appname__ = 'Configurer'
__platform__ = sys.platform
__version__ = '0.1.4'
__bundled__ = is_bundled()

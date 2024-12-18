import sys

def is_bundled():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):  # pyinstaller
        return True
    elif '__compiled__' in globals():  # nuitka
        return True
    else:
        return False

__appname__ = 'Configurer'
__platform__ = sys.platform
__version__ = '0.1.4'
__bundled__ = is_bundled()

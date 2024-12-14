import argparse
import sys

from . import __appname__
from . import __version__
from .app import Cli
from .app import Gui


def main():
    parser = argparse.ArgumentParser(prog=__appname__)
    parser.add_argument('--version', action='version', version=f"%(prog)s v{__version__}")
    parser.add_argument('--run-config', action='store_true', help="run the system config")
    args = parser.parse_args()

    if len(sys.argv) > 1:
        Cli(args)
    else:
        Gui()


if __name__ == '__main__':
    main()


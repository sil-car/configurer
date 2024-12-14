import argparse
import sys

from . import __appname__
from . import __version__
from . import Cli
from . import Gui


def main():
    parser = argparse.ArgumentParser(prog=__appname__)
    parser.add_argument('--version', action='version', version=f"%(prog)s v{__version__}")
    parser.parse_args()

    if len(sys.argv) > 1:
        Cli()
    else:
        Gui()


if __name__ == '__main__':
    main()


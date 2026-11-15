"""Entry point so the tool runs with: python -m tracker"""

import sys

from tracker.cli import main

if __name__ == "__main__":
    sys.exit(main())

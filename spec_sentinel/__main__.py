"""Allow ``python -m spec_sentinel``."""

import sys

from spec_sentinel.cli import main

if __name__ == "__main__":
    sys.exit(main())

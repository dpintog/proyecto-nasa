"""Allow running as python -m subimage_locator."""

from .cli import main
import sys

if __name__ == "__main__":
    sys.exit(main())

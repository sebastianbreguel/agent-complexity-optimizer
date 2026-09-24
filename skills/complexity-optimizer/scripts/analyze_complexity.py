#!/usr/bin/env python3
"""Entrypoint for the complexity hotspot scanner (implementation in ./complexity_scanner).

Kept at this path so documented commands and already-installed agents keep working.
Python puts this file's directory on sys.path, which makes the package importable.
"""

import sys

from complexity_scanner.cli import main

if __name__ == "__main__":
    sys.exit(main())

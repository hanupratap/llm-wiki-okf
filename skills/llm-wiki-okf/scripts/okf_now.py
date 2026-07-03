#!/usr/bin/env python3
"""Print current UTC time as ISO 8601 for OKF frontmatter. Stdlib only."""
from okf_common import now_iso

if __name__ == "__main__":
    print(now_iso())

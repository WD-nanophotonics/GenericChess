"""Retired entry point. Historical implementation is outside the import chain."""
import sys

def main(argv=None):
    print("Retired workflow. Use generic-chess-local.cmd.", file=sys.stderr)
    return 2

if __name__ == "__main__":
    raise SystemExit(main())

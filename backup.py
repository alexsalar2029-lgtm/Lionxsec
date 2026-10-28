"""Consistent SQLite backup, including committed WAL data; never overwrites a file."""
import argparse
from pathlib import Path
import sqlite3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parent/'data'/'shop.sqlite3')
    args = parser.parse_args()
    if not args.source.is_file():
        raise SystemExit('Source database does not exist.')
    if args.destination.exists():
        raise SystemExit('Destination already exists; choose a new backup filename.')
    # Exclusive creation and restrictive permissions before opening SQLite.
    import os
    fd = os.open(args.destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    with sqlite3.connect(args.source.resolve().as_uri()+'?mode=ro', uri=True) as source:
        with sqlite3.connect(args.destination) as destination:
            source.backup(destination)
    print('Backup completed.')


if __name__ == '__main__':
    main()

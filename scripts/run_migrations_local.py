#!/usr/bin/env python3
import sys
from core.paths import DB_PATH

from database.migrations import MigrationManager

def main():
    mgr = MigrationManager(DB_PATH)
    cur = mgr.get_schema_version()
    print(f"Current schema version: {cur}")
    ok = mgr.run_migrations()
    print(f"run_migrations returned: {ok}")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print("Migration error:", e)
        sys.exit(2)

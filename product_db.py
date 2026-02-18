#!/usr/bin/env python3

import sqlite3
import argparse
import os
import re
import time
import threading
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

###############################################################################
# ULID generator
###############################################################################

_CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_lock = threading.Lock()
_last_timestamp = 0
_last_random = 0


def _encode_base32(value: int, length: int) -> str:
    chars = []
    for _ in range(length):
        chars.append(_CROCKFORD_ALPHABET[value & 0x1F])
        value >>= 5
    return "".join(reversed(chars))


def new_ulid() -> str:
    global _last_timestamp, _last_random
    with _lock:
        ts = int(time.time() * 1000)
        if ts == _last_timestamp:
            _last_random += 1
        else:
            _last_timestamp = ts
            _last_random = int.from_bytes(os.urandom(10), "big")
        ulid_int = (ts << 80) | (_last_random & ((1 << 80) - 1))
        return _encode_base32(ulid_int, 26)


###############################################################################
# Database
###############################################################################

class ProductDB:

    def __init__(self, db_path: str = "product.db"):
        self.conn = sqlite3.connect(db_path, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def _create_schema(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS device_type (
            ulid TEXT PRIMARY KEY,
            part_number TEXT NOT NULL UNIQUE,
            manufacturer_name TEXT NOT NULL,
            model TEXT,
            descriptor TEXT,
            serial_number_spec TEXT
        );

        CREATE TABLE IF NOT EXISTS device_type_attribute (
            ulid TEXT PRIMARY KEY,
            device_type TEXT NOT NULL,
            attribute_name TEXT NOT NULL,
            multiplicity TEXT NOT NULL,
            FOREIGN KEY(device_type) REFERENCES device_type(ulid) ON DELETE CASCADE,
            UNIQUE(device_type, attribute_name)
        );

        CREATE TABLE IF NOT EXISTS device (
            ulid TEXT PRIMARY KEY,
            device_type TEXT NOT NULL,
            part_number TEXT NOT NULL,
            serial_number TEXT NOT NULL UNIQUE,
            FOREIGN KEY(device_type) REFERENCES device_type(ulid)
        );

        CREATE TABLE IF NOT EXISTS device_attribute (
            ulid TEXT PRIMARY KEY,
            device TEXT NOT NULL,
            attribute_type TEXT NOT NULL,
            attribute_name TEXT NOT NULL,
            value TEXT,
            FOREIGN KEY(device) REFERENCES device(ulid) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS history_entry (
            ulid TEXT PRIMARY KEY,
            entity_ulid TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            operation TEXT,
            comment TEXT
        );
        """)

    ###########################################################################
    # History
    ###########################################################################

    def _history(self, entity_ulid: str, operation: str, comment: str = ""):
        timestamp = datetime.now(timezone.utc).isoformat()
        self.conn.execute("""
            INSERT INTO history_entry
            (ulid, entity_ulid, timestamp, operation, comment)
            VALUES (?, ?, ?, ?, ?)
        """, (
            new_ulid(),
            entity_ulid,
            timestamp,
            operation,
            comment
        ))

    ###########################################################################
    # Device Type
    ###########################################################################

    def add_device_type(self, part_number, manufacturer_name,
                        model="", descriptor="", serial_number_spec="") -> str:

        ulid = new_ulid()
        self.conn.execute("""
            INSERT INTO device_type
            (ulid, part_number, manufacturer_name, model, descriptor, serial_number_spec)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ulid, part_number, manufacturer_name, model, descriptor, serial_number_spec))
        self._history(ulid, "CREATE_DEVICE_TYPE", f"{manufacturer_name}/{part_number}")
        return ulid

    def get_device_type_by_part(self, part_number):
        row = self.conn.execute("""
            SELECT * FROM device_type WHERE part_number = ?
        """, (part_number,)).fetchone()
        return row

    ###########################################################################
    # Serial Number Logic
    ###########################################################################

    def _generate_next_serial(self, device_type_ulid: str) -> str:
        row = self.conn.execute("""
            SELECT serial_number_spec FROM device_type WHERE ulid = ?
        """, (device_type_ulid,)).fetchone()
        if not row or not row["serial_number_spec"]:
            raise ValueError("No serial_number_spec defined")

        spec = row["serial_number_spec"]
        match = re.search(r"\{(\d+)\}", spec)
        if not match:
            raise ValueError("serial_number_spec must contain {n}")
        width = int(match.group(1))
        prefix = spec[:match.start()]
        suffix = spec[match.end():]

        rows = self.conn.execute("""
            SELECT serial_number FROM device WHERE device_type = ?
        """, (device_type_ulid,)).fetchall()
        max_num = 0
        pattern = re.compile(re.escape(prefix) + r"(\d+)" + re.escape(suffix))
        for r in rows:
            m = pattern.fullmatch(r["serial_number"])
            if m:
                max_num = max(max_num, int(m.group(1)))
        next_num = max_num + 1
        return f"{prefix}{str(next_num).zfill(width)}{suffix}"

    ###########################################################################
    # Device
    ###########################################################################

    def add_device(self, device_type_ulid, part_number, serial_number) -> str:
        ulid = new_ulid()
        self.conn.execute("""
            INSERT INTO device
            (ulid, device_type, part_number, serial_number)
            VALUES (?, ?, ?, ?)
        """, (ulid, device_type_ulid, part_number, serial_number))
        self._history(ulid, "CREATE_DEVICE", f"{part_number}/{serial_number}")
        return ulid

    ###########################################################################
    # Queries
    ###########################################################################

    def find_devices(self,
                     manufacturer: Optional[str] = None,
                     part_number: Optional[str] = None,
                     serial_number: Optional[str] = None,
                     model: Optional[str] = None) -> List[Dict[str, Any]]:

        query = """
        SELECT d.*, dt.model AS model, dt.manufacturer_name
        FROM device d
        JOIN device_type dt ON d.device_type = dt.ulid
        WHERE 1=1
        """
        params = []

        if manufacturer:
            query += " AND dt.manufacturer_name LIKE ?"
            params.append(f"%{manufacturer}%")
        if part_number:
            query += " AND d.part_number LIKE ?"
            params.append(f"%{part_number}%")
        if serial_number:
            query += " AND d.serial_number LIKE ?"
            params.append(f"%{serial_number}%")
        if model:
            query += " AND dt.model LIKE ?"
            params.append(f"%{model}%")

        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


###############################################################################
# CLI
###############################################################################

def main():
    parser = argparse.ArgumentParser(description="Product Database CLI")
    parser.add_argument("--db", default="product.db")
    sub = parser.add_subparsers(dest="command", required=True)

    # add-device-type
    p = sub.add_parser("add-device-type")
    p.add_argument("--part-number", required=True)
    p.add_argument("--manufacturer", required=True)
    p.add_argument("--model", default="")
    p.add_argument("--descriptor", default="")
    p.add_argument("--serial-spec", default="")

    # create-device
    p = sub.add_parser("create-device")
    p.add_argument("--part-number", required=True)
    p.add_argument("--count", type=int, default=1)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--serial")
    group.add_argument("--next-serial", action="store_true")

    # find-device
    p = sub.add_parser("find-device")
    p.add_argument("--manufacturer", help="Partial match on manufacturer_name")
    p.add_argument("--part-number", help="Partial match on part_number")
    p.add_argument("--serial", help="Partial match on serial_number")
    p.add_argument("--model", help="Partial match on device_type.model")

    args = parser.parse_args()
    db = ProductDB(args.db)

    ###########################################################################

    if args.command == "add-device-type":
        ulid = db.add_device_type(
            args.part_number,
            args.manufacturer,
            args.model,
            args.descriptor,
            args.serial_spec
        )
        print(json.dumps({"device_type_ulid": ulid}, indent=2))

    ###########################################################################

    elif args.command == "create-device":
        dt = db.get_device_type_by_part(args.part_number)
        if not dt:
            raise SystemExit(json.dumps({"error": "Unknown part number"}))

        created = []
        try:
            db.conn.execute("BEGIN")
            for _ in range(args.count):
                if args.next_serial:
                    serial = db._generate_next_serial(dt["ulid"])
                else:
                    serial = args.serial
                    if db.conn.execute(
                        "SELECT 1 FROM device WHERE serial_number = ?",
                        (serial,)
                    ).fetchone():
                        raise SystemExit(json.dumps({"error": "Serial exists"}))
                ulid = db.add_device(dt["ulid"], dt["part_number"], serial)
                created.append({"device_ulid": ulid, "serial": serial})
            db.conn.execute("COMMIT")
        except Exception:
            db.conn.execute("ROLLBACK")
            raise

        print(json.dumps({"created": created}, indent=2))

    ###########################################################################

    elif args.command == "find-device":
        devices = db.find_devices(
            manufacturer=args.manufacturer,
            part_number=args.part_number,
            serial_number=args.serial,
            model=args.model
        )
        print(json.dumps({"devices": devices}, indent=2))


if __name__ == "__main__":
    main()


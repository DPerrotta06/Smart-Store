"""RFID reader for the self-checkout.

This is the scanning logic from rfid/test_rfid_web.py, moved into the main
project so the checkout controller can call it (same idea as Hardware/fan.py).
It only talks to the reader and returns EPC strings. It knows nothing about
products, carts or the database.
"""

import re
import time
from threading import Lock

import serial

PORT = "/dev/ttyUSB0"
BAUD = 115200
INVENTORY_COMMAND = bytes.fromhex("0008220000000022")  # "read all tags in range"
SCAN_SECONDS = 2.0
POLL_INTERVAL = 0.1

EPC_LENGTH = 22  # hex characters in a store tag's EPC (the reader appends 2 more characters after it, which change on every read)

# A tag frame starts with A0 or E0 followed by the EPC
EPC_PATTERN = re.compile(rf"(?:A0|E0)([A-F0-9]{{{EPC_LENGTH}}})")
STORE_EPC_PREFIX = "000000"  # only keep tags that belong to the store

# Flask can serve several requests at once, but there is only one serial port
_port_lock = Lock()


def read_raw_hex(seconds=SCAN_SECONDS):
    """Poll the reader for `seconds` and return everything it sent, as hex text."""
    with _port_lock:
        ser = serial.Serial(PORT, BAUD, timeout=0.2)
        try:
            ser.reset_input_buffer()
            raw_hex = ""
            start = time.time()
            last_poll = 0
            while time.time() - start < seconds:
                if time.time() - last_poll > POLL_INTERVAL:
                    ser.write(INVENTORY_COMMAND)
                    last_poll = time.time()
                if ser.in_waiting > 0:
                    raw_hex += ser.read(ser.in_waiting).hex().upper()
            return raw_hex
        finally:
            ser.close()


def extract_epcs(raw_hex):
    """Pull the store's EPCs out of the raw hex stream (no duplicates).

    The stream is hex text, two characters per byte. Searching it as plain text can match across a
    byte boundary (the end of one byte plus the start of the next can spell "A0"), which produced
    phantom EPCs. So only positions that start on a byte boundary (even index) are accepted."""
    found = set()
    for i in range(0, len(raw_hex) - 2 - EPC_LENGTH + 1, 2):
        if raw_hex[i:i + 2] in ("A0", "E0"):
            epc = raw_hex[i + 2:i + 2 + EPC_LENGTH]
            if EPC_PATTERN.fullmatch(raw_hex[i:i + 2 + EPC_LENGTH]) and epc.startswith(STORE_EPC_PREFIX):
                found.add(epc)
    return sorted(found)


def scan_tags():
    """Run one scan. Returns (raw_hex, [epc, ...]). Raises on hardware errors."""
    raw_hex = read_raw_hex()
    return raw_hex, extract_epcs(raw_hex)
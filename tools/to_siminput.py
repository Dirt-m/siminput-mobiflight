#!/usr/bin/env python3
"""Put a box back on the stock SIMINPUT firmware (Linux).

1. If the box runs SIMINPUT firmware for MobiFlight, reboots it into the bootloader
   (1200 baud touch). Otherwise hold BOOTSEL while plugging it in.
2. flash_nuke.uf2 (wipes flash, including the MobiFlight config).
3. CircuitPython 9.x UF2.
4. Unpacks the stock firmware release zip onto CIRCUITPY and restores config.json.

    uv run --with pyserial python tools/to_siminput.py \
        --nuke ../flash_nuke.uf2 \
        --circuitpython ../adafruit-circuitpython-raspberry_pi_pico-en_US-9.2.8.uf2 \
        --firmware siminput-firmware-2.7.0.zip \
        --config backups/config-backup-YYYYMMDD-HHMMSS.json

Replug the box afterwards: boot.py (USB identity, drive hidden) only runs on a hard reset.
"""

import argparse
import shutil
import sys
import time
import zipfile
from pathlib import Path

import serial
from serial.tools import list_ports

from mounts import find_drive, wait_for_drive, wait_for_unmount


def copy_uf2(uf2, label="RPI-RP2"):
    drive = wait_for_drive(label)
    print(f"Copying {uf2.name} to {drive}")
    shutil.copy(uf2, drive / uf2.name)
    wait_for_unmount(label)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nuke", type=Path, required=True)
    ap.add_argument("--circuitpython", type=Path, required=True)
    ap.add_argument("--firmware", type=Path, required=True, help="stock firmware release zip")
    ap.add_argument("--config", type=Path, required=True, help="config.json backup to restore")
    args = ap.parse_args()
    for f in (args.nuke, args.circuitpython, args.firmware, args.config):
        if not f.is_file():
            sys.exit(f"No such file: {f}")

    if not find_drive("RPI-RP2"):
        ports = [p.device for p in list_ports.comports() if p.vid == 0x2E8A]
        if len(ports) != 1:
            sys.exit(f"Expected one box on MobiFlight firmware (VID 2E8A), found {ports}. "
                     "Or hold BOOTSEL while plugging it in.")
        print(f"Rebooting {ports[0]} into the bootloader")
        s = serial.Serial(ports[0], 1200)
        s.dtr = False
        s.close()

    copy_uf2(args.nuke)
    time.sleep(2)  # flash_nuke erases, then comes back as RPI-RP2
    copy_uf2(args.circuitpython)

    drive = wait_for_drive("CIRCUITPY", timeout=60)
    print(f"Installing {args.firmware.name} onto {drive}")
    with zipfile.ZipFile(args.firmware) as z:
        for name in z.namelist():
            if name.endswith("/") or name.endswith("config.json"):
                continue
            target = drive / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(name))
    shutil.copy(args.config, drive / "config.json")
    print("Done. Eject CIRCUITPY, then replug the box.")


if __name__ == "__main__":
    main()

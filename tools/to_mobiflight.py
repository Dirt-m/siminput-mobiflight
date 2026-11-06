#!/usr/bin/env python3
"""Switch a SIMINPUT box from the stock firmware to SIMINPUT firmware for MobiFlight (Linux).

1. Backs up the box's config.json over the stock serial protocol.
2. Reboots the box into the RP2040 bootloader (no BOOTSEL needed).
3. Copies the UF2 onto the RPI-RP2 drive once it mounts.

Uses the updater's Device class, so run it inside the updater's environment:

    uv run --project ../siminput-firmware-updater python tools/to_mobiflight.py \
        .pio/build/siminput_rev2/siminput_rev2_0_0_1.uf2

The backup lands in ./backups/. Keep it: switching firmware wipes the box.
"""

import json
import shutil
import sys
import time
from pathlib import Path

from serial.tools import list_ports
from siminput_updater.device import ADAFRUIT_VID, Device

from mounts import wait_for_drive


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    uf2 = Path(sys.argv[1])
    if not uf2.is_file():
        sys.exit(f"No such file: {uf2}")

    ports = [p.device for p in list_ports.comports() if p.vid == ADAFRUIT_VID]
    if len(ports) != 1:
        sys.exit(f"Expected one SIMINPUT box on the stock firmware, found {len(ports)}: {ports}")

    dev = Device()
    info = dev.connect(ports[0])
    print(f"Connected: {info}")
    config = dev.get_config()
    if not config:
        sys.exit("Box returned an empty config, not switching.")
    backups = Path("backups")
    backups.mkdir(exist_ok=True)
    backup = backups / f"config-backup-{time.strftime('%Y%m%d-%H%M%S')}.json"
    backup.write_text(json.dumps(config, indent=2))
    print(f"Config backed up to {backup}")

    dev.enter_bootloader()
    drive = wait_for_drive("RPI-RP2")
    print(f"Bootloader drive at {drive}, copying {uf2.name}")
    shutil.copy(uf2, drive / uf2.name)
    print("Done. The box reboots into the new firmware.")


if __name__ == "__main__":
    main()

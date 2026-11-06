"""Find auto-mounted USB drives by volume label (Linux, udisks style mount points)."""

import getpass
import sys
import time
from pathlib import Path


def find_drive(label):
    user = getpass.getuser()
    for base in (Path("/run/media") / user, Path("/media") / user, Path("/media")):
        p = base / label
        if p.is_dir() and any(p.iterdir()):
            return p
    return None


def wait_for_drive(label, timeout=30.0):
    """Wait for a drive to mount, then a little longer so it is fully ready."""
    print(f"Waiting for {label} to mount ...", flush=True)
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        drive = find_drive(label)
        if drive:
            time.sleep(1.0)
            return drive
        time.sleep(0.5)
    sys.exit(f"{label} did not mount within {timeout:.0f} s. Mount it and try again.")


def wait_for_unmount(label, timeout=30.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if not find_drive(label):
            return
        time.sleep(0.5)
    sys.exit(f"{label} is still mounted after {timeout:.0f} s.")

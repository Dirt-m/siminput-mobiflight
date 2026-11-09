#!/usr/bin/env python3
"""Talk to a SIMINPUT (or any MobiFlight) board over serial, without the Connector.

For development and bench tests on Linux/macOS. Speaks the same CmdMessenger
protocol as MobiFlight Connector: fields split by ',', commands end with ';',
'/' escapes.

    uv run --with pyserial tools/mftool.py info
    uv run --with pyserial tools/mftool.py upload SIMINPUT/Community/config/siminput_rev2.all-buttons.mfmc
    uv run --with pyserial tools/mftool.py upload --raw "8.4.6.0.Enc test:3.2.Backlight:"
    uv run --with pyserial tools/mftool.py monitor
    uv run --with pyserial tools/mftool.py out 0 128        # output 0 (Backlight in the presets) to 50 %
    uv run --with pyserial tools/mftool.py bootloader       # 1200 baud touch: reboot to RPI-RP2

The port defaults to the first /dev/ttyACM* with the Raspberry Pi VID; pass --port to override.
"""

import argparse
import sys
import time
import xml.etree.ElementTree as ET

import serial
from serial.tools import list_ports

# Command IDs, from src/src/commandmessenger.h
K_SET_PIN, K_STATUS, K_ENCODER, K_BUTTON = 2, 5, 6, 7
K_GET_INFO, K_INFO, K_SET_CONFIG, K_GET_CONFIG = 9, 10, 11, 12
K_RESET_CONFIG, K_SAVE_CONFIG, K_CONFIG_SAVED = 13, 14, 15
K_ACTIVATE_CONFIG, K_CONFIG_ACTIVATED, K_TRIGGER = 16, 17, 23
K_ANALOG, K_RETRIGGER_DONE, K_DEBUG = 28, 34, 255

NAMES = {K_STATUS: "status", K_ENCODER: "encoder", K_BUTTON: "button", K_INFO: "info",
         K_CONFIG_SAVED: "saved", K_CONFIG_ACTIVATED: "activated", K_ANALOG: "analog",
         K_RETRIGGER_DONE: "retrigger done", K_DEBUG: "debug"}

# Device type IDs as the Connector sends them (MobiFlight/DeviceType.cs)
TYPE_IDS = {"Button": 1, "Output": 3, "Encoder": 8, "AnalogInput": 11}
MESSAGE_SIZE = 64  # Connection.MessageSize in the board JSON


def find_port():
    for p in list_ports.comports():
        if p.vid == 0x2E8A:
            return p.device
    sys.exit("No board with VID 2E8A found. Pass --port.")


def escape(s):
    return "".join("/" + c if c in ",;/" else c for c in s)


class Board:
    def __init__(self, port):
        self.ser = serial.Serial(port, 115200, timeout=0.05)
        self.ser.dtr = True
        self.buf = b""
        time.sleep(0.2)
        self.ser.reset_input_buffer()

    def send(self, cmd, *args):
        msg = ",".join([str(cmd)] + [escape(str(a)) for a in args]) + ";"
        self.ser.write(msg.encode())

    def read(self, timeout=0.05):
        """Return the next complete command as (id, [args]) or None."""
        end = time.monotonic() + timeout
        while True:
            i, esc = 0, False
            while i < len(self.buf):
                c = self.buf[i:i + 1]
                if esc:
                    esc = False
                elif c == b"/":
                    esc = True
                elif c == b";":
                    raw, self.buf = self.buf[:i].decode(errors="replace"), self.buf[i + 1:]
                    return self._parse(raw)
                i += 1
            if time.monotonic() > end:
                return None
            self.buf += self.ser.read(256)

    @staticmethod
    def _parse(raw):
        fields, cur, esc = [], "", False
        for c in raw.strip("\r\n"):
            if esc:
                cur += c
                esc = False
            elif c == "/":
                esc = True
            elif c == ",":
                fields.append(cur)
                cur = ""
            else:
                cur += c
        fields.append(cur)
        try:
            return int(fields[0]), fields[1:]
        except ValueError:
            return None

    def expect(self, cmd, timeout=2.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            msg = self.read(0.1)
            if msg is None:
                continue
            if msg[0] == cmd:
                return msg[1]
            show(msg)
        sys.exit(f"Timeout waiting for command {cmd}")


def show(msg):
    cmd, args = msg
    print(f"{time.strftime('%H:%M:%S')} {NAMES.get(cmd, cmd):>10}  {' '.join(args)}", flush=True)


def mfmc_to_internal(path):
    """Serialize a .mfmc file the way the Connector does (Firmware/*.cs ToInternal)."""
    out = []
    for el in ET.parse(path).getroot():
        t, a = el.tag, el.attrib
        if t not in TYPE_IDS:
            continue
        if t == "Button" or t == "Output":
            parts = [a["Pin"], a["Name"]]
        elif t == "Encoder":
            parts = [a["PinLeft"], a["PinRight"], a.get("EncoderType", "0"), a["Name"]]
        elif t == "AnalogInput":
            parts = [a["Pin"], a.get("Sensitivity", "5"), a["Name"]]
        out.append(".".join([str(TYPE_IDS[t])] + parts) + ":")
    return out


def chunks(items, size):
    """Group device strings into messages no longer than the board's message size."""
    cur = ""
    for item in items:
        if cur and len(cur) + len(item) > size:
            yield cur
            cur = ""
        cur += item
    if cur:
        yield cur


def cmd_info(b, _):
    b.send(K_GET_INFO)
    t, name, serial_no, version, core = (b.expect(K_INFO) + [""] * 5)[:5]
    print(f"type: {t}\nname: {name}\nserial: {serial_no}\nversion: {version}\ncore: {core}")


def cmd_config(b, _):
    b.send(K_GET_CONFIG)
    cfg = ",".join(b.expect(K_INFO))
    for dev in filter(None, cfg.split(":")):
        print(dev)


def cmd_upload(b, args):
    items = [s + ":" for s in args.file.split(":") if s] if args.raw else mfmc_to_internal(args.file)
    b.send(K_RESET_CONFIG)
    b.expect(K_STATUS)
    for chunk in chunks(items, MESSAGE_SIZE - 8):
        b.send(K_SET_CONFIG, chunk)
        status = b.expect(K_STATUS)
        if status and status[0] == "-1":
            sys.exit("Board refused the config (too long?)")
    b.send(K_SAVE_CONFIG)
    b.expect(K_CONFIG_SAVED)
    b.send(K_ACTIVATE_CONFIG)
    b.expect(K_CONFIG_ACTIVATED)
    print(f"Uploaded {len(items)} devices.")


def cmd_monitor(b, _):
    # GetConfig marks the board ready; it only sends input events after that.
    b.send(K_GET_CONFIG)
    b.expect(K_INFO)
    b.send(K_TRIGGER)
    print("Listening, Ctrl+C to stop.")
    last_ping = time.monotonic()
    try:
        while True:
            msg = b.read(0.2)
            if msg:
                show(msg)
            if time.monotonic() - last_ping > 60:  # keep power saving mode off, like the Connector
                b.send(18, 0)
                last_ping = time.monotonic()
    except KeyboardInterrupt:
        pass


def cmd_pin(b, args):
    b.send(K_SET_PIN, args.index, args.value)  # the core takes the output device index, not the pin
    time.sleep(0.1)


def cmd_bootloader(_, args):
    s = serial.Serial(args.port, 1200)
    s.dtr = False
    s.close()
    print("Board should now show up as RPI-RP2.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info")
    sub.add_parser("config")
    up = sub.add_parser("upload")
    up.add_argument("file", help=".mfmc file, or a raw config string with --raw")
    up.add_argument("--raw", action="store_true")
    sub.add_parser("monitor")
    p = sub.add_parser("out", help="set an output: device index (order among outputs in the config, from 0) and value 0 to 255")
    p.add_argument("index", type=int)
    p.add_argument("value", type=int)
    sub.add_parser("bootloader")
    args = ap.parse_args()
    args.port = args.port or find_port()

    if args.cmd == "bootloader":
        return cmd_bootloader(None, args)
    b = Board(args.port)
    {"info": cmd_info, "config": cmd_config, "upload": cmd_upload, "monitor": cmd_monitor,
     "out": cmd_pin}[args.cmd](b, args)


if __name__ == "__main__":
    main()

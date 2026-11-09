# SIMINPUT firmware for MobiFlight

Alternative firmware for the SIMINPUT rev2 button box. With it, MobiFlight Connector sees the box as a native MobiFlight module called **SIMINPUT rev2**, with every pin already named the way SIMINPUT names them. That adds what the stock joystick firmware can't do: sim-driven outputs, starting with the backlight following the aircraft's panel lighting.

Rev2 only. Built on the [MobiFlight core firmware](https://github.com/MobiFlight/MobiFlight-FirmwareSource) through the [CommunityTemplate](https://github.com/MobiFlight/CommunityTemplate). Not affiliated with the MobiFlight project.

The stock SIMINPUT firmware stays the default. It is a plain USB joystick and works in MobiFlight as an input device too. Use this one if you want MobiFlight outputs or want to manage the box like your other MobiFlight boards.

## What you get

| Connector pin | Hardware | Use as |
|---|---|---|
| D1 to D22 | GP4 to GP25 | Button, encoder (any two pins), output (D15 and D16 on/off only: they share a PWM slice with the backlight) |
| A1 to A4 | GP26 to GP29 | Button, analog input (0 to 3.3 V), output |
| D23 to D38 | TCA9555 expander, virtual pins 30 to 45 | Button only |
| Backlight | GP2 | Output, 0 to 255 with the stock SIMINPUT brightness curve (16 bit PWM, 1 kHz) |

Two presets ship with the board: "All buttons" (the stock layout) and "Buttons, A1 to A4 analog". Pick one under the module's "upload default config" button, then rename or change devices as you like.

Limits:
- Encoders work on any two of D1 to D22, adjacent or not (tested on D3 + D7). Pick encoder type "1 detent per cycle (00)" in the Connector for the SIMINPUT encoders. Not on the expander pins: they are read over I2C and aren't fast enough.
- Analog inputs have no pull-up (the ADC read turns it off, as in the stock firmware), so a pot reads linear. An empty A jack set up as analog floats and sends the odd random value: only set up jacks with a pot plugged in as analog.
- No steppers, servos, displays, shift registers or multiplexers: every pin already goes to an input jack.
- The board needs MobiFlight Connector running. It isn't a joystick under this firmware.

## How the expander works

The MobiFlight core only reads buttons from GPIO. arduino-pico defines `pinMode()` and `digitalRead()` as weak symbols, so `SIMINPUT/siminput_expander.cpp` overrides them: pins 30 to 45 go to the TCA9555, everything else goes straight to the core. The expander is only read when it pulls INT# (GP3) low, plus a 20 ms fallback poll. If it stops answering, D23 to D38 read as released, GPIO inputs keep working, and it is probed again every second. The core sources are not modified.

## Building

VS Code with PlatformIO, or the CLI:

```
pio run -e siminput_rev2
```

The first build clones the MobiFlight core (version set in `SIMINPUT/SIMINPUT_platformio.ini`) into `src/`. Output:
- `.pio/build/siminput_rev2/siminput_rev2_<version>.uf2`: the firmware.
- `_dist/siminput_rev2_<version>.zip`: the package for the Connector's `Community` folder (firmware, board definition, presets, license).

Releases: publishing a GitHub release `vX.Y.Z` builds the zip with that version.

## Layout

```
SIMINPUT/
  SIMINPUT_platformio.ini        build env (board, features, memory sizes)
  siminput_expander.cpp          TCA9555 virtual pins
  siminput_backlight.cpp         backlight brightness curve
  Community/
    boards/siminput_rev2.board.json   what the Connector reads: pins, limits, USB IDs, links
    config/*.mfmc                     device presets
    firmware/                         flash_nuke for "reset board"; the build adds the UF2
tools/
  mftool.py           talk to the board without the Connector (info, upload, monitor, set output)
  to_mobiflight.py    stock firmware to MobiFlight, with config backup (Linux)
  to_siminput.py      back to the stock firmware, with config restore (Linux)
docs/                 goal, hardware notes, MobiFlight notes, test plan
```

## Switching firmware

Switching wipes the box, including `config.json`. Back it up first. On Linux, `tools/to_mobiflight.py` does the backup and the switch, and `tools/to_siminput.py` goes back. See `docs/TESTING.md` for the exact commands. The SIMINPUT updater app will get the same flow for Windows and macOS users.

## License

MIT, see `LICENSE`. The binary also contains the arduino-pico core (LGPL 2.1). See `SIMINPUT/Community/LICENSE.txt` for every component.

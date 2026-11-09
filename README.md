# SIMINPUT firmware for MobiFlight

Firmware that turns a SIMINPUT rev2 box into a native MobiFlight module. MobiFlight Connector shows it as **SIMINPUT rev2**, with every jack named the way it's printed on the box, and you can drive outputs from the sim. The first one is the backlight: it can follow your aircraft's panel lighting.

The stock SIMINPUT firmware stays the default. It's a plain USB joystick and works fine in MobiFlight for inputs. You only need this if you want sim-driven outputs, or want to manage the box like your other MobiFlight boards.

Rev2 boxes only. Not affiliated with the MobiFlight project.

## Installing

1. Download `siminput_rev2_<version>.zip` from [Releases](../../releases).
2. Unzip it into MobiFlight Connector's `Community` folder, `%LOCALAPPDATA%\MobiFlight\MobiFlight Connector\Community\`, so you get `Community\SIMINPUT\`. Restart the Connector.
3. Put the firmware on the box. Switching wipes the box, including your SIMINPUT configuration, so back it up first. The SIMINPUT Configurator will do the backup and the switch for you, both ways. Until then: hold BOOTSEL while plugging in the box and flash it from the Connector, which offers `SIMINPUT rev2` for the RPI-RP2 drive.
4. In the Connector, select the module and click "upload default config". That loads the "All buttons" layout.

## What you get

| Jack | Use as |
|---|---|
| D1 to D22 | Button, encoder, output |
| D23 to D38 | Button |
| A1 to A4 | Button or analog input |
| Backlight | Output, 0 to 255 |

- **Encoders** work on any two of D1 to D22, next to each other or not. Pick encoder type "1 detent per cycle (00)". D23 to D38 sit on an I2C expander and can't do encoders.
- **Pots** go on A1 to A4. Change that jack from Button to Analog Input and set sensitivity to 3 (the default 5 is coarse). Only set jacks with a pot plugged in to analog: an empty analog input picks up noise.
- **Backlight** uses the same brightness curve as the stock firmware. Map the sim value straight to 0 to 255, for example `$*2.55` for a percentage.
- D15 and D16 share a PWM channel with the backlight, so as outputs they're on/off only.

Under this firmware the box is not a joystick any more. It only talks to MobiFlight Connector, which has to be running.

## Going back to the stock firmware

Use the SIMINPUT Configurator once it supports switching. By hand: flash `flash_nuke.uf2`, then CircuitPython 9.x, then copy the stock firmware files and your backed-up `config.json` onto the CIRCUITPY drive. `tools/to_siminput.py` does exactly that on Linux.

## Building

[PlatformIO](https://platformio.org), in VS Code or on the command line:

```
pio run -e siminput_rev2
```

The first build fetches the MobiFlight core into `src/`. You get the UF2 in `.pio/build/siminput_rev2/` and the Connector package in `_dist/`. After changing anything under `SIMINPUT/Community`, delete `_build/` first, or the package keeps the old files.

Publishing a GitHub release `vX.Y.Z` builds the package with that version.

More: [how it works](docs/how-it-works.md), [testing](docs/testing.md).

## Credits and license

Built on the [MobiFlight firmware](https://github.com/MobiFlight/MobiFlight-FirmwareSource) and [CommunityTemplate](https://github.com/MobiFlight/CommunityTemplate). Thanks to the MobiFlight team.

Written by Milo with a lot of help from Claude. Everything was tested on real boxes.

MIT, see `LICENSE`. The firmware also contains the arduino-pico core (LGPL 2.1); `SIMINPUT/Community/LICENSE.txt` lists every component.

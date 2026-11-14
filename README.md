# SIMINPUT firmware for MobiFlight

Firmware that turns a SIMINPUT rev2 box into a native MobiFlight module. MobiFlight Connector shows it as **SIMINPUT rev2**, with every jack named the way it's printed on the box, and you can drive outputs from the sim. The first one is the backlight: it can follow your aircraft's panel lighting.

The stock SIMINPUT firmware stays the default. It's a plain USB joystick and works fine in MobiFlight for inputs. You only need this if you want sim-driven outputs, or want to manage the box like your other MobiFlight boards.

Rev2 boxes only. Not affiliated with the MobiFlight project.

## Installing

Use the [SIMINPUT Configurator](https://github.com/Dirt-m/siminput-firmware-updater/releases), 1.3.0 or newer. It backs up your configuration first and downloads the latest firmware itself.

1. Close MobiFlight Connector.
2. In the Configurator, connect the box, go to the Update page and click **Switch to MobiFlight firmware**. On Windows, leave "Also put the MobiFlight Connector files in its Community folder" ticked.
3. Open MobiFlight Connector, select **SIMINPUT rev2** and click "upload default config". That loads the "All buttons" layout.

A new box, or one plugged in with BOOTSEL held, shows up on the Update page in bootloader mode: click **Install MobiFlight firmware**.

By hand: unzip `siminput_rev2_<version>.zip` from [Releases](../../releases) into `%LOCALAPPDATA%\MobiFlight\MobiFlight Connector\Community\` and flash the box from the Connector while it's in bootloader mode. That skips the config backup.

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

Close MobiFlight Connector, open the Configurator, and click **Switch back to SIMINPUT firmware** on the Update page. It erases the box, installs CircuitPython and the stock firmware, and restores your backed-up configuration. Replug the box when it asks.

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

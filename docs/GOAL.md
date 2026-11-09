# Goal

Ship a MobiFlight firmware build for the SIMINPUT rev2 board, as an optional alternative to the stock SIMINPUT firmware. A user can put it on their box, and MobiFlight Connector then recognises the box as a SIMINPUT module with the right pins already defined.

## Why

The stock firmware already works in MobiFlight as a joystick, but only for inputs. A native MobiFlight build adds:
- **Sim-driven backlight.** The 8 LED backlight on GP2 follows the aircraft's panel or instrument lighting.
- **Native MobiFlight setup.** Users who build MobiFlight cockpits manage the box like their other MobiFlight boards.
- A path to future outputs (indicator LEDs, displays) if a later module or board revision adds them.

## Done means

1. A PlatformIO project built from `MobiFlight/CommunityTemplate`, for the RP2040, that produces a UF2.
2. A board JSON that describes rev2 accurately (only real pins, correct USB IDs, sensible module limits), so the Connector lists the box by name with SIMINPUT's community links.
3. All 42 inputs usable from the Connector:
   - D1 to D22 as buttons or encoder pairs,
   - A1 to A4 as buttons or analog inputs,
   - D23 to D38 (TCA9555) as buttons. This is the hard part (see `mobiflight.md`, "The expander problem").
4. The backlight usable as a PWM output.
5. Survives a missing or dead expander (GPIO inputs keep working), like the stock firmware.
6. Licensing in order: MIT notices kept, no GPL code in the binary (or source published alongside it), not branded as MobiFlight.
7. Tested on a real rev2 box with MobiFlight Connector on Windows and a sim.
8. A documented way back to the stock SIMINPUT firmware: flash_nuke, CircuitPython 9.x UF2, firmware files, the user's `config.json` restored. Plus a config backup step before switching away.

## Out of scope (for now)

- Rev1 boards.
- Changes to the stock CircuitPython firmware or the configurator, beyond what's needed later for the switch-back flow.
- Shipping it preinstalled. The first goal is an optional download.

## Decisions

1. **Board variant: settled.** `board = pico`. The stock firmware runs the Pico CircuitPython build with its filesystem at the end of 2 MB flash, so the flash is at least 2 MB and the Pico boot2 (W25Q080) works.
2. **Expander inputs: settled.** Virtual pins 30 to 45 (D23 to D38) in the board JSON. `SIMINPUT/siminput_expander.cpp` overrides arduino-pico's weak `pinMode()`/`digitalRead()` and reads the TCA9555 when INT# (GP3) is low. Expander pins appear as ordinary Buttons. No core or Connector changes. Upstream has no I2C input on its roadmap (FirmwareSource #369, Feb 2026), so the upstream route is out for now. Encoders on the expander are not supported.
3. **USB identity: for now** the arduino-pico default `2E8A:000A`, product string "SIMINPUT (MobiFlight)". The Connector tells the box apart from a plain Pico by `MobiFlightType` ("SIMINPUT rev2"). Later: apply for a Raspberry Pi PID (free for RP2040 products), which could also replace the stock firmware's unallocated `239A:F000`.
4. **Pre-pinned: settled.** One `.mfmc` preset via `Info.DeviceConfigs` ("All buttons"). Users switch A jacks to Analog Input per pot in the Connector. Users load it with a button and can still edit it. `HAS_CONFIG_IN_FLASH` was rejected: the core then refuses config uploads from the Connector.
5. **Repo: private** `Dirt-m/siminput-mobiflight` during development. Before shipping binaries it must go public (or releases must include object files): the arduino-pico core is LGPL 2.1 and statically linked, so users must be able to relink.

## Still to do

- Hardware tests: round 1 (Linux) and round 2 (Windows Connector) passed on 2026-11-09. Still open: the expander polarity reset on a box switched straight from the stock firmware (test 3 in round 1).
- Before distributing binaries: make the repo public, or ship object files with each release (arduino-pico is LGPL 2.1).
- First release: tag `v0.1.0` so the release workflow builds the zip.
- Switch flow in the SIMINPUT updater app (backup, `bootloader` command, copy UF2; and back: 1200 baud touch, flash_nuke, CircuitPython, files, config restore). `tools/to_mobiflight.py` and `tools/to_siminput.py` do this on Linux today and are the reference.
- Courtesy note to the MobiFlight team (Discord) before launch.
- siminput.com docs page.

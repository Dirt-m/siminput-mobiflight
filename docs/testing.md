# Testing

Run this checklist before a release, on a rev2 box with a few modules plugged in: some buttons, an encoder and a pot.

`mft` is short for `uv run --with pyserial python tools/mftool.py`. Button events: `0` is press, `1` is release.

## On Linux, without the Connector

Build with `pio run -e siminput_rev2`, then flash `.pio/build/siminput_rev2/siminput_rev2_0_0_1.uf2` (`mft bootloader`, or BOOTSEL, then copy it to RPI-RP2).

1. **Identity.** `mft info` shows type `SIMINPUT rev2` and the version.
2. **Config.** `mft upload SIMINPUT/Community/config/siminput_rev2.all-buttons.mfmc`, then `mft config` lists 43 devices.
3. **Buttons.** `mft monitor`. Press a few of D1 to D22 (include D20 to D22), D23 to D38 (one from each half) and A1 to A4. Each gives one `0` and one `1`, with the right name.
4. **Held at startup.** Hold a direct jack and an expander jack closed, then start `mft monitor`. Both show as `0` right away.
5. **Backlight.** `for v in 1 10 25 50 100 150 200 255 0; do mft out 0 $v; sleep 3; done`. A faint glow at 1, full at 255, off at 0, no flicker.
6. **Encoder.** Plug it into D3 and D7. `mft upload --raw "8.6.10.1.Enc:3.2.Backlight:"`, then `mft monitor`. One event per click (`0`/`2`, fast turns `1`/`3`), also on the first click after changing direction.
7. **Analog.** Pot on A1. `mft upload --raw "11.26.3.A1:3.2.Backlight:"`, then `mft monitor`. 0 to about 1023, quiet when you let go.
8. **Reset.** `mft bootloader`, copy `SIMINPUT/Community/firmware/reset.raspberry_pico_flash_nuke.uf2`, then the firmware again. `mft config` is empty.

## On Windows, with MobiFlight Connector

Unzip `_dist/siminput_rev2_<version>.zip` into `%LOCALAPPDATA%\MobiFlight\MobiFlight Connector\Community\` and restart the Connector.

1. **Detection.** The box shows up as `SIMINPUT rev2`, with the SIMINPUT links.
2. **Preset.** "Upload default config" loads "All buttons". Pin dropdowns show names like `D5`. Change A1 to an Analog Input with sensitivity 3 and check a pot reads.
3. **Inputs.** Map a direct button and an expander button to something visible in the sim. Both work on press and release.
4. **Encoder.** Map an encoder on two non-adjacent pins, type "1 detent per cycle (00)".
5. **Backlight.** Output config on `Backlight` from the panel light level (MSFS `LIGHT POTENTIOMETER:n` as `$*2.55`, X-Plane `panel_brightness_ratio[0]` as `$*255`). The box dims with the cockpit knob.
6. **Firmware install.** Put the box in RPI-RP2. The Connector offers `SIMINPUT rev2` and flashes it.
7. **Power saving.** Stop the run, or leave the Connector idle for 15 minutes: the backlight goes off and comes back on activity.

Last full run: November 2026, before v0.1.0. Both rounds passed.

# Hardware tests

Two rounds. Round 1 runs on Linux against the bare firmware, no Connector needed. Round 2 is the real thing on Windows. Use a rev2 box with the expander fitted and a few modules plugged in (at least one button, one encoder and one pot if you have them).

Every command runs from the repo root. `mft` below is short for `uv run --with pyserial python tools/mftool.py`.

MobiFlight button events: `0` is press, `1` is release.

## Round 1: Linux bench

### Build

```
pio run -e siminput_rev2
```

UF2: `.pio/build/siminput_rev2/siminput_rev2_0_0_1.uf2`.

### Switch the box over

```
uv run --project ../siminput-firmware-updater python tools/to_mobiflight.py .pio/build/siminput_rev2/siminput_rev2_0_0_1.uf2
```

This backs up `config.json` to `backups/`, reboots the box into the bootloader over the stock serial protocol and copies the UF2. Don't power-cycle the box afterwards. Test 3 checks that the firmware resets the expander state CircuitPython left behind (polarity inversion on).

### Tests

1. **Identity.** `mft info`: type `SIMINPUT rev2`, name `SIMINPUT`, version `0.0.1`, core `3.1.4`. `lsusb` shows `2e8a:000a SIMINPUT SIMINPUT (MobiFlight)`.
2. **Config.** `mft upload SIMINPUT/Community/config/siminput_rev2.all-buttons.mfmc`, then `mft config` lists 43 devices.
3. **Buttons.** `mft monitor`, then press inputs on a direct jack (D1 to D22), an expander jack (D23 to D38) and A1 to A4. Include D20 to D22 and A4 (GP23 to GP25, GP29): those pins are special on a real Pico, so this checks that the `pico` board variant leaves them alone. Each gives exactly one `0` on press and one `1` on release, with the right name. Expander buttons must not be inverted (press gives `0`). This only proves the polarity reset if the box was not power-cycled since CircuitPython.
4. **Startup state.** Hold a switch closed on an expander pin and one on a GPIO pin, then restart `mft monitor`. Both show up as pressed in the retrigger burst right after connecting. Passed 2026-11-09 (D20, D38).
5. **Backlight.** `for v in 1 10 25 50 100 150 200 255 0; do mft out 0 $v; sleep 3; done`. The argument is the output device index (Backlight is the only output, so 0), not the pin: that is what the core and the Connector use. 1 is a faint glow, 255 full, 0 off, smooth steps, no flicker. Passed on 2026-11-09.
6. **Encoder, non-adjacent pins.** Plug an encoder's A/B into two D jacks that are *not* next to each other, for example D3 and D7 (GP6, GP10). Then:
   `mft upload --raw "8.6.10.0.Enc:3.2.Backlight:"` and `mft monitor`. Turn it slowly and quickly in both directions. Expect `encoder Enc 0` (left) and `encoder Enc 2` (right), plus `1` and `3` for fast turns. If the direction is reversed, swap the pins. The third field is the encoder type (0 to 4: 1 detent per cycle at 11 or at 00, 2 detents, 4 detents). If one click gives zero, two or four events, try the others. Report which type matches the SIMINPUT encoders, so the docs can name it. 2026-11-09: counts on D3 + D7 with type 0, but the first click after a direction change is lost (wrong detent position). Type 1 (1 detent per cycle, at 00) is right for the SIMINPUT encoders.
7. **Analog.** `mft upload SIMINPUT/Community/config/siminput_rev2.analog.mfmc` (A1 analog), then `mft follow A1 0`: a pot on A1 gives 0 to 1023 and dims the backlight. 2026-11-09: works. Bridged reads 2, open floats around 200 (no pull-up, as in the stock firmware). An empty analog input follows its neighbour, hence A1 only in the preset. The ends can stop a few counts short of 0 and 1023: the core only sends a change of at least the sensitivity. Upstream behaviour, left as is.
8. **Dead expander.** Build a firmware that looks for the expander at the wrong address:
   ```
   PLATFORMIO_BUILD_FLAGS="-DSIMINPUT_TCA_ADDR=0x21" pio run -e siminput_rev2
   mft bootloader
   ```
   Copy the UF2 onto RPI-RP2. Run `mft monitor`: you should see the debug line `SIMINPUT: expander not responding`. D1 to D22 still work and D23 to D38 stay silent. Then rebuild without the flag and flash it again.
9. **Reset board.** `mft bootloader` gives RPI-RP2. Copy `SIMINPUT/Community/firmware/reset.raspberry_pico_flash_nuke.uf2`, then the normal UF2 again. `mft config` is empty (config wiped). Re-upload a preset. Passed 2026-11-09.

Send me the output of anything that fails.

## Round 2: Windows, MobiFlight Connector

### Install

1. Install MobiFlight Connector (current release) from mobiflight.com.
2. Unzip `_dist/siminput_rev2_0.0.1.zip` (or the release zip) into the Connector's `Community` folder. Default: `%LOCALAPPDATA%\MobiFlight\MobiFlight Connector\Community\`, giving `Community\SIMINPUT\boards\...`. Restart the Connector.

### Tests

1. **Detection.** Plug in the box (already on this firmware from round 1). Under Settings, MobiFlight Modules, it shows as `SIMINPUT rev2` with the SIMINPUT website/docs/support buttons.
2. **Preset.** Select the module and use the "upload default config" button to load "All buttons". The device list shows D1 to D38, A1 to A4 and Backlight. Open a Button and check the pin dropdown shows names (`D5`), not numbers.
3. **Input mapping.** Make an input config on a GPIO button and one on an expander button (D23+) that toggle something visible in the sim, for example the nav lights. Both work, both on press and release.
4. **Encoder.** Replace two buttons with an Encoder on the pins from round 1. Map it to a heading bug or similar. Check the Connector's device editor lets you pick non-adjacent pins.
5. **Backlight from the sim.** Make an output config: device `Backlight` (an Output on pin 2). Source: the aircraft's panel light level.
   - MSFS: a simvar such as `(A:LIGHT POTENTIOMETER:3, Percent)` (the index differs per aircraft) or `(A:LIGHT PANEL, Bool)` for on/off.
   - X-Plane: dataref `sim/cockpit2/switches/panel_brightness_ratio[0]` (0 to 1).
   - Scale to 0 to 255 in the config (MSFS percent: `$*2.55`, X-Plane ratio: `$*255`). Turning the panel lights knob in the cockpit dims the box.
   - The firmware already applies the stock curve (t² + 0.01), so map the sim value linearly. Check the panel knob feels right across its range.
6. **Firmware install through the Connector.** Put the box in RPI-RP2 (`mft bootloader` from Linux, or BOOTSEL). The Connector should offer `SIMINPUT rev2` among the boards for that drive and flash it.
7. **Stop and power saving.** Stop the run: does the backlight go off? Leave the Connector idle for 15+ minutes: outputs go dark (MobiFlight power saving) and come back on activity.

## Back to the stock firmware

```
uv run --with pyserial python tools/to_siminput.py \
  --nuke ../flash_nuke.uf2 \
  --circuitpython ../adafruit-circuitpython-raspberry_pi_pico-en_US-9.2.8.uf2 \
  --firmware siminput-firmware-2.7.0.zip \
  --config backups/config-backup-<timestamp>.json
```

Get the firmware zip with `gh release download v2.7.0 -R Dirt-m/siminput-firmware-v2`. Replug the box when it's done, then check in the SIMINPUT app that the config is back.

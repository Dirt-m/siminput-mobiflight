# How it works

The MobiFlight core firmware is used as is. It's fetched into `src/` at build time and never edited. Everything SIMINPUT specific lives in `SIMINPUT/`.

## The board

Rev2 is a custom PCB with a bare RP2040, not a Pico module, so all 30 GPIO are usable. GP23, GP24, GP25 and GP29 are ordinary inputs here.

| Jack | Hardware |
|---|---|
| D1 to D22 | GP4 to GP25 |
| A1 to A4 | GP26 to GP29 (ADC0 to ADC3) |
| D23 to D38 | TCA9555 expander, P0.0 to P1.7 |
| Backlight | GP2, 8 LEDs |
| (internal) | GP0/GP1: I2C to the expander at 0x20. GP3: expander INT# |

Every input is a switch to ground with an internal pull-up, so pressed reads low.

Schematic: https://oshwlab.com/milo.speelman/project_xsuqnvlv

## Expander inputs

MobiFlight only reads buttons from GPIO pins. To get D23 to D38 in anyway, the board file lists them as pins 30 to 45, which don't exist on the RP2040.

arduino-pico defines `pinMode()` and `digitalRead()` as weak functions. `SIMINPUT/siminput_expander.cpp` replaces them: pins 30 to 45 are read from the TCA9555, every other pin goes to the normal function. To MobiFlight they're just buttons.

- The expander is only read over I2C when it pulls INT# (GP3) low, plus every 20 ms as a fallback.
- At startup the firmware sets all 16 pins as inputs and turns polarity inversion off. The stock firmware leaves inversion on, and the expander keeps its settings across an RP2040 reset.
- If the expander stops answering, D23 to D38 read as released, the GPIO inputs keep working, and the firmware tries again every second. The Connector log shows a line when that happens.

Encoders need fast, direct pin reads, so they only work on D1 to D22.

## Backlight

The sim sends 0 to 255. `SIMINPUT/siminput_backlight.cpp` applies the stock firmware's curve, `(v/255)² + 0.01` (0 stays off), and drives GP2 with 16-bit PWM at 1 kHz, so the dim end is smooth.

MobiFlight writes outputs with `digitalWrite()` (weak, replaced for GP2) and `analogWrite()` (not weak). The build links with `-Wl,--wrap=analogWrite` so the core's calls for GP2 end up here too. Other pins pass straight through.

GP2 shares PWM slice 1 with GP18 and GP19 (D15, D16). The board file marks those two as non-PWM so nothing reconfigures the slice.

## Analog inputs

MobiFlight reads 10 bits (0 to 1023) and only sends a value once it has changed by at least the sensitivity. With the default of 5 that's about 200 steps across a pot; 3 is a good balance between smooth and steady. The ends can stop a couple of counts short of 0 or 1023 for the same reason.

There's no pull-up on analog inputs (`analogRead()` turns it off), same as the stock firmware. A pot reads linear, but an empty jack set to analog floats and sends random values.

## The Connector package

`SIMINPUT/Community/` is what ends up in the Connector's `Community` folder:
- `boards/siminput_rev2.board.json`: name, USB IDs, pin names, module limits, links.
- `config/siminput_rev2.all-buttons.mfmc`: the "All buttons" preset.
- `firmware/`: the build adds the UF2. `reset.raspberry_pico_flash_nuke.uf2` is for the Connector's "reset board".

The box uses the arduino-pico default USB ID `2E8A:000A`, with product name "SIMINPUT (MobiFlight)". The Connector tells it apart from a plain Pico by the type it reports, "SIMINPUT rev2".

## What's left out

SIMINPUT has no pins free for steppers, servos, displays, shift registers or multiplexers, so those are left out of the build. That also keeps AccelStepper (GPL v3) out of the binary.

## Tools

Python scripts for testing on Linux, run with `uv run --with pyserial python tools/<script>`:

- `mftool.py`: talk to the box without the Connector: `info`, `config`, `upload`, `monitor`, `out <index> <value>`, `bootloader`.
- `to_mobiflight.py` and `to_siminput.py` are the Linux originals of the Configurator's switch flow, handy for development. `to_mobiflight.py`: back up the SIMINPUT config, then switch a box on the stock firmware to this one. Needs the Configurator's code: `uv run --project ../siminput-firmware-updater`.
- `to_siminput.py`: back to the stock firmware, restoring the backed-up config.

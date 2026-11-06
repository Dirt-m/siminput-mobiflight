# SIMINPUT board rev2

Everything here comes from `../siminput-firmware-v2/code.py` (`_board_map`, `_detect_board`, `_init_hardware`), its README, and `../siminput-website/PRODUCT-FACTS.md`. Where these notes and the code disagree, the code wins.

Schematic and PCB layout: https://oshwlab.com/milo.speelman/project_xsuqnvlv (EasyEDA, public). Not checked for these notes; check it for anything marked open below.

## Overview

- MCU: RP2040 directly on a custom assembled PCB (not a Pico module). The stock firmware runs the Pico CircuitPython build.
- I/O expander: TCA9555 (16 bit, I2C, address `0x20`).
- 42 inputs: D1 to D22 on direct GPIO, A1 to A4 on the ADC pins, D23 to D38 on the expander.
- 1 output: backlight PWM (8 LEDs, 25 lm each).
- Every input is a switch closing to ground over a JST 1.25 mm 2-pin cable (red signal, black ground). No per-module electronics, no bus, no addressing. The firmware uses internal pull-ups, so inputs are active low.

## Pin map

| SIMINPUT name | Hardware | Notes |
|---|---|---|
| I2C SDA | GP0 | I2C0, to the TCA9555 |
| I2C SCL | GP1 | |
| Backlight | GP2 | PWM, 1 kHz in the CircuitPython firmware. Brightness uses a perceptual curve. |
| GP3 | TCA9555 INT# | Open drain, active low. Not used by the CircuitPython firmware. The MobiFlight build uses it to skip I2C reads when nothing changed. |
| D1 to D22 | GP4 to GP25 | Dn = GP(n+3). Pulled-up digital inputs. The only pins encoders can use. |
| A1 to A4 | GP26 to GP29 | ADC0 to ADC3. Digital input with pull-up by default, or 0 to 3.3 V analog when claimed. Never more than 3.3 V. |
| D23 to D38 | TCA9555 P0.0 to P1.7 | D(23+i) = expander pin i, i = 0 to 15 (port 0 = pins 0 to 7, port 1 = pins 8 to 15). |

How the CircuitPython firmware sets up the expander: all 16 pins as inputs (`configuration_port_0/1 = 0xFF`) and **polarity inversion on** (`polarity_inversion_port_0/1 = 0xFF`), so a closed switch reads as 1. Where the expander inputs get their pull-ups (TCA9555 internal or resistors on the PCB) isn't confirmed. Check the datasheet and schematic. The expander is polled over I2C (about 1 ms per sample). The CircuitPython firmware doesn't use the interrupt line on GP3.

Board detection: the firmware probes I2C on GP0/GP1 for `0x20`. If it's found, the board is rev2 (rev1 has its expander on GP6/GP7). A missing expander isn't fatal: the GPIO inputs keep working and the fault is reported. A MobiFlight build that is rev2 only doesn't need detection, but should still survive a dead expander.

## It's a custom PCB, not a Pico

Rev2 is a custom assembled PCB with the RP2040 chip directly on the board. It isn't a Raspberry Pi Pico module, even though the product copy and the stock firmware say "Pico". The stock firmware runs the Pico build of CircuitPython because the board is close enough to the Pico reference design.

That's why rev2 can use GP23, GP24, GP25 (as D20 to D22) and GP29 (as A4) as plain inputs. On a real Pico these are internal (SMPS mode, VBUS sense, LED, VSYS/3). Consequences for the MobiFlight build:
- The board JSON can expose all 30 GPIO. Don't copy the Pico template's pin list.
- The `raspberrypi_pico` PlatformIO board/variant is the likely starting point, but check what the schematic says about the flash chip and size, the crystal and boot2 before relying on it. There's no Pico LED on GP25 (it's D22), so make sure nothing in the core or the firmware drives it.
- USB VID/PID under MobiFlight is our call (MobiFlight's Pico template matches `VID_2E8A&PID_000A`). See open decision 3 in `GOAL.md`.

## What the modules put on the pins

Six module types plug into six slots (from PRODUCT-FACTS.md):
- **Dual-Position Module**: two positions, each a 2-way/3-way switch (some momentary), a rotary encoder, or a tactile button.
- **Rotary Module**: 5-position click rotary (one pin per position).
- **Two-Slot Rotary Switch**: 8-position rotary, spans two slots.
- **Key Module**: 3 momentary keys.
- **Lever Module**: push-pull lever on two micro switches. The middle position is "both off".
- **Guarded Switch**: 2-way toggle under a flip cover.

Mapping consequences for MobiFlight:
- Plain buttons/switches: MobiFlight `Button` devices on GPIO, or inputs from the expander.
- Encoders: two adjacent GPIO pins (D1 to D22 only), up to 10 per box. MobiFlight `Encoder` devices.
- "All off" states (3-way middle, a rotary's last position, the lever's middle): in SIMINPUT these come from a NOR rule in the firmware. MobiFlight has no rule engine on the board. The Connector handles this with button release events and conditions, so it's a configuration concern, not a firmware one.
- Which connector maps to which D number isn't documented yet, even in SIMINPUT itself (users find pins with the live monitor). We may need to write it up.

## Electrical limits

- ADC pins take 0 to 3.3 V only. A 5 V sensor needs a divider.
- RP2040 ADC is 12 bit. CircuitPython scales it to 16 bit. MobiFlight's analog input uses Arduino `analogRead` (10 bit by default on arduino-pico unless `analogReadResolution` is changed).

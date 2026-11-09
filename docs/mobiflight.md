# MobiFlight notes

Checked against the upstream GitHub repos on 2026-11-06. Re-check before relying on any detail.

## What MobiFlight is

Free, open-source software for home cockpits (MSFS, X-Plane, Prepar3D, FSX). Two halves:
- **Firmware** on a microcontroller (Arduino Mega/Uno/Nano/Pro Micro, Raspberry Pi Pico and Pico 2). Generic: at runtime the Connector tells the board which "devices" sit on which pins (buttons, encoders, analog inputs, outputs, shift registers, 7-segment, LCD, servos, steppers), and the board stores that in EEPROM (flash, on the Pico).
- **Connector**, the Windows app. Maps inputs to sim events and sim variables to outputs. Talks to the board over USB CDC serial using CmdMessenger (text commands).

The firmware is **not** a HID joystick. The board is serial only and needs the Connector running.

## Upstream layout (MobiFlight-FirmwareSource)

- `src/mobiflight.cpp`, `src/Config.cpp`, `src/CommandMessenger.cpp`: main loop, device config parsing, the serial protocol.
- `src/MF_Button`, `MF_Encoder`, `MF_Analog`, `MF_Output`, `MF_InputShifter` (74HC165), `MF_DigInMux` (CD4067), `MF_OutputShifter`, `MF_Segment`, `MF_LCDDisplay`, `MF_Servo`, `MF_Stepper`: one folder per device type.
- `src/MF_CustomDevice`: the hook that community devices plug into.
- `_Boards/*.board.json`: board definitions the Connector reads (pins, limits, USB IDs, firmware file name).
- `platformio.ini`: env `mobiflight_raspberrypico` uses maxgerhardt's `platform-raspberrypi` (arduino-pico core).

## Community boards (CommunityTemplate)

The official way for third parties to ship their own MobiFlight firmware. You create a repo from `MobiFlight/CommunityTemplate`, run `python renaming.py`, and get:
- `Community/boards/<name>.board.json`: your board as the Connector sees it. Includes `HardwareIds` (USB VID/PID regex), `FriendlyName`, `MobiFlightType`, `ModuleLimits`, the `Pins` list (with `isAnalog`, `isI2C`, `isPWM`), `CustomDeviceTypes`, and a `Community` block (project, website, docs, support links).
- `Community/devices/<name>.device.json`: each custom device type, with its config pins and `MessageTypes`.
- `MyCustomClass.cpp/.h`: your device code. Interface: `begin()`, `attach(pin, init)`, `detach()`, `set(messageID, setPoint)`, `update()`.
- Its own CI and release workflows, which produce firmware files the Connector can flash itself (`CanInstallFirmware`).

Examples in the template README: the GNC255 OLED and the KAV Simulation FCU/EFIS.

## The expander problem (core design question)

The custom device interface is **output-oriented**. `set(messageID, value)` receives data from the Connector. There is no matching path to report inputs, and none of the stock input types talk I2C. So the 22 GPIO buttons, the encoders and the 4 analog inputs work with stock MobiFlight, but D23 to D38 on the TCA9555 don't.

Decided: virtual pins (see below). The original candidates, for the record:
1. **Emulate an existing input type over I2C.** The Connector already understands `InputShifter` (74HC165 chain) and `DigInMux` events. A firmware-side variant that reads the TCA9555 but reports as an input shifter of 2 × 8 bits would need no Connector change. To check: how the shifter is configured (it takes data/clock/latch pins, which we'd have to fake or ignore) and whether pin validation in the Connector would object.
2. **Send button events from the custom device.** Call the firmware's button/input event send path directly from `update()`. Check whether upstream community devices do this and whether the Connector accepts events for pins/names it didn't configure.
3. **Upstream contribution.** Add an I2C expander input device (TCA9555/MCP23017 style) to MobiFlight-FirmwareSource and the Connector. The cleanest result, but it needs maintainer buy-in and a Connector release. Ask on their Discord; this may already be on their list.

## Licensing

- MobiFlight-FirmwareSource, CommunityTemplate, Connector: MIT (Copyright 2021 MobiFlight). Keep the notice and license text in the fork and in what ships.
- Dependencies compiled in: CmdMessenger (MIT), arduino-pico core (LGPL 2.1), Servo (LGPL 2.1), LiquidCrystal_I2C (MobiFlight fork, no license file found), **AccelStepper (GPL v3 or commercial)**.
- Because of AccelStepper, a binary that includes stepper support is covered by GPL v3 as a whole: publish the source and state where to get it. Simplest fix: SIMINPUT has no steppers, so exclude stepper support from our build and the question goes away. The LGPL parts are satisfied by the source being public.
- The MobiFlight name and logo aren't covered by MIT. Name it as SIMINPUT's build, and ask the MobiFlight team before launch (Discord) as courtesy.

## Joystick route (no firmware change, works today)

The stock SIMINPUT firmware is a standard HID joystick (128 buttons, 8 axes). MobiFlight Connector accepts joysticks as input devices, so all 42 inputs already work as inputs, including the expander pins and SIMINPUT's rule engine (toggles, encoders, NOR states). What it can't do is outputs. This project only adds value where outputs (backlight, future LEDs/displays) or native MobiFlight module setup matter. Keep that in mind when scoping.

## Chosen: virtual pins (2026-11-06)

- arduino-pico defines `pinMode`, `digitalRead` and `digitalWrite` as weak aliases of `__pinMode` etc. (`cores/rp2040/wiring_digital.cpp`). A strong definition in our folder wins at link time.
- MFButton and MFEncoder only touch pins through `pinMode` and `digitalRead`. MFInputShifter drives its own latch/clock pins, so emulating it would have meant replacing a core file.
- The Connector matches input events by device name only (`MobiFlightModule.OnButtonChange`). Its input picker lists the devices in the module config (`DeviceReferenceFactory`). Pin dropdowns show the board JSON pin `Name`.
- Unmodified core `__digitalRead()` returns LOW for pins >= 30. If the override ever fails to link, D23 to D38 would all read as pressed: an easy symptom to spot.

## Other findings

- The Connector sends analog inputs as type 11 (`kTypeAnalogInputDeprecated`). The core sets `INPUT_PULLUP`, but arduino-pico's `analogRead()` reinitialises the pin for the ADC and drops the pull-up. Measured on 2026-11-09: an empty jack floats around 150 to 250 and drifts; bridged to GND reads 2. Same as the stock firmware (`AnalogIn`, no pull).
- `Info.DeviceConfigs` in the board JSON lists `.mfmc` presets in `Community/<project>/config/`.
- The core only sends input events after the Connector has called GetConfig (`getBoardReady()`).
- The core's device modules are not compile-guarded by their `MF_*_SUPPORT` flags. Unused ones must be removed with `build_src_filter`, or their library headers (AccelStepper, Servo, LiquidCrystal_I2C) are still needed.

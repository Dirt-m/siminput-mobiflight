//
// siminput_expander.cpp
//
// SIMINPUT firmware for MobiFlight, board rev2.
//
// Makes the 16 TCA9555 expander inputs (D23 to D38) look like ordinary GPIO to
// the MobiFlight core, so they can be used as plain Button devices.
//
// How: the board JSON lists virtual pins 30 to 45 (named D23 to D38). The
// arduino-pico core defines pinMode() and digitalRead() as weak aliases of
// __pinMode() and __digitalRead(). The strong definitions below take the
// virtual pins and pass every real GPIO straight through to the core. The
// MobiFlight core sources stay untouched.
//
// Expander reads are cheap: the TCA9555 pulls INT# (GP3) low when an input
// changes, so the I2C bus is only touched when something changed, plus a slow
// fallback poll. If the expander is missing or stops answering, its pins read
// as released and the GPIO inputs keep working. It is probed again every second.
//

#include <Arduino.h>
#include <Wire.h>
#include "config.h"
#include "commandmessenger.h"

// Overridable for tests: build with -DSIMINPUT_TCA_ADDR=0x21 to simulate a dead expander.
#ifndef SIMINPUT_TCA_ADDR
#define SIMINPUT_TCA_ADDR 0x20
#endif

extern "C" void      __pinMode(pin_size_t pin, PinMode mode);
extern "C" PinStatus __digitalRead(pin_size_t pin);

namespace
{
    // Hardware, see docs/how-it-works.md
    constexpr uint8_t PIN_SDA   = 0;
    constexpr uint8_t PIN_SCL   = 1;
    constexpr uint8_t PIN_INT   = 3; // TCA9555 INT#, open drain, active low
    constexpr uint8_t TCA_ADDR  = SIMINPUT_TCA_ADDR;
    constexpr uint8_t VPIN_BASE = 30; // D23 = pin 30 = expander P0.0
    constexpr uint8_t VPIN_LAST = VPIN_BASE + 15;

    // TCA9555 registers (each is a pair: port 0, then port 1)
    constexpr uint8_t REG_INPUT    = 0x00;
    constexpr uint8_t REG_POLARITY = 0x04;
    constexpr uint8_t REG_CONFIG   = 0x06;

    constexpr uint32_t FALLBACK_POLL_MS = 20;   // read even without INT#, in case it is stuck
    constexpr uint32_t RETRY_MS         = 1000; // probe interval while the expander is missing

    bool     busReady  = false;
    bool     present   = false;
    bool     reported  = true;  // last presence state sent to the Connector log; only changes from "present" are logged
    uint16_t inputs    = 0xFFFF; // raw input levels, 1 = high = released
    uint32_t lastRead  = 0;
    uint32_t lastProbe = 0;

    void logState()
    {
        // Only once the Connector has fetched the config, so we never interleave
        // with the config handshake. kDebug only goes to the Connector log.
        if (present == reported || !getBoardReady()) return;
        reported = present;
        cmdMessenger.sendCmd(kDebug, present ? F("SIMINPUT: expander found") : F("SIMINPUT: expander not responding, D23 to D38 read as released"));
    }

    bool writePair(uint8_t reg, uint8_t port0, uint8_t port1)
    {
        Wire.beginTransmission(TCA_ADDR);
        Wire.write(reg);
        Wire.write(port0);
        Wire.write(port1);
        return Wire.endTransmission() == 0;
    }

    bool readInputs()
    {
        Wire.beginTransmission(TCA_ADDR);
        Wire.write(REG_INPUT);
        if (Wire.endTransmission(false) != 0) return false;
        if (Wire.requestFrom(TCA_ADDR, (uint8_t)2) != 2) return false;
        uint8_t p0 = Wire.read();
        uint8_t p1 = Wire.read();
        inputs     = (uint16_t)p1 << 8 | p0;
        lastRead   = millis();
        return true;
    }

    void lost()
    {
        present = false;
        inputs  = 0xFFFF;
        logState();
    }

    void probe()
    {
        lastProbe = millis();
        if (!busReady) {
            Wire.setSDA(PIN_SDA);
            Wire.setSCL(PIN_SCL);
            Wire.setTimeout(5);
            Wire.begin();
            Wire.setClock(400000);
            __pinMode(PIN_INT, INPUT_PULLUP);
            busReady = true;
        }
        // Set every register we depend on. The expander is not reset when the
        // RP2040 reboots, and the CircuitPython firmware leaves polarity
        // inversion switched on.
        present = writePair(REG_CONFIG, 0xFF, 0xFF)       // all inputs
                  && writePair(REG_POLARITY, 0x00, 0x00)  // no inversion: closed switch reads low, as MobiFlight expects
                  && readInputs();                        // also clears INT#
        if (!present) inputs = 0xFFFF;
        logState();
    }

    void refresh()
    {
        logState(); // catches a state change from before the Connector was ready
        if (!present) {
            if (millis() - lastProbe >= RETRY_MS) probe();
            return;
        }
        if (__digitalRead(PIN_INT) == LOW || millis() - lastRead >= FALLBACK_POLL_MS) {
            if (!readInputs()) lost();
        }
    }

    inline bool isVirtual(pin_size_t pin)
    {
        return pin >= VPIN_BASE && pin <= VPIN_LAST;
    }
} // namespace

extern "C" void pinMode(pin_size_t pin, PinMode mode)
{
    if (!isVirtual(pin)) {
        __pinMode(pin, mode);
        return;
    }
    // Expander pins are always inputs. Pull-ups and direction are fixed in
    // probe(). Make sure the expander has been set up before the first read.
    if (!busReady) probe();
}

extern "C" PinStatus digitalRead(pin_size_t pin)
{
    if (!isVirtual(pin)) return __digitalRead(pin);
    refresh();
    return (inputs >> (pin - VPIN_BASE)) & 1 ? HIGH : LOW;
}

// siminput_expander.cpp

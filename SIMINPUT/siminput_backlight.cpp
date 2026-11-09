//
// siminput_backlight.cpp
//
// SIMINPUT firmware for MobiFlight, board rev2.
//
// Gives the backlight (GP2) the same brightness curve as the stock SIMINPUT
// firmware: t^2 + 0.01 (quadratic, close to how the eye sees brightness, with
// a small offset so the first step above 0 glows), 0 stays off, and an optional
// cap. The sim sends a linear 0 to 255; the curve is applied here.
//
// How: MFOutput::set() calls digitalWrite() for 0 and 255 and analogWrite()
// otherwise. digitalWrite() is weak in arduino-pico, so it is overridden below.
// analogWrite() is not, so the build links with -Wl,--wrap=analogWrite, which
// sends every call to __wrap_analogWrite() below. Every pin except GP2 passes
// straight through. The MobiFlight core sources stay untouched.
//
// GP2 runs its own 16 bit PWM at 1 kHz (as the stock firmware does), so the
// low end of the curve has fine steps. GP2 shares PWM slice 1 with GP18 and
// GP19 (D15, D16); the board JSON marks those two as non PWM so the Connector
// never asks for analogWrite() on them, which would reconfigure the slice.
//

#include <Arduino.h>
#include <hardware/clocks.h>
#include <hardware/gpio.h>
#include <hardware/pwm.h>

// Brightness at 255, in percent. 100 = full, as in the stock firmware.
#ifndef SIMINPUT_BACKLIGHT_MAX_PERCENT
#define SIMINPUT_BACKLIGHT_MAX_PERCENT 100
#endif

extern "C" void __real_analogWrite(pin_size_t pin, int val);
extern "C" void __digitalWrite(pin_size_t pin, PinStatus val);

namespace
{
    constexpr uint8_t  PIN_BACKLIGHT = 2;
    constexpr uint32_t PWM_FREQ      = 1000;
    constexpr uint16_t PWM_TOP       = 65535;

    bool pwmReady = false;

    void setBacklight(uint8_t value)
    {
        uint slice = pwm_gpio_to_slice_num(PIN_BACKLIGHT);
        if (!pwmReady) {
            pwm_config c = pwm_get_default_config();
            pwm_config_set_clkdiv(&c, (float)clock_get_hz(clk_sys) / ((float)(PWM_TOP + 1) * PWM_FREQ));
            pwm_config_set_wrap(&c, PWM_TOP);
            pwm_init(slice, &c, true);
            pwmReady = true;
        }
        float t = value / 255.0f;
        if (t > 0) {
            t = t * t + 0.01f;
            if (t > 1.0f) t = 1.0f;
        }
        t *= SIMINPUT_BACKLIGHT_MAX_PERCENT / 100.0f;
        gpio_set_function(PIN_BACKLIGHT, GPIO_FUNC_PWM);
        pwm_set_gpio_level(PIN_BACKLIGHT, (uint16_t)(t * PWM_TOP + 0.5f));
    }
} // namespace

extern "C" void __wrap_analogWrite(pin_size_t pin, int val)
{
    if (pin != PIN_BACKLIGHT) {
        __real_analogWrite(pin, val);
        return;
    }
    setBacklight(val < 0 ? 0 : val > 255 ? 255 : val);
}

extern "C" void digitalWrite(pin_size_t pin, PinStatus val)
{
    if (pin != PIN_BACKLIGHT) {
        __digitalWrite(pin, val);
        return;
    }
    setBacklight(val == HIGH ? 255 : 0);
}

// siminput_backlight.cpp

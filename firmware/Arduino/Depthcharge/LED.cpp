// SPDX-License-Identifier: BSD-3-Clause
// Depthcharge: <https://github.com/nccgroup/depthcharge>

#include "LED.h"

namespace Depthcharge {
    LED::LED() : m_pin(-1), m_on(HIGH), m_off(LOW) {}

    void LED::attach(unsigned int pin, unsigned int on, unsigned int off)
    {
        m_pin = pin;
        m_on  = on;
        m_off = off;

        pinMode(m_pin, OUTPUT);
        this->on();
    }


    void LED::blink(unsigned int ms_on, unsigned int ms_off, unsigned int n)
    {
        if (m_pin < 0) {
            return;
        }

        for (unsigned int i = 0; i < n; i++) {
            this->on();
            delay(ms_on);

            this->off();
            delay(ms_off);
        }
    }

    void LED::blink_value(uint32_t value, unsigned int n,
                          unsigned int ms_bit_period)
    {
        if (m_pin < 0) {
            return;
        }

        unsigned int i;

        if (n > 32) {
            n = 32;
        }

        for (i = 0; i < n; i++) {
            if (value & (1 << 31)) {
                on();
            } else {
                off();
            }
            delay(ms_bit_period);

            value <<= 1;
        }
    }

    void LED::on() {
        m_state = true;
        digitalWrite(m_pin, m_on);
    }

    void LED::off() {
        m_state = false;
        digitalWrite(m_pin, m_off);
    }

    void LED::toggle() {
        if (m_state) {
            this->off();
        } else {
            this->on();
        }
    }
};

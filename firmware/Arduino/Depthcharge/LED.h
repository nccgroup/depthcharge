// SPDX-License-Identifier: BSD-3-Clause
// Depthcharge: <https://github.com/nccgroup/depthcharge>

#pragma once
#include <Arduino.h>
namespace Depthcharge {
    class LED {
        public:

            LED();

            void attach(unsigned int pin, unsigned int on, unsigned int off);

            void blink(unsigned int ms_on, unsigned int ms_off, unsigned int n);

            /*
             * Blink an n-bit value on the LED, MSB-first.
             *
             * The blink period is constant, but the duty cycle differs for
             * 0 and 1 bits.
             *
             * A 1-bit will be a "slow" blink at a 50% duty cycle, and a
             * 0-bit is a "fast" blink, at a 20% duty cycle.
             */
            void blink_value(uint32_t value, unsigned int n,
                             unsigned int ms_bit_period);

            void on();

            void off();

            void toggle();


        private:
            bool m_state;
            unsigned int m_pin;
            unsigned int m_on;
            unsigned int m_off;
    };
};

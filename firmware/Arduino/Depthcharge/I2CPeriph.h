// SPDX-License-Identifier: BSD-3-Clause
// Depthcharge: <https://github.com/nccgroup/depthcharge>

#pragma once
#include <Arduino.h>
#include <Wire.h>

namespace Depthcharge {

    class I2CPeriph {

        public:
            I2CPeriph();

            void attach(::TwoWire *bus, uint8_t addr, uint32_t speed);
            bool attached();

            void setAddress(uint8_t addr);
            uint8_t getAddress();

            void setSubAddressLength(uint8_t len);
            uint8_t getSubAddressLength();

            void setSpeed(uint32_t speed);
            uint32_t getSpeed();

            uint32_t getWriteBuffer(uint8_t *buf, size_t max_len);
            void setReadBuffer(uint8_t *buf, size_t len);

            // This seems to be an implicit limit Arduino APIs, unfortunately.
            // Torn between hacking around it and trying to remain portable...
            static const size_t BUFFER_SIZE = 32;

        private:
            static ::TwoWire *m_i2c;

            static uint8_t m_addr;      // Device address in [0x00, 0x7f]
            static uint32_t m_speed;    // Bus speed, Hz

            // Handle data written from the bus controller to our device buffer
            static void _handle_write(int count);

            // Handle read of data from our device buffer, to the host
            static void _handle_read();

            /* We have plenty of space on the Teensy 3.6, so no
             * reason not to simplify things by using different read/write
             * buffers.  For more memory constrained devices, we might
             * want to replace this with a single buffer. The host-code
             * is in control of the target's bus controller, so in theory,
             * we should not have to worry about concurrent accesses attempts.
             *
             * TODO: Arguably these might need to be volatile, since we're
             *       accessing them across normal and interrupt contexts.
             *
             *       However, it's a bit of a PITA since we'll have to
             *       cast away the volatile attribute when we hit the
             *       the platform-specific TwoWire APIs.
             *
             *       Need to re-read through the C++11 book and spec and mull
             *       this over. For now, we at least ensure that accesses
             *       are atomic, and no control flows are actively waiting
             *       for a change to occur from the other context.
             */
            static uint8_t m_rbuf[BUFFER_SIZE];
            static size_t  m_rcount;

            static uint8_t m_wbuf[BUFFER_SIZE];
            static size_t  m_wcount;

            // How many subaddress bytes to throw away and ignore
            static uint8_t m_subaddr_len;
    };
}

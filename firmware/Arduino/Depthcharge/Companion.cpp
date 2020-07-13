// SPDX-License-Identifier: BSD-3-Clause
// Depthcharge: <https://github.com/nccgroup/depthcharge>

#include "Depthcharge.h"
#include "Version.h"
#include "Panic.h"

#ifndef DEPTHCHARGE_LED_BLINK_PERIOD_MS
#   define DEPTHCHARGE_LED_BLINK_PERIOD_MS 1000
#endif

#define DEPTHCHARGE_LED_BLINK_DELTA (DEPTHCHARGE_LED_BLINK_PERIOD_MS / 2)


namespace Depthcharge {

    Companion::Companion() : m_caps(0) { }

    void Companion::attachHostInterface(::Stream *port)
    {
        m_comm.attach(port);
    }

    void Companion::attachLED(unsigned int pin,
                              unsigned int on_state, unsigned int off_state) {

        m_led.attach(pin, on_state, off_state);
    }

    void Companion::attachI2C(::TwoWire *bus, uint8_t addr, uint32_t speed)
    {
        m_i2c.attach(bus, addr, speed);
        m_caps |= CAP_I2C_PERIPH;
    }

    void Companion::processEvents()
    {
        static Communicator::msg msg;
        static unsigned long last_led_toggle = 0;
        unsigned long now = millis();

        if ((now - last_led_toggle) > DEPTHCHARGE_LED_BLINK_DELTA) {
            m_led.toggle();
            last_led_toggle = now;
        }

        if (Panic::active()) {
            panicLoop(); // Does not return. Emits panic reason via LED.
        }

        if (m_comm.hasRequest(msg)) {
            handleHostMessage(msg);
        }
    }

    void Companion::handleHostMessage(Communicator::msg &msg)
    {
        switch (msg.cmd) {
            case FW_GET_VERSION:
                msg.len = 4;
                msg.data[0] = VERSION_MAJOR;
                msg.data[1] = VERSION_MINOR;
                msg.data[2] = VERSION_PATCH;
                msg.data[3] = VERSION_EXTRA;
                break;

            case FW_GET_CAPABILITIES:
                static_assert(sizeof(m_caps) < sizeof(msg.data),
                              "Broken m_caps -> msg.data copy!");

                msg.len = sizeof(m_caps);
                memcpy(msg.data, &m_caps, sizeof(m_caps));
                break;


            // TODO: Move I2C_ items into subhandlers to de-dup
            // attached() logic.

            case I2C_GET_ADDR:
                msg.len = 1;
                if (m_i2c.attached()) {
                    msg.data[0] = m_i2c.getAddress();
                } else {
                    msg.data[0] = Error::NOT_SUPPORTED;
                }
                break;

            case I2C_SET_ADDR:
                if (msg.len != 1 || msg.data[0] > 0x7f) {
                    msg.data[0] = Error::INVALID_PARAM;
                } else if (m_i2c.attached()) {
                    m_i2c.setAddress(msg.data[0]);
                    msg.data[0] = SUCCESS;
                } else {
                    msg.data[0] = Error::NOT_SUPPORTED;
                }
                msg.len = 1;
                break;

            case I2C_GET_SPEED:
                if (m_i2c.attached()) {
                    const uint32_t speed = m_i2c.getSpeed();
                    msg.data[0] = speed         & 0xff;
                    msg.data[1] = (speed >> 8)  & 0xff;
                    msg.data[2] = (speed >> 16) & 0xff;
                    msg.data[3] = (speed >> 24) & 0xff;
                    msg.len = 4;
                } else {
                    msg.data[0] = Error::NOT_SUPPORTED;
                    msg.len = 1;
                }
                break;

            case I2C_SET_SPEED:
                if (msg.len != 4 || msg.data[0] == 0) {
                    msg.data[0] = Error::INVALID_PARAM;
                } else if (m_i2c.attached()) {
                    const uint32_t speed = msg.data[0]        |
                                          (msg.data[1] << 8)  |
                                          (msg.data[2] << 16) |
                                          (msg.data[3] << 24);

                    m_i2c.setSpeed(speed);
                    msg.data[0] = Error::SUCCESS;
                } else {
                    msg.data[0] = Error::NOT_SUPPORTED;
                }
                msg.len = 1;
                break;

            case I2C_GET_SUBADDR_LEN:
                if (m_i2c.attached()) {
                    msg.data[0] = m_i2c.getSubAddressLength();
                } else {
                    msg.data[0] = Error::NOT_SUPPORTED;
                }
                msg.len = 1;
                break;

            case I2C_SET_SUBADDR_LEN:
                if (m_i2c.attached()) {
                    m_i2c.setSubAddressLength(msg.data[0]);
                    msg.data[0] = Error::SUCCESS;
                } else {
                    msg.data[0] = Error::NOT_SUPPORTED;
                }
                msg.len = 1;
                break;

            // TODO: Add a flag to allow us to support U-Boot versions with
            //       and without the i2c write "-s" option. For now,
            //       we always assume bulk writes (with -s) are supported.
            case I2C_GET_MODE_FLAGS:
                msg.len = 1;
                msg.data[0] = Error::UNIMPLEMENTED;
                break;

            case I2C_SET_MODE_FLAGS:
                msg.len = 1;
                msg.data[0] = Error::UNIMPLEMENTED;
                break;

            case I2C_SET_READ_BUFFER:
                if (msg.len < 1) {
                    msg.data[0] = Error::INVALID_PARAM;
                } else if (m_i2c.attached()) {
                    m_i2c.setReadBuffer(msg.data, msg.len);
                    msg.data[0] = SUCCESS;
                } else {
                    msg.data[0] = Error::NOT_SUPPORTED;
                }
                msg.len = 1;
                break;

            case I2C_GET_WRITE_BUFFER:
                if (m_i2c.attached()) {
                    msg.len = m_i2c.getWriteBuffer(msg.data, sizeof(msg.data));
                } else {
                    msg.len = 1;
                    msg.data[0] = Error::NOT_SUPPORTED;
                }
                break;

            default:
                msg.len = 1;
                msg.data[0] = Error::INVALID_CMD;
        }

        m_comm.sendResponse(msg);
    }

    void Companion::panicLoop()
    {
        const uint32_t reason = Panic::reason();
        noInterrupts();
        while (1) {
            // Add some MSBs so we can make sense of timing
            m_led.blink_value(0xAA << 24 | reason, 32, 50);
            delay(250);
        }
    }
};

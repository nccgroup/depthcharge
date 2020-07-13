// SPDX-License-Identifier: BSD-3-Clause
// Depthcharge: <https://github.com/nccgroup/depthcharge>

#include "I2CPeriph.h"
#include "Panic.h"

#define SET_PANIC_REASON() \
    do { Panic::setReason(Panic::Source::I2CPeriph , __LINE__); } while (0)

namespace Depthcharge {

    I2CPeriph::I2CPeriph() { };

    void I2CPeriph::attach(::TwoWire *bus, uint8_t addr, uint32_t speed)
    {

        if (m_i2c) {
            /* This class does not currently support multiple buses, so induce
             * an error as early as possible. See the header file for more
             * information about what needs to change, if you require support
             * for multiple I2C buses. */
            SET_PANIC_REASON();
            return;
        }

        m_i2c  = bus;
        m_addr = addr;

        memset(m_rbuf, 0, sizeof(m_rbuf));
        m_rcount = 0;

        memset(m_wbuf, 0, sizeof(m_wbuf));
        m_wcount = 0;

        // setAddress invokes begin() because I see no other API-exposed
        // method for changing an I2C peripheral address at runtime. This
        // must be called prior to setSpeed(). Doing otherwise will hang the
        // TI Launchpad EK-TM4C123GXL.
        setAddress(addr);
        setSpeed(speed);
    }


    bool I2CPeriph::attached() {
        return m_i2c != NULL;
    }

    void I2CPeriph::setAddress(uint8_t addr)
    {
        if (m_i2c) {
            m_i2c->begin(addr);
            m_i2c->onReceive(_handle_write);
            m_i2c->onRequest(_handle_read);
        }
    }

    uint8_t I2CPeriph::getAddress()
    {
        if (m_i2c) {
            return m_addr;
        } else {
            return 0xff;
        }
    }

    void I2CPeriph::setSpeed(uint32_t speed)
    {
        if (speed != 0) {
            m_speed = speed;
            m_i2c->setClock(m_speed);
        }
    }

    uint32_t I2CPeriph::getSpeed() {
        return m_speed;
    }

    void I2CPeriph::setSubAddressLength(uint8_t len)
    {
        noInterrupts();
        m_subaddr_len = len;
        interrupts();
    }

    uint8_t I2CPeriph::getSubAddressLength()
    {
        uint8_t ret;

        noInterrupts();
        ret = m_subaddr_len;
        interrupts();

        return ret;
    }

    uint32_t I2CPeriph::getWriteBuffer(uint8_t *buf, size_t max_len)
    {
        uint32_t ret;
        noInterrupts();

        if (m_wcount > max_len) {
            ret = static_cast<uint32_t>(max_len);
        } else {
            ret = m_wcount;
        }

        memcpy(buf, m_wbuf, ret);

        interrupts();
        return ret;
    }

    // Fill data buffer for master to read
    void I2CPeriph::setReadBuffer(uint8_t *buf, size_t len)
    {
        noInterrupts();

        if (len > sizeof(m_rbuf)) {
            len = sizeof(m_rbuf);
        }

        memcpy(m_rbuf, buf, len);
        m_rcount = static_cast<uint32_t>(len);

        interrupts();
    }

    // ISR callback: Handle master's write to our buffer
    void I2CPeriph::_handle_write(int count)
    {
        if (count < 0) {
            SET_PANIC_REASON();
            return;
        } else if (static_cast<size_t>(count) > sizeof(m_wbuf)) {
            /* The Kinetis I2C driver appears to disallow this, but let's not
             * make assumptions.
             *
             * Landing here is suggestive of a bug in either our host-side
             * client, a bug in the firmware, or the target device performing
             * unexpected accesses that we're not in control of.
             *
             * Whatever it is - we need to know that we're not in control here.
             * Ingest some data so it's present for debugging, but otherwise
             * prepare to panic.
             */
            SET_PANIC_REASON();
            count = sizeof(m_wbuf);
        }

        // U-Boot wants to send a subaddress byte, so let's just toss that.
        // If you need this info setSubAddressLength(0).
        for (size_t i = 0; i < m_subaddr_len; i++) {
            m_i2c->read();
        }

        m_wcount = static_cast<size_t>(count);
        for (size_t i = 0; i < m_wcount; i++) {
            m_wbuf[i] = m_i2c->read();
        }
    }

    // ISR Callback: Handle master's read from our buffer
    void I2CPeriph::_handle_read()
    {
        m_i2c->write(m_rbuf, m_rcount);
    }

    // See header file re: static class members.
    uint8_t I2CPeriph::m_addr = 0;
    uint32_t I2CPeriph::m_speed = 0;
    ::TwoWire* I2CPeriph::m_i2c = NULL;

    uint8_t I2CPeriph::m_rbuf[BUFFER_SIZE] = { 0 };
    size_t  I2CPeriph::m_rcount = 0;

    uint8_t I2CPeriph::m_wbuf[BUFFER_SIZE] = { 0 };
    size_t  I2CPeriph::m_wcount = 0;

    uint8_t I2CPeriph::m_subaddr_len = 1;
}

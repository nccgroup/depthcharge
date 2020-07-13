// SPDX-License-Identifier: BSD-3-Clause
// Depthcharge: <https://github.com/nccgroup/depthcharge>

#pragma once

#include <Arduino.h>

#include "Communicator.h"
#include "LED.h"
#include "I2CPeriph.h"

namespace Depthcharge {

    enum Error {
        SUCCESS         = 0x00, // Operation was successful, without error
        UNIMPLEMENTED   = 0xfb, // Functionality stubbed, but not implemented
        UNINITIALIZED   = 0xfc, // Attempt to use uninitialized functionality
        INVALID_PARAM   = 0xfd, // Invalid parameter in request
        NOT_SUPPORTED   = 0xfe, // Not supported in this firmware or mode
        INVALID_CMD     = 0xff  // Invalid command identifier
    };

    /*
     * Depthcharge Companion device context
     * This is the "top level" design entity, so to speak.
     */
    class Companion {

        public:
            enum Command {
                FW_GET_VERSION          = 0x00,
                FW_GET_CAPABILITIES     = 0x01,

                // 0x02 - 0x07 reserved for future device-level settings

                I2C_GET_ADDR            = 0x08,
                I2C_SET_ADDR            = 0x09,
                I2C_GET_SPEED           = 0x0a,
                I2C_SET_SPEED           = 0x0b,
                I2C_GET_SUBADDR_LEN     = 0x0c,
                I2C_SET_SUBADDR_LEN     = 0x0d,
                I2C_GET_MODE_FLAGS      = 0x0e, // TODO: Not implemented
                I2C_SET_MODE_FLAGS      = 0x0f, // TODO: Not implemented
                I2C_SET_READ_BUFFER     = 0x10,
                I2C_GET_WRITE_BUFFER    = 0x11,

                // 0x20 - 0x2f reserved for SPI peripheral device operation

                // 0x60 - 0x7f reserved for device-level setting blowout

                /*
                 * 0x80 - 0xff is reserved for whomever is reading this.
                 * The upstream code won't use this range, so you're free to.
                 *
                 *               Happy hacking, neighbor!
                 *                    🔥☠️ jynik ☠️🔥
                 */
                NEIGHBOR_RESERVED_START = 0x80,
                NEIGHBOR_RESERVED_END   = 0xff
            };

            enum FirmwareCapabilities {
                CAP_I2C_PERIPH      = (1 << 0),
                CAP_SPI_PERIPH      = (1 << 1),  // Reserved
            };

            /* Platform implementations (in ino's) should try to use these
             * defaults, if possible, to yield consistency across targets.
             */
            static const uint32_t default_uart_baudrate = 115200;
            static const uint8_t  default_i2c_addr      = 0x78;
            static const uint32_t default_i2c_speed     = 100000;

            /*
             * Intantiate the main Depthcharge Companion firmware module
             */
            Companion();

            /*
             * Associate the Communicator with a serial port that will be used
             * to receive requests from the host.
             */
            void attachHostInterface(::Stream *port);

            void attachLED(unsigned int pin,
                           unsigned int on_state, unsigned int off_state);

            void attachI2C(::TwoWire *bus, uint8_t addr, uint32_t speed);

            /*
             * TODO
             */
            void processEvents();

        private:
            void handleHostMessage(Communicator::msg &msg);
            void panicLoop();

            static void _handleI2CRead(int n);

            uint32_t m_caps;

            Communicator m_comm; // Host interface
            I2CPeriph m_i2c;      // Operate as I2C peripheral device
            LED m_led;           // Blinks panic status
    };
};

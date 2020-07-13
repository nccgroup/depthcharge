// SPDX-License-Identifier: BSD-3-Clause
// Depthcharge: <https://github.com/nccgroup/depthcharge>

#pragma once

#include "Arduino.h"

namespace Depthcharge {
    /*
     * Instances of this represent a device <-> host interface handle.
     *
     * This just abstracts away some of the message handling so the Companion
     * code doesn't have to worry about it.
     */
    class Communicator {
        public:
            static const size_t MAX_DATA_SIZE = 64;

            struct __attribute__((packed)) msg {
                uint8_t cmd;
                uint8_t len;
                uint8_t data[MAX_DATA_SIZE];
            };

            /**
             * Instantiate a Communicator.
             *
             * It will be unusable until attach() is called to attach
             * a serial port to the device.
             */
            Communicator();

            /**
             * Associate the Communicator with a serial port that will
             * be used to receive requests from the host.
             */
            void attach(::Stream *port);

            /*
             * Check for a new request.
             *
             * If received, this function will update `request` and return true.
             *
             * Otherwise, false is returned and `request` is not modified.
             */
            bool hasRequest(msg &request);

            inline void sendResponse(msg &response) {
                if (response.len > MAX_DATA_SIZE) {
                    response.len = MAX_DATA_SIZE;
                }

                m_hostPort->write(
                    reinterpret_cast<byte*>(&response),
                    HEADER_SIZE + response.len
                );
            };

        private:
            enum state {
                UNINITIALIZED,
                IDLE,
                READ_REQUEST_HEADER,
                READ_REQUEST_DATA,
                RETURN_REQUEST,
                PANIC
            } m_state;

            ::Stream *m_hostPort;
            msg m_req;
            size_t m_data_rcvd;

            static const size_t HEADER_SIZE =
                sizeof(m_req.cmd) + sizeof(m_req.len);
    };
};

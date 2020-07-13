// SPDX-License-Identifier: BSD-3-Clause
// Depthcharge: <https://github.com/nccgroup/depthcharge>

#pragma once
#include <Arduino.h>

namespace Depthcharge {
    class Panic {
        public:
            enum Source {
                Communicator = 0x1,
                I2CPeriph    = 0x2,
            };

            static void setReason(Source source, uint16_t lineno);
            static bool active();
            static uint32_t reason();

        private:
            static uint32_t m_reason;
    };

};


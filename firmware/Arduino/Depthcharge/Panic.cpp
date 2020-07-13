// SPDX-License-Identifier: BSD-3-Clause
// Depthcharge: <https://github.com/nccgroup/depthcharge>

#include "Panic.h"
namespace Depthcharge {
    uint32_t Panic::m_reason = 0;

    void Panic::setReason(Source source, uint16_t lineno)
    {
        noInterrupts();
        if (m_reason == 0) {
            m_reason = ((source & 0xff) << 16)  | lineno;
        }
        interrupts();
    }

    bool Panic::active()
    {
        return m_reason != 0;
    }

    uint32_t Panic::reason()
    {
        return m_reason;
    }
}

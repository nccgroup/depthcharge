// SPDX-License-Identifier: BSD-3-Clause
// Depthcharge: <https://github.com/nccgroup/depthcharge>

#include "Communicator.h"
#include "Panic.h"

#define SET_PANIC_REASON() \
    do { Panic::setReason(Panic::Source::Communicator, __LINE__); } while (0)

namespace Depthcharge {

    Communicator::Communicator() :
        m_state(UNINITIALIZED), m_hostPort(NULL) {};

    void Communicator::attach(::Stream *port)
    {
        if (m_state == UNINITIALIZED) {
            m_hostPort = port;
            memset(&m_req,  0, sizeof(m_req));
            m_state = IDLE;
        }
    }

    bool Communicator::hasRequest(msg &req_out)
    {
        switch (this->m_state) {
            case IDLE:
                m_data_rcvd = 0;
                if (m_hostPort->available() >= (int) HEADER_SIZE) {
                    m_state = READ_REQUEST_HEADER;
                }
                break;

            case READ_REQUEST_HEADER: {
                size_t n = m_hostPort->readBytes(
                                reinterpret_cast<byte*>(&m_req), HEADER_SIZE);

                if (n != HEADER_SIZE) {
                    SET_PANIC_REASON();
                    m_state = PANIC;
                    return false;
                }

                if (m_req.len == 0) {
                    m_state = RETURN_REQUEST;
                } else if (m_req.len <= MAX_DATA_SIZE) {
                    m_data_rcvd = 0;
                    m_state = READ_REQUEST_DATA;
                } else {
                    SET_PANIC_REASON();
                    m_state = PANIC;
                    return false;
                }
                break;
            }

            case READ_REQUEST_DATA: {
                size_t avail = m_hostPort->available();
                if (avail > 0) {
                    size_t data_left = m_req.len - m_data_rcvd;
                    size_t to_read = (avail < data_left) ? avail : data_left;
                    uint8_t *ins = &m_req.data[m_data_rcvd];

                    size_t n = m_hostPort->readBytes(ins, to_read);
                    if (n != to_read) {
                        SET_PANIC_REASON();
                        m_state = PANIC;
                        return false;
                    }

                    m_data_rcvd += to_read;
                    if (m_data_rcvd >= m_req.len) {
                        m_state = RETURN_REQUEST;
                    }
                }
                break;
            }

            case RETURN_REQUEST:
                memcpy(&req_out, &m_req, HEADER_SIZE + m_req.len);
                if (m_req.len < MAX_DATA_SIZE) {
                    size_t len = MAX_DATA_SIZE - m_req.len;
                    memset(&req_out.data[m_req.len], 0, len);
                }
                m_state = IDLE;
                return true;

            case PANIC:
                return false;

            default:
                SET_PANIC_REASON();
                m_state = PANIC;
                return false;
        }

        return false;
    }
};

#include "jvs.h"

#include <string.h>

#include "platform.h"

uint8_t lm_jvs_node_id = LM_JVS_NODE_UNSET;
// lm_jvs_sum will overflow, this is intentional
uint8_t lm_jvs_sum = 0;
uint8_t lm_jvs_buf[64];
uint8_t lm_jvs_buf_ptr = 0;

uint8_t counter = 0;

typedef enum {
    lm_jvs_state_waiting = 0,
    lm_jvs_state_got_sync,
    lm_jvs_state_read_nbytes,
    lm_jvs_state_read_command,
    lm_jvs_state_overflow,
    lm_jvs_state_read_body,
    lm_jvs_state_sum,
} lm_jvs_state_t;
lm_jvs_state_t lm_jvs_state;

uint8_t lm_jvs_read() {
    while (!lm_platform_serial_available())
        ;
    uint8_t data = lm_platform_serial_read_one();
    if (data == LM_JVS_SYNC) {
        lm_jvs_state = lm_jvs_state_got_sync;
        return data;
    }

    if (data == LM_JVS_MARK) data = lm_platform_serial_read_one() + 1;
    lm_jvs_sum += data;
    return data;
}

void lm_jvs_write_hw(uint8_t data) {
    if (data == LM_JVS_MARK || data == LM_JVS_SYNC) {
        lm_platform_serial_write_one(LM_JVS_MARK);
        data--;
    }
    lm_platform_serial_write_one(data);
}

#define lm_jvs_write(data)                   \
    do {                                     \
        lm_jvs_buf[lm_jvs_buf_ptr++] = data; \
        lm_jvs_sum += data;                  \
    } while (0)

uint8_t note;
void lm_jvs_tick(void) {
    uint8_t dest_node;
    uint8_t nbytes;
    uint8_t command;
    uint8_t read_ptr;
    uint8_t set_low_sense = 0;

    lm_platform_serial_select(lm_select_rx);

    lm_jvs_state = lm_jvs_state_waiting;
    lm_jvs_sum = 0;

    // On paper using an FSM here may seem contrived. As per spec, we must
    // treat any E0 byte as the start of a new packet, and discard existing
    // processing we had done. The cleanest way to do this is to create a
    // 1-to-1 correlation between FSM ticks, and bytes read, such that any E0
    // byte will return us to the lm_jvs_state_got_sync state.

    while (1) {
        // digitalWrite(13, lm_jvs_state == 5);
        /*
            state 0: as expected
            state 1: sometimes holds for a little longer than expected
            state 2: as expected
            state 3: some long holds observed. only after a failure though
            state 4: as expected; never lights
            state 5: !! likely culprit
            state 6: slow, but as expected
        */

        switch (lm_jvs_state) {
            case lm_jvs_state_waiting:
                if (!lm_platform_serial_available()) return;
                if (lm_platform_serial_read_one() != LM_JVS_SYNC) return;
                lm_jvs_state = lm_jvs_state_got_sync;
                break;

            case lm_jvs_state_got_sync:
                lm_jvs_state = lm_jvs_state_read_nbytes;
                dest_node = lm_jvs_read();
                if (lm_jvs_state == lm_jvs_state_got_sync) break;

                if (dest_node == LM_JVS_NODE_MASTER) return;
                if (dest_node == LM_JVS_NODE_BROADCAST) break;
                if (dest_node != lm_jvs_node_id) return;

                break;

            case lm_jvs_state_read_nbytes:
                nbytes = lm_jvs_read();
                if (lm_jvs_state == lm_jvs_state_got_sync) break;

                if (nbytes - 1 > sizeof lm_jvs_buf) {
                    if (dest_node == LM_JVS_NODE_BROADCAST)
                        return;
                    else
                        lm_jvs_state = lm_jvs_state_overflow;
                    break;
                }

                lm_jvs_state = lm_jvs_state_read_command;
                break;

            case lm_jvs_state_read_command:
                command = lm_jvs_read();
                if (lm_jvs_state == lm_jvs_state_got_sync) break;

                lm_jvs_state = lm_jvs_state_read_body;
                read_ptr = 0;
                break;

            case lm_jvs_state_overflow:
                lm_platform_serial_select(lm_select_tx);

                lm_platform_serial_write_one(LM_JVS_SYNC);
                lm_platform_serial_write_one(LM_JVS_NODE_MASTER);
                // None of these are E0 or D0 so we can save a few cycles buy
                // not using lm_jvs_write_hw
                lm_platform_serial_write_one(2);
                lm_platform_serial_write_one(LM_JVS_STATUS_OVERFLOW);
                lm_platform_serial_write_one(LM_JVS_NODE_MASTER + 2 +
                                             LM_JVS_STATUS_OVERFLOW);

                lm_platform_serial_select(lm_select_rx);
                return;

            case lm_jvs_state_read_body:
                if (read_ptr + 1 < nbytes - 1)  // nbytes includes sum
                    lm_jvs_buf[read_ptr++] = lm_jvs_read();
                else
                    lm_jvs_state = lm_jvs_state_sum;
                break;

            case lm_jvs_state_sum: {
                uint8_t sum = lm_jvs_sum;
                uint8_t rsum = lm_jvs_read();
                if (lm_jvs_state == lm_jvs_state_got_sync) break;

                if (sum != rsum) {
                    lm_platform_serial_select(lm_select_tx);

                    // Corrupted packet!
                    lm_platform_serial_write_one(LM_JVS_SYNC);
                    lm_platform_serial_write_one(LM_JVS_NODE_MASTER);
                    lm_platform_serial_write_one(2);
                    lm_platform_serial_write_one(LM_JVS_STATUS_SUM);
                    lm_jvs_sum = LM_JVS_NODE_MASTER + 2 + LM_JVS_STATUS_SUM;
                    lm_platform_serial_write_one(lm_jvs_sum);

                    lm_platform_serial_select(lm_select_rx);
                    return;
                }
                goto lm_jvs_process_cmd;
            } break;
        }
    }
lm_jvs_process_cmd:;
    // We've finished reading the entire packet, so don't have any chances to
    // see another E0. We can return to normal flat programming (yay!).

    uint8_t status = LM_JVS_STATUS_OK;
    lm_jvs_buf_ptr = lm_jvs_sum = 0;

    switch (command) {
        // Transport configuration commands
        case LM_JVS_CMD_RESET:
            if (lm_jvs_buf[0] == LM_JVS_CMD_RESET_CHECK) {
                lm_jvs_node_id = LM_JVS_NODE_UNSET;
                lm_platform_sense_set(lm_sense_high);
                lm_platform_reset();
            }
            return;
        case LM_JVS_CMD_ASSIGN_ADDR:
            // Not for us!
            if (lm_platform_sense_get() == lm_sense_high) return;
            // We already got our address
            if (lm_jvs_node_id != LM_JVS_NODE_UNSET) return;

            lm_jvs_node_id = lm_jvs_buf[0];
            set_low_sense = 1;

            lm_jvs_write(LM_JVS_REPORT_OK);
            break;

        // Configuration queries
        case LM_JVS_CMD_READ_ID: {
            uint8_t len = strlen(lm_platform_name);

            lm_platform_serial_select(lm_select_tx);

            // Rather than using lm_jvs_write, which writes to a buffer, we
            // directly write out our output. This means we can shrink the
            // buffer size substantially, as this is the only significantly
            // large packet we support.
            lm_platform_serial_write_one(LM_JVS_SYNC);
            lm_platform_serial_write_one(LM_JVS_NODE_MASTER);
            lm_jvs_write_hw(len + 4);
            lm_jvs_write_hw(status);
            lm_jvs_write_hw(LM_JVS_REPORT_OK);
            lm_jvs_sum =
                LM_JVS_NODE_MASTER + len + 4 + status + LM_JVS_REPORT_OK;

            for (int i = 0; i <= len; i++) {
                lm_jvs_write_hw(lm_platform_name[i]);
                lm_jvs_sum += lm_platform_name[i];
            }
            lm_jvs_write_hw(lm_jvs_sum);

            lm_platform_serial_select(lm_select_rx);
            return;
        } break;
        case LM_JVS_CMD_GET_CMD_VERSION:
            lm_jvs_write(LM_JVS_REPORT_OK);
            lm_jvs_write(LM_JVS_VERSION_CMD);
            break;
        case LM_JVS_CMD_GET_JVS_VERSION:
            lm_jvs_write(LM_JVS_REPORT_OK);
            lm_jvs_write(LM_JVS_VERSION_JVS);
            break;
        case LM_JVS_CMD_GET_COMM_VERSION:
            lm_jvs_write(LM_JVS_REPORT_OK);
            lm_jvs_write(LM_JVS_VERSION_COMM);
            break;

        case LM_JVS_CMD_GET_FEATURES:
            lm_jvs_write(LM_JVS_REPORT_OK);
            lm_jvs_write(LM_JVS_FEATURE_CHANNEL);
            lm_jvs_write(0x01);  // 1 channel
            lm_jvs_write(LM_JVS_FEATURE_PAD);
            lm_jvs_write(LM_JVS_FEATURE_PAD);
            lm_jvs_write(LM_JVS_FEATURE_EOF);
            break;

        // Main graphene commands
        case LM_JVS_CMD_GRAPHENE_PING:
            // Used to measure bus speed
            lm_jvs_write(LM_JVS_REPORT_OK);
            break;
        case LM_JVS_CMD_GRAPHENE_GET_SENSE:
            lm_jvs_write(LM_JVS_REPORT_OK);
            lm_jvs_write(lm_platform_sense_get() == lm_sense_high ? 1 : 0);
            break;
        case LM_JVS_CMD_GRAPHENE_INCR: {
            counter++;
            return;
        }
        case LM_JVS_CMD_GRAPHENE_CNTR: {
            lm_jvs_write(LM_JVS_REPORT_OK);
            lm_jvs_write(counter);
            counter = 0;
            break;
        }
        case LM_JVS_CMD_GRAPHENE_DOWN:
        case LM_JVS_CMD_GRAPHENE_UP: {
            uint32_t time = *((uint32_t*)&(lm_jvs_buf[0]));
            uint8_t channel = lm_jvs_buf[4];
            note = lm_jvs_buf[5];
            uint8_t vel = lm_jvs_buf[6];

            // UP and DOWN have no response, to avoid clogging the bus!
            return;
        }

        // Unknown command
        default:
            // Don't respond to broadcast packets!
            if (dest_node == LM_JVS_NODE_BROADCAST) return;
            lm_jvs_write(LM_JVS_STATUS_UKCOM);
            break;
    }

    lm_platform_serial_select(lm_select_tx);

    lm_platform_serial_write_one(LM_JVS_SYNC);
    lm_platform_serial_write_one(LM_JVS_NODE_MASTER);
    lm_jvs_write_hw(lm_jvs_buf_ptr + 2);
    lm_jvs_write_hw(status);
    for (uint8_t i = 0; i < lm_jvs_buf_ptr; i++)
        lm_jvs_write_hw(lm_jvs_buf[i]);
    lm_jvs_write_hw(LM_JVS_NODE_MASTER + lm_jvs_buf_ptr + 2 + status +
                    lm_jvs_sum);

    lm_platform_serial_select(lm_select_rx);

    if (set_low_sense) lm_platform_sense_set(lm_sense_low);
}

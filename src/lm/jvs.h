#include <stdint.h>

void lm_jvs_tick(void);

#define LM_JVS_SYNC 0xE0
#define LM_JVS_MARK 0xD0

#define LM_JVS_NODE_MASTER 0x00
#define LM_JVS_NODE_BROADCAST 0xFF
#define LM_JVS_NODE_UNSET LM_JVS_NODE_BROADCAST

#define LM_JVS_VERSION_CMD 0x13   // 1.3
#define LM_JVS_VERSION_JVS 0x20   // 2.0
#define LM_JVS_VERSION_COMM 0x10  // 1.0

#define LM_JVS_STATUS_OK 0x01
#define LM_JVS_STATUS_UKCOM 0x02
#define LM_JVS_STATUS_SUM 0x03
#define LM_JVS_STATUS_OVERFLOW 0x04
#define LM_JVS_STATUS_UNKNOWN 0xFF

#define LM_JVS_REPORT_OK 0x01
#define LM_JVS_REPORT_PARAM_NODATA 0x02
#define LM_JVS_REPORT_PARAM_INVALID 0x03
#define LM_JVS_REPORT_BUSY 0x04

#define LM_JVS_FEATURE_PAD 0x00
#define LM_JVS_FEATURE_EOF 0x00
// We're disregarding the per-spec feature list, because it's heavily arcade-centric
#define LM_JVS_FEATURE_NOTE_CHANNEL 0x01
#define LM_JVS_FEATURE_LIGHT_CHANNEL 0x02
#define LM_JVS_FEATURE_CONTROL_CHANNEL 0x03
#define LM_JVS_FEATURE_OFFSET 0x04

#define LM_JVS_CMD_RESET_CHECK 0xD9

// Mandatory JVS commands
#define LM_JVS_CMD_RESET 0xF0
#define LM_JVS_CMD_ASSIGN_ADDR 0xF1

#define LM_JVS_CMD_READ_ID 0x10
#define LM_JVS_CMD_GET_CMD_VERSION 0x11
#define LM_JVS_CMD_GET_JVS_VERSION 0x12
#define LM_JVS_CMD_GET_COMM_VERSION 0x13
#define LM_JVS_CMD_GET_FEATURES 0x14

#define LM_JVS_CMD_REQUEST_RETRANSMIT 0x2F

// Graphene control and debug commands
#define LM_JVS_CMD_GRAPHENE_PING 0x60
#define LM_JVS_CMD_GRAPHENE_GET_SENSE 0x61
#define LM_JVS_CMD_GRAPHENE_INCR 0x62
#define LM_JVS_CMD_GRAPHENE_CNTR 0x63
// Graphene main commands
#define LM_JVS_CMD_GRAPHENE_DOWN 0x70
#define LM_JVS_CMD_GRAPHENE_UP 0x71
#define LM_JVS_CMD_GRAPHENE_LIGHT 0x72
#define LM_JVS_CMD_GRAPHENE_CONTROL 0x73

extern uint8_t lm_jvs_sum;
extern uint8_t lm_jvs_ibuf[64];
extern uint8_t lm_jvs_obuf[64];
extern uint8_t lm_jvs_obuf_ptr;
#define lm_jvs_write(data)                   \
    do {                                     \
        lm_jvs_obuf[lm_jvs_obuf_ptr++] = data; \
        lm_jvs_sum += data;                  \
    } while (0)

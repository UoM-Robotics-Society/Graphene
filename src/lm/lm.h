#define LM_SERIAL_RATE 115200

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>

void lm_setup();
void lm_tick();

extern uint8_t lm_jvs_node_id;

#ifdef __cplusplus
}

#endif

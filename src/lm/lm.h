#define LM_SERIAL_RATE 115200

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include "callbacks.h"

void lm_setup(void);
void lm_tick(void);

void lm_feature_note_channel(uint8_t channel, uint8_t midi_min, uint8_t midi_max);
void lm_feature_light_channel(uint8_t channel, uint8_t light_min, uint8_t light_max);
void lm_feature_control_channel(uint8_t channel, uint8_t control_min, uint8_t control_max);
void lm_feature_offset(int16_t offset);

extern uint8_t lm_jvs_node_id;

#ifdef __cplusplus
}
#endif

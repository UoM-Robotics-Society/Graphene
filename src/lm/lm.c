#include "lm.h"

#include "jvs.h"
#include "platform.h"

void lm_setup() { lm_platform_setup(); }

void lm_tick() { lm_jvs_tick(); }

void lm_feature_note_channel(uint8_t channel, uint8_t midi_min, uint8_t midi_max) {
    lm_jvs_write(LM_JVS_FEATURE_NOTE_CHANNEL);
    lm_jvs_write(channel);
    lm_jvs_write(midi_min);
    lm_jvs_write(midi_max);
}
void lm_feature_light_channel(uint8_t channel, uint8_t light_min, uint8_t light_max) {
    lm_jvs_write(LM_JVS_FEATURE_LIGHT_CHANNEL);
    lm_jvs_write(channel);
    lm_jvs_write(light_min);
    lm_jvs_write(light_max);
}
void lm_feature_control_channel(uint8_t channel, uint8_t control_min, uint8_t control_max) {
    lm_jvs_write(LM_JVS_FEATURE_CONTROL_CHANNEL);
    lm_jvs_write(channel);
    lm_jvs_write(control_min);
    lm_jvs_write(control_max);
}
void lm_feature_offset(int16_t offset) {
    lm_jvs_write(LM_JVS_FEATURE_OFFSET);
    lm_jvs_write(offset >> 8);
    lm_jvs_write(offset & 0xff);
    lm_jvs_write(LM_JVS_FEATURE_PAD);
}

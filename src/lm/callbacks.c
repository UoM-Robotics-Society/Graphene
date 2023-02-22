#include "callbacks.h"

void __attribute__((weak))
lm_do_note_up(uint32_t time, uint8_t channel, uint8_t note, uint8_t vel){};
void __attribute__((weak))
lm_do_note_down(uint32_t time, uint8_t channel, uint8_t note, uint8_t vel){};

void __attribute__((weak))
lm_do_light(uint32_t time, uint8_t channel, uint8_t light, uint8_t value){};

bool __attribute__((weak))
lm_do_control(uint32_t time, uint8_t channel, uint8_t control, uint8_t value) {
    return false;
};

#include "platform.h"

#include <Arduino.h>
#include <avr/wdt.h>

#include "lm.h"

constexpr uint8_t SENSE_IN = 9;
constexpr uint8_t SENSE_OUT = 10;
constexpr uint8_t SERIAL_SELECT = 11;

void lm_platform_setup() {
    pinMode(SENSE_IN, INPUT);
    pinMode(SENSE_OUT, OUTPUT);
    pinMode(SERIAL_SELECT, OUTPUT);
    Serial1.begin(LM_SERIAL_RATE);
}

int lm_platform_serial_available(void) { return Serial1.available(); }
uint8_t lm_platform_serial_read_one(void) { return Serial1.read(); }
void lm_platform_serial_write_one(uint8_t data) {
    Serial1.write(data);
    Serial1.flush();
}

void lm_platform_serial_select(lm_select_t status) { digitalWrite(SERIAL_SELECT, status); }
lm_sense_t lm_platform_sense_get(void) {
    return digitalRead(SENSE_IN) ? lm_sense_high : lm_sense_low;
}
void lm_platform_sense_set(lm_sense_t state) {
    digitalWrite(SENSE_OUT, state == lm_sense_high ? HIGH : LOW);
}

extern uint32_t num_playing;
void lm_platform_reset(void) {
    // Rebooting on a teensy isn't very clean, nor fast, so we're going to opt to not do anything
    // when a reboot is requested!

    num_playing = 0;
}

void lm_platform_features() {
    lm_feature_note_channel(0, 0, 255);

}
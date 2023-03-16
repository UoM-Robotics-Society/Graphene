#include "platform.h"

#include <Arduino.h>
#include <avr/wdt.h>

#include "lm.h"

constexpr uint8_t SENSE_IN = 10;
constexpr uint8_t SENSE_OUT = 11;
constexpr uint8_t SERIAL_SELECT = 12;

void lm_platform_setup() {
    pinMode(SENSE_IN, INPUT);
    pinMode(SENSE_OUT, OUTPUT);
    pinMode(SERIAL_SELECT, OUTPUT);
    Serial.begin(LM_SERIAL_RATE);
}

int lm_platform_serial_available(void) { return Serial.available(); }
uint8_t lm_platform_serial_read_one(void) { return Serial.read(); }
void lm_platform_serial_write_one(uint8_t data) {
    Serial.write(data);
    Serial.flush();
}

void lm_platform_serial_select(lm_select_t status) { digitalWrite(SERIAL_SELECT, status); }
lm_sense_t lm_platform_sense_get(void) {
    return digitalRead(SENSE_IN) ? lm_sense_high : lm_sense_low;
}
void lm_platform_sense_set(lm_sense_t state) {
    digitalWrite(SENSE_OUT, state == lm_sense_high ? HIGH : LOW);
}

void (*reset)(void) = 0;
void lm_platform_reset(void) { reset(); }

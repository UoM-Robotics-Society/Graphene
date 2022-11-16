#include <Arduino.h>

#include "lm/lm.h"

#define STATUS_LED 13

void setup() {
    lm_setup();
    pinMode(STATUS_LED, OUTPUT);
    pinMode(6, OUTPUT);
    pinMode(10, OUTPUT);
    pinMode(11, OUTPUT);
    pinMode(12, OUTPUT);
    digitalWrite(13, LOW);
}

#define LED_GREEN 10
#define LED_BLUE 11
#define LED_RED 12

uint8_t note = 0;
extern uint8_t lm_jvs_state;
void loop() {
    lm_tick();
    // digitalWrite(13, 0);

    // digitalWrite(10, HIGH);
    // digitalWrite(11, LOW);
    // digitalWrite(12, HIGH);

    // 12 = red

    bool red, green, blue;
    red = green = blue = false;

    if (lm_jvs_state == 0)
        // red = true;
        ;
    else if (lm_jvs_state == 1)
        red = true;
    else
        blue = true;

    digitalWrite(LED_RED, !red);
    digitalWrite(LED_GREEN, !green);
    digitalWrite(LED_BLUE, !blue);

    if (note == 0) {
        digitalWrite(6, LOW);
    } else {
        digitalWrite(6, HIGH);
        float period = (1000000 / ((float)note * 4 * 2));
        delayMicroseconds(period);
        digitalWrite(6, LOW);
        delayMicroseconds(period);
    }

    digitalWrite(STATUS_LED, lm_jvs_node_id == 0xff ? LOW : HIGH);
}

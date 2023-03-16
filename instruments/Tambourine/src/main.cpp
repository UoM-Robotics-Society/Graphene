#include <Arduino.h>
#include <Servo.h>

#include "lm.h"

#define SERVO_PIN 3

#define SERVO_HOME 115
#define SERVO_HIT 130

#define SERVO_HIT_TIME 150  // ms

Servo myservo;

void setup() {
    lm_setup();
    myservo.attach(SERVO_PIN);
}

bool swing = false;
unsigned long start = 0;

void lm_do_note_up(uint32_t time, uint8_t channel, uint8_t note, uint8_t vel){};
void lm_do_note_down(uint32_t time, uint8_t channel, uint8_t note, uint8_t vel) {
    swing = true;
    start = millis();
};

void loop() {
    lm_tick();

    if (swing) {
        myservo.write(SERVO_HIT);
        if (millis() - start > SERVO_HIT_TIME) {
            swing = false;
        }
    } else {
        myservo.write(SERVO_HOME);
    }
}


void lm_platform_features() {
    lm_feature_note_channel(0, 64, 64);
    lm_feature_offset(0);
}
const char *lm_platform_name = "Tambourine;Ver1.00;";

#include <Arduino.h>

#include "g6.h"
#include "lm.h"

extern uint8_t lm_g6_node_id;

#define NUM_STEPPERS 4
constexpr struct {
    uint8_t dir_pin;
    uint8_t step_pin;
} stepper_config[NUM_STEPPERS] = {
    { .dir_pin = 8, .step_pin = 30 },
    { .dir_pin = 6, .step_pin = 3 },
    { .dir_pin = 4, .step_pin = 2 },
    { .dir_pin = 7, .step_pin = 5 },
};

struct {
    uint8_t note;
    float freq;
    uint32_t rate;
    uint32_t nextToggle;
    bool state;

} playing[NUM_STEPPERS];
uint32_t num_playing = 0;

void setup() {
    pinMode(LED_BUILTIN, OUTPUT);
    digitalWrite(LED_BUILTIN, HIGH);

    Serial.begin(9600);

    for (auto i = 0; i < NUM_STEPPERS; i++) {
        pinMode(stepper_config[i].step_pin, OUTPUT);
        pinMode(stepper_config[i].dir_pin, OUTPUT);

        digitalWrite(stepper_config[i].dir_pin, LOW);
    }

    lm_setup();
}

void lm_do_note_up(uint32_t time, uint8_t channel, uint8_t note, uint8_t vel) {
    if (channel != 0) return;
    for (auto i = 0; i < num_playing;) {
        if (playing[i].note != note) {
            i++;
            continue;
        }

        // Shift all the others forward one
        for (auto j = i; j < NUM_STEPPERS - 1; j++) {
            playing[j].note = playing[j + 1].note;
            playing[j].freq = playing[j + 1].freq;
        }
        num_playing--;
    }
}
void lm_do_note_down(uint32_t time, uint8_t channel, uint8_t note, uint8_t vel) {
    if (channel != 0) return;

    if (num_playing >= NUM_STEPPERS) return;
    float freq = 440.0 * pow(2.0, (((float)note - 69.0) / 12.0));
    playing[num_playing].note = note;
    playing[num_playing].rate = 1000'000 / freq;
    playing[num_playing].nextToggle = 0;
    playing[num_playing++].freq = freq;
}

void loop() {
    lm_tick();

    Serial.println(num_playing);

    if (lm_g6_node_id == LM_G6_NODE_UNSET) {
        // Blink as a warning when unaddressed
        digitalWrite(LED_BUILTIN, (millis() % 250 >= 200) ? HIGH : LOW);
    } else {
        // HIGH by default so we always either have an LED lit or noise being
        // made (ie signs of power).
        digitalWrite(LED_BUILTIN, num_playing > 0 ? LOW : HIGH);
    }

    uint32_t now = micros();

    for (auto i = 0; i < NUM_STEPPERS; i++) {
        if (i < num_playing) {
            if (now > playing[i].nextToggle) {
                playing[i].state = !playing[i].state;
                digitalWrite(stepper_config[i].step_pin, playing[i].state);

                playing[i].nextToggle = now + playing[i].rate;
            }
        }
    }
}

const char *lm_platform_name = "Musical Steppers;Ver2.00;";

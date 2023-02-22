#include <Arduino.h>
#include <SPI.h>

#include "lm/lm.h"

constexpr uint8_t SR_LATCH_PIN = 53;  // latch shift register
constexpr uint8_t SR_RESET_PIN = 41;  // reset shift register

// Microseconds
constexpr int VELOCITY_MIN = 900;
constexpr int VELOCITY_MAX = 1300;

// Voltage set to 6.5V use Time_2 between 1000 - 2000 for vol 0-100
constexpr int SOLENOID_ON_TIME = 1000;   // Pulse width in uSec Fixed
constexpr int SOLENOID_OFF_TIME = 1000;  // Pulse width in uSec Fixed

#define _len(x) (sizeof(x) / sizeof(x)[0])

constexpr int MIDI_MIN = 79;
const uint8_t MIDI_TO_SR[] = {
    29,  // G0 (midi 79 = MIDI_LOWEST)
    0,   // G0#
    28,  // A1
    1,   // A1#
    27,  // B1
    26,  // C1
    2,   // C1#
    25,  // D1
    3,   // D1#
    24,  // E1
    23,  // F1
    4,   // F1#
    22,  // G1
    5,   // G1#
    21,  // A2
    6,   // A2#
    20,  // B2
    19,  // C2
    7,   // C2#
    18,  // D2
    8,   // D2#
    17,  // E2
    16,  // F2
    9,   // F2#
    15,  // G2
    10,  // G2#
    14,  // A3
    11,  // A3#
    13,  // B3
    12,  // C3 (midi 108)
};
constexpr uint8_t SR_CHAIN_SIZE = _len(MIDI_TO_SR);
const int SOLENOID_CALIBRATION[SR_CHAIN_SIZE] = {
    300, 0,    220, -120, 300, 220,  -100, 250, -100, 200,
    200, -150, 250, -50,  350, 50,   400,  300, 0,    300,
    -50, 270,  420, -50,  350, -220, 250,  50,  0,    0,
};
constexpr uint8_t MIDI_MAX = MIDI_MIN + SR_CHAIN_SIZE - 1;

constexpr byte REG_SOLENOID_ON = 0b00000010;
constexpr byte MASK_SOLENOID_OFF = ~REG_SOLENOID_ON;
constexpr byte REG_LED_ON = 0b00000100;
constexpr byte MASK_LED_OFF = ~REG_LED_ON;
constexpr byte REG_NONE = 0b00000000;
byte sr_data[SR_CHAIN_SIZE];
int solenoid_time;
bool shift_dirty = false;

/* Wipe sr_data */
inline void sr_clear() { memset(sr_data, REG_NONE, sizeof sr_data); }
/* Wipe all note data leaving LED data intact */
inline void sr_clear_notes() {
    for (unsigned int i = 0; i < _len(sr_data); i++)
        sr_data[i] &= MASK_SOLENOID_OFF;
}
/* Wipe all LED data leaving note data intact */
inline void sr_clear_leds() {
    for (unsigned int i = 0; i < _len(sr_data); i++)
        sr_data[i] &= MASK_LED_OFF;
}

/* Reset all shift registers */
inline void sr_reset() {
    digitalWrite(SR_RESET_PIN, LOW);
    delayMicroseconds(2);
    // Latch in the nothingness
    digitalWrite(SR_LATCH_PIN, HIGH);
    delayMicroseconds(2);
    digitalWrite(SR_LATCH_PIN, LOW);
}
/* Latch data into the shift registers */
inline void sr_shift_data() {
    digitalWrite(SR_RESET_PIN, HIGH);
    digitalWrite(SR_LATCH_PIN, LOW);
    for (unsigned int i = 0; i < _len(sr_data); i++) SPI.transfer(sr_data[i]);
    // Latch in the new data
    digitalWrite(SR_LATCH_PIN, HIGH);
    delayMicroseconds(2);
    digitalWrite(SR_LATCH_PIN, LOW);
}

/** Play the notes that have been loaded into sr_data
 *
 * Sends two timed pulses to all applicable solenoids. */
inline void play_notes() {
    // solenoid_time == 0 implies no note data to process, so just flush the
    // buffer
    if (solenoid_time == 0) {
        sr_shift_data();
        return;
    }

    // First Pulse
    sr_shift_data();
    delayMicroseconds(SOLENOID_ON_TIME);
    sr_reset();
    delayMicroseconds(SOLENOID_OFF_TIME);

    // Second Pulse
    sr_shift_data();
    delayMicroseconds(solenoid_time);
    sr_reset();
    sr_clear_notes();

    // Restore any LED data that was in there
    sr_shift_data();
}

/** Load a single note's calibration data into sr_data
 * @param note The MIDI note to play. This must be pre-validated!
 * @return A calibration adjustment to apply to the second solenoid pulse to
 * normalise volume
 */
inline int load_note(uint8_t note) {
    sr_data[MIDI_TO_SR[note - MIDI_MIN]] |= REG_SOLENOID_ON;
    return SOLENOID_CALIBRATION[note - MIDI_MIN];
}

void setup() {
    pinMode(SR_LATCH_PIN, OUTPUT);
    pinMode(SR_RESET_PIN, OUTPUT);
    pinMode(LED_BUILTIN, OUTPUT);
    digitalWrite(SR_LATCH_PIN, LOW);
    digitalWrite(SR_RESET_PIN, LOW);

    SPI.begin();
    SPI.beginTransaction(
        SPISettings(2000000, MSBFIRST, SPI_MODE0));  // 100kHz Shift Clock

    sr_clear();
    sr_reset();

    digitalWrite(13, 0);
    lm_setup();
}

void lm_do_note_up(uint32_t time, uint8_t channel, uint8_t note,
                   uint8_t vel){};
void lm_do_note_down(uint32_t time, uint8_t channel, uint8_t note,
                     uint8_t vel) {
    if (channel != 0) return;
    if (note < MIDI_MIN || note > MIDI_MAX) return;

    solenoid_time =
        ((VELOCITY_MAX - VELOCITY_MIN) / 127 * vel) + VELOCITY_MIN;
    solenoid_time += load_note(note);

    shift_dirty = true;
};
void lm_do_light(uint32_t time, uint8_t channel, uint8_t light,
                 uint8_t value) {
    if (channel != 0) return;
    if (light < MIDI_MIN || light > MIDI_MAX) return;

    if (value == 255)
        sr_data[MIDI_TO_SR[light - MIDI_MIN]] = REG_LED_ON;
    else
        sr_data[MIDI_TO_SR[light - MIDI_MIN]] &= MASK_LED_OFF;

    shift_dirty = true;
};
bool lm_do_control(uint32_t time, uint8_t channel, uint8_t control,
                   uint8_t value) {
    if (channel != 0) return false;

    switch (control) {
        case 0:
            sr_reset();
            return true;
        case 1:
            sr_clear_leds();
            shift_dirty = true;
            return true;
        default:
            return false;
    }
};

void loop() {
    solenoid_time = 0;

    lm_tick();
    if (shift_dirty) {
        shift_dirty = false;
        play_notes();
    }
}

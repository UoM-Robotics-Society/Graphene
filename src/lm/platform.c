#include "platform.h"

#include "lm.h"

// These are all safe default bodies for these functions, however instruments should overwrite
// these implementations

void __attribute__((weak)) lm_platform_setup(){};
int __attribute__((weak)) lm_platform_serial_available(void) { return 0; };
uint8_t __attribute__((weak)) lm_platform_serial_read_one(void) { return 0xFF; };
void __attribute__((weak)) lm_platform_serial_write_one(uint8_t data){};
void __attribute__((weak)) lm_platform_reset(void){};

lm_sense_t __attribute__((weak)) lm_platform_sense_get(void) { return lm_sense_high; };
void __attribute__((weak)) lm_platform_sense_set(lm_sense_t state){};
void __attribute__((weak)) lm_platform_serial_select(lm_select_t status);

void __attribute__((weak)) lm_platform_features(void){};

const char* __attribute__((weak)) lm_platform_name = "libmusician;Ver1.00;";

#include "lm.h"

#include "jvs.h"
#include "platform.h"

void lm_setup() {
    lm_platform_setup();
}

void lm_tick() {
    lm_jvs_tick();
}

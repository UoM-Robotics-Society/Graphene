#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    lm_sense_low = 0,
    lm_sense_high = 1,
} lm_sense_t;
typedef enum {
    lm_select_rx = 0,
    lm_select_tx = 1,
} lm_select_t;

void lm_platform_setup();

int lm_platform_serial_available(void);
uint8_t lm_platform_serial_read_one(void);
void lm_platform_serial_write_one(uint8_t data);

lm_sense_t lm_platform_sense_get(void);
void lm_platform_sense_set(lm_sense_t state);
void lm_platform_serial_select(lm_select_t status);
void lm_platform_reset(void);

void lm_platform_features(void);

/*
 * Return the identification name for this robot.
 * Contains three fields, seperated by semicolons:
 *   robot name;version;additional description
 *
 * For example:
 *   graphene;Ver1.00;The main conductor
 *
 * This must be 99 characters or fewer (100 including null!)
 */
extern const char* lm_platform_name;

#ifdef __cplusplus
}
#endif

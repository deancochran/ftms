#ifndef FTMS_FTMS_H
#define FTMS_FTMS_H

#include <limits.h>
#include <stddef.h>
#include <stdint.h>

#if CHAR_BIT != 8
#error "FTMS requires 8-bit bytes"
#endif

#ifdef __cplusplus
extern "C" {
#endif

typedef enum ftms_result {
  FTMS_OK = 0,
  FTMS_ERROR_NULL = 1,
  FTMS_ERROR_LENGTH = 2,
  FTMS_ERROR_KIND = 3,
  FTMS_ERROR_RANGE = 4
} ftms_result;

/* These masks name the defined FTMS 1.0 bits; raw words retain reserved bits. */
#define FTMS_MACHINE_FEATURE_AVERAGE_SPEED (UINT32_C(1) << 0)
#define FTMS_MACHINE_FEATURE_CADENCE (UINT32_C(1) << 1)
#define FTMS_MACHINE_FEATURE_TOTAL_DISTANCE (UINT32_C(1) << 2)
#define FTMS_MACHINE_FEATURE_INCLINATION (UINT32_C(1) << 3)
#define FTMS_MACHINE_FEATURE_ELEVATION_GAIN (UINT32_C(1) << 4)
#define FTMS_MACHINE_FEATURE_PACE (UINT32_C(1) << 5)
#define FTMS_MACHINE_FEATURE_STEP_COUNT (UINT32_C(1) << 6)
#define FTMS_MACHINE_FEATURE_RESISTANCE_LEVEL (UINT32_C(1) << 7)
#define FTMS_MACHINE_FEATURE_STRIDE_COUNT (UINT32_C(1) << 8)
#define FTMS_MACHINE_FEATURE_EXPENDED_ENERGY (UINT32_C(1) << 9)
#define FTMS_MACHINE_FEATURE_HEART_RATE (UINT32_C(1) << 10)
#define FTMS_MACHINE_FEATURE_METABOLIC_EQUIVALENT (UINT32_C(1) << 11)
#define FTMS_MACHINE_FEATURE_ELAPSED_TIME (UINT32_C(1) << 12)
#define FTMS_MACHINE_FEATURE_REMAINING_TIME (UINT32_C(1) << 13)
#define FTMS_MACHINE_FEATURE_POWER (UINT32_C(1) << 14)
#define FTMS_MACHINE_FEATURE_FORCE_ON_BELT (UINT32_C(1) << 15)
#define FTMS_MACHINE_FEATURE_USER_DATA_RETENTION (UINT32_C(1) << 16)
#define FTMS_TARGET_FEATURE_SPEED (UINT32_C(1) << 0)
#define FTMS_TARGET_FEATURE_INCLINATION (UINT32_C(1) << 1)
#define FTMS_TARGET_FEATURE_RESISTANCE_LEVEL (UINT32_C(1) << 2)
#define FTMS_TARGET_FEATURE_POWER (UINT32_C(1) << 3)
#define FTMS_TARGET_FEATURE_HEART_RATE (UINT32_C(1) << 4)
#define FTMS_TARGET_FEATURE_EXPENDED_ENERGY (UINT32_C(1) << 5)
#define FTMS_TARGET_FEATURE_STEP_NUMBER (UINT32_C(1) << 6)
#define FTMS_TARGET_FEATURE_STRIDE_NUMBER (UINT32_C(1) << 7)
#define FTMS_TARGET_FEATURE_DISTANCE (UINT32_C(1) << 8)
#define FTMS_TARGET_FEATURE_TRAINING_TIME (UINT32_C(1) << 9)
#define FTMS_TARGET_FEATURE_TIME_TWO_HR_ZONES (UINT32_C(1) << 10)
#define FTMS_TARGET_FEATURE_TIME_THREE_HR_ZONES (UINT32_C(1) << 11)
#define FTMS_TARGET_FEATURE_TIME_FIVE_HR_ZONES (UINT32_C(1) << 12)
#define FTMS_TARGET_FEATURE_INDOOR_BIKE_SIMULATION (UINT32_C(1) << 13)
#define FTMS_TARGET_FEATURE_WHEEL_CIRCUMFERENCE (UINT32_C(1) << 14)
#define FTMS_TARGET_FEATURE_SPIN_DOWN (UINT32_C(1) << 15)
#define FTMS_TARGET_FEATURE_CADENCE (UINT32_C(1) << 16)

typedef struct ftms_features {
  uint32_t machine;
  uint32_t target;
} ftms_features;

typedef enum ftms_range_kind {
  FTMS_RANGE_SPEED,
  FTMS_RANGE_INCLINATION,
  FTMS_RANGE_RESISTANCE_LEVEL,
  FTMS_RANGE_HEART_RATE,
  FTMS_RANGE_POWER
} ftms_range_kind;

typedef enum ftms_range_unit {
  FTMS_UNIT_KILOMETRES_PER_HOUR,
  FTMS_UNIT_PERCENT,
  FTMS_UNIT_LEVEL,
  FTMS_UNIT_BEATS_PER_MINUTE,
  FTMS_UNIT_WATTS
} ftms_range_unit;
typedef struct ftms_range {
  ftms_range_kind kind;
  int32_t minimum;
  int32_t maximum;
  int32_t increment;
  uint16_t scale_divisor;
  ftms_range_unit unit;
} ftms_range;

typedef enum ftms_resistance_range_format {
  FTMS_RESISTANCE_RANGE_UINT8_WHOLE = 0,
  FTMS_RESISTANCE_RANGE_SINT16_TENTHS = 1
} ftms_resistance_range_format;
typedef struct ftms_range_format_options {
  ftms_resistance_range_format resistance_format;
} ftms_range_format_options;

typedef enum ftms_range_profile {
  FTMS_RANGE_PROFILE_UINT16_HUNDREDTHS,
  FTMS_RANGE_PROFILE_SINT16_TENTHS,
  FTMS_RANGE_PROFILE_UINT8_WHOLE,
  FTMS_RANGE_PROFILE_UINT8_BPM,
  FTMS_RANGE_PROFILE_SINT16_WATTS
} ftms_range_profile;
typedef enum ftms_range_inspection_status {
  FTMS_RANGE_INSPECTION_VALID,
  FTMS_RANGE_INSPECTION_LENGTH,
  FTMS_RANGE_INSPECTION_RANGE
} ftms_range_inspection_status;
/* For both candidate and top-level inspection, value is meaningful ONLY when
 * status == FTMS_RANGE_INSPECTION_VALID. Otherwise it is zeroed storage, not a
 * valid zero-valued range. JSON/report adapters represent that absence as null. */
typedef struct ftms_range_inspection_candidate {
  ftms_range_profile profile;
  size_t expected_size;
  ftms_range_inspection_status status;
  ftms_range value;
} ftms_range_inspection_candidate;
typedef struct ftms_range_inspection {
  ftms_range_profile selected_profile;
  size_t observed_size;
  size_t expected_size;
  ftms_range_inspection_status status;
  ftms_range value;
  size_t candidate_count;
  ftms_range_inspection_candidate candidates[2];
} ftms_range_inspection;

/* Inputs and outputs may overlap: all input bytes are read before *out is written.
 * On any error *out is untouched. The library retains no pointers and allocates
 * no memory. */
ftms_result ftms_decode_features(const uint8_t *data, size_t size,
                                 ftms_features *out);
ftms_result ftms_decode_range(ftms_range_kind kind, const uint8_t *data,
                               size_t size, ftms_range *out);
/* NULL options preserve the historical three-byte UINT8 resistance range.
 * SINT16_TENTHS explicitly selects the six-byte signed layout and divisor 10. */
ftms_result ftms_decode_range_with_format(ftms_range_kind kind, const uint8_t *data,
                                           size_t size,
                                           const ftms_range_format_options *options,
                                           ftms_range *out);
/* Inspection is diagnostic: malformed lengths/ranges return FTMS_OK and are
 * represented in `status`. It never selects an alternative from bytes. */
ftms_result ftms_inspect_range(ftms_range_kind kind, const uint8_t *data,
                               size_t size, ftms_range_inspection *out);
ftms_result ftms_inspect_range_with_format(ftms_range_kind kind, const uint8_t *data,
                                           size_t size,
                                           const ftms_range_format_options *options,
                                           ftms_range_inspection *out);

/* Encode the raw FTMS Feature characteristic (machine word then target word,
 * little-endian). Defined and reserved bits are both retained verbatim.
 *
 * `features` and `out` may overlap. `written` must not overlap either input or
 * output storage. On error neither `out` nor `*written` is modified. */
ftms_result ftms_encode_features(const ftms_features *features, uint8_t *out,
                                 size_t capacity, size_t *written);

/* Encode a Supported Range characteristic. `range` must use the exact unit and
 * scale divisor prescribed by its kind. `range` and `out` may overlap;
 * `written` must not overlap either input or output storage. On error neither
 * `out` nor `*written` is modified. */
ftms_result ftms_encode_range(const ftms_range *range, uint8_t *out,
                               size_t capacity, size_t *written);
ftms_result ftms_encode_range_with_format(const ftms_range *range,
                                           const ftms_range_format_options *options,
                                           uint8_t *out, size_t capacity,
                                           size_t *written);

#ifdef __cplusplus
} /* extern "C" */
#endif
#endif

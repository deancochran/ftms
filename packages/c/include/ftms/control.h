#ifndef FTMS_CONTROL_H
#define FTMS_CONTROL_H

#include "ftms/ftms.h"

#ifdef __cplusplus
extern "C" {
#endif

/* FTMS 1.0 Control Point wire opcodes.  Values in request payloads are raw
 * fixed-point integers; their units and divisors are recorded below. */
typedef enum ftms_control_opcode {
  FTMS_CONTROL_REQUEST_CONTROL = 0x00,
  FTMS_CONTROL_RESET = 0x01,
  FTMS_CONTROL_SET_TARGET_SPEED = 0x02,
  FTMS_CONTROL_SET_TARGET_INCLINATION = 0x03,
  FTMS_CONTROL_SET_TARGET_RESISTANCE = 0x04,
  FTMS_CONTROL_SET_TARGET_POWER = 0x05,
  FTMS_CONTROL_SET_TARGET_HEART_RATE = 0x06,
  FTMS_CONTROL_START_RESUME = 0x07,
  FTMS_CONTROL_STOP_PAUSE = 0x08,
  FTMS_CONTROL_SET_TARGETED_EXPENDED_ENERGY = 0x09,
  FTMS_CONTROL_SET_TARGETED_STEPS = 0x0a,
  FTMS_CONTROL_SET_TARGETED_STRIDES = 0x0b,
  FTMS_CONTROL_SET_TARGETED_DISTANCE = 0x0c,
  FTMS_CONTROL_SET_TARGETED_TRAINING_TIME = 0x0d,
  FTMS_CONTROL_SET_TARGETED_TIME_TWO_HR_ZONES = 0x0e,
  FTMS_CONTROL_SET_TARGETED_TIME_THREE_HR_ZONES = 0x0f,
  FTMS_CONTROL_SET_TARGETED_TIME_FIVE_HR_ZONES = 0x10,
  FTMS_CONTROL_SET_INDOOR_BIKE_SIMULATION = 0x11,
  FTMS_CONTROL_SET_WHEEL_CIRCUMFERENCE = 0x12,
  FTMS_CONTROL_SPIN_DOWN = 0x13,
  FTMS_CONTROL_SET_TARGETED_CADENCE = 0x14
} ftms_control_opcode;

typedef enum ftms_stop_pause_action {
  FTMS_STOP = 1,
  FTMS_PAUSE = 2
} ftms_stop_pause_action;
typedef enum ftms_spin_down_action {
  FTMS_SPIN_DOWN_START = 1,
  FTMS_SPIN_DOWN_IGNORE = 2
} ftms_spin_down_action;
typedef enum ftms_control_result_code {
  FTMS_CONTROL_SUCCESS = 1, FTMS_CONTROL_NOT_SUPPORTED = 2,
  FTMS_CONTROL_INVALID_PARAMETER = 3, FTMS_CONTROL_OPERATION_FAILED = 4,
  FTMS_CONTROL_NOT_PERMITTED = 5
} ftms_control_result_code;

typedef struct ftms_control_request {
  ftms_control_opcode opcode;
  union {
    uint16_t speed_centikph;             /* 0.01 km/h */
    int16_t inclination_tenth_percent;   /* 0.1 percent */
    int16_t resistance_tenth_level;      /* 0.1 level; ESR11 corrected SINT16 */
    int16_t power_watts;
    uint8_t heart_rate_bpm;
    ftms_stop_pause_action stop_pause;
    uint16_t energy_kcal, steps, strides, training_seconds;
    uint32_t distance_metres;            /* must be <= 0x00ffffff */
    uint16_t zone_seconds[5];
    struct { int16_t wind_millimetres_per_second; int16_t grade_hundredth_percent;
             uint8_t crr_ten_thousandth; uint8_t cw_hundredth_kg_per_m; } simulation;
    uint16_t wheel_circumference_tenth_mm;
    ftms_spin_down_action spin_down;
    uint16_t cadence_half_rpm;
  } value;
} ftms_control_request;

typedef enum ftms_control_response_parameter {
  FTMS_CONTROL_RESPONSE_NONE = 0,
  FTMS_CONTROL_RESPONSE_SPIN_DOWN_SPEEDS = 1
} ftms_control_response_parameter;
typedef struct ftms_control_response {
  uint8_t request_opcode; /* retained raw for forward compatibility */
  uint8_t result_code;    /* retained raw for forward compatibility */
  ftms_control_response_parameter parameter;
  uint16_t spin_down_low_centikph, spin_down_high_centikph;
  uint8_t unknown_request, unknown_result;
  /* Decode-only diagnostics. Extra bytes are not retained; callers that need
   * them must retain their input buffer. Successful Spin Down is structural:
   * it permits only no parameters or exactly two UINT16 speed parameters. */
  uint8_t unexpected_parameters;
} ftms_control_response;

/* Request encode/decode and response encode/decode are exact-length codecs.
 * Encoders first validate and capacity-check, then write, so output and *written
 * are unchanged on error. Decoders leave *out unchanged on error. Input/output
 * overlap is supported for encode and decode because decoded/encoded values are
 * staged locally. `written` must not overlap `out` or the input structure:
 * writing the size could otherwise overwrite encoded bytes or an input member.
 * FTMS_ERROR_KIND means unknown opcode or invalid enum value;
 * FTMS_ERROR_RANGE means a field or response structure is invalid. */
ftms_result ftms_encode_control_request(const ftms_control_request *request, uint8_t *out, size_t capacity, size_t *written);
ftms_result ftms_decode_control_request(const uint8_t *data, size_t size, ftms_control_request *out);
ftms_result ftms_encode_control_response(const ftms_control_response *response, uint8_t *out, size_t capacity, size_t *written);
ftms_result ftms_decode_control_response(const uint8_t *data, size_t size, ftms_control_response *out);

#ifdef __cplusplus
} /* extern "C" */
#endif
#endif

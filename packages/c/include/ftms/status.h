#ifndef FTMS_STATUS_H
#define FTMS_STATUS_H

#include "ftms/control.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Raw FTMS 1.0 values are deliberately exposed: callers apply display units. */
typedef enum ftms_machine_status_opcode {
  FTMS_MACHINE_STATUS_RESET = 0x01,
  FTMS_MACHINE_STATUS_STOPPED_OR_PAUSED = 0x02,
  FTMS_MACHINE_STATUS_SAFETY_KEY = 0x03,
  FTMS_MACHINE_STATUS_STARTED_OR_RESUMED = 0x04,
  FTMS_MACHINE_STATUS_TARGET_SPEED = 0x05,
  FTMS_MACHINE_STATUS_TARGET_INCLINATION = 0x06,
  FTMS_MACHINE_STATUS_TARGET_RESISTANCE = 0x07,
  FTMS_MACHINE_STATUS_TARGET_POWER = 0x08,
  FTMS_MACHINE_STATUS_TARGET_HEART_RATE = 0x09,
  FTMS_MACHINE_STATUS_TARGET_ENERGY = 0x0a,
  FTMS_MACHINE_STATUS_TARGET_STEPS = 0x0b,
  FTMS_MACHINE_STATUS_TARGET_STRIDES = 0x0c,
  FTMS_MACHINE_STATUS_TARGET_DISTANCE = 0x0d,
  FTMS_MACHINE_STATUS_TARGET_TRAINING_TIME = 0x0e,
  FTMS_MACHINE_STATUS_TARGET_TWO_HR_ZONES = 0x0f,
  FTMS_MACHINE_STATUS_TARGET_THREE_HR_ZONES = 0x10,
  FTMS_MACHINE_STATUS_TARGET_FIVE_HR_ZONES = 0x11,
  FTMS_MACHINE_STATUS_SIMULATION = 0x12,
  FTMS_MACHINE_STATUS_WHEEL_CIRCUMFERENCE = 0x13,
  FTMS_MACHINE_STATUS_SPIN_DOWN = 0x14,
  FTMS_MACHINE_STATUS_TARGET_CADENCE = 0x15,
  FTMS_MACHINE_STATUS_CONTROL_PERMISSION_LOST = 0xff
} ftms_machine_status_opcode;

typedef struct ftms_machine_status {
  uint8_t opcode;                 /* retained raw, including unknown opcodes */
  uint8_t action;                 /* stop/pause or spin-down raw action */
  ftms_control_request parameter; /* raw fixed-point operand for mapped opcodes */
  uint8_t parameter_present;
  uint8_t unknown_opcode;
  uint8_t reserved_value;
  uint8_t truncated;
  uint8_t trailing_bytes;
} ftms_machine_status;

typedef struct ftms_training_status {
  uint8_t flags;
  uint8_t code;
  size_t text_offset; /* caller-owned input location; no pointer is retained */
  size_t text_size;
  uint8_t text_present;
  uint8_t extended_string;
  uint8_t reserved_flags;
  uint8_t reserved_value;
  uint8_t invalid_flags;
  uint8_t invalid_utf8;
  uint8_t truncated;
  uint8_t trailing_bytes;
} ftms_training_status;

/* Decoders accept input/output overlap. Truncation, including empty input,
 * returns FTMS_OK with truncated diagnostics and available raw fields. Empty
 * Machine Status has opcode 0 and unknown_opcode set; it is not a valid status.
 * FTMS_OK means evidence decoded, not a complete/conformant payload. Argument
 * errors leave *out unchanged. Training text remains in
 * caller-owned input; text_offset/text_size identify it without retention.
 * Encoders validate before writing and leave out and *written unchanged on any
 * error. `written` must not overlap inputs or output. For training encoding,
 * text and out must not overlap. Encoders reject diagnostic-bearing/incomplete
 * values; machine parameter.opcode must match the status's operand kind.
 * Training flags/code and the explicit text input are authoritative; decoded
 * text offsets and redundant text-present flags are not encoder inputs. */
ftms_result ftms_decode_machine_status(const uint8_t *data, size_t size,
                                       ftms_machine_status *out);
ftms_result ftms_encode_machine_status(const ftms_machine_status *status,
                                       uint8_t *out, size_t capacity,
                                       size_t *written);
ftms_result ftms_decode_training_status(const uint8_t *data, size_t size,
                                        ftms_training_status *out);
ftms_result ftms_encode_training_status(const ftms_training_status *status,
                                        const uint8_t *text, size_t text_size,
                                        uint8_t *out, size_t capacity,
                                        size_t *written);

#ifdef __cplusplus
} /* extern "C" */
#endif
#endif

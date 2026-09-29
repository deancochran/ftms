#ifndef FTMS_MEASUREMENT_H
#define FTMS_MEASUREMENT_H

#include "ftms/ftms.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Raw FTMS measurement values keep their wire units. Speed and average speed
 * are 0.01 km/h (divide by 360 for m/s); cadence and stroke rate are 0.5 rpm;
 * inclination, ramp angle, and MET are 0.1; Cross Trainer stride count is
 * 0.1 stride; Treadmill elevation gains are 0.1 m. Stair Climber stride count,
 * other elevation gains, distance, pace, energy, time, resistance, power,
 * heart rate, floor/step/stroke counts are unit 1. `present` says bytes were
 * supplied; `unavailable` says those bytes carried the defined sentinel:
 * SINT16 +32767, UINT16 65535, or UINT8 255. Signed -32768 is valid. */
typedef enum ftms_measurement_kind {
  FTMS_MEASUREMENT_TREADMILL = 0, FTMS_MEASUREMENT_CROSS_TRAINER = 1,
  FTMS_MEASUREMENT_STEP_CLIMBER = 2, FTMS_MEASUREMENT_STAIR_CLIMBER = 3,
  FTMS_MEASUREMENT_ROWER = 4, FTMS_MEASUREMENT_INDOOR_BIKE = 5
} ftms_measurement_kind;

/* These caller-owned wire-format selections are compatibility overrides, not
 * device identification. NULL selects the historical FTMS layouts below. */
typedef enum ftms_measurement_resistance_format {
  FTMS_MEASUREMENT_RESISTANCE_UINT8_WHOLE = 0,
  FTMS_MEASUREMENT_RESISTANCE_SINT16_TENTHS = 1
} ftms_measurement_resistance_format;
typedef enum ftms_treadmill_pace_format {
  FTMS_TREADMILL_PACE_UINT16 = 0,
  FTMS_TREADMILL_PACE_UINT8_LEGACY = 1
} ftms_treadmill_pace_format;
typedef struct ftms_measurement_format_options {
  ftms_measurement_resistance_format resistance_format;
  ftms_treadmill_pace_format treadmill_pace_format;
} ftms_measurement_format_options;

typedef enum ftms_measurement_field {
  FTMS_M_SPEED, FTMS_M_AVERAGE_SPEED, FTMS_M_DISTANCE, FTMS_M_INCLINATION,
  FTMS_M_RAMP_ANGLE, FTMS_M_POSITIVE_ELEVATION, FTMS_M_NEGATIVE_ELEVATION,
  FTMS_M_INSTANTANEOUS_PACE, FTMS_M_AVERAGE_PACE, FTMS_M_TOTAL_ENERGY,
  FTMS_M_ENERGY_PER_HOUR, FTMS_M_ENERGY_PER_MINUTE, FTMS_M_HEART_RATE,
  FTMS_M_MET, FTMS_M_ELAPSED_TIME, FTMS_M_REMAINING_TIME, FTMS_M_FORCE_ON_BELT,
  FTMS_M_POWER, FTMS_M_STEP_RATE, FTMS_M_AVERAGE_STEP_RATE, FTMS_M_STRIDE_COUNT,
  FTMS_M_RESISTANCE, FTMS_M_AVERAGE_POWER, FTMS_M_FLOOR_COUNT, FTMS_M_STEP_COUNT,
  FTMS_M_STROKE_RATE, FTMS_M_STROKE_COUNT, FTMS_M_AVERAGE_STROKE_RATE,
  FTMS_M_CADENCE, FTMS_M_AVERAGE_CADENCE, FTMS_MEASUREMENT_FIELD_COUNT
} ftms_measurement_field;

typedef struct ftms_measurement {
  ftms_measurement_kind kind;
  uint32_t flags;                 /* received/emitted little-endian flag word */
  uint64_t present, unavailable;  /* FTMS_M_* bit sets */
  int32_t value[FTMS_MEASUREMENT_FIELD_COUNT];
  uint8_t more_data;              /* a fragment; no reassembly is performed */
  uint8_t backward;               /* Cross Trainer direction flag, not a field */
  uint8_t truncated, trailing_bytes, reserved_flags;
  size_t bytes_read;
} ftms_measurement;

/* A planned characteristic value.  `length` is the number of bytes in `value`;
 * it is never greater than FTMS_MEASUREMENT_PACKET_VALUE_MAX.  The fixed bound
 * makes the planner usable without allocation. */
#define FTMS_MEASUREMENT_PACKET_VALUE_MAX 64U
#define FTMS_MEASUREMENT_PLAN_MAX_PACKETS 32U
typedef struct ftms_measurement_packet {
  uint8_t value[FTMS_MEASUREMENT_PACKET_VALUE_MAX];
  size_t length;
} ftms_measurement_packet;

/* Decode retains raw flags and returns FTMS_OK for structurally parseable
 * prefixes, including truncated prefixes (see `truncated`; `bytes_read` is the
 * offset of the last complete field, not a partial field). Invalid kind,
 * null arguments, or input shorter than flags return an error and leave out
 * unchanged. Encode rejects RFU flags, incomplete fields and values outside
 * their wire widths/sentinel rules. Encoding is controlled solely by `flags`;
 * decode diagnostic members and `more_data`/`backward` are output metadata and
 * are ignored by encode. It stages at most 64 bytes before writing;
 * out and written are unchanged on error. Input and output may overlap through
 * staging. `written` must not overlap either input or output storage. */
ftms_result ftms_decode_measurement(ftms_measurement_kind kind, const uint8_t *data,
                                    size_t size, ftms_measurement *out);
ftms_result ftms_encode_measurement(const ftms_measurement *measurement, uint8_t *out,
                                     size_t capacity, size_t *written);
/* `_with_format` keeps `value[]` in selected raw wire integers. In particular,
 * it does not turn a signed-tenths resistance value into a legacy whole-level
 * value. The legacy public functions are exactly equivalent to NULL options. */
ftms_result ftms_decode_measurement_with_format(ftms_measurement_kind kind,
                                                const uint8_t *data, size_t size,
                                                const ftms_measurement_format_options *options,
                                                ftms_measurement *out);
ftms_result ftms_encode_measurement_with_format(const ftms_measurement *measurement,
                                                const ftms_measurement_format_options *options,
                                                uint8_t *out, size_t capacity,
                                                size_t *written);

/* Plan self-contained FTMS measurement characteristic values for one immutable,
 * complete snapshot. `value_budget` is the characteristic-value byte budget
 * (for ordinary ATT notifications this is commonly ATT_MTU - 3), not an ATT
 * MTU. The planner does not perform transport I/O or reassembly.
 *
 * A snapshot must have flags More Data clear. If its complete encoding fits,
 * one unchanged record is emitted. Otherwise optional flag groups are greedily
 * packed in wire order into non-final records, without splitting a paired
 * group; the mandatory instantaneous group is emitted in the final record.
 * Every non-final record has More Data set and the final record has it clear.
 * All selected values, including unavailable sentinels, retain their wire form.
 *
 * First call with `packets == NULL` and `packet_capacity == 0` to query the
 * required packet count. For output, `packet_capacity` is an element count and
 * must be sufficient. `snapshot`, `packets`, and `count` must not overlap and
 * snapshot storage must remain unchanged for the call. Any error leaves packets
 * and `*count` unchanged. The maximum valid worst case is below the published
 * FTMS_MEASUREMENT_PLAN_MAX_PACKETS bound. */
ftms_result ftms_measurement_plan(const ftms_measurement *snapshot,
                                   size_t value_budget,
                                   ftms_measurement_packet *packets,
                                    size_t packet_capacity, size_t *count);
/* Uses the same explicit profile for validation, group budgeting, and every
 * emitted packet. NULL is exactly ftms_measurement_plan's historical layout. */
ftms_result ftms_measurement_plan_with_format(const ftms_measurement *snapshot,
                                    const ftms_measurement_format_options *options,
                                    size_t value_budget,
                                    ftms_measurement_packet *packets,
                                    size_t packet_capacity, size_t *count);

/* Bounded receive-side reassembly for one equipment connection/generation.
 * The caller owns one context per connection, initializes it for that
 * connection's kind and generation, and explicitly resets it on disconnect or
 * before accepting a new generation. It has no clock or transport behavior. */
typedef enum ftms_record_status {
  FTMS_RECORD_PENDING = 0, FTMS_RECORD_COMPLETE, FTMS_RECORD_INVALID,
  FTMS_RECORD_EXPIRED, FTMS_RECORD_GENERATION
} ftms_record_status;

typedef struct ftms_record_context {
  ftms_measurement_kind kind;
  uint32_t generation, max_age, started_at;
  uint8_t active;
  ftms_measurement merged;
} ftms_record_context;

/* An alternate-layout receive context.  The selected profile is copied by
 * value at initialization and remains fixed until the next
 * ftms_record_init_with_format call; it is never inferred from a fragment.
 * This is a separate public type so ftms_record_context keeps its established
 * ABI layout.  Treat its contents as API-owned after initialization. */
typedef struct ftms_record_format_context {
  ftms_record_context record;
  ftms_measurement_format_options options;
} ftms_record_format_context;

/* Initialize a caller-owned context. Invalid kind, null context, zero age, or
 * an age >= 2^31 returns INVALID and leaves the context unchanged. Reset
 * discards pending data. A context must be initialized before feed. All access
 * to one context must be serialized by the caller (one event loop or external
 * synchronization); distinct contexts may be used independently. No internal
 * locks or interrupt-safety guarantee is provided.
 *
 * Feed strictly decodes one characteristic-value byte string: RFU flags,
 * truncation, trailing bytes, and malformed wire values are INVALID. Non-final
 * fragments accumulate disjoint optional field groups; a final fragment
 * supplies the mandatory group. Duplicate fields or a Cross Trainer direction
 * change are INVALID and discard pending data. A generation mismatch is
 * GENERATION (before checking expiry) and also discards it; callers reset/init explicitly before a new
 * generation. While pending, an incoming fragment at age >= max_age (unsigned
 * subtraction, valid across wrap for configured ages below 2^31) is EXPIRED,
 * discards both pending data and that input, and never emits an old partial
 * record. The deadline starts with the first non-final fragment and does not
 * slide.
 *
 * `out` is written only for COMPLETE. `context`, input bytes, and `out` must
 * not overlap; input remains stable for the call. A final standalone fragment
 * completes directly. COMPLETE output has More Data clear and unioned selected
 * groups, preserving presence, unavailable sentinels, and decoded raw values.
 * For assembled output, bytes_read is zero: no single received byte span exists.
 * Standalone output retains its decoded bytes_read. These complete outputs have
 * no truncation/trailing/RFU diagnostics. COMPLETE does not prove that every
 * fragment arrived: FTMS has no general record sequence identifier. */
ftms_record_status ftms_record_init(ftms_record_context *context,
                                    ftms_measurement_kind kind,
                                    uint32_t generation, uint32_t max_age);
void ftms_record_reset(ftms_record_context *context);
ftms_record_status ftms_record_feed(ftms_record_context *context,
                                     const uint8_t *data, size_t size,
                                     uint32_t generation, uint32_t now,
                                     ftms_measurement *out);
/* Format-aware assembly uses the same profile for strict fragment decode and
 * canonical re-encode. NULL options selects the historical default. Options
 * are copied before context storage is written, so an options pointer may name
 * context->options. Invalid options, kind, age, or a null context return
 * INVALID without changing any context bytes. Reset preserves the chosen
 * profile; reinitialization deliberately discards any pending record. */
ftms_record_status ftms_record_init_with_format(ftms_record_format_context *context,
                                                ftms_measurement_kind kind,
                                                const ftms_measurement_format_options *options,
                                                uint32_t generation, uint32_t max_age);
void ftms_record_reset_with_format(ftms_record_format_context *context);
ftms_record_status ftms_record_feed_with_format(ftms_record_format_context *context,
                                                const uint8_t *data, size_t size,
                                                uint32_t generation, uint32_t now,
                                                ftms_measurement *out);
#ifdef __cplusplus
}
#endif
#endif

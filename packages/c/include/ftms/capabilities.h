#ifndef FTMS_CAPABILITIES_H
#define FTMS_CAPABILITIES_H

#include "ftms/ftms.h"

#ifdef __cplusplus
extern "C" {
#endif

#define FTMS_CAP_UUID_BYTES 16U
#define FTMS_CAP_RANGE_COUNT 5U
#define FTMS_CAP_OPERATION_COUNT 21U
#define FTMS_CAP_NO_INDEX SIZE_MAX
#define FTMS_CAP_NO_TARGET UINT8_C(255)
#define FTMS_CAP_PROP_READ UINT16_C(0x0002)
#define FTMS_CAP_PROP_WRITE UINT16_C(0x0008)
#define FTMS_CAP_PROP_NOTIFY UINT16_C(0x0010)
#define FTMS_CAP_PROP_INDICATE UINT16_C(0x0020)

typedef enum ftms_cap_discovery {
  FTMS_CAP_DISCOVERY_NOT_ATTEMPTED, FTMS_CAP_DISCOVERY_PARTIAL,
  FTMS_CAP_DISCOVERY_COMPLETE, FTMS_CAP_DISCOVERY_FAILED
} ftms_cap_discovery;
typedef enum ftms_cap_service_scope {
  FTMS_CAP_SERVICE_UNKNOWN, FTMS_CAP_SERVICE_PRESENT,
  FTMS_CAP_SERVICE_ABSENT, FTMS_CAP_SERVICE_AMBIGUOUS
} ftms_cap_service_scope;
typedef enum ftms_cap_read_state {
  FTMS_CAP_READ_NOT_ATTEMPTED, FTMS_CAP_READ_SUCCESS, FTMS_CAP_READ_FAILED
} ftms_cap_read_state;
typedef enum ftms_cap_read_reason {
  FTMS_CAP_READ_REASON_NONE, FTMS_CAP_READ_REASON_GENERIC,
  FTMS_CAP_READ_REASON_SECURITY_REQUIRED, FTMS_CAP_READ_REASON_UNAVAILABLE,
  FTMS_CAP_READ_REASON_TIMEOUT, FTMS_CAP_READ_REASON_DISCONNECTED
} ftms_cap_read_reason;
typedef enum ftms_cap_presence {
  FTMS_CAP_PRESENCE_UNKNOWN, FTMS_CAP_PRESENCE_ABSENT,
  FTMS_CAP_PRESENCE_UNIQUE, FTMS_CAP_PRESENCE_AMBIGUOUS
} ftms_cap_presence;
typedef enum ftms_cap_decode {
  FTMS_CAP_DECODE_NOT_ATTEMPTED, FTMS_CAP_DECODE_VALID,
  FTMS_CAP_DECODE_MALFORMED, FTMS_CAP_DECODE_FAILED
} ftms_cap_decode;
typedef enum ftms_cap_declaration {
  FTMS_CAP_DECLARATION_UNKNOWN, FTMS_CAP_DECLARATION_NOT_SUPPORTED,
  FTMS_CAP_DECLARATION_SUPPORTED
} ftms_cap_declaration;
/* SATISFIED means only the static prerequisites examined here, never permission. */
typedef enum ftms_cap_prerequisite {
  FTMS_CAP_PREREQUISITE_NOT_APPLICABLE, FTMS_CAP_PREREQUISITE_SATISFIED,
  FTMS_CAP_PREREQUISITE_INCOMPLETE, FTMS_CAP_PREREQUISITE_INCONSISTENT
} ftms_cap_prerequisite;

enum {
  FTMS_CAP_KIND_UNKNOWN, FTMS_CAP_KIND_FEATURE, FTMS_CAP_KIND_TREADMILL,
  FTMS_CAP_KIND_CROSS_TRAINER, FTMS_CAP_KIND_STEP_CLIMBER,
  FTMS_CAP_KIND_STAIR_CLIMBER, FTMS_CAP_KIND_ROWER, FTMS_CAP_KIND_INDOOR_BIKE,
  FTMS_CAP_KIND_TRAINING_STATUS, FTMS_CAP_KIND_SPEED_RANGE,
  FTMS_CAP_KIND_INCLINATION_RANGE, FTMS_CAP_KIND_RESISTANCE_RANGE,
  FTMS_CAP_KIND_HEART_RATE_RANGE, FTMS_CAP_KIND_POWER_RANGE,
  FTMS_CAP_KIND_CONTROL_POINT, FTMS_CAP_KIND_MACHINE_STATUS, FTMS_CAP_KIND_COUNT
};

/* Operation reason flags: unavailable evidence is not contradictory evidence. */
#define FTMS_CAP_REASON_SCOPE_UNAVAILABLE UINT32_C(0x001)
#define FTMS_CAP_REASON_DISCOVERY_INCOMPLETE UINT32_C(0x002)
#define FTMS_CAP_REASON_FEATURE_UNAVAILABLE UINT32_C(0x004)
#define FTMS_CAP_REASON_FEATURE_INVALID UINT32_C(0x008)
#define FTMS_CAP_REASON_CONTROL_POINT_UNAVAILABLE UINT32_C(0x010)
#define FTMS_CAP_REASON_CONTROL_POINT_INVALID UINT32_C(0x020)
#define FTMS_CAP_REASON_STATUS_UNAVAILABLE UINT32_C(0x040)
#define FTMS_CAP_REASON_STATUS_INVALID UINT32_C(0x080)
#define FTMS_CAP_REASON_RANGE_UNAVAILABLE UINT32_C(0x100)
#define FTMS_CAP_REASON_RANGE_INVALID UINT32_C(0x200)
#define FTMS_CAP_REASON_C7_EVIDENCE_UNAVAILABLE UINT32_C(0x400)
typedef enum ftms_cap_truth {
  FTMS_CAP_TRUTH_UNKNOWN, FTMS_CAP_TRUTH_FALSE, FTMS_CAP_TRUTH_TRUE
} ftms_cap_truth;
typedef struct ftms_cap_c7_evidence {
  ftms_cap_truth bonding_supported;
  ftms_cap_truth feature_may_change_over_lifetime;
} ftms_cap_c7_evidence;

typedef struct ftms_cap_characteristic {
  uint8_t uuid[FTMS_CAP_UUID_BYTES];
  uint16_t properties;
  ftms_cap_read_state read_state;
  ftms_cap_read_reason read_reason;
  const uint8_t *read_bytes;
  size_t read_size;
} ftms_cap_characteristic;
typedef struct ftms_cap_snapshot {
  ftms_cap_discovery discovery;
  ftms_cap_service_scope service_scope;
  uint32_t generation;
  const ftms_cap_characteristic *characteristics;
  size_t characteristic_count;
} ftms_cap_snapshot;
typedef struct ftms_cap_observation {
  size_t input_index;
  uint8_t uuid[FTMS_CAP_UUID_BYTES];
  uint16_t properties;
  uint8_t known_kind;
  ftms_cap_read_state read_state;
  ftms_cap_read_reason read_reason;
  size_t read_size;
} ftms_cap_observation;
typedef enum ftms_cap_diagnostic_code {
  FTMS_CAP_DIAG_SCOPE_UNAVAILABLE, FTMS_CAP_DIAG_DISCOVERY_INCOMPLETE,
  FTMS_CAP_DIAG_DISCOVERY_FAILED, FTMS_CAP_DIAG_DUPLICATE_CHARACTERISTIC,
  FTMS_CAP_DIAG_REQUIRED_CHARACTERISTIC_MISSING,
  FTMS_CAP_DIAG_REQUIRED_PROPERTY_MISSING, FTMS_CAP_DIAG_EXCLUDED_PROPERTY_PRESENT,
  FTMS_CAP_DIAG_READ_FAILED, FTMS_CAP_DIAG_READ_SECURITY_REQUIRED,
  FTMS_CAP_DIAG_MALFORMED_BYTES, FTMS_CAP_DIAG_REQUIRED_RANGE_MISSING,
  FTMS_CAP_DIAG_SCOPE_CONTRADICTION, FTMS_CAP_DIAG_C7_EVIDENCE_INSUFFICIENT
} ftms_cap_diagnostic_code;
typedef struct ftms_cap_diagnostic {
  ftms_cap_diagnostic_code code;
  uint8_t known_kind;
  size_t input_index;
} ftms_cap_diagnostic;
typedef struct ftms_cap_feature_evidence {
  ftms_cap_presence presence;
  ftms_cap_decode decode;
  size_t input_index;
  uint32_t machine_raw, target_raw, machine_unknown, target_unknown;
} ftms_cap_feature_evidence;
typedef struct ftms_cap_range_evidence {
  ftms_cap_presence presence;
  ftms_cap_decode decode;
  size_t input_index;
  ftms_range value;
} ftms_cap_range_evidence;
typedef struct ftms_cap_operation {
  uint8_t opcode;
  uint8_t target_bit;
  uint8_t optional_in_table;
  ftms_cap_declaration declaration;
  ftms_cap_prerequisite prerequisite;
  uint32_t reasons;
} ftms_cap_operation;
typedef struct ftms_cap_report {
  uint32_t generation;
  ftms_cap_discovery discovery;
  ftms_cap_service_scope service_scope;
  size_t observation_count, diagnostic_count;
  /* UNKNOWN slot is always UNKNOWN; other slots follow the kind enumeration. */
  ftms_cap_presence presence[FTMS_CAP_KIND_COUNT];
  ftms_cap_feature_evidence feature;
  /* Native range-kind order: speed, inclination, resistance, heart rate, power. */
  ftms_cap_range_evidence ranges[FTMS_CAP_RANGE_COUNT];
  /* Array is indexed by wire opcode 0x00 through 0x14. */
  ftms_cap_operation operations[FTMS_CAP_OPERATION_COUNT];
} ftms_cap_report;
typedef struct ftms_cap_requirements {
  size_t observation_count, diagnostic_count;
} ftms_cap_requirements;
typedef struct ftms_cap_output {
  ftms_cap_observation *observations;
  size_t observation_capacity;
  ftms_cap_diagnostic *diagnostics;
  size_t diagnostic_capacity;
  ftms_cap_report report;
} ftms_cap_output;

/* UUIDs are 16 bytes in display/network order: 0000xxxx-0000-1000-8000-00805f9b34fb.
 * One snapshot describes one caller-selected service instance/generation.
 * Input/output objects and buffers must not overlap and must remain stable during
 * each call. Raw read bytes remain caller-owned; result indices refer to them.
 * No pointers are retained. For non-success reads, bytes/size must be NULL/zero;
 * reason must be NONE unless FAILED. SUCCESS with NULL/zero is malformed evidence.
 * Only lengths 8 (Feature), 3 or 6 (ranges) are decoded; other evidence is opaque.
 * Requirements returns exact element counts. Buffers may be NULL for zero counts.
 * NULL arguments -> ERROR_NULL; invalid enums/state combinations -> ERROR_KIND;
 * insufficient capacities/unrepresentable counts -> ERROR_LENGTH. All errors leave
 * outputs and output buffers untouched. FTMS_OK means evaluation completed, NOT
 * protocol consistency, GATT completeness, or permission to issue commands.
 * A range value/raw Feature words are meaningful only when decode == VALID. */
ftms_result ftms_capability_requirements(const ftms_cap_snapshot *snapshot,
                                        ftms_cap_requirements *out);
ftms_result ftms_evaluate_capabilities(const ftms_cap_snapshot *snapshot,
                                      ftms_cap_output *out);
/* Explicit range layout is caller-owned evidence, never device inference. NULL
 * preserves historical layouts. Invalid options fail before any output mutation. */
ftms_result ftms_capability_requirements_with_format(const ftms_cap_snapshot *snapshot,
                                        const ftms_range_format_options *options,
                                        ftms_cap_requirements *out);
ftms_result ftms_evaluate_capabilities_with_format(const ftms_cap_snapshot *snapshot,
                                      const ftms_range_format_options *options,
                                       ftms_cap_output *out);
/* C.7 facts are explicit: keeping snapshot unchanged preserves source/ABI use of
 * existing initializers and avoids interpreting uninitialized appended storage.
 * NULL means unknown. */
ftms_result ftms_capability_requirements_with_c7(const ftms_cap_snapshot *snapshot,
                                        const ftms_range_format_options *options,
                                        const ftms_cap_c7_evidence *c7, ftms_cap_requirements *out);
ftms_result ftms_evaluate_capabilities_with_c7(const ftms_cap_snapshot *snapshot,
                                       const ftms_range_format_options *options,
                                       const ftms_cap_c7_evidence *c7, ftms_cap_output *out);

#ifdef __cplusplus
} /* extern "C" */
#endif
#endif

#include "ftms/capabilities.h"
#include "ftms/control.h"
#include "ftms/measurement.h"
#include "ftms/status.h"

int main(void) {
  uint8_t bytes[8] = {0}; size_t written = 0U;
  ftms_control_request request = {FTMS_CONTROL_REQUEST_CONTROL, {0}};
  const ftms_control_format_options command_format = {FTMS_CONTROL_RESISTANCE_UINT8_TENTHS};
  const uint8_t resistance_request[] = {0x04U, 0x7bU};
  ftms_features features = {0U, 0U};
  ftms_range_inspection inspection;
  const uint8_t range_bytes[] = {0U, 0U, 100U, 0U, 1U, 0U};
  const ftms_range_format_options range_format = {FTMS_RESISTANCE_RANGE_SINT16_TENTHS};
  ftms_cap_snapshot snapshot = {FTMS_CAP_DISCOVERY_COMPLETE, FTMS_CAP_SERVICE_PRESENT, 7U, NULL, 0U};
  const ftms_cap_c7_evidence c7 = {FTMS_CAP_TRUTH_FALSE, FTMS_CAP_TRUTH_FALSE};
  ftms_cap_requirements requirements;
  ftms_cap_diagnostic diagnostics[1];
  ftms_cap_output out = {0};
  ftms_measurement measurement;
  ftms_measurement record_measurement = {0};
  ftms_record_format_context record;
  const ftms_measurement_format_options signed_resistance = {
    FTMS_MEASUREMENT_RESISTANCE_SINT16_TENTHS, FTMS_TREADMILL_PACE_UINT16};
  ftms_training_status training = {0U, 1U, 0U, 0U, 0U, 0U, 0U, 0U, 0U, 0U, 0U, 0U};
  uint8_t more_data[] = {1U, 0U};
  const uint8_t partial[] = {0x61U, 0x00U, 0x78U, 0x00U, 0x2cU, 0x01U};
  const uint8_t final[] = {0x00U, 0x00U, 0x01U, 0x00U};
  out.diagnostics = diagnostics; out.diagnostic_capacity = 1;
  if (ftms_inspect_range(FTMS_RANGE_RESISTANCE_LEVEL, range_bytes, sizeof range_bytes,
                         &inspection) != FTMS_OK || inspection.status != FTMS_RANGE_INSPECTION_LENGTH ||
      inspection.candidate_count != 2U || inspection.candidates[1].status != FTMS_RANGE_INSPECTION_VALID ||
      ftms_inspect_range_with_format(FTMS_RANGE_RESISTANCE_LEVEL, range_bytes, sizeof range_bytes,
                                    &range_format, &inspection) != FTMS_OK ||
      inspection.status != FTMS_RANGE_INSPECTION_VALID || inspection.value.maximum != 100) return 1;
  if (ftms_decode_control_request_with_format(resistance_request, sizeof resistance_request,
                                             &command_format, &request) != FTMS_OK ||
      request.value.resistance_tenth_level != 123 ||
      ftms_encode_control_request_with_format(&request, &command_format, bytes, sizeof bytes,
                                             &written) != FTMS_OK ||
      written != 2U || bytes[0] != 0x04U || bytes[1] != 0x7bU) return 1;
  request.opcode = FTMS_CONTROL_REQUEST_CONTROL;
  if (ftms_record_init_with_format(&record, FTMS_MEASUREMENT_INDOOR_BIKE,
                                   &signed_resistance, 1U, 5U) != FTMS_RECORD_PENDING ||
      ftms_record_feed_with_format(&record, partial, sizeof partial, 1U, 1U,
                                   &record_measurement) != FTMS_RECORD_PENDING) return 1;
  ftms_record_reset_with_format(&record);
  if (ftms_record_feed_with_format(&record, partial, sizeof partial, 1U, 2U,
                                   &record_measurement) != FTMS_RECORD_PENDING ||
      ftms_record_feed_with_format(&record, final, sizeof final, 1U, 3U,
                                   &record_measurement) != FTMS_RECORD_COMPLETE) return 1;
  if (ftms_encode_features(&features, bytes, sizeof bytes, &written) != FTMS_OK || written != 8U ||
      ftms_decode_features(bytes, sizeof bytes, &features) != FTMS_OK ||
       ftms_encode_control_request(&request, bytes, sizeof bytes, &written) != FTMS_OK || written != 1U ||
       ftms_capability_requirements_with_c7(&snapshot, NULL, &c7, &requirements) != FTMS_OK ||
         ftms_evaluate_capabilities_with_c7(&snapshot, NULL, &c7, &out) != FTMS_OK ||
        ftms_decode_measurement(FTMS_MEASUREMENT_INDOOR_BIKE, more_data,
                                sizeof more_data, &measurement) != FTMS_OK ||
        ftms_encode_training_status(&training, NULL, 0U, bytes, sizeof bytes, &written) != FTMS_OK || written != 2U) return 1;
  return features.target == 0 && requirements.observation_count == 0 &&
    requirements.diagnostic_count == 1 && out.report.generation == 7 &&
    diagnostics[0].code == FTMS_CAP_DIAG_REQUIRED_CHARACTERISTIC_MISSING &&
      out.report.operations[2].declaration == FTMS_CAP_DECLARATION_UNKNOWN &&
      measurement.kind == FTMS_MEASUREMENT_INDOOR_BIKE && measurement.more_data == 1U &&
      measurement.present == 0U && record_measurement.value[FTMS_M_RESISTANCE] == 120 &&
      record_measurement.value[FTMS_M_POWER] == 300 && record_measurement.value[FTMS_M_SPEED] == 1 ? 0 : 2;
}

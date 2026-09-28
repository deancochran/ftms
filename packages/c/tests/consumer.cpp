#include "ftms/capabilities.h"
#include "ftms/control.h"
#include "ftms/measurement.h"
#include "ftms/status.h"

int main() {
  ftms_control_request request = {FTMS_CONTROL_REQUEST_CONTROL, {0}};
  uint8_t control[1] = {0}; size_t written = 0;
  if (ftms_encode_control_request(&request, control, sizeof control, &written) != FTMS_OK || written != 1U) return 3;
  unsigned char bytes[8] = {};
  ftms_features features{};
  ftms_cap_snapshot snapshot = {FTMS_CAP_DISCOVERY_COMPLETE, FTMS_CAP_SERVICE_PRESENT, 7U, nullptr, 0U};
  ftms_cap_requirements requirements{};
  ftms_cap_diagnostic diagnostics[1]{};
  ftms_cap_output out{};
  ftms_measurement measurement{};
  ftms_training_status training{};
  training.code = 1U;
  unsigned char more_data[] = {1U, 0U};
  out.diagnostics = diagnostics; out.diagnostic_capacity = 1;
  if (ftms_encode_features(&features, bytes, sizeof bytes, &written) != FTMS_OK || written != 8U ||
      ftms_decode_features(bytes, sizeof bytes, &features) != FTMS_OK ||
      ftms_capability_requirements(&snapshot, &requirements) != FTMS_OK ||
       ftms_evaluate_capabilities(&snapshot, &out) != FTMS_OK ||
       ftms_decode_measurement(FTMS_MEASUREMENT_INDOOR_BIKE, more_data,
                               sizeof more_data, &measurement) != FTMS_OK ||
       ftms_encode_training_status(&training, nullptr, 0U, bytes, sizeof bytes, &written) != FTMS_OK || written != 2U) return 1;
  return features.target == 0 && requirements.observation_count == 0 &&
    requirements.diagnostic_count == 1 && out.report.generation == 7 &&
    diagnostics[0].code == FTMS_CAP_DIAG_REQUIRED_CHARACTERISTIC_MISSING &&
     out.report.operations[2].declaration == FTMS_CAP_DECLARATION_UNKNOWN &&
     measurement.kind == FTMS_MEASUREMENT_INDOOR_BIKE && measurement.more_data == 1U &&
     measurement.present == 0U ? 0 : 2;
}

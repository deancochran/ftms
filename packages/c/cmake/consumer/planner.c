#include "ftms/measurement.h"
#include "ftms/capabilities.h"

int main(void) {
  ftms_measurement snapshot = {0};
  ftms_measurement assembled = {0};
  ftms_record_format_context records = {0};
  size_t count = 0U;
  const ftms_measurement_format_options measurement_options = {
    FTMS_MEASUREMENT_RESISTANCE_SINT16_TENTHS, FTMS_TREADMILL_PACE_UINT8_LEGACY};
  const ftms_range_format_options range_options = {FTMS_RESISTANCE_RANGE_SINT16_TENTHS};
  ftms_cap_snapshot evidence = {0};
  ftms_cap_requirements requirements;
  ftms_cap_output report = {0};
  ftms_cap_diagnostic diagnostics[64];
  snapshot.kind = FTMS_MEASUREMENT_INDOOR_BIKE;
  snapshot.flags = UINT32_C(0x860);
  snapshot.present = (UINT64_C(1) << FTMS_M_SPEED) | (UINT64_C(1) << FTMS_M_RESISTANCE) |
    (UINT64_C(1) << FTMS_M_POWER) | (UINT64_C(1) << FTMS_M_ELAPSED_TIME);
  snapshot.value[FTMS_M_SPEED] = 0;
  snapshot.value[FTMS_M_RESISTANCE] = 120;
  snapshot.value[FTMS_M_POWER] = 300;
  snapshot.value[FTMS_M_ELAPSED_TIME] = 901;
  if (ftms_measurement_plan(&snapshot, 4U, NULL, 0U, &count) != FTMS_OK || count != 4U) return 1;
  if (ftms_measurement_plan_with_format(&snapshot, &measurement_options, 6U, NULL, 0U, &count) != FTMS_OK || count != 3U) return 2;
  if (ftms_record_init_with_format(&records, FTMS_MEASUREMENT_INDOOR_BIKE,
                                   &measurement_options, 4U, 10U) != FTMS_RECORD_PENDING) return 3;
  { const uint8_t first[] = {0x61,0x00,0x78,0x00,0x2c,0x01};
    const uint8_t second[] = {0x01,0x08,0x85,0x03};
    const uint8_t final[] = {0x00,0x00,0x01,0x00};
    if (ftms_record_feed_with_format(&records, first, sizeof first, 4U, 0U, &assembled) != FTMS_RECORD_PENDING ||
        ftms_record_feed_with_format(&records, second, sizeof second, 4U, 1U, &assembled) != FTMS_RECORD_PENDING) return 4;
    ftms_record_reset_with_format(&records);
    if (ftms_record_feed_with_format(&records, final, sizeof final, 4U, 2U, &assembled) != FTMS_RECORD_COMPLETE ||
        assembled.value[FTMS_M_SPEED] != 1) return 5; }
  if (ftms_capability_requirements_with_format(&evidence, &range_options, &requirements) != FTMS_OK) return 6;
  report.diagnostics = diagnostics;
  report.diagnostic_capacity = sizeof diagnostics / sizeof diagnostics[0];
  if (ftms_evaluate_capabilities_with_format(&evidence, &range_options, &report) != FTMS_OK) return 7;
  return report.report.diagnostic_count == requirements.diagnostic_count ? 0 : 8;
}

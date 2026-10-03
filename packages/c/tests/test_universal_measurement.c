#include <assert.h>
#include <string.h>
#include "ftms/measurement.h"

static uint16_t uuid_for(ftms_measurement_kind kind) {
  static const uint16_t uuids[] = {FTMS_UUID16_TREADMILL_DATA,
    FTMS_UUID16_CROSS_TRAINER_DATA, FTMS_UUID16_STEP_CLIMBER_DATA,
    FTMS_UUID16_STAIR_CLIMBER_DATA, FTMS_UUID16_ROWER_DATA,
    FTMS_UUID16_INDOOR_BIKE_DATA};
  return uuids[(unsigned)kind];
}

int main(void) {
  const ftms_measurement_kind kinds[] = {FTMS_MEASUREMENT_TREADMILL,
    FTMS_MEASUREMENT_CROSS_TRAINER, FTMS_MEASUREMENT_STEP_CLIMBER,
    FTMS_MEASUREMENT_STAIR_CLIMBER, FTMS_MEASUREMENT_ROWER,
    FTMS_MEASUREMENT_INDOOR_BIKE};
  size_t i;
  /* Independently enumerate every public metric mapping. The accessor projects
   * caller-owned raw evidence; decoding itself is covered by the corpus runner. */
  {
    const struct { ftms_measurement_metric metric; ftms_measurement_field field; unsigned divisor; } mappings[] = {
      {FTMS_METRIC_SPEED_METRES_PER_SECOND, FTMS_M_SPEED, 360},
      {FTMS_METRIC_AVERAGE_SPEED_METRES_PER_SECOND, FTMS_M_AVERAGE_SPEED, 360},
      {FTMS_METRIC_DISTANCE_METRES, FTMS_M_DISTANCE, 1},
      {FTMS_METRIC_INCLINATION_PERCENT, FTMS_M_INCLINATION, 10},
      {FTMS_METRIC_RAMP_ANGLE_DEGREES, FTMS_M_RAMP_ANGLE, 10},
      {FTMS_METRIC_POSITIVE_ELEVATION_METRES, FTMS_M_POSITIVE_ELEVATION, 10},
      {FTMS_METRIC_NEGATIVE_ELEVATION_METRES, FTMS_M_NEGATIVE_ELEVATION, 10},
      {FTMS_METRIC_INSTANTANEOUS_PACE_SECONDS_PER_500_METRES, FTMS_M_INSTANTANEOUS_PACE, 1},
      {FTMS_METRIC_AVERAGE_PACE_SECONDS_PER_500_METRES, FTMS_M_AVERAGE_PACE, 1},
      {FTMS_METRIC_ENERGY_KCAL, FTMS_M_TOTAL_ENERGY, 1},
      {FTMS_METRIC_ENERGY_PER_HOUR_KCAL, FTMS_M_ENERGY_PER_HOUR, 1},
      {FTMS_METRIC_ENERGY_PER_MINUTE_KCAL, FTMS_M_ENERGY_PER_MINUTE, 1},
      {FTMS_METRIC_HEART_RATE_BPM, FTMS_M_HEART_RATE, 1},
      {FTMS_METRIC_METABOLIC_EQUIVALENT, FTMS_M_MET, 10},
      {FTMS_METRIC_ELAPSED_SECONDS, FTMS_M_ELAPSED_TIME, 1},
      {FTMS_METRIC_REMAINING_SECONDS, FTMS_M_REMAINING_TIME, 1},
      {FTMS_METRIC_FORCE_NEWTONS, FTMS_M_FORCE_ON_BELT, 1},
      {FTMS_METRIC_POWER_WATTS, FTMS_M_POWER, 1},
      {FTMS_METRIC_AVERAGE_POWER_WATTS, FTMS_M_AVERAGE_POWER, 1},
      {FTMS_METRIC_STEP_RATE_PER_MINUTE, FTMS_M_STEP_RATE, 1},
      {FTMS_METRIC_AVERAGE_STEP_RATE_PER_MINUTE, FTMS_M_AVERAGE_STEP_RATE, 1},
      {FTMS_METRIC_STRIDE_COUNT, FTMS_M_STRIDE_COUNT, 1},
      {FTMS_METRIC_RESISTANCE_LEVEL, FTMS_M_RESISTANCE, 1},
      {FTMS_METRIC_FLOOR_COUNT, FTMS_M_FLOOR_COUNT, 1},
      {FTMS_METRIC_STEP_COUNT, FTMS_M_STEP_COUNT, 1},
      {FTMS_METRIC_STROKE_RATE_PER_MINUTE, FTMS_M_STROKE_RATE, 2},
      {FTMS_METRIC_STROKE_COUNT, FTMS_M_STROKE_COUNT, 1},
      {FTMS_METRIC_AVERAGE_STROKE_RATE_PER_MINUTE, FTMS_M_AVERAGE_STROKE_RATE, 2},
      {FTMS_METRIC_CADENCE_RPM, FTMS_M_CADENCE, 2},
      {FTMS_METRIC_AVERAGE_CADENCE_RPM, FTMS_M_AVERAGE_CADENCE, 2}
    };
    size_t family;
    assert(sizeof mappings / sizeof *mappings == 30U);
    for (family = 0; family < 6U; ++family) for (i = 0; i < 30U; ++i) {
      ftms_measurement_view view = {0}; ftms_measurement_fixed_point value;
      unsigned divisor = mappings[i].divisor;
      view.raw.kind = kinds[family];
      view.raw.present = UINT64_C(1) << mappings[i].field;
      view.raw.value[mappings[i].field] = (int32_t)(1000U + i);
      if ((mappings[i].field == FTMS_M_POSITIVE_ELEVATION || mappings[i].field == FTMS_M_NEGATIVE_ELEVATION) && family != 0U) divisor = 1;
      if (mappings[i].field == FTMS_M_STRIDE_COUNT && family == 1U) divisor = 10;
      assert(ftms_measurement_metric_value(&view, mappings[i].metric, &value) == FTMS_MEASUREMENT_VALUE_NUMERIC);
      assert(value.numerator == (int32_t)(1000U + i) && value.denominator == divisor);
    }
  }
  for (i = 0U; i < sizeof kinds / sizeof *kinds; ++i) {
    ftms_measurement_kind mapped; ftms_measurement input = {0};
    ftms_measurement_view view, saved; uint8_t bytes[64]; size_t written;
    input.kind = kinds[i]; input.flags = 0U; input.present = UINT64_C(1) << FTMS_M_SPEED;
    if (kinds[i] == FTMS_MEASUREMENT_STEP_CLIMBER || kinds[i] == FTMS_MEASUREMENT_STAIR_CLIMBER) {
      input.present = (UINT64_C(1) << FTMS_M_FLOOR_COUNT);
      input.value[FTMS_M_FLOOR_COUNT] = 2;
      if (kinds[i] == FTMS_MEASUREMENT_STEP_CLIMBER) {
        input.present |= UINT64_C(1) << FTMS_M_STEP_COUNT;
        input.value[FTMS_M_STEP_COUNT] = 3;
      }
    } else if (kinds[i] == FTMS_MEASUREMENT_ROWER) {
      input.present = (UINT64_C(1) << FTMS_M_STROKE_RATE) | (UINT64_C(1) << FTMS_M_STROKE_COUNT);
      input.value[FTMS_M_STROKE_RATE] = 30; input.value[FTMS_M_STROKE_COUNT] = 2;
    } else input.value[FTMS_M_SPEED] = 360;
    assert(ftms_measurement_kind_from_uuid16(uuid_for(kinds[i]), &mapped) == FTMS_OK && mapped == kinds[i]);
    assert(ftms_encode_measurement(&input, bytes, sizeof bytes, &written) == FTMS_OK);
    assert(ftms_decode_measurement_uuid16_view(uuid_for(kinds[i]), bytes, written, NULL, &view) == FTMS_OK);
    assert(view.raw.kind == kinds[i] && view.format.resistance_format == FTMS_MEASUREMENT_RESISTANCE_UINT8_WHOLE);
    if (written > 2U) {
      assert(ftms_decode_measurement_uuid16_view(uuid_for(kinds[i]), bytes, written - 1U, NULL, &view) == FTMS_OK);
      assert(view.raw.truncated == 1U);
    }
    saved = view;
    assert(ftms_decode_measurement_uuid16_view(uuid_for(kinds[i]), bytes, 0, NULL, &view) == FTMS_ERROR_LENGTH);
    assert(memcmp(&view, &saved, sizeof view) == 0);
    assert(ftms_decode_measurement_uuid16_view(uuid_for(kinds[i]), bytes, written, NULL, NULL) == FTMS_ERROR_NULL);
    assert(ftms_decode_measurement_uuid16_view(UINT16_C(0x1234), bytes, written, NULL, &view) == FTMS_ERROR_KIND);
    assert(memcmp(&view, &saved, sizeof view) == 0);
  }
  {
    const uint8_t data[] = {0, 0, 104, 1}; /* Treadmill speed = 360 raw. */
    ftms_measurement_view v; ftms_measurement_fixed_point x;
    assert(ftms_decode_measurement_uuid16_view(FTMS_UUID16_TREADMILL_DATA, data, sizeof data, NULL, &v) == FTMS_OK);
    assert(ftms_measurement_metric_value(&v, FTMS_METRIC_SPEED_METRES_PER_SECOND, &x) == FTMS_MEASUREMENT_VALUE_NUMERIC);
    assert(x.numerator == 360 && x.denominator == 360);
    assert(ftms_measurement_metric_value(&v, FTMS_METRIC_POWER_WATTS, &x) == FTMS_MEASUREMENT_VALUE_ABSENT);
  }
  {
    const ftms_measurement_format_options signed_resistance = {FTMS_MEASUREMENT_RESISTANCE_SINT16_TENTHS, FTMS_TREADMILL_PACE_UINT16};
    const uint8_t data[] = {0x20, 0, 1, 0, 246, 255}; /* bike speed, signed resistance -1.0 */
    ftms_measurement_view v; ftms_measurement_fixed_point x;
    assert(ftms_decode_measurement_uuid16_view(FTMS_UUID16_INDOOR_BIKE_DATA, data, sizeof data, &signed_resistance, &v) == FTMS_OK);
    assert(ftms_measurement_metric_value(&v, FTMS_METRIC_RESISTANCE_LEVEL, &x) == FTMS_MEASUREMENT_VALUE_NUMERIC);
    assert(x.numerator == -10 && x.denominator == 10);
  }
  {
    ftms_measurement_view invalid = {0}; ftms_measurement_fixed_point x = {7, 9};
    invalid.raw.kind = (ftms_measurement_kind)6;
    assert(ftms_measurement_metric_value(&invalid, FTMS_METRIC_POWER_WATTS, &x) == FTMS_MEASUREMENT_VALUE_ABSENT);
    assert(x.numerator == 7 && x.denominator == 9);
    assert(ftms_measurement_metric_value(NULL, FTMS_METRIC_POWER_WATTS, &x) == FTMS_MEASUREMENT_VALUE_ABSENT);
    assert(x.numerator == 7 && x.denominator == 9);
    assert(ftms_measurement_metric_value(&invalid, (ftms_measurement_metric)30, &x) == FTMS_MEASUREMENT_VALUE_ABSENT);
    assert(x.numerator == 7 && x.denominator == 9);
    invalid.raw.kind = FTMS_MEASUREMENT_TREADMILL;
    invalid.format.resistance_format = (ftms_measurement_resistance_format)2;
    assert(ftms_measurement_metric_value(&invalid, FTMS_METRIC_POWER_WATTS, &x) == FTMS_MEASUREMENT_VALUE_ABSENT);
    assert(x.numerator == 7 && x.denominator == 9);
  }
  {
    const ftms_measurement_format_options legacy = {FTMS_MEASUREMENT_RESISTANCE_UINT8_WHOLE, FTMS_TREADMILL_PACE_UINT8_LEGACY};
    const uint8_t data[] = {0x20, 0, 1, 0, 7}; /* speed, legacy instantaneous pace */
    ftms_measurement_view v; ftms_measurement_fixed_point x;
    assert(ftms_decode_measurement_uuid16_view(FTMS_UUID16_TREADMILL_DATA, data, sizeof data, &legacy, &v) == FTMS_OK);
    assert(ftms_measurement_metric_value(&v, FTMS_METRIC_INSTANTANEOUS_PACE_SECONDS_PER_500_METRES, &x) == FTMS_MEASUREMENT_VALUE_UNKNOWN_UNIT);
  }
  {
    const uint8_t data[] = {0x80, 0, 1, 0, 255, 255, 255}; /* treadmill energy group unavailable */
    ftms_measurement_view v; ftms_measurement_fixed_point x;
    assert(ftms_decode_measurement_uuid16_view(FTMS_UUID16_TREADMILL_DATA, data, sizeof data, NULL, &v) == FTMS_OK);
    assert(ftms_measurement_metric_value(&v, FTMS_METRIC_ENERGY_KCAL, &x) == FTMS_MEASUREMENT_VALUE_UNAVAILABLE);
  }
  return 0;
}

#include <stdio.h>
#include <stdint.h>

#include <ftms/control.h>
#include <ftms/measurement.h>

static int require_result(ftms_result result, const char *what) {
  if (result == FTMS_OK) return 1;
  fprintf(stderr, "%s failed: %d\n", what, (int)result);
  return 0;
}

static void print_value(const char *name, int32_t value, const char *unit) {
  printf("  %s: %ld %s\n", name, (long)value, unit);
}

int main(void) {
  static const uint8_t bike[] = {0xfe, 0x1f, 0xe8, 0x03, 0x84, 0x03, 0xb4, 0x00,
    0xaa, 0x00, 0xe8, 0x03, 0x00, 0x08, 0xfa, 0x00, 0xf0, 0x00, 0x2c, 0x01,
    0x90, 0x01, 0x05, 0x91, 0x50, 0x58, 0x02, 0x64, 0x00};
  static const uint8_t treadmill[] = {0xfe, 0x1f, 0xe8, 0x03, 0x84, 0x03, 0x03,
    0x02, 0x01, 0xf1, 0xff, 0x19, 0x00, 0x7b, 0x00, 0x2d, 0x00, 0x2c, 0x01,
    0x40, 0x01, 0xf4, 0x01, 0x58, 0x02, 0x0a, 0x96, 0x55, 0x10, 0x0e, 0x58,
    0x02, 0xec, 0xff, 0xfa, 0x00};
  static const uint8_t truncated[] = {0xfe, 0x1f, 0xe8};
  static const uint8_t feature_bytes[] = {0x03, 0, 0, 0, 0x08, 0, 0, 0};
  ftms_measurement value;
  ftms_features features;
  ftms_control_request request = {FTMS_CONTROL_REQUEST_CONTROL, {0}};
  ftms_control_response response = {FTMS_CONTROL_REQUEST_CONTROL, FTMS_CONTROL_SUCCESS,
    FTMS_CONTROL_RESPONSE_NONE, 0, 0, 0, 0, 0};
  ftms_control_response decoded_response;
  uint8_t request_bytes[1];
  uint8_t response_bytes[3];
  size_t written = 0;

  if (!require_result(ftms_decode_features(feature_bytes, sizeof feature_bytes, &features),
      "Feature decode") || !(features.machine & FTMS_MACHINE_FEATURE_CADENCE) ||
      !(features.target & FTMS_TARGET_FEATURE_POWER)) return 1;
  puts("Feature declarations: cadence measurement and power target (not control permission)");

  if (!require_result(ftms_decode_measurement(FTMS_MEASUREMENT_INDOOR_BIKE, bike,
      sizeof bike, &value), "Indoor Bike decode") || value.truncated ||
      value.value[FTMS_M_POWER] != 250 || value.value[FTMS_M_CADENCE] != 180) return 1;
  puts("Indoor Bike raw values (divide speed by 100; cadence by 2):");
  print_value("speed", value.value[FTMS_M_SPEED], "0.01 km/h");
  print_value("average speed", value.value[FTMS_M_AVERAGE_SPEED], "0.01 km/h");
  print_value("cadence", value.value[FTMS_M_CADENCE], "0.5 rpm");
  print_value("average cadence", value.value[FTMS_M_AVERAGE_CADENCE], "0.5 rpm");
  print_value("distance", value.value[FTMS_M_DISTANCE], "m");
  print_value("resistance", value.value[FTMS_M_RESISTANCE], "level");
  print_value("power", value.value[FTMS_M_POWER], "W");
  print_value("average power", value.value[FTMS_M_AVERAGE_POWER], "W");
  print_value("energy", value.value[FTMS_M_TOTAL_ENERGY], "kcal");
  print_value("energy per hour", value.value[FTMS_M_ENERGY_PER_HOUR], "kcal/h");
  print_value("energy per minute", value.value[FTMS_M_ENERGY_PER_MINUTE], "kcal/min");
  print_value("heart rate", value.value[FTMS_M_HEART_RATE], "bpm");
  print_value("MET", value.value[FTMS_M_MET], "0.1 MET");
  print_value("elapsed time", value.value[FTMS_M_ELAPSED_TIME], "s");
  print_value("remaining time", value.value[FTMS_M_REMAINING_TIME], "s");

  if (!require_result(ftms_decode_measurement(FTMS_MEASUREMENT_TREADMILL, treadmill,
      sizeof treadmill, &value), "Treadmill decode") || value.truncated ||
      value.value[FTMS_M_INCLINATION] != -15 || value.value[FTMS_M_POWER] != 250) return 1;
  puts("Treadmill raw values (speed is 0.01 km/h; inclination is 0.1%):");
  print_value("speed", value.value[FTMS_M_SPEED], "0.01 km/h");
  print_value("average speed", value.value[FTMS_M_AVERAGE_SPEED], "0.01 km/h");
  print_value("distance", value.value[FTMS_M_DISTANCE], "m");
  print_value("inclination", value.value[FTMS_M_INCLINATION], "0.1 percent");
  print_value("ramp angle", value.value[FTMS_M_RAMP_ANGLE], "0.1 degree");
  print_value("positive elevation", value.value[FTMS_M_POSITIVE_ELEVATION], "0.1 m");
  print_value("negative elevation", value.value[FTMS_M_NEGATIVE_ELEVATION], "0.1 m");
  print_value("instantaneous pace", value.value[FTMS_M_INSTANTANEOUS_PACE], "s/500m");
  print_value("average pace", value.value[FTMS_M_AVERAGE_PACE], "s/500m");
  print_value("energy", value.value[FTMS_M_TOTAL_ENERGY], "kcal");
  print_value("energy per hour", value.value[FTMS_M_ENERGY_PER_HOUR], "kcal/h");
  print_value("energy per minute", value.value[FTMS_M_ENERGY_PER_MINUTE], "kcal/min");
  print_value("heart rate", value.value[FTMS_M_HEART_RATE], "bpm");
  print_value("MET", value.value[FTMS_M_MET], "0.1 MET");
  print_value("elapsed time", value.value[FTMS_M_ELAPSED_TIME], "s");
  print_value("remaining time", value.value[FTMS_M_REMAINING_TIME], "s");
  print_value("force on belt", value.value[FTMS_M_FORCE_ON_BELT], "N");
  print_value("power", value.value[FTMS_M_POWER], "W");

  if (!require_result(ftms_decode_measurement(FTMS_MEASUREMENT_INDOOR_BIKE, truncated,
      sizeof truncated, &value), "Truncated measurement decode") || !value.truncated) return 1;
  if (!require_result(ftms_encode_control_request(&request, request_bytes,
      sizeof request_bytes, &written), "Request Control encode") || written != 1 || request_bytes[0] != 0) return 1;
  if (!require_result(ftms_encode_control_response(&response, response_bytes,
      sizeof response_bytes, &written), "Response encode") || written != 3 ||
      response_bytes[0] != 0x80 || response_bytes[1] != 0 || response_bytes[2] != 1 ||
      !require_result(ftms_decode_control_response(response_bytes, written, &decoded_response),
      "Response decode") || decoded_response.result_code != FTMS_CONTROL_SUCCESS) return 1;
  puts("Request Control bytes: 0x00 (encoded only; not sent)");
  puts("Simulated Response Code bytes: 0x80 0x00 0x01 (a codec sample, not an automatic grant)");
  puts("A codec result is not BLE discovery, control ownership, security, indication, or actuator authorization.");
  return 0;
}

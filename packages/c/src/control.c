#include "ftms/control.h"

static uint16_t read_u16le(const uint8_t *bytes) {
  return (uint16_t)((uint16_t)bytes[0] | ((uint16_t)bytes[1] << 8));
}

static int16_t read_i16le(const uint8_t *bytes) {
  uint16_t value = read_u16le(bytes);
  return value <= UINT16_C(32767) ? (int16_t)value
                                  : (int16_t)((int32_t)value - INT32_C(65536));
}

static void write_u16le(uint8_t *bytes, uint16_t value) {
  bytes[0] = (uint8_t)value;
  bytes[1] = (uint8_t)(value >> 8);
}

static int is_known_opcode(uint8_t opcode) { return opcode <= UINT8_C(0x14); }

static int is_request_opcode(ftms_control_opcode opcode) {
  return opcode >= FTMS_CONTROL_REQUEST_CONTROL &&
         opcode <= FTMS_CONTROL_SET_TARGETED_CADENCE;
}

static int valid_options(const ftms_control_format_options *options) {
  return options == NULL || (unsigned)options->resistance_format <= FTMS_CONTROL_RESISTANCE_UINT8_TENTHS;
}

static size_t request_length(uint8_t opcode, const ftms_control_format_options *options) {
  if (opcode == FTMS_CONTROL_SET_TARGET_RESISTANCE && options != NULL &&
      options->resistance_format == FTMS_CONTROL_RESISTANCE_UINT8_TENTHS) return 2U;
  switch (opcode) {
    case FTMS_CONTROL_REQUEST_CONTROL:
    case FTMS_CONTROL_RESET:
    case FTMS_CONTROL_START_RESUME:
      return 1U;
    case FTMS_CONTROL_SET_TARGET_HEART_RATE:
    case FTMS_CONTROL_STOP_PAUSE:
    case FTMS_CONTROL_SPIN_DOWN:
      return 2U;
    case FTMS_CONTROL_SET_TARGETED_DISTANCE:
      return 4U;
    case FTMS_CONTROL_SET_TARGETED_TIME_TWO_HR_ZONES:
      return 5U;
    case FTMS_CONTROL_SET_TARGETED_TIME_THREE_HR_ZONES:
    case FTMS_CONTROL_SET_INDOOR_BIKE_SIMULATION:
      return 7U;
    case FTMS_CONTROL_SET_TARGETED_TIME_FIVE_HR_ZONES:
      return 11U;
    default:
      return is_known_opcode(opcode) ? 3U : 0U;
  }
}

static int is_action_value(int value) { return value == 1 || value == 2; }
static int is_result_value(uint8_t value) { return value >= 1U && value <= 5U; }

ftms_result ftms_encode_control_request_with_format(const ftms_control_request *request,
                                                     const ftms_control_format_options *options,
                                                     uint8_t *out, size_t capacity,
                                                     size_t *written) {
  uint8_t local[11] = {0U};
  size_t length;
  size_t index;

  if (request == NULL || out == NULL || written == NULL) return FTMS_ERROR_NULL;
  if (!is_request_opcode(request->opcode) || !valid_options(options)) return FTMS_ERROR_KIND;
  if (request->opcode == FTMS_CONTROL_SET_TARGET_RESISTANCE && options != NULL &&
      options->resistance_format == FTMS_CONTROL_RESISTANCE_UINT8_TENTHS &&
      (request->value.resistance_tenth_level < 0 || request->value.resistance_tenth_level > 255)) return FTMS_ERROR_RANGE;
  length = request_length((uint8_t)request->opcode, options);
  if (request->opcode == FTMS_CONTROL_STOP_PAUSE &&
      !is_action_value((int)request->value.stop_pause)) return FTMS_ERROR_RANGE;
  if (request->opcode == FTMS_CONTROL_SPIN_DOWN &&
      !is_action_value((int)request->value.spin_down)) return FTMS_ERROR_RANGE;
  if (request->opcode == FTMS_CONTROL_SET_TARGETED_DISTANCE &&
      request->value.distance_metres > UINT32_C(0x00ffffff)) return FTMS_ERROR_RANGE;
  if (capacity < length) return FTMS_ERROR_LENGTH;

  local[0] = (uint8_t)request->opcode;
  switch (request->opcode) {
    case FTMS_CONTROL_SET_TARGET_SPEED: write_u16le(local + 1U, request->value.speed_centikph); break;
    case FTMS_CONTROL_SET_TARGET_INCLINATION: write_u16le(local + 1U, (uint16_t)request->value.inclination_tenth_percent); break;
    case FTMS_CONTROL_SET_TARGET_RESISTANCE:
      if (options != NULL && options->resistance_format == FTMS_CONTROL_RESISTANCE_UINT8_TENTHS) local[1] = (uint8_t)request->value.resistance_tenth_level;
      else write_u16le(local + 1U, (uint16_t)request->value.resistance_tenth_level);
      break;
    case FTMS_CONTROL_SET_TARGET_POWER: write_u16le(local + 1U, (uint16_t)request->value.power_watts); break;
    case FTMS_CONTROL_SET_TARGET_HEART_RATE: local[1] = request->value.heart_rate_bpm; break;
    case FTMS_CONTROL_STOP_PAUSE: local[1] = (uint8_t)request->value.stop_pause; break;
    case FTMS_CONTROL_SET_TARGETED_EXPENDED_ENERGY: write_u16le(local + 1U, request->value.energy_kcal); break;
    case FTMS_CONTROL_SET_TARGETED_STEPS: write_u16le(local + 1U, request->value.steps); break;
    case FTMS_CONTROL_SET_TARGETED_STRIDES: write_u16le(local + 1U, request->value.strides); break;
    case FTMS_CONTROL_SET_TARGETED_DISTANCE:
      local[1] = (uint8_t)request->value.distance_metres;
      local[2] = (uint8_t)(request->value.distance_metres >> 8);
      local[3] = (uint8_t)(request->value.distance_metres >> 16);
      break;
    case FTMS_CONTROL_SET_TARGETED_TRAINING_TIME: write_u16le(local + 1U, request->value.training_seconds); break;
    case FTMS_CONTROL_SET_TARGETED_TIME_TWO_HR_ZONES:
    case FTMS_CONTROL_SET_TARGETED_TIME_THREE_HR_ZONES:
    case FTMS_CONTROL_SET_TARGETED_TIME_FIVE_HR_ZONES:
      for (index = 0U; index < (length - 1U) / 2U; ++index) write_u16le(local + 1U + index * 2U, request->value.zone_seconds[index]);
      break;
    case FTMS_CONTROL_SET_INDOOR_BIKE_SIMULATION:
      write_u16le(local + 1U, (uint16_t)request->value.simulation.wind_millimetres_per_second);
      write_u16le(local + 3U, (uint16_t)request->value.simulation.grade_hundredth_percent);
      local[5] = request->value.simulation.crr_ten_thousandth;
      local[6] = request->value.simulation.cw_hundredth_kg_per_m;
      break;
    case FTMS_CONTROL_SET_WHEEL_CIRCUMFERENCE: write_u16le(local + 1U, request->value.wheel_circumference_tenth_mm); break;
    case FTMS_CONTROL_SPIN_DOWN: local[1] = (uint8_t)request->value.spin_down; break;
    case FTMS_CONTROL_SET_TARGETED_CADENCE: write_u16le(local + 1U, request->value.cadence_half_rpm); break;
    default: break;
  }
  for (index = 0U; index < length; ++index) out[index] = local[index];
  *written = length;
  return FTMS_OK;
}

ftms_result ftms_encode_control_request(const ftms_control_request *request,
                                         uint8_t *out, size_t capacity,
                                         size_t *written) {
  return ftms_encode_control_request_with_format(request, NULL, out, capacity, written);
}

ftms_result ftms_decode_control_request_with_format(const uint8_t *data, size_t size,
                                                     const ftms_control_format_options *options,
                                                     ftms_control_request *out) {
  ftms_control_request local = {0};
  size_t length;
  size_t index;
  if (!valid_options(options)) return FTMS_ERROR_KIND;
  if (data == NULL || out == NULL) return FTMS_ERROR_NULL;
  if (size < 1U) return FTMS_ERROR_LENGTH;
  if (!is_known_opcode(data[0])) return FTMS_ERROR_KIND;
  length = request_length(data[0], options);
  if (size != length) return FTMS_ERROR_LENGTH;
  local.opcode = (ftms_control_opcode)data[0];
  switch (data[0]) {
    case 2: local.value.speed_centikph = read_u16le(data + 1U); break;
    case 3: local.value.inclination_tenth_percent = read_i16le(data + 1U); break;
    case 4: local.value.resistance_tenth_level = options != NULL && options->resistance_format == FTMS_CONTROL_RESISTANCE_UINT8_TENTHS ? (int16_t)data[1] : read_i16le(data + 1U); break;
    case 5: local.value.power_watts = read_i16le(data + 1U); break;
    case 6: local.value.heart_rate_bpm = data[1]; break;
    case 8: if (!is_action_value((int)data[1])) return FTMS_ERROR_RANGE; local.value.stop_pause = (ftms_stop_pause_action)data[1]; break;
    case 9: local.value.energy_kcal = read_u16le(data + 1U); break;
    case 10: local.value.steps = read_u16le(data + 1U); break;
    case 11: local.value.strides = read_u16le(data + 1U); break;
    case 12: local.value.distance_metres = (uint32_t)data[1] | ((uint32_t)data[2] << 8) | ((uint32_t)data[3] << 16); break;
    case 13: local.value.training_seconds = read_u16le(data + 1U); break;
    case 14: case 15: case 16: for (index = 0U; index < (length - 1U) / 2U; ++index) local.value.zone_seconds[index] = read_u16le(data + 1U + index * 2U); break;
    case 17: local.value.simulation.wind_millimetres_per_second = read_i16le(data + 1U); local.value.simulation.grade_hundredth_percent = read_i16le(data + 3U); local.value.simulation.crr_ten_thousandth = data[5]; local.value.simulation.cw_hundredth_kg_per_m = data[6]; break;
    case 18: local.value.wheel_circumference_tenth_mm = read_u16le(data + 1U); break;
    case 19: if (!is_action_value((int)data[1])) return FTMS_ERROR_RANGE; local.value.spin_down = (ftms_spin_down_action)data[1]; break;
    case 20: local.value.cadence_half_rpm = read_u16le(data + 1U); break;
    default: break;
  }
  *out = local;
  return FTMS_OK;
}

ftms_result ftms_decode_control_request(const uint8_t *data, size_t size,
                                         ftms_control_request *out) {
  return ftms_decode_control_request_with_format(data, size, NULL, out);
}

ftms_result ftms_encode_control_response(const ftms_control_response *response,
                                         uint8_t *out, size_t capacity,
                                         size_t *written) {
  uint8_t local[7] = {0U};
  size_t length;
  size_t index;
  if (response == NULL || out == NULL || written == NULL) return FTMS_ERROR_NULL;
  if (!is_result_value(response->result_code)) return FTMS_ERROR_RANGE;
  if (!is_known_opcode(response->request_opcode) && response->result_code != FTMS_CONTROL_NOT_SUPPORTED) return FTMS_ERROR_KIND;
  if (response->parameter == FTMS_CONTROL_RESPONSE_NONE) length = 3U;
  else if (response->parameter == FTMS_CONTROL_RESPONSE_SPIN_DOWN_SPEEDS && response->request_opcode == FTMS_CONTROL_SPIN_DOWN && response->result_code == FTMS_CONTROL_SUCCESS) length = 7U;
  else return FTMS_ERROR_RANGE;
  if (capacity < length) return FTMS_ERROR_LENGTH;
  local[0] = UINT8_C(0x80); local[1] = response->request_opcode; local[2] = response->result_code;
  if (length == 7U) { write_u16le(local + 3U, response->spin_down_low_centikph); write_u16le(local + 5U, response->spin_down_high_centikph); }
  for (index = 0U; index < length; ++index) out[index] = local[index];
  *written = length;
  return FTMS_OK;
}

ftms_result ftms_decode_control_response(const uint8_t *data, size_t size,
                                         ftms_control_response *out) {
  ftms_control_response local = {0};
  if (data == NULL || out == NULL) return FTMS_ERROR_NULL;
  if (size < 3U) return FTMS_ERROR_LENGTH;
  if (data[0] != UINT8_C(0x80)) return FTMS_ERROR_KIND;
  local.request_opcode = data[1]; local.result_code = data[2];
  local.unknown_request = (uint8_t)!is_known_opcode(data[1]);
  local.unknown_result = (uint8_t)!is_result_value(data[2]);
  if (size == 3U) { *out = local; return FTMS_OK; }
  if (data[1] == FTMS_CONTROL_SPIN_DOWN && data[2] == FTMS_CONTROL_SUCCESS) {
    if (size != 7U) return FTMS_ERROR_LENGTH;
    local.parameter = FTMS_CONTROL_RESPONSE_SPIN_DOWN_SPEEDS;
    local.spin_down_low_centikph = read_u16le(data + 3U);
    local.spin_down_high_centikph = read_u16le(data + 5U);
  } else local.unexpected_parameters = 1U;
  *out = local;
  return FTMS_OK;
}

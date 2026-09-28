#include "ftms/status.h"

static uint16_t read_u16le(const uint8_t *p) {
  return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}
static int16_t read_i16le(const uint8_t *p) {
  uint16_t v = read_u16le(p);
  return v <= UINT16_C(32767) ? (int16_t)v : (int16_t)((int32_t)v - INT32_C(65536));
}
static void write_u16le(uint8_t *p, uint16_t v) {
  p[0] = (uint8_t)v;
  p[1] = (uint8_t)(v >> 8);
}
static int valid_utf8(const uint8_t *p, size_t n) {
  size_t i = 0U;
  while (i < n) {
    uint8_t a = p[i++];
    unsigned need;
    if (a < 0x80U) continue;
    if (a >= 0xc2U && a <= 0xdfU) need = 1U;
    else if (a >= 0xe0U && a <= 0xefU) need = 2U;
    else if (a >= 0xf0U && a <= 0xf4U) need = 3U;
    else return 0;
    if (n - i < (size_t)need) return 0;
    if ((need == 2U && ((a == 0xe0U && p[i] < 0xa0U) ||
                        (a == 0xedU && p[i] > 0x9fU))) ||
        (need == 3U && ((a == 0xf0U && p[i] < 0x90U) ||
                        (a == 0xf4U && p[i] > 0x8fU)))) return 0;
    while (need-- != 0U) if ((p[i++] & 0xc0U) != 0x80U) return 0;
  }
  return 1;
}
static size_t machine_length(uint8_t code) {
  switch (code) {
    case 0x01: case 0x03: case 0x04: case 0xff: return 1U;
    case 0x02: case 0x09: case 0x14: return 2U;
    case 0x0d: return 4U;
    case 0x0f: return 5U;
    case 0x10: case 0x12: return 7U;
    case 0x11: return 11U;
    default: return (code >= 0x05U && code <= 0x08U) ||
                    (code >= 0x0aU && code <= 0x0cU) ||
                    code == 0x0eU || code == 0x13U || code == 0x15U ? 3U : 0U;
  }
}
static int known_machine(uint8_t code) { return machine_length(code) != 0U; }
static int canonical_machine(uint8_t code) { return known_machine(code); }
static int valid_stop(uint8_t v) { return v == 1U || v == 2U; }
static int valid_spin_status(uint8_t v) { return v >= 1U && v <= 4U; }

static void decode_parameter(uint8_t code, const uint8_t *p, ftms_machine_status *s) {
  ftms_control_request *r = &s->parameter;
  s->parameter_present = 1U;
  if (code >= 0x05U && code <= 0x09U) r->opcode = (ftms_control_opcode)(code - 3U);
  else if (code >= 0x0aU && code <= 0x13U) r->opcode = (ftms_control_opcode)(code - 1U);
  else if (code == 0x15U) r->opcode = FTMS_CONTROL_SET_TARGETED_CADENCE;
  switch (code) {
    case 0x02: s->action = p[1]; s->reserved_value = (uint8_t)!valid_stop(p[1]); s->parameter_present = 0U; break;
    case 0x05: r->value.speed_centikph = read_u16le(p + 1U); break;
    case 0x06: r->value.inclination_tenth_percent = read_i16le(p + 1U); break;
    case 0x07: r->value.resistance_tenth_level = read_i16le(p + 1U); break;
    case 0x08: r->value.power_watts = read_i16le(p + 1U); break;
    case 0x09: r->value.heart_rate_bpm = p[1]; break;
    case 0x0a: r->value.energy_kcal = read_u16le(p + 1U); break;
    case 0x0b: r->value.steps = read_u16le(p + 1U); break;
    case 0x0c: r->value.strides = read_u16le(p + 1U); break;
    case 0x0d: r->value.distance_metres = (uint32_t)p[1] | ((uint32_t)p[2] << 8) | ((uint32_t)p[3] << 16); break;
    case 0x0e: r->value.training_seconds = read_u16le(p + 1U); break;
    case 0x0f: case 0x10: case 0x11: { size_t i; for (i = 0U; i < (machine_length(code) - 1U) / 2U; ++i) r->value.zone_seconds[i] = read_u16le(p + 1U + i * 2U); break; }
    case 0x12: r->value.simulation.wind_millimetres_per_second = read_i16le(p + 1U); r->value.simulation.grade_hundredth_percent = read_i16le(p + 3U); r->value.simulation.crr_ten_thousandth = p[5]; r->value.simulation.cw_hundredth_kg_per_m = p[6]; break;
    case 0x13: r->value.wheel_circumference_tenth_mm = read_u16le(p + 1U); break;
    case 0x14: s->action = p[1]; s->reserved_value = (uint8_t)!valid_spin_status(p[1]); s->parameter_present = 0U; break;
    case 0x15: r->value.cadence_half_rpm = read_u16le(p + 1U); break;
    default: s->parameter_present = 0U; break;
  }
}

ftms_result ftms_decode_machine_status(const uint8_t *data, size_t size, ftms_machine_status *out) {
  ftms_machine_status local = {0}; size_t length;
  if (data == NULL || out == NULL) return FTMS_ERROR_NULL;
  if (size == 0U) { local.truncated = 1U; local.unknown_opcode = 1U; *out = local; return FTMS_OK; }
  local.opcode = data[0]; length = machine_length(data[0]);
  if (length == 0U) { local.unknown_opcode = 1U; *out = local; return FTMS_OK; }
  if (size < length) { local.truncated = 1U; *out = local; return FTMS_OK; }
  decode_parameter(data[0], data, &local);
  local.trailing_bytes = (uint8_t)(size > length);
  *out = local;
  return FTMS_OK;
}

ftms_result ftms_encode_machine_status(const ftms_machine_status *s, uint8_t *out, size_t capacity, size_t *written) {
  uint8_t local[11] = {0U}; size_t length; size_t i;
  if (s == NULL || out == NULL || written == NULL) return FTMS_ERROR_NULL;
  if (!canonical_machine(s->opcode) || s->unknown_opcode || s->reserved_value || s->truncated || s->trailing_bytes) return FTMS_ERROR_KIND;
  length = machine_length(s->opcode);
  if ((s->opcode == 0x02U && !valid_stop(s->action)) || (s->opcode == 0x14U && !valid_spin_status(s->action))) return FTMS_ERROR_RANGE;
  if (s->opcode >= 0x05U && s->opcode <= 0x13U && !s->parameter_present) return FTMS_ERROR_RANGE;
  if (s->opcode == 0x15U && !s->parameter_present) return FTMS_ERROR_RANGE;
  if (s->parameter_present) {
    unsigned expected = s->opcode >= 0x05U && s->opcode <= 0x09U ? (unsigned)s->opcode - 3U
      : (s->opcode >= 0x0aU && s->opcode <= 0x13U) || s->opcode == 0x15U ? (unsigned)s->opcode - 1U : 256U;
    if (s->parameter_present != 1U || (unsigned)s->parameter.opcode != expected) return FTMS_ERROR_KIND;
  }
  if (s->opcode == 0x0dU && s->parameter.value.distance_metres > UINT32_C(0x00ffffff)) return FTMS_ERROR_RANGE;
  if (capacity < length) return FTMS_ERROR_LENGTH;
  local[0] = s->opcode;
  if (s->opcode == 0x02U || s->opcode == 0x14U) local[1] = s->action;
  else if (s->parameter_present) {
    switch (s->opcode) {
      case 0x05: write_u16le(local + 1U, s->parameter.value.speed_centikph); break; case 0x06: write_u16le(local + 1U, (uint16_t)s->parameter.value.inclination_tenth_percent); break;
      case 0x07: write_u16le(local + 1U, (uint16_t)s->parameter.value.resistance_tenth_level); break; case 0x08: write_u16le(local + 1U, (uint16_t)s->parameter.value.power_watts); break;
      case 0x09: local[1] = s->parameter.value.heart_rate_bpm; break; case 0x0a: write_u16le(local + 1U, s->parameter.value.energy_kcal); break;
      case 0x0b: write_u16le(local + 1U, s->parameter.value.steps); break; case 0x0c: write_u16le(local + 1U, s->parameter.value.strides); break;
      case 0x0d: local[1] = (uint8_t)s->parameter.value.distance_metres; local[2] = (uint8_t)(s->parameter.value.distance_metres >> 8); local[3] = (uint8_t)(s->parameter.value.distance_metres >> 16); break;
      case 0x0e: write_u16le(local + 1U, s->parameter.value.training_seconds); break;
      case 0x0f: case 0x10: case 0x11: for (i = 0U; i < (length - 1U) / 2U; ++i) write_u16le(local + 1U + i * 2U, s->parameter.value.zone_seconds[i]); break;
      case 0x12: write_u16le(local + 1U, (uint16_t)s->parameter.value.simulation.wind_millimetres_per_second); write_u16le(local + 3U, (uint16_t)s->parameter.value.simulation.grade_hundredth_percent); local[5] = s->parameter.value.simulation.crr_ten_thousandth; local[6] = s->parameter.value.simulation.cw_hundredth_kg_per_m; break;
      case 0x13: write_u16le(local + 1U, s->parameter.value.wheel_circumference_tenth_mm); break; case 0x15: write_u16le(local + 1U, s->parameter.value.cadence_half_rpm); break; default: break;
    }
  }
  for (i = 0U; i < length; ++i) out[i] = local[i];
  *written = length;
  return FTMS_OK;
}

ftms_result ftms_decode_training_status(const uint8_t *data, size_t size, ftms_training_status *out) {
  ftms_training_status local = {0};
  if (data == NULL || out == NULL) return FTMS_ERROR_NULL;
  if (size < 2U) {
    local.truncated = 1U;
    if (size != 0U) local.flags = data[0];
    *out = local;
    return FTMS_OK;
  }
  local.flags = data[0]; local.code = data[1]; local.text_present = (uint8_t)(data[0] & 1U); local.extended_string = (uint8_t)((data[0] >> 1) & 1U);
  local.reserved_flags = (uint8_t)(data[0] & 0xfcU); local.invalid_flags = (uint8_t)(local.extended_string && !local.text_present); local.reserved_value = (uint8_t)(data[1] > 0x0fU);
  if (local.text_present) { local.text_offset = 2U; local.text_size = size - 2U; local.invalid_utf8 = (uint8_t)!valid_utf8(data + 2U, local.text_size); }
  else local.trailing_bytes = (uint8_t)(size > 2U);
  *out = local; return FTMS_OK;
}

ftms_result ftms_encode_training_status(const ftms_training_status *s, const uint8_t *text, size_t text_size, uint8_t *out, size_t capacity, size_t *written) {
  size_t length; size_t i;
  uint8_t flags, code;
  if (s == NULL || out == NULL || written == NULL || (text_size != 0U && text == NULL)) return FTMS_ERROR_NULL;
  if (s->code > 0x0fU || (s->flags & 0xfcU) != 0U || ((s->flags & 2U) != 0U && (s->flags & 1U) == 0U)) return FTMS_ERROR_RANGE;
  if (s->truncated || s->reserved_flags || s->reserved_value || s->invalid_flags || s->invalid_utf8 || s->trailing_bytes) return FTMS_ERROR_RANGE;
  if ((s->flags & 1U) == 0U && text_size != 0U) return FTMS_ERROR_RANGE;
  if (text_size > SIZE_MAX - 2U) return FTMS_ERROR_LENGTH;
  length = 2U + (((s->flags & 1U) != 0U) ? text_size : 0U);
  if (capacity < length) return FTMS_ERROR_LENGTH;
  if ((s->flags & 1U) != 0U && !valid_utf8(text, text_size)) return FTMS_ERROR_RANGE;
  flags = s->flags; code = s->code;
  out[0] = flags;
  out[1] = code;
  for (i = 0U; i < text_size; ++i) out[2U + i] = text[i];
  *written = length;
  return FTMS_OK;
}

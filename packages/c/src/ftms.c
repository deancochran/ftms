#include "ftms/ftms.h"

static uint16_t read_u16le(const uint8_t *bytes) {
  return (uint16_t)((uint16_t)bytes[0] | ((uint16_t)bytes[1] << 8));
}

static uint32_t read_u32le(const uint8_t *bytes) {
  return (uint32_t)bytes[0] | ((uint32_t)bytes[1] << 8) |
         ((uint32_t)bytes[2] << 16) | ((uint32_t)bytes[3] << 24);
}

static void write_u16le(uint8_t *bytes, uint16_t value) {
  bytes[0] = (uint8_t)value;
  bytes[1] = (uint8_t)(value >> 8);
}

static void write_u32le(uint8_t *bytes, uint32_t value) {
  bytes[0] = (uint8_t)value;
  bytes[1] = (uint8_t)(value >> 8);
  bytes[2] = (uint8_t)(value >> 16);
  bytes[3] = (uint8_t)(value >> 24);
}

static int32_t signed_u16(uint16_t value) {
  if (value <= UINT16_C(32767)) {
    return (int32_t)value;
  }
  return (int32_t)value - INT32_C(65536);
}

ftms_result ftms_decode_features(const uint8_t *data, size_t size,
                                 ftms_features *out) {
  ftms_features local;

  if (out == NULL || data == NULL) {
    return FTMS_ERROR_NULL;
  }
  if (size != 8U) {
    return FTMS_ERROR_LENGTH;
  }
  local.machine = read_u32le(data);
  local.target = read_u32le(data + 4U);
  *out = local;
  return FTMS_OK;
}

ftms_result ftms_decode_range(ftms_range_kind kind, const uint8_t *data,
                              size_t size, ftms_range *out) {
  ftms_range local;
  size_t expected_size;

  switch (kind) {
    case FTMS_RANGE_SPEED:
    case FTMS_RANGE_INCLINATION:
    case FTMS_RANGE_POWER:
      expected_size = 6U;
      break;
    case FTMS_RANGE_RESISTANCE_LEVEL:
    case FTMS_RANGE_HEART_RATE:
      expected_size = 3U;
      break;
    default:
      return FTMS_ERROR_KIND;
  }
  if (out == NULL || data == NULL) {
    return FTMS_ERROR_NULL;
  }
  if (size != expected_size) {
    return FTMS_ERROR_LENGTH;
  }

  local.kind = kind;
  if (expected_size == 6U) {
    uint16_t minimum = read_u16le(data);
    uint16_t maximum = read_u16le(data + 2U);
    uint16_t increment = read_u16le(data + 4U);

    if (kind == FTMS_RANGE_INCLINATION || kind == FTMS_RANGE_POWER) {
      local.minimum = signed_u16(minimum);
      local.maximum = signed_u16(maximum);
    } else {
      local.minimum = (int32_t)minimum;
      local.maximum = (int32_t)maximum;
    }
    local.increment = (int32_t)increment;
  } else {
    local.minimum = (int32_t)data[0];
    local.maximum = (int32_t)data[1];
    local.increment = (int32_t)data[2];
  }
  if (local.minimum > local.maximum || local.increment == 0) {
    return FTMS_ERROR_RANGE;
  }

  switch (kind) {
    case FTMS_RANGE_SPEED:
      local.scale_divisor = 100U;
      local.unit = FTMS_UNIT_KILOMETRES_PER_HOUR;
      break;
    case FTMS_RANGE_INCLINATION:
      local.scale_divisor = 10U;
      local.unit = FTMS_UNIT_PERCENT;
      break;
    case FTMS_RANGE_RESISTANCE_LEVEL:
      local.scale_divisor = 1U;
      local.unit = FTMS_UNIT_LEVEL;
      break;
    case FTMS_RANGE_HEART_RATE:
      local.scale_divisor = 1U;
      local.unit = FTMS_UNIT_BEATS_PER_MINUTE;
      break;
    case FTMS_RANGE_POWER:
      local.scale_divisor = 1U;
      local.unit = FTMS_UNIT_WATTS;
      break;
    default:
      return FTMS_ERROR_KIND;
  }
  *out = local;
  return FTMS_OK;
}

ftms_result ftms_encode_features(const ftms_features *features, uint8_t *out,
                                 size_t capacity, size_t *written) {
  ftms_features local;
  uint8_t staged[8];

  if (features == NULL || out == NULL || written == NULL) {
    return FTMS_ERROR_NULL;
  }
  if (capacity < sizeof staged) {
    return FTMS_ERROR_LENGTH;
  }
  local = *features;
  write_u32le(staged, local.machine);
  write_u32le(staged + 4U, local.target);
  out[0] = staged[0]; out[1] = staged[1]; out[2] = staged[2]; out[3] = staged[3];
  out[4] = staged[4]; out[5] = staged[5]; out[6] = staged[6]; out[7] = staged[7];
  *written = sizeof staged;
  return FTMS_OK;
}

ftms_result ftms_encode_range(const ftms_range *range, uint8_t *out,
                              size_t capacity, size_t *written) {
  ftms_range local;
  uint8_t staged[6];
  size_t required;
  int signed_values;

  if (range == NULL || out == NULL || written == NULL) {
    return FTMS_ERROR_NULL;
  }
  local = *range;
  switch (local.kind) {
    case FTMS_RANGE_SPEED:
      required = 6U; signed_values = 0;
      if (local.scale_divisor != 100U || local.unit != FTMS_UNIT_KILOMETRES_PER_HOUR) return FTMS_ERROR_RANGE;
      break;
    case FTMS_RANGE_INCLINATION:
      required = 6U; signed_values = 1;
      if (local.scale_divisor != 10U || local.unit != FTMS_UNIT_PERCENT) return FTMS_ERROR_RANGE;
      break;
    case FTMS_RANGE_RESISTANCE_LEVEL:
      required = 3U; signed_values = 0;
      if (local.scale_divisor != 1U || local.unit != FTMS_UNIT_LEVEL) return FTMS_ERROR_RANGE;
      break;
    case FTMS_RANGE_HEART_RATE:
      required = 3U; signed_values = 0;
      if (local.scale_divisor != 1U || local.unit != FTMS_UNIT_BEATS_PER_MINUTE) return FTMS_ERROR_RANGE;
      break;
    case FTMS_RANGE_POWER:
      required = 6U; signed_values = 1;
      if (local.scale_divisor != 1U || local.unit != FTMS_UNIT_WATTS) return FTMS_ERROR_RANGE;
      break;
    default:
      return FTMS_ERROR_KIND;
  }
  if (local.minimum > local.maximum || local.increment <= 0) return FTMS_ERROR_RANGE;
  if (signed_values) {
    if (local.minimum < -32768 || local.minimum > 32767 || local.maximum < -32768 || local.maximum > 32767) return FTMS_ERROR_RANGE;
  } else if (local.minimum < 0 || local.minimum > (required == 3U ? 255 : 65535) ||
             local.maximum < 0 || local.maximum > (required == 3U ? 255 : 65535)) {
    return FTMS_ERROR_RANGE;
  }
  if (local.increment > (required == 3U ? 255 : 65535)) return FTMS_ERROR_RANGE;
  if (capacity < required) return FTMS_ERROR_LENGTH;
  if (required == 3U) {
    staged[0] = (uint8_t)local.minimum;
    staged[1] = (uint8_t)local.maximum;
    staged[2] = (uint8_t)local.increment;
  } else {
    write_u16le(staged, (uint16_t)local.minimum);
    write_u16le(staged + 2U, (uint16_t)local.maximum);
    write_u16le(staged + 4U, (uint16_t)local.increment);
  }
  out[0] = staged[0]; out[1] = staged[1]; out[2] = staged[2];
  if (required == 6U) { out[3] = staged[3]; out[4] = staged[4]; out[5] = staged[5]; }
  *written = required;
  return FTMS_OK;
}

ftms_result ftms_decode_range_with_format(ftms_range_kind kind, const uint8_t *data,
                                          size_t size,
                                          const ftms_range_format_options *options,
                                          ftms_range *out) {
  ftms_range local;
  if (options == NULL || options->resistance_format == FTMS_RESISTANCE_RANGE_UINT8_WHOLE)
    return ftms_decode_range(kind, data, size, out);
  if (options->resistance_format != FTMS_RESISTANCE_RANGE_SINT16_TENTHS) return FTMS_ERROR_KIND;
  if (kind != FTMS_RANGE_RESISTANCE_LEVEL) return FTMS_ERROR_KIND;
  if (data == NULL || out == NULL) return FTMS_ERROR_NULL;
  if (size != 6U) return FTMS_ERROR_LENGTH;
  local.kind = kind; local.minimum = signed_u16(read_u16le(data));
  local.maximum = signed_u16(read_u16le(data + 2U));
  local.increment = (int32_t)read_u16le(data + 4U);
  local.scale_divisor = 10U; local.unit = FTMS_UNIT_LEVEL;
  if (local.minimum > local.maximum || local.increment == 0) return FTMS_ERROR_RANGE;
  *out = local; return FTMS_OK;
}

ftms_result ftms_encode_range_with_format(const ftms_range *range,
                                          const ftms_range_format_options *options,
                                          uint8_t *out, size_t capacity,
                                          size_t *written) {
  uint8_t staged[6];
  if (options == NULL || options->resistance_format == FTMS_RESISTANCE_RANGE_UINT8_WHOLE)
    return ftms_encode_range(range, out, capacity, written);
  if (options->resistance_format != FTMS_RESISTANCE_RANGE_SINT16_TENTHS) return FTMS_ERROR_KIND;
  if (range == NULL || out == NULL || written == NULL) return FTMS_ERROR_NULL;
  if (range->kind != FTMS_RANGE_RESISTANCE_LEVEL) return FTMS_ERROR_KIND;
  if (range->scale_divisor != 10U || range->unit != FTMS_UNIT_LEVEL ||
      range->minimum < -32768 || range->minimum > 32767 ||
      range->maximum < -32768 || range->maximum > 32767 ||
      range->increment < 1 || range->increment > 65535 ||
      range->minimum > range->maximum) return FTMS_ERROR_RANGE;
  if (capacity < 6U) return FTMS_ERROR_LENGTH;
  write_u16le(staged, (uint16_t)range->minimum);
  write_u16le(staged + 2U, (uint16_t)range->maximum);
  write_u16le(staged + 4U, (uint16_t)range->increment);
  out[0] = staged[0]; out[1] = staged[1]; out[2] = staged[2];
  out[3] = staged[3]; out[4] = staged[4]; out[5] = staged[5]; *written = 6U;
  return FTMS_OK;
}

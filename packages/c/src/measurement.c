#include "ftms/measurement.h"

typedef struct field_def { uint8_t bit, width, field, signed_value, unavailable; } field_def;
typedef struct kind_def { uint8_t flag_bytes; uint32_t valid; const field_def *fields; size_t count; } kind_def;
#define F(b,w,x,s,u) {b,w,FTMS_M_##x,s,u}
/* A repeated bit deliberately keeps paired/group fields simultaneous. */
static const field_def treadmill[] = {F(0,2,SPEED,0,0),F(1,2,AVERAGE_SPEED,0,0),F(2,3,DISTANCE,0,0),F(3,2,INCLINATION,1,1),F(3,2,RAMP_ANGLE,1,1),F(4,2,POSITIVE_ELEVATION,0,0),F(4,2,NEGATIVE_ELEVATION,0,0),F(5,2,INSTANTANEOUS_PACE,0,0),F(6,2,AVERAGE_PACE,0,0),F(7,2,TOTAL_ENERGY,0,1),F(7,2,ENERGY_PER_HOUR,0,1),F(7,1,ENERGY_PER_MINUTE,0,1),F(8,1,HEART_RATE,0,0),F(9,1,MET,0,0),F(10,2,ELAPSED_TIME,0,0),F(11,2,REMAINING_TIME,0,0),F(12,2,FORCE_ON_BELT,1,1),F(12,2,POWER,1,1)};
static const field_def cross[] = {F(0,2,SPEED,0,0),F(1,2,AVERAGE_SPEED,0,0),F(2,3,DISTANCE,0,0),F(3,2,STEP_RATE,0,1),F(3,2,AVERAGE_STEP_RATE,0,1),F(4,2,STRIDE_COUNT,0,0),F(5,2,POSITIVE_ELEVATION,0,0),F(5,2,NEGATIVE_ELEVATION,0,0),F(6,2,INCLINATION,1,1),F(6,2,RAMP_ANGLE,1,1),F(7,1,RESISTANCE,0,0),F(8,2,POWER,1,0),F(9,2,AVERAGE_POWER,1,0),F(10,2,TOTAL_ENERGY,0,1),F(10,2,ENERGY_PER_HOUR,0,1),F(10,1,ENERGY_PER_MINUTE,0,1),F(11,1,HEART_RATE,0,0),F(12,1,MET,0,0),F(13,2,ELAPSED_TIME,0,0),F(14,2,REMAINING_TIME,0,0)};
static const field_def step[] = {F(0,2,FLOOR_COUNT,0,0),F(0,2,STEP_COUNT,0,0),F(1,2,STEP_RATE,0,0),F(2,2,AVERAGE_STEP_RATE,0,0),F(3,2,POSITIVE_ELEVATION,0,0),F(4,2,TOTAL_ENERGY,0,1),F(4,2,ENERGY_PER_HOUR,0,1),F(4,1,ENERGY_PER_MINUTE,0,1),F(5,1,HEART_RATE,0,0),F(6,1,MET,0,0),F(7,2,ELAPSED_TIME,0,0),F(8,2,REMAINING_TIME,0,0)};
static const field_def stair[] = {F(0,2,FLOOR_COUNT,0,0),F(1,2,STEP_RATE,0,0),F(2,2,AVERAGE_STEP_RATE,0,0),F(3,2,POSITIVE_ELEVATION,0,0),F(4,2,STRIDE_COUNT,0,0),F(5,2,TOTAL_ENERGY,0,1),F(5,2,ENERGY_PER_HOUR,0,1),F(5,1,ENERGY_PER_MINUTE,0,1),F(6,1,HEART_RATE,0,0),F(7,1,MET,0,0),F(8,2,ELAPSED_TIME,0,0),F(9,2,REMAINING_TIME,0,0)};
static const field_def rower[] = {F(0,1,STROKE_RATE,0,0),F(0,2,STROKE_COUNT,0,0),F(1,1,AVERAGE_STROKE_RATE,0,0),F(2,3,DISTANCE,0,0),F(3,2,INSTANTANEOUS_PACE,0,0),F(4,2,AVERAGE_PACE,0,0),F(5,2,POWER,1,0),F(6,2,AVERAGE_POWER,1,0),F(7,1,RESISTANCE,0,0),F(8,2,TOTAL_ENERGY,0,1),F(8,2,ENERGY_PER_HOUR,0,1),F(8,1,ENERGY_PER_MINUTE,0,1),F(9,1,HEART_RATE,0,0),F(10,1,MET,0,0),F(11,2,ELAPSED_TIME,0,0),F(12,2,REMAINING_TIME,0,0)};
static const field_def bike[] = {F(0,2,SPEED,0,0),F(1,2,AVERAGE_SPEED,0,0),F(2,2,CADENCE,0,0),F(3,2,AVERAGE_CADENCE,0,0),F(4,3,DISTANCE,0,0),F(5,1,RESISTANCE,0,0),F(6,2,POWER,1,0),F(7,2,AVERAGE_POWER,1,0),F(8,2,TOTAL_ENERGY,0,1),F(8,2,ENERGY_PER_HOUR,0,1),F(8,1,ENERGY_PER_MINUTE,0,1),F(9,1,HEART_RATE,0,0),F(10,1,MET,0,0),F(11,2,ELAPSED_TIME,0,0),F(12,2,REMAINING_TIME,0,0)};
static const kind_def defs[]={{2,0x1fff,treadmill,sizeof treadmill/sizeof *treadmill},{3,0xffff,cross,sizeof cross/sizeof *cross},{2,0x01ff,step,sizeof step/sizeof *step},{2,0x03ff,stair,sizeof stair/sizeof *stair},{2,0x1fff,rower,sizeof rower/sizeof *rower},{2,0x1fff,bike,sizeof bike/sizeof *bike}};
static uint32_t get(const uint8_t *p,uint8_t n){uint32_t v=0;uint8_t i;for(i=0;i<n;i++)v|=(uint32_t)p[i]<<(8U*i);return v;}
static void put(uint8_t *p,uint8_t n,uint32_t v){uint8_t i;for(i=0;i<n;i++)p[i]=(uint8_t)(v>>(8U*i));}
static int valid(ftms_measurement_kind k) { return (unsigned)k < 6U; }
static int mandatory(const field_def *f){return f->bit==0;}
static int valid_options(const ftms_measurement_format_options *options) {
  return options == NULL || ((unsigned)options->resistance_format <= FTMS_MEASUREMENT_RESISTANCE_SINT16_TENTHS &&
    (unsigned)options->treadmill_pace_format <= FTMS_TREADMILL_PACE_UINT8_LEGACY);
}

ftms_result ftms_measurement_kind_from_uuid16(uint16_t uuid16,
                                              ftms_measurement_kind *out) {
  ftms_measurement_kind kind;
  if (out == NULL) return FTMS_ERROR_NULL;
  switch (uuid16) {
    case FTMS_UUID16_TREADMILL_DATA: kind = FTMS_MEASUREMENT_TREADMILL; break;
    case FTMS_UUID16_CROSS_TRAINER_DATA: kind = FTMS_MEASUREMENT_CROSS_TRAINER; break;
    case FTMS_UUID16_STEP_CLIMBER_DATA: kind = FTMS_MEASUREMENT_STEP_CLIMBER; break;
    case FTMS_UUID16_STAIR_CLIMBER_DATA: kind = FTMS_MEASUREMENT_STAIR_CLIMBER; break;
    case FTMS_UUID16_ROWER_DATA: kind = FTMS_MEASUREMENT_ROWER; break;
    case FTMS_UUID16_INDOOR_BIKE_DATA: kind = FTMS_MEASUREMENT_INDOOR_BIKE; break;
    default: return FTMS_ERROR_KIND;
  }
  *out = kind;
  return FTMS_OK;
}
static field_def formatted_field(ftms_measurement_kind kind, field_def field,
                                 const ftms_measurement_format_options *options) {
  if (options != NULL && field.field == FTMS_M_RESISTANCE &&
      (kind == FTMS_MEASUREMENT_CROSS_TRAINER || kind == FTMS_MEASUREMENT_ROWER || kind == FTMS_MEASUREMENT_INDOOR_BIKE) &&
      options->resistance_format == FTMS_MEASUREMENT_RESISTANCE_SINT16_TENTHS) { field.width = 2U; field.signed_value = 1U; }
  if (options != NULL && kind == FTMS_MEASUREMENT_TREADMILL &&
      (field.field == FTMS_M_INSTANTANEOUS_PACE || field.field == FTMS_M_AVERAGE_PACE) &&
      options->treadmill_pace_format == FTMS_TREADMILL_PACE_UINT8_LEGACY) field.width = 1U;
  return field;
}
static uint32_t sentinel(const field_def *field) {
  if (field->signed_value) return UINT32_C(0x7fff);
  return field->width == 1U ? UINT32_C(0xff) : UINT32_C(0xffff);
}

static int selected(const ftms_measurement *measurement, const field_def *field) {
  if (mandatory(field)) return (measurement->flags & 1U) == 0U;
  return (measurement->flags & (UINT32_C(1) << field->bit)) != 0U;
}

ftms_result ftms_decode_measurement_with_format(ftms_measurement_kind kind, const uint8_t *data, size_t size, const ftms_measurement_format_options *options, ftms_measurement *out) {
  const kind_def *definition; ftms_measurement decoded = {0}; size_t offset, index;
  if (!valid(kind) || !valid_options(options)) return FTMS_ERROR_KIND;
  if (data == NULL || out == NULL) return FTMS_ERROR_NULL;
  definition = &defs[(unsigned)kind];
  if (size < definition->flag_bytes) return FTMS_ERROR_LENGTH;
  decoded.kind = kind; decoded.flags = get(data, definition->flag_bytes);
  decoded.more_data = (uint8_t)(decoded.flags & 1U);
  decoded.backward = (uint8_t)(kind == FTMS_MEASUREMENT_CROSS_TRAINER &&
                               ((decoded.flags & UINT32_C(0x8000)) != 0U));
  decoded.reserved_flags = (uint8_t)((decoded.flags & ~definition->valid) != 0U);
  offset = definition->flag_bytes;
  for (index = 0U; index < definition->count; ++index) {
    field_def changed, *field = &changed; uint32_t raw;
    changed = formatted_field(kind, definition->fields[index], options);
    if (!selected(&decoded, field)) continue;
    if (offset + field->width > size) { decoded.truncated = 1U; decoded.bytes_read = offset; *out = decoded; return FTMS_OK; }
    raw = get(data + offset, field->width); offset += field->width;
    decoded.present |= UINT64_C(1) << field->field;
    if (field->unavailable && raw == sentinel(field)) decoded.unavailable |= UINT64_C(1) << field->field;
    else if (field->signed_value && raw > UINT32_C(0x7fff)) decoded.value[field->field] = (int32_t)raw - INT32_C(65536);
    else decoded.value[field->field] = (int32_t)raw;
  }
  decoded.bytes_read = offset; decoded.trailing_bytes = (uint8_t)(offset < size); *out = decoded;
  return FTMS_OK;
}

ftms_result ftms_encode_measurement_with_format(const ftms_measurement *measurement, const ftms_measurement_format_options *options, uint8_t *out, size_t capacity, size_t *written) {
  const kind_def *definition; uint8_t local[64] = {0}; uint64_t required = 0U;
  size_t offset, index, byte;
  if (measurement == NULL || out == NULL || written == NULL) return FTMS_ERROR_NULL;
  if (!valid(measurement->kind) || !valid_options(options)) return FTMS_ERROR_KIND;
  definition = &defs[(unsigned)measurement->kind];
  if ((measurement->flags & ~definition->valid) != 0U ||
      (measurement->unavailable & ~measurement->present) != 0U) return FTMS_ERROR_RANGE;
  for (index = 0U; index < definition->count; ++index) if (selected(measurement, &definition->fields[index])) required |= UINT64_C(1) << definition->fields[index].field;
  if (measurement->present != required) return FTMS_ERROR_RANGE;
  put(local, definition->flag_bytes, measurement->flags); offset = definition->flag_bytes;
  for (index = 0U; index < definition->count; ++index) {
    field_def changed, *field = &changed; uint64_t bit; int32_t value;
    changed = formatted_field(measurement->kind, definition->fields[index], options);
    bit = UINT64_C(1) << field->field;
    if (!selected(measurement, field)) continue;
    if (sizeof local - offset < field->width) return FTMS_ERROR_LENGTH;
    value = measurement->value[field->field];
    if ((measurement->unavailable & bit) != 0U) { if (!field->unavailable) return FTMS_ERROR_RANGE; put(local + offset, field->width, sentinel(field)); }
    else {
      uint32_t maximum = field->width == 1U ? UINT32_C(255)
        : field->width == 2U ? UINT32_C(65535) : UINT32_C(0xffffff);
      if (field->signed_value && (value < INT32_C(-32768) || value > INT32_C(32767))) return FTMS_ERROR_RANGE;
      if (!field->signed_value && (value < 0 || (uint32_t)value > maximum)) return FTMS_ERROR_RANGE;
      if (field->unavailable && (uint32_t)value == sentinel(field)) return FTMS_ERROR_RANGE;
      put(local + offset, field->width, (uint32_t)value);
    }
    offset += field->width;
  }
  if (offset > sizeof local || capacity < offset) return FTMS_ERROR_LENGTH;
  for (byte = 0U; byte < offset; ++byte) out[byte] = local[byte];
  *written = offset;
  return FTMS_OK;
}

ftms_result ftms_decode_measurement(ftms_measurement_kind kind, const uint8_t *data, size_t size, ftms_measurement *out) { return ftms_decode_measurement_with_format(kind, data, size, NULL, out); }
ftms_result ftms_encode_measurement(const ftms_measurement *measurement, uint8_t *out, size_t capacity, size_t *written) { return ftms_encode_measurement_with_format(measurement, NULL, out, capacity, written); }

ftms_result ftms_decode_measurement_view(ftms_measurement_kind kind,
                                         const uint8_t *data, size_t size,
                                         const ftms_measurement_format_options *format,
                                         ftms_measurement_view *out) {
  ftms_measurement_view decoded = {0};
  ftms_result result;
  if (out == NULL) return FTMS_ERROR_NULL;
  if (!valid_options(format)) return FTMS_ERROR_KIND;
  if (format != NULL) decoded.format = *format;
  result = ftms_decode_measurement_with_format(kind, data, size, format, &decoded.raw);
  if (result != FTMS_OK) return result;
  *out = decoded;
  return FTMS_OK;
}

ftms_result ftms_decode_measurement_uuid16_view(uint16_t uuid16,
                                                const uint8_t *data, size_t size,
                                                const ftms_measurement_format_options *format,
                                                ftms_measurement_view *out) {
  ftms_measurement_kind kind;
  ftms_result result = ftms_measurement_kind_from_uuid16(uuid16, &kind);
  if (result != FTMS_OK) return result;
  return ftms_decode_measurement_view(kind, data, size, format, out);
}

static ftms_measurement_field metric_field(ftms_measurement_metric metric) {
  static const ftms_measurement_field fields[] = {
    FTMS_M_SPEED, FTMS_M_AVERAGE_SPEED, FTMS_M_DISTANCE, FTMS_M_INCLINATION,
    FTMS_M_RAMP_ANGLE, FTMS_M_POSITIVE_ELEVATION, FTMS_M_NEGATIVE_ELEVATION,
    FTMS_M_INSTANTANEOUS_PACE, FTMS_M_AVERAGE_PACE, FTMS_M_TOTAL_ENERGY,
    FTMS_M_ENERGY_PER_HOUR, FTMS_M_ENERGY_PER_MINUTE, FTMS_M_HEART_RATE,
    FTMS_M_MET, FTMS_M_ELAPSED_TIME, FTMS_M_REMAINING_TIME, FTMS_M_FORCE_ON_BELT,
    FTMS_M_POWER, FTMS_M_AVERAGE_POWER, FTMS_M_STEP_RATE, FTMS_M_AVERAGE_STEP_RATE,
    FTMS_M_STRIDE_COUNT, FTMS_M_RESISTANCE, FTMS_M_FLOOR_COUNT, FTMS_M_STEP_COUNT,
    FTMS_M_STROKE_RATE, FTMS_M_STROKE_COUNT, FTMS_M_AVERAGE_STROKE_RATE,
    FTMS_M_CADENCE, FTMS_M_AVERAGE_CADENCE };
  return fields[(unsigned)metric];
}

ftms_measurement_value_state ftms_measurement_metric_value(
    const ftms_measurement_view *view, ftms_measurement_metric metric,
    ftms_measurement_fixed_point *out) {
  ftms_measurement_field field; uint64_t bit; uint16_t denominator = 1U;
  if (view == NULL || !valid(view->raw.kind) || !valid_options(&view->format) ||
      (unsigned)metric > FTMS_METRIC_AVERAGE_CADENCE_RPM)
    return FTMS_MEASUREMENT_VALUE_ABSENT;
  field = metric_field(metric); bit = UINT64_C(1) << field;
  if ((view->raw.present & bit) == 0U) return FTMS_MEASUREMENT_VALUE_ABSENT;
  if ((view->raw.unavailable & bit) != 0U) return FTMS_MEASUREMENT_VALUE_UNAVAILABLE;
  if ((metric == FTMS_METRIC_INSTANTANEOUS_PACE_SECONDS_PER_500_METRES ||
       metric == FTMS_METRIC_AVERAGE_PACE_SECONDS_PER_500_METRES) &&
      view->raw.kind == FTMS_MEASUREMENT_TREADMILL &&
      view->format.treadmill_pace_format == FTMS_TREADMILL_PACE_UINT8_LEGACY)
    return FTMS_MEASUREMENT_VALUE_UNKNOWN_UNIT;
  if (metric == FTMS_METRIC_SPEED_METRES_PER_SECOND ||
      metric == FTMS_METRIC_AVERAGE_SPEED_METRES_PER_SECOND) denominator = 360U;
  else if (metric == FTMS_METRIC_INCLINATION_PERCENT ||
           metric == FTMS_METRIC_RAMP_ANGLE_DEGREES ||
           metric == FTMS_METRIC_METABOLIC_EQUIVALENT ||
           ((metric == FTMS_METRIC_POSITIVE_ELEVATION_METRES || metric == FTMS_METRIC_NEGATIVE_ELEVATION_METRES) &&
            view->raw.kind == FTMS_MEASUREMENT_TREADMILL) ||
           (metric == FTMS_METRIC_STRIDE_COUNT && view->raw.kind == FTMS_MEASUREMENT_CROSS_TRAINER) ||
           (metric == FTMS_METRIC_RESISTANCE_LEVEL &&
            view->format.resistance_format == FTMS_MEASUREMENT_RESISTANCE_SINT16_TENTHS)) denominator = 10U;
  else if (metric == FTMS_METRIC_STROKE_RATE_PER_MINUTE ||
           metric == FTMS_METRIC_AVERAGE_STROKE_RATE_PER_MINUTE ||
           metric == FTMS_METRIC_CADENCE_RPM || metric == FTMS_METRIC_AVERAGE_CADENCE_RPM) denominator = 2U;
  if (out != NULL) { out->numerator = view->raw.value[field]; out->denominator = denominator; }
  return FTMS_MEASUREMENT_VALUE_NUMERIC;
}

static size_t group_width(ftms_measurement_kind kind, const kind_def *definition, size_t start,
                          const ftms_measurement_format_options *options) {
  size_t width = 0U, index; uint8_t bit = definition->fields[start].bit;
  for (index = start; index < definition->count && definition->fields[index].bit == bit; ++index)
    width += formatted_field(kind, definition->fields[index], options).width;
  return width;
}

static size_t group_end(const kind_def *definition, size_t start) {
  uint8_t bit = definition->fields[start].bit;
  while (start < definition->count && definition->fields[start].bit == bit) ++start;
  return start;
}

static void fragment_from(const ftms_measurement *source, const kind_def *definition,
                          uint32_t flags, ftms_measurement *fragment) {
  size_t index;
  *fragment = *source;
  fragment->flags = flags; fragment->present = 0U; fragment->unavailable = 0U;
  for (index = 0U; index < definition->count; ++index) {
    const field_def *field = &definition->fields[index]; uint64_t bit;
    if (!selected(fragment, field)) continue;
    bit = UINT64_C(1) << field->field;
    fragment->present |= bit;
    if ((source->unavailable & bit) != 0U) fragment->unavailable |= bit;
  }
}

ftms_result ftms_measurement_plan(const ftms_measurement *snapshot,
                                  size_t value_budget,
                                  ftms_measurement_packet *packets,
                                   size_t packet_capacity, size_t *count) {
  return ftms_measurement_plan_with_format(snapshot, NULL, value_budget, packets, packet_capacity, count);
}
ftms_result ftms_measurement_plan_with_format(const ftms_measurement *snapshot,
                                   const ftms_measurement_format_options *options,
                                   size_t value_budget, ftms_measurement_packet *packets,
                                   size_t packet_capacity, size_t *count) {
  const kind_def *definition; ftms_measurement fragment;
  uint8_t checked[64]; size_t complete, index, required = 1U, used = 0U;
  size_t flag_bytes, mandatory_width, optional_in_current = 0U;
  uint32_t current_flags = 0U, fixed_flags = 0U, field_flag_mask = 0U;
  int query;
  if (snapshot == NULL || count == NULL) return FTMS_ERROR_NULL;
  if (packets == NULL && packet_capacity != 0U) return FTMS_ERROR_NULL;
  query = packets == NULL;
  if (!valid(snapshot->kind) || !valid_options(options)) return FTMS_ERROR_KIND;
  if ((snapshot->flags & 1U) != 0U) return FTMS_ERROR_RANGE;
  definition = &defs[(unsigned)snapshot->kind]; flag_bytes = definition->flag_bytes;
  for (index = 0U; index < definition->count; ++index)
    field_flag_mask |= UINT32_C(1) << definition->fields[index].bit;
  /* Cross Trainer's backward-direction flag is metadata, not a value group. */
  fixed_flags = snapshot->flags & ~field_flag_mask;
  /* Reuse the canonical encoder as the complete immutable-snapshot validator. */
  if (ftms_encode_measurement_with_format(snapshot, options, checked, sizeof checked, &complete) != FTMS_OK)
    return FTMS_ERROR_RANGE;
  mandatory_width = group_width(snapshot->kind, definition, 0U, options);
  if (value_budget < flag_bytes + mandatory_width) return FTMS_ERROR_LENGTH;
  if (complete <= value_budget) {
    if (query) { *count = 1U; return FTMS_OK; }
    if (packet_capacity < 1U) return FTMS_ERROR_LENGTH;
    for (index = 0U; index < complete; ++index) packets[0].value[index] = checked[index];
    packets[0].length = complete; *count = 1U; return FTMS_OK;
  }
  /* Count optional-only records before writing anything. Bit-zero is mandatory
   * and deliberately reserved for the last record. */
  for (index = group_end(definition, 0U); index < definition->count;) {
    size_t width = group_width(snapshot->kind, definition, index, options); uint8_t bit = definition->fields[index].bit;
    if ((snapshot->flags & (UINT32_C(1) << bit)) != 0U) {
      if (value_budget < flag_bytes + width) return FTMS_ERROR_LENGTH;
      if (optional_in_current != 0U && used + width > value_budget - flag_bytes) {
        ++required; used = 0U; optional_in_current = 0U;
      }
      used += width; ++optional_in_current;
    }
    index = group_end(definition, index);
  }
  if (optional_in_current != 0U) ++required;
  if (required > FTMS_MEASUREMENT_PLAN_MAX_PACKETS) return FTMS_ERROR_LENGTH;
  if (query) { *count = required; return FTMS_OK; }
  if (packet_capacity < required) return FTMS_ERROR_LENGTH;
  /* Emit exactly the groups counted above. Each encode is already known valid
   * because it is a subset of the validated snapshot. */
  required = 0U; used = 0U; optional_in_current = 0U;
  for (index = group_end(definition, 0U); index < definition->count;) {
    size_t width = group_width(snapshot->kind, definition, index, options); uint8_t bit = definition->fields[index].bit;
    if ((snapshot->flags & (UINT32_C(1) << bit)) != 0U) {
      if (optional_in_current != 0U && used + width > value_budget - flag_bytes) {
        fragment_from(snapshot, definition, fixed_flags | current_flags | 1U, &fragment);
        (void)ftms_encode_measurement_with_format(&fragment, options, packets[required].value, value_budget,
                                      &packets[required].length);
        ++required; current_flags = 0U; used = 0U; optional_in_current = 0U;
      }
      current_flags |= UINT32_C(1) << bit; used += width; ++optional_in_current;
    }
    index = group_end(definition, index);
  }
  if (optional_in_current != 0U) {
    fragment_from(snapshot, definition, fixed_flags | current_flags | 1U, &fragment);
    (void)ftms_encode_measurement_with_format(&fragment, options, packets[required].value, value_budget,
                                  &packets[required].length);
    ++required;
  }
  fragment_from(snapshot, definition, fixed_flags, &fragment);
  (void)ftms_encode_measurement_with_format(&fragment, options, packets[required].value, value_budget,
                                &packets[required].length);
  ++required; *count = required;
  return FTMS_OK;
}

void ftms_record_reset(ftms_record_context *context) {
  if (context != NULL) { context->active = 0U; context->started_at = 0U; }
}

static ftms_record_status record_init_core(ftms_record_context *context,
                                           ftms_measurement_kind kind,
                                           uint32_t generation, uint32_t max_age) {
  ftms_record_context initialized = {0};
  if (context == NULL || !valid(kind) || max_age == 0U || max_age >= UINT32_C(0x80000000))
    return FTMS_RECORD_INVALID;
  initialized.kind = kind; initialized.generation = generation; initialized.max_age = max_age;
  *context = initialized;
  return FTMS_RECORD_PENDING;
}

ftms_record_status ftms_record_init(ftms_record_context *context,
                                     ftms_measurement_kind kind,
                                     uint32_t generation, uint32_t max_age) {
  return record_init_core(context, kind, generation, max_age);
}

static int strict_fragment(ftms_measurement_kind kind, const uint8_t *data,
                            size_t size, const ftms_measurement_format_options *options,
                            ftms_measurement *fragment) {
  uint8_t canonical[64]; size_t written, index;
  if (ftms_decode_measurement_with_format(kind, data, size, options, fragment) != FTMS_OK) return 0;
  if (fragment->truncated != 0U || fragment->trailing_bytes != 0U ||
       fragment->reserved_flags != 0U ||
       ftms_encode_measurement_with_format(fragment, options, canonical, sizeof canonical, &written) != FTMS_OK ||
      written != size) return 0;
  for (index = 0U; index < size; ++index) if (canonical[index] != data[index]) return 0;
  return 1;
}

static int has_mandatory(const kind_def *definition, const ftms_measurement *fragment) {
  size_t index;
  for (index = 0U; index < definition->count && definition->fields[index].bit == 0U; ++index)
    if ((fragment->present & (UINT64_C(1) << definition->fields[index].field)) == 0U) return 0;
  return 1;
}

static ftms_record_status record_feed_core(ftms_record_context *context,
                                           const ftms_measurement_format_options *options,
                                           const uint8_t *data, size_t size,
                                           uint32_t generation, uint32_t now,
                                           ftms_measurement *out) {
  ftms_measurement fragment, complete;
  size_t index;
  if (context == NULL || data == NULL || out == NULL || !valid_options(options) || !valid(context->kind) ||
      context->max_age == 0U || context->max_age >= UINT32_C(0x80000000))
    return FTMS_RECORD_INVALID;
  if (generation != context->generation) { ftms_record_reset(context); return FTMS_RECORD_GENERATION; }
  if (context->active != 0U && (uint32_t)(now - context->started_at) >= context->max_age) {
    ftms_record_reset(context); return FTMS_RECORD_EXPIRED;
  }
  if (!strict_fragment(context->kind, data, size, options, &fragment)) {
    ftms_record_reset(context); return FTMS_RECORD_INVALID;
  }
  if (context->active == 0U) {
    if (fragment.more_data == 0U) { *out = fragment; return FTMS_RECORD_COMPLETE; }
    context->merged = fragment; context->merged.flags &= ~UINT32_C(1); context->merged.more_data = 0U;
    context->started_at = now; context->active = 1U;
    return FTMS_RECORD_PENDING;
  }
  if (fragment.backward != context->merged.backward ||
      (fragment.present & context->merged.present) != 0U) {
    ftms_record_reset(context); return FTMS_RECORD_INVALID;
  }
  if (fragment.more_data == 0U && !has_mandatory(&defs[(unsigned)context->kind], &fragment)) {
    ftms_record_reset(context); return FTMS_RECORD_INVALID;
  }
  context->merged.flags |= fragment.flags & ~UINT32_C(1);
  context->merged.present |= fragment.present;
  context->merged.unavailable |= fragment.unavailable;
  for (index = 0U; index < FTMS_MEASUREMENT_FIELD_COUNT; ++index)
    if ((fragment.present & (UINT64_C(1) << index)) != 0U)
      context->merged.value[index] = fragment.value[index];
  if (fragment.more_data != 0U) return FTMS_RECORD_PENDING;
  complete = context->merged; complete.flags &= ~UINT32_C(1); complete.more_data = 0U;
  /* There is no single input byte span for an assembled record. */
  complete.bytes_read = 0U;
  *out = complete;
  ftms_record_reset(context);
  return FTMS_RECORD_COMPLETE;
}

ftms_record_status ftms_record_feed(ftms_record_context *context,
                                     const uint8_t *data, size_t size,
                                     uint32_t generation, uint32_t now,
                                     ftms_measurement *out) {
  return record_feed_core(context, NULL, data, size, generation, now, out);
}

ftms_record_status ftms_record_init_with_format(ftms_record_format_context *context,
                                                ftms_measurement_kind kind,
                                                const ftms_measurement_format_options *options,
                                                uint32_t generation, uint32_t max_age) {
  ftms_measurement_format_options copied = {FTMS_MEASUREMENT_RESISTANCE_UINT8_WHOLE,
                                             FTMS_TREADMILL_PACE_UINT16};
  ftms_record_format_context initialized = {0};
  if (options != NULL) copied = *options;
  if (context == NULL || !valid_options(&copied) || !valid(kind) || max_age == 0U ||
      max_age >= UINT32_C(0x80000000)) return FTMS_RECORD_INVALID;
  initialized.options = copied;
  if (record_init_core(&initialized.record, kind, generation, max_age) != FTMS_RECORD_PENDING)
    return FTMS_RECORD_INVALID;
  *context = initialized;
  return FTMS_RECORD_PENDING;
}

void ftms_record_reset_with_format(ftms_record_format_context *context) {
  if (context != NULL) ftms_record_reset(&context->record);
}

ftms_record_status ftms_record_feed_with_format(ftms_record_format_context *context,
                                                const uint8_t *data, size_t size,
                                                uint32_t generation, uint32_t now,
                                                ftms_measurement *out) {
  if (context == NULL || !valid_options(&context->options)) return FTMS_RECORD_INVALID;
  return record_feed_core(&context->record, &context->options, data, size, generation, now, out);
}

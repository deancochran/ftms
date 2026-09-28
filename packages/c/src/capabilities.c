#include "ftms/capabilities.h"

static const uint8_t base_uuid[12] = {
  0, 0, 0x10, 0, 0x80, 0, 0, 0x80, 0x5f, 0x9b, 0x34, 0xfb
};
static const uint8_t target_for_opcode[FTMS_CAP_OPERATION_COUNT] = {
  255, 255, 0, 1, 2, 3, 4, 255, 255, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16
};
/* Target bits 3/4 are power/heart rate, unlike UUID/native range order. */
static const uint8_t range_for_target[5] = {
  FTMS_RANGE_SPEED, FTMS_RANGE_INCLINATION, FTMS_RANGE_RESISTANCE_LEVEL,
  FTMS_RANGE_POWER, FTMS_RANGE_HEART_RATE
};

static uint8_t kind_of(const uint8_t uuid[FTMS_CAP_UUID_BYTES]) {
  unsigned value;
  size_t i;
  if (uuid[0] != 0U || uuid[1] != 0U) return FTMS_CAP_KIND_UNKNOWN;
  for (i = 0; i < sizeof base_uuid; ++i) {
    if (uuid[i + 4U] != base_uuid[i]) return FTMS_CAP_KIND_UNKNOWN;
  }
  value = ((unsigned)uuid[2] << 8) | uuid[3];
  if (value < 0x2accU || value > 0x2adaU) return FTMS_CAP_KIND_UNKNOWN;
  return (uint8_t)(FTMS_CAP_KIND_FEATURE + value - 0x2accU);
}

static uint16_t required_props(uint8_t kind) {
  if (kind == FTMS_CAP_KIND_FEATURE ||
      (kind >= FTMS_CAP_KIND_SPEED_RANGE && kind <= FTMS_CAP_KIND_POWER_RANGE)) {
    return FTMS_CAP_PROP_READ;
  }
  if (kind == FTMS_CAP_KIND_TRAINING_STATUS) {
    return FTMS_CAP_PROP_READ | FTMS_CAP_PROP_NOTIFY;
  }
  if (kind == FTMS_CAP_KIND_CONTROL_POINT) {
    return FTMS_CAP_PROP_WRITE | FTMS_CAP_PROP_INDICATE;
  }
  return FTMS_CAP_PROP_NOTIFY;
}

static ftms_result validate(const ftms_cap_snapshot *s) {
  size_t i;
  if (s == NULL) return FTMS_ERROR_NULL;
  if ((unsigned)s->discovery > (unsigned)FTMS_CAP_DISCOVERY_FAILED ||
      (unsigned)s->service_scope > (unsigned)FTMS_CAP_SERVICE_AMBIGUOUS) {
    return FTMS_ERROR_KIND;
  }
  /* At most three per-observation diagnostics plus fewer than 64 fixed ones.
   * Check representable buffer sizes before walking any caller array. */
  if (s->characteristic_count > SIZE_MAX / sizeof(ftms_cap_characteristic) ||
      s->characteristic_count > SIZE_MAX / sizeof(ftms_cap_observation) ||
      s->characteristic_count > (SIZE_MAX / sizeof(ftms_cap_diagnostic) - 64U) / 3U) {
    return FTMS_ERROR_LENGTH;
  }
  if (s->characteristic_count != 0U && s->characteristics == NULL) return FTMS_ERROR_NULL;
  for (i = 0; i < s->characteristic_count; ++i) {
    const ftms_cap_characteristic *c = &s->characteristics[i];
    if ((unsigned)c->read_state > (unsigned)FTMS_CAP_READ_FAILED ||
        (unsigned)c->read_reason > (unsigned)FTMS_CAP_READ_REASON_DISCONNECTED ||
        (c->read_state != FTMS_CAP_READ_FAILED && c->read_reason != FTMS_CAP_READ_REASON_NONE) ||
        (c->read_state != FTMS_CAP_READ_SUCCESS && (c->read_size != 0U || c->read_bytes != NULL))) {
      return FTMS_ERROR_KIND;
    }
    if (c->read_state == FTMS_CAP_READ_SUCCESS && c->read_size != 0U && c->read_bytes == NULL) {
      return FTMS_ERROR_NULL;
    }
  }
  return FTMS_OK;
}
static int valid_range_options(const ftms_range_format_options *options) {
  return options == NULL || (unsigned)options->resistance_format <= FTMS_RESISTANCE_RANGE_SINT16_TENTHS;
}

static void add_diag(ftms_cap_diagnostic *diags, ftms_cap_report *r,
                     ftms_cap_diagnostic_code code, uint8_t kind, size_t index) {
  if (diags != NULL) {
    diags[r->diagnostic_count].code = code;
    diags[r->diagnostic_count].known_kind = kind;
    diags[r->diagnostic_count].input_index = index;
  }
  ++r->diagnostic_count;
}

static ftms_cap_decode decode_feature(const ftms_cap_characteristic *c,
                                     ftms_cap_feature_evidence *e) {
  ftms_features value;
  if (c->read_state == FTMS_CAP_READ_FAILED) return FTMS_CAP_DECODE_FAILED;
  if (c->read_state != FTMS_CAP_READ_SUCCESS) return FTMS_CAP_DECODE_NOT_ATTEMPTED;
  if (c->read_size != 8U || ftms_decode_features(c->read_bytes, c->read_size, &value) != FTMS_OK) {
    return FTMS_CAP_DECODE_MALFORMED;
  }
  e->machine_raw = value.machine;
  e->target_raw = value.target;
  e->machine_unknown = value.machine & ~UINT32_C(0x1ffff);
  e->target_unknown = value.target & ~UINT32_C(0x1ffff);
  return FTMS_CAP_DECODE_VALID;
}

static ftms_cap_decode decode_range(const ftms_cap_characteristic *c,
                                    ftms_range_kind kind, const ftms_range_format_options *options,
                                    ftms_range *value) {
  if (c->read_state == FTMS_CAP_READ_FAILED) return FTMS_CAP_DECODE_FAILED;
  if (c->read_state != FTMS_CAP_READ_SUCCESS) return FTMS_CAP_DECODE_NOT_ATTEMPTED;
  if (c->read_size == 0U || (kind == FTMS_RANGE_RESISTANCE_LEVEL
      ? ftms_decode_range_with_format(kind, c->read_bytes, c->read_size, options, value)
      : ftms_decode_range(kind, c->read_bytes, c->read_size, value)) != FTMS_OK) {
    return FTMS_CAP_DECODE_MALFORMED;
  }
  return FTMS_CAP_DECODE_VALID;
}

/* Missing confirmed evidence, duplicates, and invalid properties are contradictions.
 * Read/decode state is checked separately for Feature and range prerequisites. */
static uint32_t characteristic_reasons(const ftms_cap_snapshot *s, const ftms_cap_report *r,
                                      const size_t first[FTMS_CAP_KIND_COUNT], uint8_t kind,
                                      uint32_t unavailable, uint32_t invalid) {
  if (r->presence[kind] == FTMS_CAP_PRESENCE_UNKNOWN) return unavailable;
  if (r->presence[kind] != FTMS_CAP_PRESENCE_UNIQUE) return invalid;
  if (s->characteristics[first[kind]].properties != required_props(kind)) return invalid;
  return 0U;
}

static uint32_t decode_reasons(ftms_cap_decode state, uint32_t unavailable, uint32_t invalid) {
  if (state == FTMS_CAP_DECODE_MALFORMED) return invalid;
  return state == FTMS_CAP_DECODE_VALID ? 0U : unavailable;
}

static void evaluate_operations(const ftms_cap_snapshot *s, ftms_cap_report *r,
                                const size_t first[FTMS_CAP_KIND_COUNT]) {
  size_t opcode;
  const uint32_t invalid_mask = FTMS_CAP_REASON_FEATURE_INVALID |
    FTMS_CAP_REASON_CONTROL_POINT_INVALID | FTMS_CAP_REASON_STATUS_INVALID |
    FTMS_CAP_REASON_RANGE_INVALID;
  const int scope_ok = s->service_scope == FTMS_CAP_SERVICE_PRESENT;
  const int absent = s->service_scope == FTMS_CAP_SERVICE_ABSENT &&
    s->discovery == FTMS_CAP_DISCOVERY_COMPLETE && s->characteristic_count == 0U;
  const int scope_contradiction = s->service_scope == FTMS_CAP_SERVICE_ABSENT && !absent;
  for (opcode = 0; opcode < FTMS_CAP_OPERATION_COUNT; ++opcode) {
    ftms_cap_operation *o = &r->operations[opcode];
    uint8_t bit = target_for_opcode[opcode];
    o->opcode = (uint8_t)opcode;
    o->target_bit = bit;
    o->optional_in_table = (uint8_t)(opcode == 0x12U || opcode == 0x13U);
    o->declaration = FTMS_CAP_DECLARATION_UNKNOWN;
    o->prerequisite = FTMS_CAP_PREREQUISITE_INCOMPLETE;
    if (!scope_ok) {
      o->reasons = FTMS_CAP_REASON_SCOPE_UNAVAILABLE;
      if (absent) {
        o->declaration = FTMS_CAP_DECLARATION_NOT_SUPPORTED;
        o->prerequisite = FTMS_CAP_PREREQUISITE_NOT_APPLICABLE;
      } else if (scope_contradiction) {
        o->prerequisite = FTMS_CAP_PREREQUISITE_INCONSISTENT;
      }
      continue;
    }
    if (bit == FTMS_CAP_NO_TARGET) {
      if (r->presence[FTMS_CAP_KIND_CONTROL_POINT] == FTMS_CAP_PRESENCE_UNIQUE) {
        o->declaration = FTMS_CAP_DECLARATION_SUPPORTED;
      } else if (r->presence[FTMS_CAP_KIND_CONTROL_POINT] == FTMS_CAP_PRESENCE_ABSENT) {
        o->declaration = FTMS_CAP_DECLARATION_NOT_SUPPORTED;
      }
    } else if (r->feature.decode == FTMS_CAP_DECODE_VALID) {
      o->declaration = (r->feature.target_raw & (UINT32_C(1) << bit)) != 0U
        ? FTMS_CAP_DECLARATION_SUPPORTED : FTMS_CAP_DECLARATION_NOT_SUPPORTED;
    }
    if (o->declaration == FTMS_CAP_DECLARATION_NOT_SUPPORTED) {
      o->prerequisite = FTMS_CAP_PREREQUISITE_NOT_APPLICABLE;
      continue;
    }
    if (s->discovery != FTMS_CAP_DISCOVERY_COMPLETE) o->reasons |= FTMS_CAP_REASON_DISCOVERY_INCOMPLETE;
    o->reasons |= characteristic_reasons(s, r, first, FTMS_CAP_KIND_FEATURE,
      FTMS_CAP_REASON_FEATURE_UNAVAILABLE, FTMS_CAP_REASON_FEATURE_INVALID);
    if (bit != FTMS_CAP_NO_TARGET && r->feature.presence == FTMS_CAP_PRESENCE_UNIQUE) {
      o->reasons |= decode_reasons(r->feature.decode,
        FTMS_CAP_REASON_FEATURE_UNAVAILABLE, FTMS_CAP_REASON_FEATURE_INVALID);
    }
    o->reasons |= characteristic_reasons(s, r, first, FTMS_CAP_KIND_CONTROL_POINT,
      FTMS_CAP_REASON_CONTROL_POINT_UNAVAILABLE, FTMS_CAP_REASON_CONTROL_POINT_INVALID);
    o->reasons |= characteristic_reasons(s, r, first, FTMS_CAP_KIND_MACHINE_STATUS,
      FTMS_CAP_REASON_STATUS_UNAVAILABLE, FTMS_CAP_REASON_STATUS_INVALID);
    /* Unknown declarations must not invent required ranges. */
    if (bit < 5U && o->declaration == FTMS_CAP_DECLARATION_SUPPORTED) {
      uint8_t range = range_for_target[bit];
      uint8_t kind = (uint8_t)(FTMS_CAP_KIND_SPEED_RANGE + range);
      o->reasons |= characteristic_reasons(s, r, first, kind,
        FTMS_CAP_REASON_RANGE_UNAVAILABLE, FTMS_CAP_REASON_RANGE_INVALID);
      if (r->ranges[range].presence == FTMS_CAP_PRESENCE_UNIQUE) {
        o->reasons |= decode_reasons(r->ranges[range].decode,
          FTMS_CAP_REASON_RANGE_UNAVAILABLE, FTMS_CAP_REASON_RANGE_INVALID);
      }
    }
    if ((o->reasons & invalid_mask) != 0U) o->prerequisite = FTMS_CAP_PREREQUISITE_INCONSISTENT;
    else if (o->reasons == 0U) o->prerequisite = FTMS_CAP_PREREQUISITE_SATISFIED;
  }
}

static void evaluate(const ftms_cap_snapshot *s, ftms_cap_observation *observations,
                      ftms_cap_diagnostic *diags, const ftms_range_format_options *options,
                      ftms_cap_report *r) {
  size_t i;
  uint8_t counts[FTMS_CAP_KIND_COUNT] = {0};
  size_t first[FTMS_CAP_KIND_COUNT] = {0};
  const int scope_ok = s->service_scope == FTMS_CAP_SERVICE_PRESENT;
  /* Character-byte access avoids a hosted string.h dependency. Compiler-generated
   * runtime helpers remain toolchain-dependent and are checked separately. */
  for (i = 0; i < sizeof *r; ++i) ((unsigned char *)r)[i] = 0;
  r->generation = s->generation;
  r->discovery = s->discovery;
  r->service_scope = s->service_scope;
  r->observation_count = s->characteristic_count;
  for (i = 0; i < s->characteristic_count; ++i) {
    const ftms_cap_characteristic *c = &s->characteristics[i];
    uint8_t kind = kind_of(c->uuid);
    if (observations != NULL) {
      size_t byte;
      observations[i].input_index = i;
      for (byte = 0; byte < FTMS_CAP_UUID_BYTES; ++byte) observations[i].uuid[byte] = c->uuid[byte];
      observations[i].properties = c->properties;
      observations[i].known_kind = kind;
      observations[i].read_state = c->read_state;
      observations[i].read_reason = c->read_reason;
      observations[i].read_size = c->read_size;
    }
    if (kind != FTMS_CAP_KIND_UNKNOWN) {
      if (counts[kind] == 0U) first[kind] = i;
      if (counts[kind] < 2U) ++counts[kind];
    }
  }
  for (i = 1; i < FTMS_CAP_KIND_COUNT; ++i) {
    if (counts[i] > 1U) {
      r->presence[i] = FTMS_CAP_PRESENCE_AMBIGUOUS;
      add_diag(diags, r, FTMS_CAP_DIAG_DUPLICATE_CHARACTERISTIC, (uint8_t)i, first[i]);
    } else if (counts[i] == 1U) r->presence[i] = FTMS_CAP_PRESENCE_UNIQUE;
    else if (s->discovery == FTMS_CAP_DISCOVERY_COMPLETE && scope_ok) {
      r->presence[i] = FTMS_CAP_PRESENCE_ABSENT;
    }
  }
  if (!scope_ok) add_diag(diags, r, FTMS_CAP_DIAG_SCOPE_UNAVAILABLE, 0, FTMS_CAP_NO_INDEX);
  if (s->service_scope == FTMS_CAP_SERVICE_ABSENT &&
      (s->discovery != FTMS_CAP_DISCOVERY_COMPLETE || s->characteristic_count != 0U)) {
    add_diag(diags, r, FTMS_CAP_DIAG_SCOPE_CONTRADICTION, 0, FTMS_CAP_NO_INDEX);
  }
  if (s->discovery != FTMS_CAP_DISCOVERY_COMPLETE) {
    add_diag(diags, r, s->discovery == FTMS_CAP_DISCOVERY_FAILED
      ? FTMS_CAP_DIAG_DISCOVERY_FAILED : FTMS_CAP_DIAG_DISCOVERY_INCOMPLETE, 0, FTMS_CAP_NO_INDEX);
  }
  for (i = 0; i < s->characteristic_count; ++i) {
    const ftms_cap_characteristic *c = &s->characteristics[i];
    uint8_t kind = kind_of(c->uuid);
    uint16_t required = required_props(kind);
    if (kind == FTMS_CAP_KIND_UNKNOWN || !scope_ok) continue;
    if ((c->properties & required) != required) {
      add_diag(diags, r, FTMS_CAP_DIAG_REQUIRED_PROPERTY_MISSING, kind, i);
    }
    if ((c->properties & (uint16_t)~required) != 0U) {
      add_diag(diags, r, FTMS_CAP_DIAG_EXCLUDED_PROPERTY_PRESENT, kind, i);
    }
    if (c->read_state == FTMS_CAP_READ_FAILED) {
      add_diag(diags, r, c->read_reason == FTMS_CAP_READ_REASON_SECURITY_REQUIRED
        ? FTMS_CAP_DIAG_READ_SECURITY_REQUIRED : FTMS_CAP_DIAG_READ_FAILED, kind, i);
    }
  }
  r->feature.presence = r->presence[FTMS_CAP_KIND_FEATURE];
  r->feature.input_index = FTMS_CAP_NO_INDEX;
  if (scope_ok && r->feature.presence == FTMS_CAP_PRESENCE_UNIQUE) {
    r->feature.input_index = first[FTMS_CAP_KIND_FEATURE];
    r->feature.decode = decode_feature(&s->characteristics[r->feature.input_index], &r->feature);
    if (r->feature.decode == FTMS_CAP_DECODE_MALFORMED) {
      add_diag(diags, r, FTMS_CAP_DIAG_MALFORMED_BYTES, FTMS_CAP_KIND_FEATURE, r->feature.input_index);
    }
  }
  for (i = 0; i < FTMS_CAP_RANGE_COUNT; ++i) {
    uint8_t kind = (uint8_t)(FTMS_CAP_KIND_SPEED_RANGE + i);
    ftms_cap_range_evidence *e = &r->ranges[i];
    e->presence = r->presence[kind];
    e->input_index = FTMS_CAP_NO_INDEX;
    if (scope_ok && e->presence == FTMS_CAP_PRESENCE_UNIQUE) {
      e->input_index = first[kind];
      e->decode = decode_range(&s->characteristics[e->input_index], (ftms_range_kind)i, options, &e->value);
      if (e->decode == FTMS_CAP_DECODE_MALFORMED) {
        add_diag(diags, r, FTMS_CAP_DIAG_MALFORMED_BYTES, kind, e->input_index);
      }
    }
  }
  if (scope_ok) {
    if (r->feature.presence == FTMS_CAP_PRESENCE_ABSENT) {
      add_diag(diags, r, FTMS_CAP_DIAG_REQUIRED_CHARACTERISTIC_MISSING, FTMS_CAP_KIND_FEATURE, FTMS_CAP_NO_INDEX);
    }
    if ((r->presence[FTMS_CAP_KIND_CONTROL_POINT] == FTMS_CAP_PRESENCE_UNIQUE ||
         r->presence[FTMS_CAP_KIND_CONTROL_POINT] == FTMS_CAP_PRESENCE_AMBIGUOUS) &&
        r->presence[FTMS_CAP_KIND_MACHINE_STATUS] == FTMS_CAP_PRESENCE_ABSENT) {
      add_diag(diags, r, FTMS_CAP_DIAG_REQUIRED_CHARACTERISTIC_MISSING, FTMS_CAP_KIND_MACHINE_STATUS, FTMS_CAP_NO_INDEX);
    }
    if (r->feature.decode == FTMS_CAP_DECODE_VALID) {
      if ((r->feature.target_raw & UINT32_C(0x1ffff)) != 0U &&
          r->presence[FTMS_CAP_KIND_CONTROL_POINT] == FTMS_CAP_PRESENCE_ABSENT) {
        add_diag(diags, r, FTMS_CAP_DIAG_REQUIRED_CHARACTERISTIC_MISSING, FTMS_CAP_KIND_CONTROL_POINT, FTMS_CAP_NO_INDEX);
      }
      for (i = 0; i < 5U; ++i) {
        uint8_t range = range_for_target[i];
        if ((r->feature.target_raw & (UINT32_C(1) << i)) != 0U &&
            r->ranges[range].presence == FTMS_CAP_PRESENCE_ABSENT) {
          add_diag(diags, r, FTMS_CAP_DIAG_REQUIRED_RANGE_MISSING,
            (uint8_t)(FTMS_CAP_KIND_SPEED_RANGE + range), FTMS_CAP_NO_INDEX);
        }
      }
    }
  }
  evaluate_operations(s, r, first);
}

ftms_result ftms_capability_requirements(const ftms_cap_snapshot *s, ftms_cap_requirements *out) {
  return ftms_capability_requirements_with_format(s, NULL, out);
}
ftms_result ftms_capability_requirements_with_format(const ftms_cap_snapshot *s,
                                                     const ftms_range_format_options *options,
                                                     ftms_cap_requirements *out) {
  ftms_cap_report report;
  ftms_result result;
  if (out == NULL) return FTMS_ERROR_NULL;
  if (!valid_range_options(options)) return FTMS_ERROR_KIND;
  result = validate(s);
  if (result != FTMS_OK) return result;
  evaluate(s, NULL, NULL, options, &report);
  out->observation_count = report.observation_count;
  out->diagnostic_count = report.diagnostic_count;
  return FTMS_OK;
}

ftms_result ftms_evaluate_capabilities(const ftms_cap_snapshot *s, ftms_cap_output *out) {
  return ftms_evaluate_capabilities_with_format(s, NULL, out);
}
ftms_result ftms_evaluate_capabilities_with_format(const ftms_cap_snapshot *s,
                                                   const ftms_range_format_options *options,
                                                   ftms_cap_output *out) {
  ftms_cap_report report;
  ftms_result result;
  if (out == NULL) return FTMS_ERROR_NULL;
  if (!valid_range_options(options)) return FTMS_ERROR_KIND;
  result = validate(s);
  if (result != FTMS_OK) return result;
  evaluate(s, NULL, NULL, options, &report);
  if (out->observation_capacity < report.observation_count || out->diagnostic_capacity < report.diagnostic_count) {
    return FTMS_ERROR_LENGTH;
  }
  if ((report.observation_count != 0U && out->observations == NULL) ||
      (report.diagnostic_count != 0U && out->diagnostics == NULL)) return FTMS_ERROR_NULL;
  evaluate(s, out->observations, out->diagnostics, options, &out->report);
  return FTMS_OK;
}

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ftms/ftms.h"

static const char *profile(ftms_range_profile value) {
  static const char *names[] = {"uint16Hundredths", "signed16Tenths", "uint8Whole", "uint8Bpm", "signed16Watts"};
  return value <= FTMS_RANGE_PROFILE_SINT16_WATTS ? names[value] : "invalid";
}
static const char *status(ftms_range_inspection_status value) {
  static const char *names[] = {"valid", "length", "range"};
  return value <= FTMS_RANGE_INSPECTION_RANGE ? names[value] : "invalid";
}
static void emit_value(ftms_range_inspection_status state, const ftms_range *value) {
  static const char *kinds[] = {"speed", "inclination", "resistance", "heartRate", "power"};
  if (state != FTMS_RANGE_INSPECTION_VALID) fputs("null", stdout);
  else printf("{\"kind\":\"%s\",\"minimum\":%ld,\"maximum\":%ld,\"increment\":%ld,\"scaleDivisor\":%u,\"unit\":%d}", kinds[value->kind], (long)value->minimum, (long)value->maximum, (long)value->increment, (unsigned)value->scale_divisor, (int)value->unit);
}
int main(int argc, char **argv) {
  uint8_t bytes[128]; size_t count = 0U; size_t i; ftms_range_inspection out;
  ftms_range_format_options options; ftms_range_format_options *option = NULL;
  ftms_result result;
  if (argc < 3 || argc > 4) return 2;
  for (i = 0U; argv[2][i] != '\0'; i += 2U) {
    char piece[3] = {argv[2][i], argv[2][i + 1U], '\0'};
    char *end; unsigned long value;
    if (argv[2][i + 1U] == '\0' || count == sizeof bytes) return 2;
    value = strtoul(piece, &end, 16); if (*end != '\0' || value > 255UL) return 2;
    bytes[count++] = (uint8_t)value;
  }
  if (argc == 4) { options.resistance_format = strcmp(argv[3], "signed16Tenths") == 0 ? FTMS_RESISTANCE_RANGE_SINT16_TENTHS : FTMS_RESISTANCE_RANGE_UINT8_WHOLE; option = &options; }
  result = ftms_inspect_range_with_format((ftms_range_kind)strtol(argv[1], NULL, 10), bytes, count, option, &out);
  if (result != FTMS_OK) { printf("{\"result\":%d}\n", (int)result); return 0; }
  printf("{\"selectedProfile\":\"%s\",\"actualLength\":%zu,\"expectedLength\":%zu,\"status\":\"%s\",\"value\":", profile(out.selected_profile), out.observed_size, out.expected_size, status(out.status));
  emit_value(out.status, &out.value);
  fputs(",\"candidates\":[", stdout);
  for (i = 0U; i < out.candidate_count; ++i) {
    const ftms_range_inspection_candidate *candidate = &out.candidates[i];
    if (i) putchar(',');
    printf("{\"profile\":\"%s\",\"expectedLength\":%zu,\"status\":\"%s\",\"value\":", profile(candidate->profile), candidate->expected_size, status(candidate->status));
    emit_value(candidate->status, &candidate->value);
    putchar('}');
  }
  puts("]}"); return 0;
}

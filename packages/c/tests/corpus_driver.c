#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "ftms/ftms.h"

static int parse_hex(const char *text, uint8_t *bytes, size_t *size) {
  size_t length = strlen(text);
  size_t index;

  if (length % 2U != 0U || length / 2U > 16U) {
    return 0;
  }
  for (index = 0U; index < length / 2U; index++) {
    char pair[3] = {text[index * 2U], text[index * 2U + 1U], '\0'};
    char *end;
    unsigned long value = strtoul(pair, &end, 16);

    if (*end != '\0' || value > 255U) {
      return 0;
    }
    bytes[index] = (uint8_t)value;
  }
  *size = length / 2U;
  return 1;
}

static int range_kind_from_name(const char *name, ftms_range_kind *kind) {
  if (strcmp(name, "speed") == 0) {
    *kind = FTMS_RANGE_SPEED;
  } else if (strcmp(name, "inclination") == 0) {
    *kind = FTMS_RANGE_INCLINATION;
  } else if (strcmp(name, "resistance") == 0) {
    *kind = FTMS_RANGE_RESISTANCE_LEVEL;
  } else if (strcmp(name, "heartRate") == 0) {
    *kind = FTMS_RANGE_HEART_RATE;
  } else if (strcmp(name, "power") == 0) {
    *kind = FTMS_RANGE_POWER;
  } else {
    return 0;
  }
  return 1;
}

int main(int argc, char **argv) {
  uint8_t bytes[16];
  size_t size;
  ftms_range_format_options format;
  const ftms_range_format_options *options = NULL;

  if (argc == 4) {
    char *end;
    long selected = strtol(argv[3], &end, 10);
    if (*end != '\0' || selected < 0L || selected > 1L) return 64;
    format.resistance_format = (ftms_resistance_range_format)selected;
    options = &format;
  } else if (argc != 3) return 64;
  if (!parse_hex(argv[2], bytes, &size)) {
    return 64;
  }
  if (strcmp(argv[1], "feature") == 0) {
    ftms_features features;
    ftms_result result = ftms_decode_features(bytes, size, &features);

    if (result != FTMS_OK) {
      printf("error %d\n", (int)result);
    } else {
      printf("ok %u %u\n", (unsigned)features.machine, (unsigned)features.target);
    }
    return 0;
  }
  {
    ftms_range_kind kind;
    ftms_range range;
    ftms_result result;

    if (!range_kind_from_name(argv[1], &kind)) {
      return 64;
    }
    result = ftms_decode_range_with_format(kind, bytes, size, options, &range);
    if (result != FTMS_OK) {
      printf("error %d\n", (int)result);
    } else {
      const char *decoded_kind;
      switch (range.kind) {
        case FTMS_RANGE_SPEED: decoded_kind = "speed"; break;
        case FTMS_RANGE_INCLINATION: decoded_kind = "inclination"; break;
        case FTMS_RANGE_RESISTANCE_LEVEL: decoded_kind = "resistance"; break;
        case FTMS_RANGE_HEART_RATE: decoded_kind = "heartRate"; break;
        case FTMS_RANGE_POWER: decoded_kind = "power"; break;
        default: return 65;
      }
      printf("ok %s %ld %ld %ld %u %d\n", decoded_kind, (long)range.minimum,
             (long)range.maximum, (long)range.increment,
             (unsigned)range.scale_divisor, (int)range.unit);
    }
  }
  return 0;
}

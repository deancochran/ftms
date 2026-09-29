/* Host-only stateful bridge. Expected values are never part of this grammar. */
#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#include "ftms/measurement.h"

#define MAX_LINES 1024U

static int uint32_token(const char *text, uint32_t *value) {
  uint64_t number = 0U;
  size_t i;
  if (!text[0]) return 0;
  for (i = 0U; text[i]; ++i) {
    if (text[i] < '0' || text[i] > '9' ||
        number > (UINT32_MAX - (uint32_t)(text[i] - '0')) / 10U) return 0;
    number = number * 10U + (uint32_t)(text[i] - '0');
  }
  *value = (uint32_t)number;
  return 1;
}

static int hex_digit(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  return -1;
}

static int bytes_token(const char *text, uint8_t *bytes, size_t *size) {
  size_t i, length = strlen(text);
  if (!strcmp(text, "-")) { *size = 0U; return 1; }
  if ((length & 1U) || length > 128U) return 0;
  for (i = 0U; i < length / 2U; ++i) {
    int hi = hex_digit(text[i * 2U]), lo = hex_digit(text[i * 2U + 1U]);
    if (hi < 0 || lo < 0) return 0;
    bytes[i] = (uint8_t)((unsigned)hi * 16U + (unsigned)lo);
  }
  *size = length / 2U;
  return 1;
}

static const char *status_name(ftms_record_status status) {
  static const char *names[] = {"pending", "complete", "invalid", "expired", "generation"};
  return (unsigned)status <= FTMS_RECORD_GENERATION ? names[(unsigned)status] : "invalid";
}

static void raw_json(const ftms_measurement *m) {
  size_t i;
  printf("{\"status\":\"complete\",\"raw\":{\"kind\":%u,\"flags\":%" PRIu32
         ",\"present\":%" PRIu64 ",\"unavailable\":%" PRIu64 ",\"values\":[",
         (unsigned)m->kind, m->flags, m->present, m->unavailable);
  for (i = 0U; i < FTMS_MEASUREMENT_FIELD_COUNT; ++i)
    printf("%s%" PRId32, i ? "," : "", m->value[i]);
  printf("],\"moreData\":%u,\"backward\":%u,\"truncated\":%u,\"trailingBytes\":%u,"
         "\"reservedFlags\":%u,\"bytesRead\":%zu}}\n",
         (unsigned)m->more_data, (unsigned)m->backward, (unsigned)m->truncated,
         (unsigned)m->trailing_bytes, (unsigned)m->reserved_flags, m->bytes_read);
}

int main(void) {
  char line[1026];
  unsigned count = 0U;
  int connected = 0, initialized = 0;
  ftms_record_format_context context;
  while (fgets(line, sizeof line, stdin) != NULL) {
    char *tokens[7], *token;
    size_t argc = 0U, size, byte;
    uint32_t kind, generation, age, resistance, pace, now;
    uint8_t bytes[64];
    ftms_measurement out;
    ftms_record_status status;
    if (++count > MAX_LINES || strchr(line, '\n') == NULL) return 2;
    token = strtok(line, " \t\r\n");
    while (token != NULL && argc < 7U) {
      tokens[argc++] = token;
      token = strtok(NULL, " \t\r\n");
    }
    if (argc == 0U || token != NULL) return 2;
    if (!strcmp(tokens[0], "init") || !strcmp(tokens[0], "reconnect")) {
      ftms_measurement_format_options format;
      if (argc != 6U || !uint32_token(tokens[1], &kind) ||
          !uint32_token(tokens[2], &generation) || !uint32_token(tokens[3], &age) ||
          !uint32_token(tokens[4], &resistance) || !uint32_token(tokens[5], &pace) ||
          kind > 5U || resistance > 1U || pace > 1U) return 2;
      format.resistance_format = (ftms_measurement_resistance_format)resistance;
      format.treadmill_pace_format = (ftms_treadmill_pace_format)pace;
      status = ftms_record_init_with_format(&context, (ftms_measurement_kind)kind,
                                            &format, generation, age);
      initialized = status == FTMS_RECORD_PENDING;
      connected = initialized;
      printf("{\"status\":\"%s\"}\n", status_name(status));
      continue;
    }
    if (!initialized) return 2;
    if (!strcmp(tokens[0], "disconnect") || !strcmp(tokens[0], "reset")) {
      if (argc != 1U) return 2;
      ftms_record_reset_with_format(&context);
      if (!strcmp(tokens[0], "disconnect")) connected = 0;
      puts("{\"status\":\"pending\"}");
      continue;
    }
    if (strcmp(tokens[0], "feed") || argc != 4U ||
        !uint32_token(tokens[1], &generation) || !uint32_token(tokens[2], &now) ||
        !bytes_token(tokens[3], bytes, &size)) return 2;
    if (!connected) { puts("{\"status\":\"disconnected\"}"); continue; }
    memset(&out, 0xa5, sizeof out);
    status = ftms_record_feed_with_format(&context, bytes, size, generation, now, &out);
    if (status == FTMS_RECORD_COMPLETE) raw_json(&out);
    else {
      for (byte = 0U; byte < sizeof out; ++byte)
        if (((const unsigned char *)&out)[byte] != 0xa5U) return 3;
      printf("{\"status\":\"%s\"}\n", status_name(status));
    }
  }
  return ferror(stdin) ? 2 : 0;
}

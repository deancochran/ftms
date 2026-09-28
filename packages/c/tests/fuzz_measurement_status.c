#include <stdio.h>
#include <string.h>
#include "ftms/measurement.h"
#include "ftms/status.h"

static uint32_t next(uint32_t *state) {
  *state = *state * UINT32_C(1664525) + UINT32_C(1013904223);
  return *state;
}
int main(void) {
  uint32_t state = 1;
  unsigned iteration;
  for (iteration = 0; iteration < 10000U; ++iteration) {
    uint8_t bytes[64], encoded[80], saved_bytes[80];
    size_t i, size = (size_t)(next(&state) % 65U), written = 99;
    ftms_measurement m, before;
    ftms_machine_status machine;
    ftms_training_status training;
    ftms_result result;
    ftms_measurement_kind kind = (ftms_measurement_kind)(next(&state) % 8U);
    for (i = 0; i < sizeof bytes; ++i) bytes[i] = (uint8_t)(next(&state) >> 24);
    memset(&m, 0xa5, sizeof m); memcpy(&before, &m, sizeof m);
    result = ftms_decode_measurement(kind, bytes, size, &m);
    if (result != FTMS_OK) {
      if (memcmp(&m, &before, sizeof m) != 0) return 1;
    } else {
      if (m.bytes_read > size || (m.unavailable & ~m.present)) return 2;
      memset(encoded, 0xa5, sizeof encoded); memcpy(saved_bytes, encoded, sizeof encoded);
      result = ftms_encode_measurement(&m, encoded, sizeof encoded, &written);
      if (result != FTMS_OK) {
        if (written != 99 || memcmp(encoded, saved_bytes, sizeof encoded) != 0) return 3;
      } else {
        if (m.truncated || m.reserved_flags || written != m.bytes_read || memcmp(bytes, encoded, written)) return 4;
      }
    }
    /* Cycle through known and unknown opcodes with malformed operand lengths. */
    bytes[0] = (uint8_t)(next(&state) % 24U);
    if (ftms_decode_machine_status(bytes, size, &machine) != FTMS_OK) return 5;
    memset(encoded, 0xa5, sizeof encoded); memcpy(saved_bytes, encoded, sizeof encoded); written = 99;
    result = ftms_encode_machine_status(&machine, encoded, sizeof encoded, &written);
    if (result != FTMS_OK) {
      if (written != 99 || memcmp(encoded, saved_bytes, sizeof encoded)) return 6;
    } else if (written != size || memcmp(bytes, encoded, written)) return 7;
    if (ftms_decode_training_status(bytes, size, &training) != FTMS_OK) return 8;
    if (training.text_offset > size || training.text_size > size - training.text_offset) return 9;
    memset(encoded, 0xa5, sizeof encoded); memcpy(saved_bytes, encoded, sizeof encoded); written = 99;
    result = ftms_encode_training_status(&training, bytes + training.text_offset,
                                         training.text_size, encoded, sizeof encoded, &written);
    if (result != FTMS_OK) {
      if (written != 99 || memcmp(encoded, saved_bytes, sizeof encoded)) return 10;
    } else if (written != size || memcmp(bytes, encoded, written)) return 11;
  }
  puts("deterministic measurement/status fuzz: 10000 inputs passed");
  return 0;
}

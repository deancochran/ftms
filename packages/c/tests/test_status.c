#include "ftms/status.h"

#include <assert.h>
#include <string.h>

static void check_machine(const uint8_t *wire, size_t size) {
  ftms_machine_status status = {0};
  uint8_t encoded[11] = {0};
  size_t written = 99U;
  assert(ftms_decode_machine_status(wire, size, &status) == FTMS_OK);
  assert(status.opcode == wire[0]);
  assert(status.unknown_opcode == 0U);
  assert(status.truncated == 0U);
  if (wire[0] == 0x05U) assert(status.parameter.value.speed_centikph == UINT16_C(0x1234));
  if (wire[0] == 0x06U) assert(status.parameter.value.inclination_tenth_percent == -2);
  if (wire[0] == 0x07U) assert(status.parameter.value.resistance_tenth_level == -3);
  if (wire[0] == 0x0dU) assert(status.parameter.value.distance_metres == UINT32_C(0x123456));
  if (wire[0] == 0x12U) assert(status.parameter.value.simulation.grade_hundredth_percent == -3);
  if (wire[0] == 0x14U) assert(status.action == 4U);
  assert(ftms_encode_machine_status(&status, encoded, sizeof encoded, &written) == FTMS_OK);
  assert(written == size);
  assert(memcmp(encoded, wire, size) == 0);
}

static void test_all_machine_opcodes(void) {
  static const uint8_t cases[][11] = {
    {0x01}, {0x02, 0x01}, {0x03}, {0x04}, {0x05, 0x34, 0x12},
    {0x06, 0xfe, 0xff}, {0x07, 0xfd, 0xff}, {0x08, 0xfe, 0xff},
    {0x09, 0x44}, {0x0a, 0x34, 0x12}, {0x0b, 0x34, 0x12},
    {0x0c, 0x34, 0x12}, {0x0d, 0x56, 0x34, 0x12}, {0x0e, 0x34, 0x12},
    {0x0f, 1, 0, 2, 0}, {0x10, 1, 0, 2, 0, 3, 0},
    {0x11, 1, 0, 2, 0, 3, 0, 4, 0, 5, 0},
    {0x12, 0xfe, 0xff, 0xfd, 0xff, 6, 7}, {0x13, 0x34, 0x12},
    {0x14, 0x04}, {0x15, 0x34, 0x12}, {0xff}
  };
  static const size_t sizes[] = {1U, 2U, 1U, 1U, 3U, 3U, 3U, 3U, 2U,
    3U, 3U, 3U, 4U, 3U, 5U, 7U, 11U, 7U, 3U, 2U, 3U, 1U};
  size_t i;
  for (i = 0U; i < sizeof sizes / sizeof sizes[0]; ++i) check_machine(cases[i], sizes[i]);
  for (i = 0U; i < sizeof sizes / sizeof sizes[0]; ++i) {
    size_t prefix;
    for (prefix = 0U; prefix < sizes[i]; ++prefix) {
      ftms_machine_status status = {0};
      assert(ftms_decode_machine_status(cases[i], prefix, &status) == FTMS_OK);
      if (prefix != 0U) assert(status.opcode == cases[i][0] && status.truncated == 1U);
    }
  }
}

static void test_machine_diagnostics(void) {
  uint8_t truncated[] = {0x07, 0x80};
  uint8_t unknown[] = {0x16, 7U};
  uint8_t reserved_stop[] = {0x02, 3U, 9U};
  ftms_machine_status status = {0};
  size_t i;
  for (i = 0U; i < sizeof truncated; ++i) {
    assert(ftms_decode_machine_status(truncated, i, &status) == FTMS_OK);
  }
  assert(ftms_decode_machine_status(truncated, sizeof truncated, &status) == FTMS_OK);
  assert(status.opcode == 0x07U && status.truncated == 1U && status.parameter_present == 0U);
  assert(ftms_decode_machine_status(unknown, sizeof unknown, &status) == FTMS_OK);
  assert(status.opcode == 0x16U && status.unknown_opcode == 1U);
  assert(ftms_encode_machine_status(&status, unknown, sizeof unknown, &i) == FTMS_ERROR_KIND);
  assert(ftms_decode_machine_status(reserved_stop, sizeof reserved_stop, &status) == FTMS_OK);
  assert(status.reserved_value == 1U && status.trailing_bytes == 1U);
}

static void test_training(void) {
  static const uint8_t text[] = {0xe2, 0x98, 0x83};
  uint8_t wire[] = {0x03, 0x0f, 0xe2, 0x98, 0x83};
  uint8_t invalid[] = {0x01, 0x01, 0xc0};
  uint8_t trailing[] = {0x00, 0x01, 0x99};
  ftms_training_status status = {0};
  uint8_t encoded[5] = {0xaa, 0xaa, 0xaa, 0xaa, 0xaa};
  size_t written = 77U;
  assert(ftms_decode_training_status(wire, sizeof wire, &status) == FTMS_OK);
  assert(status.text_present == 1U && status.extended_string == 1U && status.text_offset == 2U && status.text_size == sizeof text);
  assert(ftms_encode_training_status(&status, text, sizeof text, encoded, sizeof encoded, &written) == FTMS_OK);
  assert(written == sizeof wire && memcmp(encoded, wire, sizeof wire) == 0);
  assert(ftms_decode_training_status(invalid, sizeof invalid, &status) == FTMS_OK);
  assert(status.invalid_utf8 == 1U);
  assert(ftms_decode_training_status(trailing, sizeof trailing, &status) == FTMS_OK);
  assert(status.trailing_bytes == 1U);
  assert(ftms_decode_training_status(wire, 0U, &status) == FTMS_OK);
  assert(status.truncated == 1U && status.code == 0U);
  assert(ftms_decode_training_status(wire, 1U, &status) == FTMS_OK);
  assert(status.truncated == 1U && status.flags == wire[0]);
  status.flags = 0x01U; status.code = 0x10U;
  memset(encoded, 0xaa, sizeof encoded);
  written = 77U;
  assert(ftms_encode_training_status(&status, text, sizeof text, encoded, sizeof encoded, &written) == FTMS_ERROR_RANGE);
  assert(encoded[0] == 0xaaU && written == 77U);
}

int main(void) {
  test_all_machine_opcodes();
  test_machine_diagnostics();
  test_training();
  return 0;
}

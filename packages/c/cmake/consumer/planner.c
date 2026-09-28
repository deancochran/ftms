#include "ftms/measurement.h"

int main(void) {
  ftms_measurement snapshot = {0};
  size_t count = 0U;
  snapshot.kind = FTMS_MEASUREMENT_INDOOR_BIKE;
  snapshot.present = UINT64_C(1) << FTMS_M_SPEED;
  snapshot.value[FTMS_M_SPEED] = 0;
  return ftms_measurement_plan(&snapshot, 4U, NULL, 0U, &count) == FTMS_OK &&
                 count == 1U
             ? 0
             : 1;
}

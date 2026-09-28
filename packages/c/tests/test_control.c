#include <stdio.h>
#include <string.h>
#include "ftms/control.h"
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "control CHECK %d: %s\n", __LINE__, #x); return 1; } } while (0)

static int one(ftms_control_request r, const uint8_t *expected, size_t n) {
  uint8_t bytes[12] = {0xa5U}; ftms_control_request decoded; size_t written = 99U;
  CHECK(ftms_encode_control_request(&r, bytes, sizeof bytes, &written) == FTMS_OK);
  CHECK(written == n && memcmp(bytes, expected, n) == 0);
  CHECK(ftms_decode_control_request(bytes, n, &decoded) == FTMS_OK);
  CHECK(decoded.opcode == r.opcode);
  switch (r.opcode) {
    case FTMS_CONTROL_SET_TARGET_SPEED: CHECK(decoded.value.speed_centikph == r.value.speed_centikph); break;
    case FTMS_CONTROL_SET_TARGET_INCLINATION: CHECK(decoded.value.inclination_tenth_percent == r.value.inclination_tenth_percent); break;
    case FTMS_CONTROL_SET_TARGET_RESISTANCE: CHECK(decoded.value.resistance_tenth_level == r.value.resistance_tenth_level); break;
    case FTMS_CONTROL_SET_TARGET_POWER: CHECK(decoded.value.power_watts == r.value.power_watts); break;
    case FTMS_CONTROL_SET_TARGET_HEART_RATE: CHECK(decoded.value.heart_rate_bpm == r.value.heart_rate_bpm); break;
    case FTMS_CONTROL_STOP_PAUSE: CHECK(decoded.value.stop_pause == r.value.stop_pause); break;
    case FTMS_CONTROL_SET_TARGETED_EXPENDED_ENERGY: CHECK(decoded.value.energy_kcal == r.value.energy_kcal); break;
    case FTMS_CONTROL_SET_TARGETED_STEPS: CHECK(decoded.value.steps == r.value.steps); break;
    case FTMS_CONTROL_SET_TARGETED_STRIDES: CHECK(decoded.value.strides == r.value.strides); break;
    case FTMS_CONTROL_SET_TARGETED_DISTANCE: CHECK(decoded.value.distance_metres == r.value.distance_metres); break;
    case FTMS_CONTROL_SET_TARGETED_TRAINING_TIME: CHECK(decoded.value.training_seconds == r.value.training_seconds); break;
    case FTMS_CONTROL_SET_TARGETED_TIME_TWO_HR_ZONES:
    case FTMS_CONTROL_SET_TARGETED_TIME_THREE_HR_ZONES:
    case FTMS_CONTROL_SET_TARGETED_TIME_FIVE_HR_ZONES: CHECK(memcmp(decoded.value.zone_seconds, r.value.zone_seconds, (n - 1U)) == 0); break;
    case FTMS_CONTROL_SET_INDOOR_BIKE_SIMULATION: CHECK(memcmp(&decoded.value.simulation, &r.value.simulation, sizeof r.value.simulation) == 0); break;
    case FTMS_CONTROL_SET_WHEEL_CIRCUMFERENCE: CHECK(decoded.value.wheel_circumference_tenth_mm == r.value.wheel_circumference_tenth_mm); break;
    case FTMS_CONTROL_SPIN_DOWN: CHECK(decoded.value.spin_down == r.value.spin_down); break;
    case FTMS_CONTROL_SET_TARGETED_CADENCE: CHECK(decoded.value.cadence_half_rpm == r.value.cadence_half_rpm); break;
    default: break;
  }
  return 0;
}
static int boundary_contract(void) {
  union { ftms_control_request value; uint8_t bytes[sizeof(ftms_control_request)]; } request;
  union { ftms_control_response value; uint8_t bytes[sizeof(ftms_control_response)]; } response;
  uint8_t bytes[16], before[16];
  ftms_control_request saved_request;
  ftms_control_response saved_response;
  size_t written = 77;
  unsigned which;
  memset(&request, 0, sizeof request);
  request.value.opcode = FTMS_CONTROL_SET_TARGET_RESISTANCE;
  request.value.value.resistance_tenth_level = -12;
  CHECK(ftms_encode_control_request(&request.value, request.bytes, sizeof request.bytes, &written) == FTMS_OK);
  CHECK(written == 3 && memcmp(request.bytes, "\004\364\377", 3) == 0);
  CHECK(ftms_decode_control_request(request.bytes, 3, &request.value) == FTMS_OK);
  CHECK(request.value.opcode == FTMS_CONTROL_SET_TARGET_RESISTANCE && request.value.value.resistance_tenth_level == -12);
  memset(&response, 0, sizeof response);
  memcpy(response.bytes, "\200\023\001\350\003\210\023", 7);
  CHECK(ftms_decode_control_response(response.bytes, 7, &response.value) == FTMS_OK);
  CHECK(response.value.spin_down_low_centikph == 1000 && response.value.spin_down_high_centikph == 5000);
  CHECK(ftms_encode_control_response(&response.value, response.bytes, sizeof response.bytes, &written) == FTMS_OK);
  CHECK(written == 7 && memcmp(response.bytes, "\200\023\001\350\003\210\023", 7) == 0);
  for (which = 0; which < 4U; ++which) {
    size_t capacity = sizeof bytes;
    memset(bytes, 0xa5, sizeof bytes); memcpy(before, bytes, sizeof before); written = 77;
    memset(&request, 0, sizeof request);
    request.value.opcode = FTMS_CONTROL_SET_TARGET_SPEED;
    if (which == 0) capacity = 2;
    if (which == 1) request.value.opcode = (ftms_control_opcode)256;
    if (which == 2) { request.value.opcode = FTMS_CONTROL_STOP_PAUSE; request.value.value.stop_pause = (ftms_stop_pause_action)257; }
    CHECK(ftms_encode_control_request(which == 3 ? NULL : &request.value, bytes, capacity, &written) != FTMS_OK);
    CHECK(written == 77 && memcmp(bytes, before, sizeof bytes) == 0);
    memset(&response, 0, sizeof response);
    response.value.request_opcode = 0; response.value.result_code = 1;
    if (which == 1) response.value.request_opcode = 255;
    if (which == 2) response.value.result_code = 6;
    CHECK(ftms_encode_control_response(which == 3 ? NULL : &response.value, bytes, capacity, &written) != FTMS_OK);
    CHECK(written == 77 && memcmp(bytes, before, sizeof bytes) == 0);
  }
  memset(&request, 0xa5, sizeof request); memcpy(&saved_request, &request.value, sizeof saved_request);
  memset(&response, 0xa5, sizeof response); memcpy(&saved_response, &response.value, sizeof saved_response);
  for (which = 0; which < 4U; ++which) {
    size_t size = which == 0 ? 0 : (which == 1 ? 3 : 2);
    bytes[0] = which == 1 ? 255 : 8; bytes[1] = 0;
    CHECK(ftms_decode_control_request(which == 3 ? NULL : bytes, size, &request.value) != FTMS_OK);
    CHECK(memcmp(&request.value, &saved_request, sizeof saved_request) == 0);
    bytes[0] = which == 1 ? 255 : 128; bytes[1] = 19; bytes[2] = 1;
    CHECK(ftms_decode_control_response(which == 3 ? NULL : bytes, size, &response.value) != FTMS_OK);
    CHECK(memcmp(&response.value, &saved_response, sizeof saved_response) == 0);
  }
  return 0;
}
int test_control(void) {
  ftms_control_request r; uint8_t b[12], saved[12]; size_t w=77U;
  static const uint8_t expected[][11] = {{0},{1},{2,210,4},{3,244,255},{4,244,255},{5,156,255},{6,150},{7},{8,2},{9,244,1},{10,88,2},{11,188,2},{12,3,2,1},{13,16,14},{14,10,0,20,0},{15,10,0,20,0,30,0},{16,10,0,20,0,30,0,40,0,50,0},{17,232,3,250,0,10,20},{18,8,82},{19,1},{20,180,0}};
  static const size_t sizes[] = {1,1,3,3,3,3,2,1,2,3,3,3,4,3,5,7,11,7,3,2,3};
  unsigned op;
  for(op=0;op<21U;op++) { memset(&r,0,sizeof r); r.opcode=(ftms_control_opcode)op;
    switch(op) { case 2:r.value.speed_centikph=1234;break;case 3:r.value.inclination_tenth_percent=-12;break;case 4:r.value.resistance_tenth_level=-12;break;case 5:r.value.power_watts=-100;break;case 6:r.value.heart_rate_bpm=150;break;case 8:r.value.stop_pause=FTMS_PAUSE;break;case 9:r.value.energy_kcal=500;break;case 10:r.value.steps=600;break;case 11:r.value.strides=700;break;case 12:r.value.distance_metres=66051;break;case 13:r.value.training_seconds=3600;break;case 14:r.value.zone_seconds[0]=10;r.value.zone_seconds[1]=20;break;case 15:r.value.zone_seconds[0]=10;r.value.zone_seconds[1]=20;r.value.zone_seconds[2]=30;break;case 16:r.value.zone_seconds[0]=10;r.value.zone_seconds[1]=20;r.value.zone_seconds[2]=30;r.value.zone_seconds[3]=40;r.value.zone_seconds[4]=50;break;case 17:r.value.simulation.wind_millimetres_per_second=1000;r.value.simulation.grade_hundredth_percent=250;r.value.simulation.crr_ten_thousandth=10;r.value.simulation.cw_hundredth_kg_per_m=20;break;case 18:r.value.wheel_circumference_tenth_mm=21000;break;case 19:r.value.spin_down=FTMS_SPIN_DOWN_START;break;case 20:r.value.cadence_half_rpm=180;break;default:break; }
    CHECK(one(r, expected[op], sizes[op]) == 0);
  }
  memset(&r,0,sizeof r); r.opcode=FTMS_CONTROL_SET_TARGETED_DISTANCE;r.value.distance_metres=UINT32_C(0x01000000); memset(b,0x5a,sizeof b);memcpy(saved,b,sizeof b);CHECK(ftms_encode_control_request(&r,b,sizeof b,&w)==FTMS_ERROR_RANGE&&w==77U&&memcmp(b,saved,sizeof b)==0);
  r.opcode=FTMS_CONTROL_STOP_PAUSE;r.value.stop_pause=(ftms_stop_pause_action)3;CHECK(ftms_encode_control_request(&r,b,sizeof b,&w)==FTMS_ERROR_RANGE);
  r.opcode=(ftms_control_opcode)-1;CHECK(ftms_encode_control_request(&r,b,sizeof b,&w)==FTMS_ERROR_KIND);
  r.opcode=(ftms_control_opcode)256;CHECK(ftms_encode_control_request(&r,b,sizeof b,&w)==FTMS_ERROR_KIND);
  r.opcode=FTMS_CONTROL_STOP_PAUSE;r.value.stop_pause=(ftms_stop_pause_action)257;CHECK(ftms_encode_control_request(&r,b,sizeof b,&w)==FTMS_ERROR_RANGE);
  r.opcode=FTMS_CONTROL_SPIN_DOWN;r.value.spin_down=(ftms_spin_down_action)256;CHECK(ftms_encode_control_request(&r,b,sizeof b,&w)==FTMS_ERROR_RANGE);
  r.opcode=FTMS_CONTROL_SET_TARGET_SPEED;r.value.speed_centikph=1;CHECK(ftms_encode_control_request(&r,b,2U,&w)==FTMS_ERROR_LENGTH);
  b[0]=4;b[1]=1;b[2]=0;CHECK(ftms_decode_control_request(b,3U,&r)==FTMS_OK&&r.value.resistance_tenth_level==1);b[0]=8;b[1]=3;CHECK(ftms_decode_control_request(b,2U,&r)==FTMS_ERROR_RANGE);b[0]=21;CHECK(ftms_decode_control_request(b,1U,&r)==FTMS_ERROR_KIND);CHECK(ftms_decode_control_request(b,0U,&r)==FTMS_ERROR_LENGTH);CHECK(ftms_decode_control_request(b,SIZE_MAX,&r)==FTMS_ERROR_KIND);CHECK(ftms_encode_control_request(NULL,b,sizeof b,&w)==FTMS_ERROR_NULL);CHECK(ftms_encode_control_request(&r,NULL,sizeof b,&w)==FTMS_ERROR_NULL);CHECK(ftms_encode_control_request(&r,b,sizeof b,NULL)==FTMS_ERROR_NULL);
  { ftms_control_response x={19,1,FTMS_CONTROL_RESPONSE_SPIN_DOWN_SPEEDS,1000,5000,0,0,0}, y; uint8_t response[]={128,19,1,232,3,136,19};
    CHECK(ftms_encode_control_response(&x,b,sizeof b,&w)==FTMS_OK&&w==7U&&memcmp(b,response,7U)==0);CHECK(ftms_decode_control_response(response,7U,&y)==FTMS_OK&&y.parameter==FTMS_CONTROL_RESPONSE_SPIN_DOWN_SPEEDS&&y.spin_down_high_centikph==5000U);
    response[1]=21;CHECK(ftms_decode_control_response(response,3U,&y)==FTMS_OK&&y.unknown_request==1U);response[0]=129;CHECK(ftms_decode_control_response(response,3U,&y)==FTMS_ERROR_KIND);response[0]=128;response[1]=5;response[2]=1;response[3]=0;CHECK(ftms_decode_control_response(response,4U,&y)==FTMS_OK&&y.unexpected_parameters==1U);response[1]=19;CHECK(ftms_decode_control_response(response,4U,&y)==FTMS_ERROR_LENGTH);response[1]=5;response[2]=6;CHECK(ftms_decode_control_response(response,3U,&y)==FTMS_OK&&y.unknown_result==1U);
    x.result_code=6;CHECK(ftms_encode_control_response(&x,b,sizeof b,&w)==FTMS_ERROR_RANGE);x.result_code=2;x.request_opcode=21;x.parameter=FTMS_CONTROL_RESPONSE_NONE;CHECK(ftms_encode_control_response(&x,b,sizeof b,&w)==FTMS_OK);x.result_code=1;CHECK(ftms_encode_control_response(&x,b,sizeof b,&w)==FTMS_ERROR_KIND);
  }
  { union { ftms_control_response response; uint8_t bytes[sizeof(ftms_control_response)]; } overlap;
    memset(&overlap, 0, sizeof overlap); overlap.response.request_opcode=19;overlap.response.result_code=1;overlap.response.parameter=FTMS_CONTROL_RESPONSE_SPIN_DOWN_SPEEDS;overlap.response.spin_down_low_centikph=1000;overlap.response.spin_down_high_centikph=5000;
    CHECK(ftms_encode_control_response(&overlap.response,overlap.bytes,sizeof overlap.bytes,&w)==FTMS_OK&&w==7U&&memcmp(overlap.bytes,"\200\023\001\350\003\210\023",7U)==0);
    b[0]=0;b[1]=2;b[2]=0xd2;b[3]=4;CHECK(ftms_decode_control_request(b+1U,3U,&r)==FTMS_OK&&r.value.speed_centikph==1234U);
  }
  CHECK(boundary_contract() == 0);
  return 0;
}

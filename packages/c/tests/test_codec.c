#include <stdio.h>
#include <string.h>
#include "ftms/ftms.h"
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "CHECK failed: %s:%d: %s\n", __FILE__, __LINE__, #x); return 1; } } while (0)
int test_capabilities(void);
int test_control(void);
static int same(const void *a, const void *b, size_t n) { return memcmp(a,b,n)==0; }
int main(void) {
  uint8_t feature[9]={0x55U,0xffU,0xffU,1U,0U,0xffU,0xffU,1U,0U};
  ftms_features f={UINT32_C(0xdeadbeef),UINT32_C(0xcafebabe)}, saved=f;
  ftms_range r={FTMS_RANGE_SPEED,1,2,3,4,FTMS_UNIT_WATTS}, rs=r;
  uint8_t speed[6]={244U,1U,184U,11U,50U,0U}, inclination[6]={156U,255U,144U,1U,5U,0U};
  uint8_t power[6]={156U,255U,160U,15U,5U,0U}, resistance[3]={1U,100U,1U}, heart[3]={60U,200U,1U};
  uint8_t reverse[6]={232U,3U,100U,0U,1U,0U}, zero[6]={0U,0U,1U,0U,0U,0U};
  CHECK(ftms_decode_features(feature+1U,8U,&f)==FTMS_OK); CHECK(f.machine==UINT32_C(0x0001ffff)); CHECK(f.target==UINT32_C(0x0001ffff));
  { uint8_t zero_feature[8]={0U}; uint8_t one[8]={0U}; unsigned bit;
    CHECK(ftms_decode_features(zero_feature,8U,&f)==FTMS_OK); CHECK(f.machine==0U && f.target==0U);
    for (bit=0U;bit<17U;bit++) { memset(one,0,sizeof one); one[bit/8U]=(uint8_t)(UINT8_C(1) << (bit%8U)); CHECK(ftms_decode_features(one,8U,&f)==FTMS_OK); CHECK(f.machine==(UINT32_C(1)<<bit) && f.target==0U); memset(one,0,sizeof one); one[4U+bit/8U]=(uint8_t)(UINT8_C(1) << (bit%8U)); CHECK(ftms_decode_features(one,8U,&f)==FTMS_OK); CHECK(f.machine==0U && f.target==(UINT32_C(1)<<bit)); }
    memset(one,0,sizeof one); one[3]=UINT8_C(0x80); one[7]=UINT8_C(0x80); CHECK(ftms_decode_features(one,8U,&f)==FTMS_OK); CHECK(f.machine==UINT32_C(0x80000000) && f.target==UINT32_C(0x80000000));
  }
  { ftms_features before_failure=f; CHECK(ftms_decode_features(feature+1U,7U,&f)==FTMS_ERROR_LENGTH); CHECK(same(&f,&before_failure,sizeof f)); }
  CHECK(ftms_decode_features(NULL,8U,&f)==FTMS_ERROR_NULL); CHECK(ftms_decode_features(feature+1U,8U,NULL)==FTMS_ERROR_NULL);
  CHECK(ftms_decode_range(FTMS_RANGE_SPEED,speed,6U,&r)==FTMS_OK); CHECK(r.minimum==500 && r.maximum==3000 && r.increment==50 && r.scale_divisor==100U);
  CHECK(ftms_decode_range(FTMS_RANGE_INCLINATION,inclination,6U,&r)==FTMS_OK); CHECK(r.minimum==-100 && r.maximum==400 && r.increment==5 && r.scale_divisor==10U);
  CHECK(ftms_decode_range(FTMS_RANGE_POWER,power,6U,&r)==FTMS_OK); CHECK(r.minimum==-100 && r.maximum==4000 && r.increment==5);
  CHECK(ftms_decode_range(FTMS_RANGE_RESISTANCE_LEVEL,resistance,3U,&r)==FTMS_OK); CHECK(r.minimum==1 && r.maximum==100 && r.unit==FTMS_UNIT_LEVEL);
  CHECK(ftms_decode_range(FTMS_RANGE_HEART_RATE,heart,3U,&r)==FTMS_OK); CHECK(r.minimum==60 && r.maximum==200 && r.unit==FTMS_UNIT_BEATS_PER_MINUTE);
  CHECK(ftms_decode_range(FTMS_RANGE_SPEED,speed,5U,&r)==FTMS_ERROR_LENGTH); CHECK(ftms_decode_range(FTMS_RANGE_SPEED,speed,7U,&r)==FTMS_ERROR_LENGTH); CHECK(ftms_decode_range(FTMS_RANGE_SPEED,speed,SIZE_MAX,&r)==FTMS_ERROR_LENGTH);
  r=rs; CHECK(ftms_decode_range((ftms_range_kind)99,NULL,0U,&r)==FTMS_ERROR_KIND); CHECK(same(&r,&rs,sizeof r));
  CHECK(ftms_decode_range(FTMS_RANGE_SPEED,NULL,6U,&r)==FTMS_ERROR_NULL); CHECK(ftms_decode_range(FTMS_RANGE_SPEED,speed,6U,NULL)==FTMS_ERROR_NULL);
  r=rs; CHECK(ftms_decode_range(FTMS_RANGE_POWER,reverse,6U,&r)==FTMS_ERROR_RANGE); CHECK(same(&r,&rs,sizeof r));
  CHECK(ftms_decode_range(FTMS_RANGE_SPEED,zero,6U,&r)==FTMS_ERROR_RANGE);
  {
    ftms_range_inspection inspection;
    ftms_range_inspection saved_inspection;
    ftms_range_format_options signed_format = {FTMS_RESISTANCE_RANGE_SINT16_TENTHS};
    uint8_t alternate[6] = {0U,0U,100U,0U,1U,0U};
    CHECK(ftms_inspect_range(FTMS_RANGE_RESISTANCE_LEVEL,alternate,6U,&inspection)==FTMS_OK);
    CHECK(inspection.selected_profile==FTMS_RANGE_PROFILE_UINT8_WHOLE && inspection.observed_size==6U);
    CHECK(inspection.expected_size==3U && inspection.status==FTMS_RANGE_INSPECTION_LENGTH);
    CHECK(inspection.candidate_count==2U && inspection.candidates[1].profile==FTMS_RANGE_PROFILE_SINT16_TENTHS);
    CHECK(inspection.candidates[1].status==FTMS_RANGE_INSPECTION_VALID && inspection.candidates[1].value.maximum==100);
    CHECK(ftms_inspect_range_with_format(FTMS_RANGE_RESISTANCE_LEVEL,alternate,6U,&signed_format,&inspection)==FTMS_OK);
    CHECK(inspection.selected_profile==FTMS_RANGE_PROFILE_SINT16_TENTHS && inspection.status==FTMS_RANGE_INSPECTION_VALID);
    saved_inspection=inspection;
    CHECK(ftms_inspect_range_with_format(FTMS_RANGE_SPEED,alternate,6U,&signed_format,&inspection)==FTMS_ERROR_KIND);
    CHECK(same(&inspection,&saved_inspection,sizeof inspection));
    CHECK(ftms_inspect_range(FTMS_RANGE_SPEED,NULL,6U,&inspection)==FTMS_ERROR_NULL);
    CHECK(ftms_inspect_range(FTMS_RANGE_SPEED,alternate,SIZE_MAX,&inspection)==FTMS_OK);
    CHECK(inspection.status==FTMS_RANGE_INSPECTION_LENGTH && inspection.observed_size==SIZE_MAX);
  }
  { uint8_t extrema[6]={0U,128U,255U,127U,1U,0U}; CHECK(ftms_decode_range(FTMS_RANGE_POWER,extrema,6U,&r)==FTMS_OK); CHECK(r.minimum==-32768 && r.maximum==32767); }
  {
    uint8_t encoded[8] = {0U}; size_t written = 99U;
    ftms_features raw = {UINT32_C(0x81abcdef), UINT32_C(0xf0123456)};
    uint8_t expected[8] = {239U,205U,171U,129U,86U,52U,18U,240U};
    CHECK(ftms_encode_features(&raw,encoded,sizeof encoded,&written)==FTMS_OK);
    CHECK(written==8U && same(encoded,expected,sizeof expected));
    CHECK(ftms_decode_features(encoded,written,&f)==FTMS_OK && same(&f,&raw,sizeof raw));
    { union { ftms_features input; uint8_t bytes[sizeof(ftms_features)]; } overlap;
      overlap.input=raw; written=0U;
      CHECK(ftms_encode_features(&overlap.input,overlap.bytes,sizeof overlap.bytes,&written)==FTMS_OK);
      CHECK(written==8U && same(overlap.bytes,expected,8U)); }
    memset(encoded,0xa5,sizeof encoded); written=77U;
    CHECK(ftms_encode_features(&raw,encoded,7U,&written)==FTMS_ERROR_LENGTH);
    CHECK(written==77U && encoded[0]==0xa5U && encoded[7]==0xa5U);
    CHECK(ftms_encode_features(NULL,encoded,sizeof encoded,&written)==FTMS_ERROR_NULL);
    CHECK(ftms_encode_features(&raw,NULL,sizeof encoded,&written)==FTMS_ERROR_NULL);
    CHECK(ftms_encode_features(&raw,encoded,sizeof encoded,NULL)==FTMS_ERROR_NULL);
  }
  {
    struct range_vector { ftms_range value; uint8_t bytes[6]; size_t size; } vectors[] = {
      {{FTMS_RANGE_SPEED, 0, 65535, 1, 100U, FTMS_UNIT_KILOMETRES_PER_HOUR}, {0,0,255,255,1,0}, 6U},
      {{FTMS_RANGE_INCLINATION, -32768, 32767, 65535, 10U, FTMS_UNIT_PERCENT}, {0,128,255,127,255,255}, 6U},
      {{FTMS_RANGE_POWER, -100, 4000, 5, 1U, FTMS_UNIT_WATTS}, {156,255,160,15,5,0}, 6U},
      {{FTMS_RANGE_RESISTANCE_LEVEL, 1, 255, 1, 1U, FTMS_UNIT_LEVEL}, {1,255,1,0,0,0}, 3U},
      {{FTMS_RANGE_HEART_RATE, 60, 200, 1, 1U, FTMS_UNIT_BEATS_PER_MINUTE}, {60,200,1,0,0,0}, 3U}
    };
    size_t i;
    for (i=0U;i<sizeof vectors/sizeof vectors[0];i++) {
      uint8_t encoded[6]={0}; size_t written=0U; ftms_range decoded;
      CHECK(ftms_encode_range(&vectors[i].value,encoded,sizeof encoded,&written)==FTMS_OK);
      CHECK(written==vectors[i].size && same(encoded,vectors[i].bytes,written));
      CHECK(ftms_decode_range(vectors[i].value.kind,encoded,written,&decoded)==FTMS_OK);
      CHECK(decoded.kind==vectors[i].value.kind && decoded.minimum==vectors[i].value.minimum &&
            decoded.maximum==vectors[i].value.maximum && decoded.increment==vectors[i].value.increment &&
            decoded.scale_divisor==vectors[i].value.scale_divisor && decoded.unit==vectors[i].value.unit);
    }
    { union { ftms_range input; uint8_t bytes[sizeof(ftms_range)]; } overlap; size_t written=0U;
      overlap.input=vectors[2].value;
      CHECK(ftms_encode_range(&overlap.input,overlap.bytes,sizeof overlap.bytes,&written)==FTMS_OK);
      CHECK(written==6U && same(overlap.bytes,vectors[2].bytes,6U)); }
    { uint8_t encoded[6]={9,9,9,9,9,9}; size_t written=55U; ftms_range bad=vectors[0].value;
      bad.kind=(ftms_range_kind)-1; CHECK(ftms_encode_range(&bad,encoded,sizeof encoded,&written)==FTMS_ERROR_KIND);
      bad.kind=(ftms_range_kind)256; CHECK(ftms_encode_range(&bad,encoded,sizeof encoded,&written)==FTMS_ERROR_KIND);
      bad=vectors[0].value; bad.unit=FTMS_UNIT_WATTS; CHECK(ftms_encode_range(&bad,encoded,sizeof encoded,&written)==FTMS_ERROR_RANGE);
      bad=vectors[0].value; bad.scale_divisor=1U; CHECK(ftms_encode_range(&bad,encoded,sizeof encoded,&written)==FTMS_ERROR_RANGE);
      bad=vectors[0].value; bad.minimum=2; bad.maximum=1; CHECK(ftms_encode_range(&bad,encoded,sizeof encoded,&written)==FTMS_ERROR_RANGE);
      bad=vectors[0].value; bad.increment=0; CHECK(ftms_encode_range(&bad,encoded,sizeof encoded,&written)==FTMS_ERROR_RANGE);
      bad=vectors[0].value; bad.maximum=INT32_MAX; CHECK(ftms_encode_range(&bad,encoded,sizeof encoded,&written)==FTMS_ERROR_RANGE);
      bad=vectors[3].value; bad.maximum=256; CHECK(ftms_encode_range(&bad,encoded,sizeof encoded,&written)==FTMS_ERROR_RANGE);
      CHECK(written==55U && encoded[0]==9U && encoded[5]==9U);
      CHECK(ftms_encode_range(NULL,encoded,sizeof encoded,&written)==FTMS_ERROR_NULL);
      CHECK(ftms_encode_range(&vectors[0].value,NULL,sizeof encoded,&written)==FTMS_ERROR_NULL);
      CHECK(ftms_encode_range(&vectors[0].value,encoded,sizeof encoded,NULL)==FTMS_ERROR_NULL);
      written=66U; CHECK(ftms_encode_range(&vectors[0].value,encoded,0U,&written)==FTMS_ERROR_LENGTH && written==66U);
    }
  }
  (void)saved; if (test_control() != 0) return 1; return test_capabilities();
}

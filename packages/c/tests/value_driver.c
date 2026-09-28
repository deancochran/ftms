#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#include "ftms/ftms.h"

static int kind(const char *text, ftms_range_kind *out) {
  if (strcmp(text,"speed")==0) *out=FTMS_RANGE_SPEED;
  else if (strcmp(text,"inclination")==0) *out=FTMS_RANGE_INCLINATION;
  else if (strcmp(text,"resistance")==0) *out=FTMS_RANGE_RESISTANCE_LEVEL;
  else if (strcmp(text,"heartRate")==0) *out=FTMS_RANGE_HEART_RATE;
  else if (strcmp(text,"power")==0) *out=FTMS_RANGE_POWER;
  else return 0;
  return 1;
}
static void hex(const uint8_t *p, size_t n) { size_t i; for(i=0;i<n;i++) printf("%02x",(unsigned)p[i]); }
static int i32(const char *text, int32_t *out) { char *end; long long value; errno=0; value=strtoll(text,&end,10); if(errno || end==text || *end!='\0' || value < INT32_MIN || value > INT32_MAX) return 0; *out=(int32_t)value; return 1; }
static int u16(const char *text, uint16_t *out) { char *end; long long value; errno=0; value=strtoll(text,&end,10); if(errno || end==text || *end!='\0' || value < 0 || value > UINT16_MAX) return 0; *out=(uint16_t)value; return 1; }
static int u32(const char *text, uint32_t *out) { char *end; long long value; errno=0; value=strtoll(text,&end,10); if(errno || end==text || *end!='\0' || value < 0 || value > UINT32_MAX) return 0; *out=(uint32_t)value; return 1; }
int main(int argc, char **argv) {
  uint8_t out[8]; size_t n=0U; ftms_result result;
  if (argc==4 && strcmp(argv[1],"features")==0) { ftms_features f; if(!u32(argv[2],&f.machine) || !u32(argv[3],&f.target)) return 64; result=ftms_encode_features(&f,out,sizeof out,&n); }
  else if ((argc==8 || argc==9) && strcmp(argv[1],"range")==0) { ftms_range r; int32_t unit, selected; ftms_range_format_options format; const ftms_range_format_options *options=NULL; if(!kind(argv[2],&r.kind) || !i32(argv[3],&r.minimum) || !i32(argv[4],&r.maximum) || !i32(argv[5],&r.increment) || !u16(argv[6],&r.scale_divisor) || !i32(argv[7],&unit) || unit<0 || unit>INT_MAX) return 64; if(argc==9) { if(!i32(argv[8],&selected) || selected<0 || selected>1) return 64; format.resistance_format=(ftms_resistance_range_format)selected; options=&format; } r.unit=(ftms_range_unit)unit; result=ftms_encode_range_with_format(&r,options,out,sizeof out,&n); }
  else return 64;
  if(result!=FTMS_OK) { printf("error %d\n",(int)result); return 0; }
  printf("ok "); hex(out,n); printf(" %lu\n",(unsigned long)n); return 0;
}

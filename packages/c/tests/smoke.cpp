#include "ftms/capabilities.h"
#include "ftms/capabilities.h"
int main() { ftms_features f{}; unsigned char b[8] = {}; ftms_cap_snapshot s={FTMS_CAP_DISCOVERY_COMPLETE,FTMS_CAP_SERVICE_PRESENT,0U,nullptr,0U}; ftms_cap_requirements q{}; return ftms_decode_features(b, sizeof b, &f) != FTMS_OK || ftms_capability_requirements(&s,&q) != FTMS_OK; }

#include "ftms/ftms.h"
int main(void) { ftms_features f = {0U, 0U}; return ftms_decode_features((const uint8_t *)"\0\0\0\0\0\0\0\0", 8U, &f) != FTMS_OK; }

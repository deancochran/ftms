# Host verification only; no CMake dependency or toolchain download is required.
CC ?= cc
AR ?= ar
CFLAGS = -std=c99 -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Werror -Iinclude
BUILD = build
PREFIX ?= /usr/local
DESTDIR ?=

all: $(BUILD)/libftms.a
$(BUILD):
	mkdir -p $(BUILD)
$(BUILD)/ftms.o: src/ftms.c include/ftms/ftms.h | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@
$(BUILD)/capabilities.o: src/capabilities.c include/ftms/capabilities.h include/ftms/ftms.h | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@
$(BUILD)/control.o: src/control.c include/ftms/control.h include/ftms/ftms.h | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@
$(BUILD)/measurement.o: src/measurement.c include/ftms/measurement.h include/ftms/ftms.h | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@
$(BUILD)/status.o: src/status.c include/ftms/status.h include/ftms/control.h include/ftms/ftms.h | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@
$(BUILD)/libftms.a: $(BUILD)/ftms.o $(BUILD)/control.o $(BUILD)/capabilities.o $(BUILD)/measurement.o $(BUILD)/status.o
	$(AR) rcs $@ $^
install: $(BUILD)/libftms.a
	install -d "$(DESTDIR)$(PREFIX)/include/ftms" "$(DESTDIR)$(PREFIX)/lib"
	install -m 644 include/ftms/*.h "$(DESTDIR)$(PREFIX)/include/ftms/"
	install -m 644 $(BUILD)/libftms.a "$(DESTDIR)$(PREFIX)/lib/libftms.a"
test: $(BUILD)/libftms.a
	$(CC) $(CFLAGS) src/ftms.c src/status.c tests/status_driver.c -o $(BUILD)/status-driver
	python3 -m unittest tests/test_status_adapter.py
	python3 tests/status_adapter.py $(BUILD)/status-driver
	$(CC) $(CFLAGS) src/ftms.c src/measurement.c tests/measurement_driver.c -o $(BUILD)/measurement-driver
	python3 -m unittest tests/test_measurement_adapter.py
	python3 tests/measurement_adapter.py $(BUILD)/measurement-driver
	$(CC) $(CFLAGS) src/ftms.c src/measurement.c tests/test_measurement.c -o $(BUILD)/test-measurement
	$(BUILD)/test-measurement
	clang $(CFLAGS) -fsanitize=address,undefined -fno-omit-frame-pointer src/ftms.c src/measurement.c tests/test_measurement.c -o $(BUILD)/test-measurement-sanitized
	$(BUILD)/test-measurement-sanitized
	$(CC) $(CFLAGS) src/ftms.c src/status.c tests/test_status.c -o $(BUILD)/test-status
	$(BUILD)/test-status
	clang $(CFLAGS) -fsanitize=address,undefined -fno-omit-frame-pointer src/ftms.c src/status.c tests/test_status.c -o $(BUILD)/test-status-sanitized
	$(BUILD)/test-status-sanitized
	$(CC) $(CFLAGS) src/ftms.c src/control.c tests/control_driver.c -o $(BUILD)/control-driver
	$(CC) $(CFLAGS) src/ftms.c tests/value_driver.c -o $(BUILD)/value-driver
	$(CC) $(CFLAGS) src/ftms.c tests/corpus_driver.c -o $(BUILD)/corpus-driver
	python3 -m unittest tests/test_value_adapter.py
	python3 tests/value_adapter.py $(BUILD)/value-driver $(BUILD)/corpus-driver
	python3 -m unittest tests/test_corpus_adapter.py
	python3 -m unittest tests/test_capability_corpus.py
	python3 -m unittest tests/test_control_adapter.py
	$(CC) $(CFLAGS) src/ftms.c src/control.c src/capabilities.c tests/test_codec.c tests/test_control.c tests/test_capabilities.c -o $(BUILD)/test-codec
	$(BUILD)/test-codec
	$(CC) $(CFLAGS) src/ftms.c src/capabilities.c tests/capability_driver.c -o $(BUILD)/capability-driver
	python3 tests/capability_adapter.py $(BUILD)/capability-driver
	clang $(CFLAGS) -fsanitize=address,undefined -fno-omit-frame-pointer src/ftms.c src/control.c src/capabilities.c tests/test_codec.c tests/test_control.c tests/test_capabilities.c -o $(BUILD)/test-codec-sanitized
	$(BUILD)/test-codec-sanitized
	clang $(CFLAGS) -fsanitize=address,undefined -fno-omit-frame-pointer src/ftms.c src/control.c src/capabilities.c tests/fuzz.c -o $(BUILD)/fuzz
	$(BUILD)/fuzz
	clang $(CFLAGS) -fsanitize=address,undefined -fno-omit-frame-pointer src/ftms.c src/measurement.c src/status.c tests/fuzz_measurement_status.c -o $(BUILD)/fuzz-measurement-status
	$(BUILD)/fuzz-measurement-status
	$(CC) $(CFLAGS) src/ftms.c tests/corpus_driver.c -o $(BUILD)/corpus-driver
	python3 tests/compatibility_adapter.py $(BUILD)/measurement-driver $(BUILD)/corpus-driver $(BUILD)/value-driver
	python3 tests/corpus_adapter.py $(BUILD)/corpus-driver $(BUILD)/control-driver $(BUILD)/measurement-driver $(BUILD)/status-driver
	python3 tests/control_adapter.py $(BUILD)/control-driver
	python3 scripts/verify-consumers.py
	python3 scripts/verify-source-bundle.py
	python3 -m unittest tests/test_source_bundle.py
# Compile-only evidence, not a linked image or board execution. ABI helpers are
# intentionally reported; consumers must provide their embedded compiler runtime.
check-embedded: | $(BUILD)
	clang --target=arm-none-eabi -mcpu=cortex-m0 -mthumb $(CFLAGS) -Oz -ffreestanding -fstack-usage -c src/ftms.c -o $(BUILD)/ftms-cortex-m0.o
	clang --target=arm-none-eabi -mcpu=cortex-m0 -mthumb $(CFLAGS) -Oz -ffreestanding -fstack-usage -c src/control.c -o $(BUILD)/control-cortex-m0.o
	clang --target=arm-none-eabi -mcpu=cortex-m0 -mthumb $(CFLAGS) -Oz -ffreestanding -fstack-usage -c src/capabilities.c -o $(BUILD)/capabilities-cortex-m0.o
	clang --target=arm-none-eabi -mcpu=cortex-m0 -mthumb $(CFLAGS) -Oz -ffreestanding -fstack-usage -c src/measurement.c -o $(BUILD)/measurement-cortex-m0.o
	clang --target=arm-none-eabi -mcpu=cortex-m0 -mthumb $(CFLAGS) -Oz -ffreestanding -fstack-usage -c src/status.c -o $(BUILD)/status-cortex-m0.o
	size $(BUILD)/ftms-cortex-m0.o $(BUILD)/control-cortex-m0.o $(BUILD)/capabilities-cortex-m0.o $(BUILD)/measurement-cortex-m0.o $(BUILD)/status-cortex-m0.o
	nm -u $(BUILD)/ftms-cortex-m0.o $(BUILD)/control-cortex-m0.o $(BUILD)/capabilities-cortex-m0.o $(BUILD)/measurement-cortex-m0.o $(BUILD)/status-cortex-m0.o
	cat $(BUILD)/ftms-cortex-m0.su $(BUILD)/control-cortex-m0.su $(BUILD)/capabilities-cortex-m0.su $(BUILD)/measurement-cortex-m0.su $(BUILD)/status-cortex-m0.su
clean:
	rm -rf $(BUILD)
.PHONY: all install test check-embedded clean

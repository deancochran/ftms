import 'dart:typed_data';

import 'package:deancochran_ftms/deancochran_ftms.dart';

void main() {
  // Synthetic Indoor Bike Data, not a device capture.
  final bytes = Uint8List.fromList([0x44, 0, 0x10, 0x0e, 0xb4, 0, 0xfa, 0]);
  final universal = decodeFtmsMeasurement('0x2ad2', bytes);
  if (universal.status != MeasurementUuidDecodeStatus.known) {
    throw StateError('Indoor Bike UUID was not recognized');
  }
  final metrics = universal.normalized!;
  if (metrics.speedMps != 10 ||
      metrics.cadenceRpm != 90 ||
      metrics.powerWatts != 250) {
    throw StateError('Unexpected decoded measurement');
  }
  print(
    '${metrics.speedMps} m/s, ${metrics.cadenceRpm} rpm, ${metrics.powerWatts} W',
  );

  // Producing these bytes does not authorize transmitting them to equipment.
  final request = encodeControlRequest(ControlRequest(5, [250]));
  if (request.length != 3 ||
      request[0] != 5 ||
      request[1] != 250 ||
      request[2] != 0) {
    throw StateError('Unexpected target-power encoding');
  }
}

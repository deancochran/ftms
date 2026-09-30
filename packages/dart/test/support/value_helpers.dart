import 'dart:convert';
import 'dart:typed_data';

import 'corpus.dart';

Map<String, Object?> fixture(String name) =>
    (jsonDecode(
              readCorpus(
                '../../shared/conformance/$name/v1/${name == 'inspection' ? 'fixtures' : 'vectors'}.json',
              ),
            )
            as Map<Object?, Object?>)
        .cast<String, Object?>();
List<Object?> objects(Object? value) => value as List<Object?>;
Map<String, Object?> object(Object? value) =>
    (value as Map<Object?, Object?>).cast<String, Object?>();
Uint8List wire(Object? values) =>
    Uint8List.fromList(objects(values).cast<int>());

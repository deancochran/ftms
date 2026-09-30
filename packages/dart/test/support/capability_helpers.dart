import 'dart:convert';
import 'dart:typed_data';

import 'package:deancochran_ftms/deancochran_ftms.dart';

CapabilitySnapshot snapshotFromJson(Map<String, Object?> value) {
  final c7 = value['c7'] as Map<String, Object?>?;
  return CapabilitySnapshot(
    discovery: CapabilityDiscovery.values[value['discovery'] as int],
    scope: CapabilityServiceScope.values[value['scope'] as int],
    generation: value['generation'] as int,
    c7: c7 == null
        ? null
        : CapabilityC7Evidence(
            bondingSupported:
                CapabilityTruth.values[c7['bondingSupported'] as int],
            featureMayChangeOverLifetime: CapabilityTruth
                .values[c7['featureMayChangeOverLifetime'] as int],
          ),
    characteristics: (value['characteristics'] as List<Object?>).map((item) {
      final c = item as Map<String, Object?>;
      return CapabilityCharacteristic(
        uuid: c['uuid'] as String,
        properties: c['properties'] as int,
        readState: CapabilityReadState.values[c['readState'] as int],
        reason: CapabilityReadReason.values[c['reason'] as int],
        bytes: _hex(c['bytes'] as String),
      );
    }).toList(),
  );
}

Uint8List _hex(String source) => Uint8List.fromList([
  for (var i = 0; i < source.length; i += 2)
    int.parse(source.substring(i, i + 2), radix: 16),
]);

/// Corpus expansion only; it does not invoke capability interpretation.
Object? expand(Map<String, Object?> templates, Map<String, Object?> expansion) {
  final name = expansion['template'];
  if (name is! String || !templates.containsKey(name)) {
    throw FormatException('unknown template');
  }
  var root = _copy(templates[name]);
  for (final raw in expansion['edits']! as List<Object?>) {
    root = _edit(root, raw as Map<String, Object?>);
  }
  return root;
}

Object? _copy(Object? value) => jsonDecode(jsonEncode(value));
Object? _edit(Object? root, Map<String, Object?> edit) {
  final path = edit['path'];
  if (path is! List<Object?>) throw FormatException('path');
  final op = edit['op'] ?? 'replace';
  if (op is! String ||
      !const {'replace', 'append', 'remove'}.contains(op) ||
      (op == 'remove'
          ? edit.containsKey('value')
          : !edit.containsKey('value'))) {
    throw FormatException('edit');
  }
  if (path.isEmpty) {
    if (op != 'replace') {
      throw FormatException('root');
    }
    return _copy(edit['value']);
  }
  final parts = List<Object?>.from(path);
  final last = parts.removeLast();
  final parents = _walk([root], parts);
  for (final parent in parents) {
    for (final target in _targets(parent, last, op == 'replace')) {
      if (op == 'replace') {
        _set(parent, target, _copy(edit['value']));
      } else if (op == 'append') {
        final array = _get(parent, target);
        if (array is! List) {
          throw FormatException('append');
        }
        array.add(_copy(edit['value']));
      } else {
        _remove(parent, target);
      }
    }
  }
  return root;
}

List<Object?> _walk(List<Object?> current, List<Object?> segments) {
  for (final segment in segments) {
    final next = <Object?>[];
    for (final node in current) {
      for (final target in _targets(node, segment, true)) {
        next.add(_get(node, target));
      }
    }
    current = next;
  }
  return current;
}

List<Object> _targets(Object? container, Object? segment, bool replace) {
  if (container is Map<String, Object?>) {
    if (segment is! String || !container.containsKey(segment)) {
      throw FormatException('key');
    }
    return [segment];
  }
  if (container is List) {
    if (segment == '*' && replace) {
      return List.generate(container.length, (i) => i);
    }
    if (segment is List<Object?>) {
      if (!replace ||
          segment.toSet().length != segment.length ||
          segment.any((x) => x is! int || x < 0 || x >= container.length)) {
        throw FormatException('selection');
      }
      return segment.cast<int>();
    }
    if (segment is! int || segment < 0 || segment >= container.length) {
      throw FormatException('index');
    }
    return [segment];
  }
  throw FormatException('container');
}

Object? _get(Object? parent, Object target) => parent is List
    ? parent[target as int]
    : (parent as Map<String, Object?>)[target as String];
void _set(Object? parent, Object target, Object? value) {
  if (parent is List) {
    parent[target as int] = value;
  } else {
    (parent as Map<String, Object?>)[target as String] = value;
  }
}

void _remove(Object? parent, Object target) {
  if (parent is List) {
    parent.removeAt(target as int);
  } else {
    (parent as Map<String, Object?>).remove(target as String);
  }
}

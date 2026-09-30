import 'dart:io';

String readCorpus(String path) => File(path).readAsStringSync();

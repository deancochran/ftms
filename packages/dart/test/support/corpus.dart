/// Test-only access to canonical files. Browser data is generated, never edited.
library;

export 'corpus_vm.dart' if (dart.library.js_interop) 'corpus_browser.g.dart';

import json, unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
m = SourceFileLoader("release_assets", str(Path(__file__).with_name("github-release-assets.py"))).load_module()
SHA = "a" * 40
class Tests(unittest.TestCase):
 def test_plan_absent_matching_partial_mismatch_and_tag(self):
  self.assertEqual(m.plan_release("c-v1", SHA, {"a":"1"}, {"commit":SHA,"exists":False,"assets":{}}), ["create"])
  with self.assertRaises(ValueError): m.plan_release("c-v1", SHA, {"a":"1"}, {"commit":"b"*40,"exists":False,"assets":{}})
  self.assertEqual(m.plan_release("c-v1", SHA, {"a":"1"}, {"commit":SHA,"assets":{"a":"1"}}), ["continue"])
  self.assertEqual(m.plan_release("c-v1", SHA, {"a":"1","b":"2"}, {"commit":SHA,"assets":{"a":"1"}}), ["upload:b"])
  with self.assertRaises(ValueError): m.plan_release("bad tag", SHA, {}, None)
  with self.assertRaises(ValueError): m.plan_release("c-v1", SHA, {"a":"2"}, {"commit":SHA,"assets":{"a":"1"}})
 def test_api_shape_peels_tag_and_downloads_null_digest(self):
  calls=[]
  def call(args, binary=False):
   calls.append((args,binary))
   if "/commits/" in args[2]: return SHA
   if "/releases/tags/" in args[2]: return json.dumps({"assets":[{"name":"a","url":"assets/7","digest":None}]})
   return b"bytes" if binary else ""
  state=m.remote_release("owner/repo", "c-v1", call)
  self.assertEqual(state, {"commit":SHA,"assets":{"a":"277089d91c0bdf4f2e6862ba7e4a07605119431f5d13f726dd352b06f1b206a9"}})
  self.assertTrue(any(binary for _,binary in calls))
 def test_definite_404_is_absent(self):
  def call(args, binary=False):
   if "/commits/" in args[2]: return SHA
   raise RuntimeError("HTTP 404: Not Found")
  self.assertEqual(m.remote_release("o/r", "c-v1", call), {"commit":SHA,"exists":False,"assets":{}})
 def test_non_404_fails_closed(self):
  def call(args, binary=False):
   if "/commits/" in args[2]: return SHA
   raise RuntimeError("HTTP 403: Forbidden")
  with self.assertRaises(RuntimeError): m.remote_release("o/r", "c-v1", call)

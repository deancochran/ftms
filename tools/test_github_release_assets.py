import json, unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
m = SourceFileLoader("release_assets", str(Path(__file__).with_name("github-release-assets.py"))).load_module()
SHA = "a" * 40
class Tests(unittest.TestCase):
 def test_upload_must_be_followed_by_complete_public_verification(self):
  args=SimpleNamespace(files=["archive.tgz"], repo="owner/repo", tag="c-v1", commit=SHA, title="release", notes="notes.md", not_latest=True)
  absent={"commit":SHA,"exists":False,"assets":{}}
  for public in ({"commit":SHA,"assets":{"archive.tgz":"digest"}}, absent, {"commit":SHA,"assets":{"archive.tgz":"wrong"}}):
   with self.subTest(public=public), patch.object(m, "sha256", return_value="digest"), patch.object(m, "remote_release", side_effect=[absent, public]) as remote, patch.object(m.subprocess, "run") as execute:
    if public.get("assets", {}).get("archive.tgz") == "digest": m.run(args)
    else:
     with self.assertRaises(ValueError): m.run(args)
    execute.assert_called_once()
    self.assertEqual(remote.call_args.kwargs, {"download":True})
 def test_plan_absent_matching_partial_mismatch_and_tag(self):
  self.assertEqual(m.plan_release("c-v1", SHA, {"a":"1"}, {"commit":SHA,"exists":False,"assets":{}}), ["create"])
  with self.assertRaises(ValueError): m.plan_release("c-v1", SHA, {"a":"1"}, {"commit":"b"*40,"exists":False,"assets":{}})
  self.assertEqual(m.plan_release("c-v1", SHA, {"a":"1"}, {"commit":SHA,"assets":{"a":"1"}}), ["continue"])
  self.assertEqual(m.plan_release("c-v1", SHA, {"a":"1","b":"2"}, {"commit":SHA,"assets":{"a":"1"}}), ["upload:b"])
  with self.assertRaises(ValueError): m.plan_release("bad tag", SHA, {}, None)
  with self.assertRaises(ValueError): m.plan_release("c-v1", SHA, {"a":"2"}, {"commit":SHA,"assets":{"a":"1"}})
  with self.assertRaises(ValueError): m.plan_release("c-v1", SHA, {"a":"1"}, {"commit":SHA,"assets":{"a":"1","extra":"2"}})
 def test_post_upload_downloads_even_when_api_has_digest(self):
  def call(args, binary=False):
   if "/commits/" in args[2]: return SHA
   if "/releases/tags/" in args[2]: return json.dumps({"assets":[{"name":"a","url":"assets/7","digest":"sha256:untrusted"}]})
   self.assertTrue(binary)
   return b"bytes"
  state=m.remote_release("owner/repo", "c-v1", call, download=True)
  self.assertEqual(state["assets"]["a"], "277089d91c0bdf4f2e6862ba7e4a07605119431f5d13f726dd352b06f1b206a9")
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

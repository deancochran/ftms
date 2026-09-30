import json, unittest, urllib.error
from pathlib import Path
from importlib.machinery import SourceFileLoader
m=SourceFileLoader("retry",str(Path(__file__).parents[1]/"scripts/release_retry.py")).load_module()
class Tests(unittest.TestCase):
 def test_absent_partial_identical_and_mismatch(self):
  expected={"a":"1","b":"2"}
  def absent(_): raise urllib.error.HTTPError("url",404,"missing",None,None)
  self.assertEqual(m.plan("1",expected,absent),["a","b"])
  self.assertEqual(m.plan("1",expected,lambda _:json.dumps({"urls":[{"filename":"a","digests":{"sha256":"1"}}]})),["b"])
  self.assertEqual(m.plan("1",expected,lambda _:json.dumps({"urls":[{"filename":"a","digests":{"sha256":"1"}},{"filename":"b","digests":{"sha256":"2"}}]})),[])
  with self.assertRaises(ValueError): m.plan("1",expected,lambda _:json.dumps({"urls":[{"filename":"a","digests":{"sha256":"x"}}]}))
  with self.assertRaises(ValueError): m.plan("1",expected,lambda _:json.dumps({"urls":[{"filename":"a","digests":{}}]}))
 def test_registry_errors_are_not_absence(self):
  def forbidden(_): raise urllib.error.HTTPError("url",403,"forbidden",None,None)
  with self.assertRaises(urllib.error.HTTPError): m.plan("1",{"a":"1"},forbidden)
  def unavailable(_): raise urllib.error.URLError("offline")
  with self.assertRaises(urllib.error.URLError): m.plan("1",{"a":"1"},unavailable)

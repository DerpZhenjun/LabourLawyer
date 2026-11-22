import json
from hashlib import sha256
import tempfile
import unittest
from pathlib import Path

from compact_proof_experiment import Capsule

class CompactProofTests(unittest.TestCase):
    def setUp(self):
        self.scope = tempfile.TemporaryDirectory()
        self.root = Path(self.scope.name)
        self.addCleanup(self.scope.cleanup)
        self.body = b'isolated synthetic original fixture'
        self.sha = sha256(self.body).hexdigest()
        self.source = '1' * 24
        self.contract = '2' * 64
        self.entry = {'region_code':'320281','kind':'application','source_id':self.source,
                      'original_sha256':self.sha,'contract_id':self.contract,
                      'template_id':'fixture-1','version':1}
        self.path = self.root / (self.sha+'.docx')
        self.path.write_bytes(self.body)

    def capsule(self,entries):
        data = json.dumps({'schema':'PILOT_QA_EXPERIMENT_ONLY','rows':entries}).encode()
        return Capsule(data,sha256(data).hexdigest())

    def test_same_binding_and_bytes(self):
        self.assertEqual(self.capsule([self.entry]).resolve(self.root,self.entry), self.body)

    def test_cross_region_and_stale_contract(self):
        capsule=self.capsule([self.entry])
        for bad in (dict(self.entry,region_code='320282'),dict(self.entry,version=2),
                    dict(self.entry,contract_id='3'*64),dict(self.entry,kind='evidence')):
            with self.subTest(field=bad):
                with self.assertRaises(ValueError):
                    capsule.resolve(self.root,bad)

    def test_provider_namespace_does_not_become_a_file_path(self):
        valid=dict(self.entry,template_id='official-source:blank')
        self.assertEqual(self.capsule([valid]).resolve(self.root,valid),self.body)
        invalid=dict(valid,template_id='C:/other')
        with self.assertRaises(ValueError):
            self.capsule([invalid])

    def test_modified_original_is_rejected(self):
        capsule=self.capsule([self.entry])
        self.path.write_bytes(b'modified')
        with self.assertRaises(ValueError):
            capsule.resolve(self.root,self.entry)

    def test_bad_capsule_digest_or_duplicate(self):
        with self.assertRaises(ValueError):
            Capsule(b'{}','0'*64)
        with self.assertRaises(ValueError):
            self.capsule([self.entry,self.entry])

    def test_no_additional_attachment_roles_or_paths(self):
        unsafe=dict(self.entry,attachment='../../old-case.docx')
        with self.assertRaises(ValueError):
            self.capsule([unsafe])

if __name__=='__main__':
    unittest.main()

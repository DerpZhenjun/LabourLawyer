"""Candidate preparation is isolated, repeat-safe and never a server launcher."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import sqlite3
from contextlib import closing
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from candidate_review import prepare,verify,extend_hunan


class CandidateReviewTests(unittest.TestCase):
    def test_prepared_data_is_exact_and_never_replaces_existing_stores(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.runtime') as folder:
            self.assertTrue(Path(folder).resolve().is_relative_to((ROOT/'.runtime').resolve()))
            output=Path(folder)/'candidate'
            result=prepare(ROOT,output)
            self.assertEqual((result['guides'],result['candidate_guides'],result['generatable_localities']),(188,7,171))
            self.assertEqual(len(set(result['candidate_source_ids'])),7)
            before={p:p.read_bytes() for p in output.iterdir()}
            self.assertEqual(verify(ROOT,output),result)
            self.assertTrue(all(p.read_bytes()==body for p,body in before.items()))
            with self.assertRaises(ValueError):prepare(ROOT,output)
            extended=extend_hunan(ROOT,output)
            self.assertEqual((extended['guides'],extended['candidate_guides'],extended['generatable_localities']),(190,9,173))
            with closing(sqlite3.connect(output/'before-hunan-extension/regional-guides.sqlite')) as saved:
                self.assertEqual(saved.execute('SELECT COUNT(*) FROM regional_current').fetchone()[0],188)
                self.assertEqual(saved.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual((output/'before-hunan-extension/manifest.json').read_bytes(),before[output/'manifest.json'])
            self.assertEqual(verify(ROOT,output),extended)
            after=(output/'regional-guides.sqlite').read_bytes()
            with self.assertRaises(ValueError):extend_hunan(ROOT,output)
            self.assertEqual((output/'regional-guides.sqlite').read_bytes(),after)
            p=output/'manifest.json';changed=json.loads(p.read_text('utf-8'));changed['published']=True;p.write_text(json.dumps(changed),'utf-8')
            with self.assertRaises(ValueError):verify(ROOT,output)

    def test_non_runtime_output_is_rejected_before_creating_anything(self):
        with self.assertRaises(ValueError):prepare(ROOT,ROOT/'backend/data/not-a-candidate')
        self.assertFalse((ROOT/'backend/data/not-a-candidate').exists())


if __name__=='__main__':unittest.main()

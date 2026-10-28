"""The alternate portal must not re-capture already completed own localities."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from regional_directory import DirectoryStore

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('sichuan_v4_worker',ROOT/'scripts/collect-sichuan-v4-night.py')
worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)


class V4Queue(unittest.TestCase):
    def test_skip_completed_own_guide_but_not_another_locality(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);store=DirectoryStore(base/'directory.sqlite')
            original_base,original_root=worker.BASE,worker.ROOT
            worker.BASE,worker.ROOT=base,base
            try:
                for code in ['510302000000','513328000000']:
                    payload={'region_code':code,'city':'测试市','district':code,'region_metadata':{}}
                    store.enqueue('sichuan_capture',payload)
                    item={'data':{'title':'劳动人事争议仲裁申请','areacode':code,
                                  'url':'https://www.sczwfw.gov.cn/jiq4/front/transition/ywTransToDetail_summary?areaCode='+code}}
                    (base/'discovery').mkdir(exist_ok=True)
                    (base/'discovery'/(code+'.json')).write_text(json.dumps({'response':{'data':[item]}}),'utf8')
                file=base/'captures/510302000000/guide.json';file.parent.mkdir(parents=True)
                file.write_text(json.dumps({'province':'sichuan','city':'测试市','district':'510302000000','region_code':'510302000000'}),'utf8')
                self.assertEqual(worker.enqueue_candidates(store),1)
                self.assertEqual(store.claim('sichuan_v4_capture')['payload']['region_code'],'513328000000')
                self.assertIsNone(store.claim('sichuan_v4_capture'))
            finally:worker.BASE,worker.ROOT=original_base,original_root


if __name__=='__main__':unittest.main()

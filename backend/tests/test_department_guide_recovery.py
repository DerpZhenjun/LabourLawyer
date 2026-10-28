import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
def module(name,filename):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/filename);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
recovery=module('department_recovery','recover-department-guides.py')
acquire=module('department_acquire','openclaw-acquire-guides.py')

class DepartmentRecoveryTests(unittest.TestCase):
    def test_promotion_rejects_changed_or_missing_cached_screenshot(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.runtime') as temp:
            folder=Path(temp)
            (folder/'observations.json').write_text(json.dumps([{'screenshot':'actual.png','screenshot_sha256':'wrong'}]),'utf8')
            with self.assertRaisesRegex(ValueError,'missing or hash changed'):acquire.require_saved_evidence(folder)
            (folder/'actual.png').write_bytes(b'actual screenshot bytes')
            with self.assertRaisesRegex(ValueError,'missing or hash changed'):acquire.require_saved_evidence(folder)
            self.assertEqual((folder/'actual.png').read_bytes(),b'actual screenshot bytes')

    def test_incomplete_cached_guide_is_retained_and_rejected_before_any_browser(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.runtime') as temp:
            run=Path(temp);folder=run/'department-guide-recovery/hebei';folder.mkdir(parents=True)
            ready=folder/'verified-guide.json';ready.write_text('{}','utf8')
            with patch.object(recovery,'BrowserLane') as browser:
                with self.assertRaisesRegex(ValueError,'lacks observations'):recovery.recover('hebei',run)
                browser.assert_not_called();self.assertEqual(ready.read_text('utf8'),'{}')

    def test_pdf_numbered_materials_stop_at_fees_and_keep_literal_labels(self):
        text='申请材料\n1.单位申办人社会保障卡或居民身份证。\n2.申请书。\n3.有关证据材料。\n4.用人单位工商登记信息。\n收费依据\n及标准\n不收费\n办事时间\n工作日'
        self.assertEqual(recovery.numbered_materials(text),['单位申办人社会保障卡或居民身份证','申请书','有关证据材料','用人单位工商登记信息'])

    def test_cached_cross_province_source_is_rejected_without_browser_or_publication(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.runtime') as temp:
            root=Path(temp);run=root/'run';folder=run/'department-guide-recovery/hebei';folder.mkdir(parents=True)
            (folder/'verified-guide.json').write_text(json.dumps({'guide_url':'https://banshi.beijing.gov.cn/guide','service_name':'劳动人事争议仲裁申请','materials':['申请书'],'region_code':'110000000000'}),'utf8')
            original={'state':'stalled','status':{'guide_found':False}}
            with patch.object(acquire,'ROOT',root),patch.object(acquire.subprocess,'run') as process:
                self.assertEqual(acquire.recover_department_source(run,'hebei',original),original)
                process.assert_not_called();self.assertFalse((run/'hebei/task.json').exists())

if __name__=='__main__':unittest.main()

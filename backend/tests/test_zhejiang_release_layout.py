"""Own Yuhang regression cases found during offline release document review."""
from pathlib import Path
import json,sys,unittest
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
import regional_zhejiang_documents as adapter
from regional_zhejiang import parse_yuhang_capture,REPORT

class YuhangReleaseLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder=ROOT/REPORT;manifest=folder/'SHA256-MANIFEST.json'
        if not manifest.is_file():raise unittest.SkipTest('Private sealed own Yuhang evidence is not distributed')
        files=json.loads(manifest.read_text(encoding='utf8'))['files']
        if any(not (folder/p).is_file() for p in files):raise unittest.SkipTest('Private sealed capture incomplete; never reconstruct or reseal')
        cls.guide=adapter.with_zhejiang_capabilities(parse_yuhang_capture(folder,manifest))
        cls.template=next(t for t in cls.guide['templates'] if t['document_types']==['evidence'])
        if not (ROOT/cls.template['file']).is_file():raise unittest.SkipTest('Own canonical original unavailable')

    def evidence(self):
        return adapter.fill_zhejiang_document(self.guide,self.template,'evidence',ROOT/self.template['file'],{
            'caseNumber':'虚构余杭排版案号','submitterName':'不得自动填入手签处','submitDate':'2026-10-29',
            'evidenceList':[{'name':f'虚构证据{i}','pageCount':'2页','source':'虚构测试人员保存',
                'purpose':f'第{i}项虚构软件测试材料，仅用于检查较长文字换行、原始表头和跨页连续性。'} for i in range(1,11)]})

    def test_case_value_preserves_the_own_original_static_label(self):
        table=self.evidence().tables[0]
        self.assertEqual(table.rows[0].cells[0].text,'案号')
        self.assertEqual(table.rows[0].cells[1].text,'虚构余杭排版案号')
        self.assertNotIn('不得自动填入手签处','\n'.join(c.text for r in table.rows for c in r.cells))

    def test_long_records_are_whole_and_own_headers_repeat_on_continuation_pages(self):
        table=self.evidence().tables[0]
        for row in table.rows[:2]:
            self.assertIsNotNone(row._tr.get_or_add_trPr().find(qn('w:tblHeader')))
        for row in table.rows:
            self.assertIsNotNone(row._tr.get_or_add_trPr().find(qn('w:cantSplit')))
        text='\n'.join(c.text for r in table.rows for c in r.cells)
        for i in range(1,11):self.assertIn(f'第{i}项虚构软件测试材料',text)

if __name__=='__main__':unittest.main()

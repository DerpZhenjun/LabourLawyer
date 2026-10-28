from pathlib import Path
import sys
import unittest


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from template_paths import get_template_path
from WenShu.Zhejiang.ELdocx import generate_ELdocx
from WenShu.Zhejiang.LAdocx import generate_LAdocx


class ZhejiangOfficialTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            get_template_path("《劳动人事争议仲裁申请书》.docx", "zhejiang")
            get_template_path("《证据清单》.docx", "zhejiang")
        except FileNotFoundError as exc:
            raise unittest.SkipTest("浙江官方模板尚未放入 ZheJiangSheng 目录") from exc

    def test_worker_application_uses_official_template_and_removes_employer_form(self):
        document = generate_LAdocx(
            {
                "committeeName": "杭州市劳动人事争议仲裁委员会",
                "applicantName": "测试申请人",
                "birthDate": "1990-05-06",
                "gender": "男",
                "nationality": "汉族",
                "idNumber": "330100199005060011",
                "phone": "13800000000",
                "householdType": "本省非农业户口",
                "idAddress": "浙江省杭州市测试路1号",
                "respondentName": "杭州测试有限公司",
                "socialCreditCode": "91330100TEST000001",
                "registeredAddress": "浙江省杭州市注册地址",
                "mailingAddress": "浙江省杭州市收件地址",
                "workAddress": "浙江省杭州市工作地址",
                "requests": ["请求支付拖欠工资15000元。"],
                "factsReason": "申请人于2024年3月入职，被申请人尚未支付约定工资。",
                "copyCount": 1,
                "applicationDate": "2026-09-16",
            },
            get_template_path("《劳动人事争议仲裁申请书》.docx", "zhejiang"),
        )
        self.assertEqual(len(document.tables), 1)
        text = "\n".join(cell.text for row in document.tables[0].rows for cell in row.cells)
        self.assertIn("测试申请人", text)
        self.assertIn("杭州测试有限公司", text)
        self.assertIn("请求支付拖欠工资15000元", text)
        self.assertIn("杭州市劳动人事争议仲裁委员会", text)
        footer = document.tables[0].rows[-1].cells[0].paragraphs
        self.assertEqual(len(footer), 10)
        self.assertEqual(footer[0].text, "此致")
        self.assertEqual(footer[1].text, "敬礼")
        self.assertIn("杭州市劳动人事争议仲裁委员会", footer[2].text)
        self.assertTrue(footer[2].runs[1].underline)
        self.assertNotIn("测试申请人", footer[3].text)
        self.assertIn("2026年", footer[4].text)
        self.assertIn("附：申请书副本", footer[5].text)
        self.assertIn("1", footer[5].text)
        self.assertIn("4.申请书副本份数", footer[9].text)

    def test_blank_application_returns_fillable_official_worker_template(self):
        document = generate_LAdocx(
            {"requests": [], "copyCount": 1},
            get_template_path("《劳动人事争议仲裁申请书》.docx", "zhejiang"),
        )
        self.assertEqual(len(document.tables), 1)
        text = "\n".join(cell.text for row in document.tables[0].rows for cell in row.cells)
        self.assertIn("申请人", text)
        self.assertIn("仲裁请求", text)

    def test_evidence_list_supports_more_than_official_nine_rows(self):
        evidence = [
            {"name": f"证据{i}", "pageCount": "1页", "source": "本人保存", "purpose": f"说明事项{i}"}
            for i in range(1, 11)
        ]
        document = generate_ELdocx(
            {
                "committeeName": "杭州市劳动人事争议仲裁委员会",
                "caseNumber": "浙杭劳人仲案测试号",
                "copyCount": 2,
                "submitterName": "测试申请人",
                "submitDate": "2026-09-16",
                "evidenceList": evidence,
            },
            get_template_path("《证据清单》.docx", "zhejiang"),
        )
        table = document.tables[0]
        self.assertEqual(len(table.rows), 14)
        text = "\n".join(cell.text for row in table.rows for cell in row.cells)
        self.assertIn("证据10", text)
        self.assertNotIn("测试申请人", text)
        self.assertIn("2026年9月16日", text)
        self.assertIn("杭州市劳动人事争议仲裁委员会", document.paragraphs[0].text)
        footer = document.paragraphs[-1]
        self.assertIn("本表一式2份提交仲裁委", footer.text)
        self.assertEqual(footer.runs[0].font.size.pt, 14)

    def test_blank_evidence_list_returns_official_template(self):
        document = generate_ELdocx(
            {"copyCount": 2, "evidenceList": [{"name": "", "pageCount": "", "source": "", "purpose": ""}]},
            get_template_path("《证据清单》.docx", "zhejiang"),
        )
        self.assertEqual(len(document.tables), 1)
        self.assertEqual(len(document.tables[0].rows), 13)
        self.assertGreaterEqual(len(document.tables[0].columns), 6)


if __name__ == "__main__":
    unittest.main()

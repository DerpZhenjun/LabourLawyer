from pathlib import Path
import sys
import unittest


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from template_paths import get_template_path
from WenShu.Guangdong.ELdocx import generate_ELdocx
from WenShu.Guangdong.LAdocx import generate_LAdocx


class GuangdongOfficialTemplateTests(unittest.TestCase):
    def test_worker_application_uses_only_worker_form(self):
        document = generate_LAdocx(
            {
                "committeeName": "广州市劳动人事争议仲裁委员会",
                "applicantName": "测试申请人",
                "birthDate": "1990-05-06",
                "gender": "男",
                "nationality": "汉族",
                "idNumber": "440100199005060011",
                "phone": "13800000000",
                "householdType": "本省非农业户口",
                "idAddress": "广东省广州市测试路1号",
                "applicantMailingAddress": "广东省广州市收件地址",
                "respondentName": "广州测试有限公司",
                "socialCreditCode": "91440100TEST000001",
                "registeredAddress": "广东省广州市注册地址",
                "mailingAddress": "广东省广州市收件地址",
                "workAddress": "广东省广州市工作地址",
                "legalRepName": "张某",
                "legalRepPhone": "020-12345678",
                "legalRepPosition": "执行董事",
                "companyContact": "李某",
                "companyContactPhone": "13900000000",
                "requests": ["请求支付拖欠工资15000元。"],
                "claimCalculation": "5000元/月×3个月=15000元",
                "employmentDate": "2024-03-01",
                "jobTitle": "运营专员",
                "signedContract": "有",
                "contractStartDate": "2024-03-01",
                "contractEndDate": "2027-02-28",
                "workSchedule": "每周工作5天，每天8小时",
                "attendanceRequired": "是",
                "attendanceMethod": "钉钉打卡",
                "salaryPaymentMethod": "转账",
                "salaryReceiptRequired": "不需要签收",
                "startingSalary": "5000元/月",
                "salaryAdjustments": "无",
                "currentlyEmployed": "否",
                "departureDate": "2026-04-01",
                "departureReason": "公司通知解除劳动关系",
                "averageMonthlySalary": "5000",
                "factsReason": "申请人于2024年3月入职，被申请人尚未支付约定工资。",
                "copyCount": 1,
                "applicationDate": "2026-09-16",
            },
            get_template_path("仲裁申请书.docx", "guangdong"),
        )
        self.assertEqual(len(document.tables), 4)
        text = "\n".join(document.paragraphs[index].text for index in range(len(document.paragraphs)))
        text += "\n" + "\n".join(cell.text for table in document.tables for row in table.rows for cell in row.cells)
        self.assertIn("测试申请人", text)
        self.assertIn("广州测试有限公司", text)
        self.assertIn("请求支付拖欠工资15000元", text)
        self.assertIn("广州市劳动人事争议仲裁委员会", text)
        parties = document.tables[0]
        self.assertIn("1990年", parties.rows[0].cells[7].text)
        self.assertIn("月", parties.rows[0].cells[7].text)
        self.assertIn("□以《当事人有效送达地址确认书》为准", parties.rows[3].cells[1].text)
        self.assertIn("☑其他：广东省广州市收件地址", parties.rows[3].cells[1].text)
        facts = document.tables[2]
        self.assertIn("☑每周工作5天，每天工作8小时", facts.rows[4].cells[1].text)
        self.assertIn("☑转账", facts.rows[5].cells[7].text)
        self.assertIn("☑不需签收", facts.rows[5].cells[10].text)
        self.assertIn("5000元/月", facts.rows[9].cells[8].text)

    def test_blank_application_returns_official_template(self):
        document = generate_LAdocx(
            {"requests": [], "copyCount": 1},
            get_template_path("仲裁申请书.docx", "guangdong"),
        )
        self.assertEqual(len(document.tables), 4)
        text = "\n".join(cell.text for table in document.tables for row in table.rows for cell in row.cells)
        self.assertIn("仲裁请求", text)
        self.assertIn("事实和理由", text)

    def test_evidence_list_supports_more_than_official_nine_rows(self):
        evidence = [
            {"name": f"证据{i}", "pageCount": "1页", "source": "本人保存", "purpose": f"说明事项{i}"}
            for i in range(1, 11)
        ]
        document = generate_ELdocx(
            {
                "committeeName": "广州市劳动人事争议仲裁委员会",
                "caseNumber": "粤穗劳人仲案测试号",
                "copyCount": 2,
                "submitterName": "测试申请人",
                "submitDate": "2026-09-16",
                "evidenceList": evidence,
            },
            get_template_path("证据清单.docx", "guangdong"),
        )
        table = document.tables[0]
        self.assertEqual(len(table.rows), 11)
        text = "\n".join(cell.text for row in table.rows for cell in row.cells)
        text += "\n" + "\n".join(paragraph.text for paragraph in document.paragraphs)
        self.assertIn("证据10", text)
        self.assertNotIn("测试申请人", text)
        self.assertIn("2026年9月16日", text)
        footer = document.paragraphs[3]
        self.assertNotIn("测试申请人", footer.text)
        self.assertIn("提交时间：2026年9月16日", footer.text)

    def test_blank_evidence_list_returns_official_template(self):
        document = generate_ELdocx(
            {"copyCount": 2, "evidenceList": [{"name": "", "pageCount": "", "source": "", "purpose": ""}]},
            get_template_path("证据清单.docx", "guangdong"),
        )
        self.assertEqual(len(document.tables), 1)
        self.assertEqual(len(document.tables[0].rows), 10)
        self.assertEqual(len(document.tables[0].columns), 4)


if __name__ == "__main__":
    unittest.main()

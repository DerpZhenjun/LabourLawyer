from pathlib import Path
import ast
import sys
import unittest


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from template_paths import DEFAULT_TEMPLATE_ROOT, get_template_path


class TemplateOnlyGenerationTests(unittest.TestCase):
    def test_official_template_root_is_the_required_directory(self):
        self.assertEqual(DEFAULT_TEMPLATE_ROOT, REPOSITORY_ROOT / "templates" / "_docx")
        self.assertTrue(DEFAULT_TEMPLATE_ROOT.is_dir())

    def test_enabled_province_documents_resolve_inside_template_root(self):
        paths = [
            get_template_path("《劳动人事争议仲裁申请书》.docx", "zhejiang"),
            get_template_path("《证据清单》.docx", "zhejiang"),
            get_template_path("仲裁申请书.docx", "guangdong"),
            get_template_path("证据清单.docx", "guangdong"),
        ]
        for path in paths:
            self.assertTrue(path.is_relative_to(DEFAULT_TEMPLATE_ROOT))
            self.assertTrue(path.is_file())

    def test_generators_do_not_create_blank_word_documents(self):
        generator_root = BACKEND_DIR / "WenShu"
        offenders = []
        for path in generator_root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or node.args or node.keywords:
                    continue
                if isinstance(node.func, ast.Name) and node.func.id == "Document":
                    offenders.append(str(path.relative_to(REPOSITORY_ROOT)))
        self.assertEqual(offenders, [], f"禁止从空白 Document() 生成文书：{offenders}")

    def test_no_legacy_text_or_injury_generators_are_exposed(self):
        self.assertFalse((BACKEND_DIR / "WenShu" / "WIAdocx.py").exists())
        self.assertFalse((BACKEND_DIR / "routes" / "others" / "wia.py").exists())
        mini_program = (REPOSITORY_ROOT / "miniprogram" / "pages" / "province" / "index.js").read_text(encoding="utf-8")
        self.assertNotIn("generated = `", mini_program)


if __name__ == "__main__":
    unittest.main()

from hashlib import sha256
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import json
import unittest

from compact_sanitized_layout_experiment import clean_official_layout, LayoutBindings


class SanitizedLayoutTests(unittest.TestCase):
    def fixture(self):
        output = BytesIO()
        with ZipFile(output, 'w') as package:
            package.writestr('word/document.xml', '<layout><visible>保留版式</visible></layout>')
            package.writestr('docProps/core.xml', '<core><creator>synthetic editor</creator><title>keep</title></core>')
            package.writestr('docProps/app.xml', '<properties><Manager>synthetic field</Manager><Pages>1</Pages></properties>')
            package.writestr('docProps/custom.xml', '<Properties><property name="synthetic property">synthetic opaque value</property></Properties>')
        return output.getvalue()

    def test_only_editor_fields_removed(self):
        original = self.fixture()
        derivative, changed = clean_official_layout(original)
        self.assertEqual(set(changed), {'docProps/core.xml', 'docProps/app.xml', 'docProps/custom.xml'})
        self.assertNotEqual(original, derivative)
        with ZipFile(BytesIO(original)) as before, ZipFile(BytesIO(derivative)) as after:
            self.assertEqual(before.namelist(), after.namelist())
            self.assertEqual(before.read('word/document.xml'), after.read('word/document.xml'))
            joined = after.read('docProps/core.xml') + after.read('docProps/app.xml') + after.read('docProps/custom.xml')
            self.assertNotIn(b'synthetic', joined)
            self.assertIn(b'<title>keep</title>', joined)
            self.assertIn(b'<Pages>1</Pages>', joined)
        self.assertEqual(clean_official_layout(derivative), (derivative, ()))

    def test_runtime_distinguishes_original_from_layout(self):
        source = self.fixture()
        layout, _ = clean_official_layout(source)
        original_hash = sha256(source).hexdigest()
        layout_hash = sha256(layout).hexdigest()
        blob = json.dumps({'schema': 1, 'rows': [{'official_original_sha256': original_hash,
                                                  'sanitized_layout_sha256': layout_hash}]}).encode()
        pin = sha256(blob).hexdigest()
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / (layout_hash + '.docx')
            path.write_bytes(layout)
            binding = LayoutBindings(blob, pin, {original_hash})
            self.assertEqual(binding.resolve(root, original_hash), layout)
            with self.assertRaises(ValueError):
                binding.resolve(root, layout_hash)
            path.write_bytes(source)
            with self.assertRaises(ValueError):
                binding.resolve(root, original_hash)
        for mismatched in ('0' * 64, []):
            with self.assertRaises(ValueError):
                LayoutBindings(blob, mismatched, {original_hash})


if __name__ == '__main__':
    unittest.main()

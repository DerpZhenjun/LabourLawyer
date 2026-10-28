"""Browser daemon may inherit stdout; CLI completion must not await daemon EOF."""
import importlib
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch


class BrowserProcessLifecycleTests(unittest.TestCase):
    def test_completed_cli_does_not_wait_for_daemon_inherited_output_handles(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
        module=importlib.import_module('collect-chengdu-districts')
        code="import subprocess,sys,json; subprocess.Popen([sys.executable,'-c','import time; time.sleep(3)']); print(json.dumps({'success':True,'data':{'opened':True}}),flush=True)"
        with tempfile.TemporaryDirectory() as folder, patch.object(module,'CLI',sys.executable),patch.object(module,'OUT',Path(folder)):
            started=time.monotonic()
            result=module.browser('-c',code)
            elapsed=time.monotonic()-started
            self.assertEqual(result,{'opened':True})
            self.assertLess(elapsed,2,'Completed browser command waited for long-lived daemon output EOF')

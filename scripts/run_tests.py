# -*- coding: utf-8 -*-
"""运行全部测试(解析 + 识别 + E2E)。"""
from __future__ import absolute_import, unicode_literals

import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tests import test_e2e, test_parser


def main():
    ok = True
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTests(loader.loadTestsFromModule(test_parser))
    suite.addTests(loader.loadTestsFromModule(test_e2e))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    ok = ok and result.wasSuccessful()

    # core/analysis 的自研测试器(pytest 风格,直接运行)
    ana_test = os.path.join(ROOT, "tests", "test_analysis.py")
    print("\n== core/analysis tests ==")
    proc = subprocess.Popen([sys.executable, ana_test],
                            cwd=ROOT, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    out, _ = proc.communicate()
    sys.stdout.buffer.write(out)
    ok = ok and proc.returncode == 0
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

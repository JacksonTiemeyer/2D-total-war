#!/usr/bin/env python3
"""Runner script for Patch B smoke tests."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

print("=== Patch B Smoke Tests ===\n")

from tests.patchb_smoke_test import run_all

success = run_all()
print("\n" + ("ALL TESTS PASSED" if success else "SOME TESTS FAILED"))
sys.exit(0 if success else 1)

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = ROOT / "SDK_testing"

TESTS = [
    "test_sdk_smoke.py",
    "test_sdk_contract.py",
    "test_sdk_scenarios.py",
]


def run_test(script_name: str) -> bool:
    script_path = TEST_DIR / script_name
    print(f"\n=== Running {script_name} ===")
    proc = subprocess.run([sys.executable, str(script_path)], cwd=str(ROOT))
    ok = proc.returncode == 0
    print(f"=== {script_name}: {'PASS' if ok else 'FAIL'} ===")
    return ok


def main() -> None:
    print("FairnessOps SDK test suite")
    print(f"Project root: {ROOT}")

    results = {name: run_test(name) for name in TESTS}
    failed = [name for name, ok in results.items() if not ok]

    print("\n=== Final Summary ===")
    for name in TESTS:
        print(f"{name}: {'PASS' if results[name] else 'FAIL'}")

    print("\nOutput roots:")
    print(f"- Smoke/contract: {ROOT / 'runs' / 'sdk_test_outputs' / 'smoke'}")
    print(f"- Scenarios:      {ROOT / 'runs' / 'sdk_test_outputs' / 'scenarios'}")

    if failed:
        print(f"\nOverall: FAIL ({len(failed)} failed)")
        sys.exit(1)

    print("\nOverall: PASS")


if __name__ == "__main__":
    main()

import subprocess, sys
from pathlib import Path

ROOT = str(Path(__file__).parent)
PYTHON = str(Path(ROOT) / '.venv' / 'bin' / 'python')

sys.path.insert(0, ROOT)
from dotenv import load_dotenv; load_dotenv()
from dev_crew.tasks import SMOKE_TESTS

PREAMBLE = (
    "import sys, os\n"
    f"sys.path.insert(0, {ROOT!r})\n"
    f"os.chdir({ROOT!r})\n"
    "from dotenv import load_dotenv; load_dotenv()\n"
)

failures = []
for name, code in SMOKE_TESTS:
    r = subprocess.run([PYTHON, '-c', PREAMBLE + code], capture_output=True, text=True)
    ok = 'PASS' in r.stdout
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if not ok:
        failures.append(name)
        print(r.stderr[-300:])

print()
print(f"결과: {len(SMOKE_TESTS) - len(failures)}/{len(SMOKE_TESTS)} 통과")
if not failures:
    print("모두 통과 → 개발자 에이전트 생략")

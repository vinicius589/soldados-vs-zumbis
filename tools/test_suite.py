"""Executa unittest sem ocultar falhas, testes ausentes ou skips."""
import argparse
import json
from pathlib import Path
import time
import unittest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    suite=unittest.defaultTestLoader.discover(str(root/'tests'),pattern='test_*.py')
    started=time.monotonic()
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    passed=result.wasSuccessful() and result.testsRun>0 and not result.skipped
    report={'ok':passed,'tests':result.testsRun,'failures':len(result.failures),
            'errors':len(result.errors),'skipped':len(result.skipped),
            'seconds':round(time.monotonic()-started,3),
            'failed_tests':[str(test) for test,_ in result.failures+result.errors]}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2),encoding='utf-8')
    return 0 if passed else 1


if __name__=='__main__':
    raise SystemExit(main())

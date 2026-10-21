"""Validação local/CI com cobertura de ramos, saves isolados e evidências."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
# Limites por módulo: a média global não pode esconder uma regressão crítica.
COVERAGE_FLOORS={'projectile_combat.py':95,'timing.py':95,'snapshot.py':85}


def coverage_gate(report):
    results={}
    for name,floor in COVERAGE_FLOORS.items():
        matching=[data['summary'] for path,data in report['files'].items() if Path(path).name==name]
        if len(matching)!=1:
            raise ValueError('Módulo ausente ou ambíguo na cobertura: '+name)
        summary=matching[0]
        if not summary.get('num_branches'):
            raise ValueError('Cobertura sem medição de ramos: '+name)
        percent=summary['percent_covered']
        results[name]={'combined_percent':percent,'minimum':floor,
                       'missing_lines':summary['missing_lines'],
                       'missing_branches':summary['missing_branches']}
        if percent<floor:
            raise ValueError(f'{name}: cobertura {percent:.2f}% abaixo de {floor}%')
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/quality')
    args=parser.parse_args()
    output=args.output.resolve(); output.mkdir(parents=True,exist_ok=True)
    # Diretório novo por execução evita aceitar evidências antigas.
    run=Path(tempfile.mkdtemp(prefix='run-',dir=output))
    temp=run/'temp'; temp.mkdir()
    env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',SVZ_RENDERER='software',
             PYTHONPATH=str(ROOT/'src'),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',
             SVZ_DATA_DIR=str(run/'saves'),SVZ_SAVE_PATH=str(run/'saves/campanha.json'),
             TEMP=str(temp),TMP=str(temp),COVERAGE_FILE=str(run/'.coverage'))
    report={'ok':False,'directory':str(run),'stages':[]}
    def execute(name,arguments,timeout=600):
        started=time.monotonic()
        with (run/f'{name}.log').open('w',encoding='utf-8') as log:
            result=subprocess.run([sys.executable,*arguments],cwd=ROOT,env=env,
                                  stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
        report['stages'].append({'name':name,'returncode':result.returncode,
                                 'seconds':round(time.monotonic()-started,3)})
        if result.returncode:
            raise RuntimeError(f'Falha em {name}; veja {run/name}.log')
        print(name.upper()+'_OK',flush=True)
    try:
        execute('check',['tools/manage.py','check'])
        execute('unittest',['-m','coverage','run','--branch','--source=src/svz','tools/test_suite.py',
                            '--report',str(run/'unittest.json')])
        execute('coverage_json',['-m','coverage','json','-o',str(run/'coverage.json')])
        execute('coverage_xml',['-m','coverage','xml','-o',str(run/'coverage.xml')])
        execute('coverage_html',['-m','coverage','html','-d',str(run/'coverage_html')])
        report['coverage']=coverage_gate(json.loads((run/'coverage.json').read_text()))
        execute('smoke',['tests/smoke_test.py'])
        execute('regression',['tools/regression.py','--game-dir',str(ROOT),'--layout','final',
                              '--output-dir',str(run/'regression')])
        execute('benchmark',['tools/benchmark.py','--samples','60','--output',str(run/'benchmark.json')])
        report['ok']=True
    except (RuntimeError,ValueError,OSError,subprocess.TimeoutExpired) as exc:
        report['error']=str(exc)
        print(str(exc),file=sys.stderr)
    finally:
        (run/'summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        (output/'latest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return 0 if report['ok'] else 1


if __name__=='__main__':
    raise SystemExit(main())

"""Controle da versão final: verificar, testar, construir e distribuir."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def check() -> int:
    manifest = json.loads((ROOT / 'assets/manifest.json').read_text(encoding='utf-8'))
    errors = []
    for name, expected in manifest.items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT / 'assets'):
            errors.append(f'Recurso fora da pasta assets: {name}')
            continue
        if not path.is_file():
            errors.append(f'Recurso ausente: {name}')
        elif hashlib.sha256(path.read_bytes()).hexdigest() != expected['sha256']:
            errors.append(f'Recurso modificado ou incompleto: {name}')
    source = [ROOT / 'main.py', *ROOT.joinpath('src').rglob('*.py'), *ROOT.joinpath('tests').glob('*.py'), *ROOT.joinpath('tools').glob('*.py')]
    for path in source:
        try:
            ast.parse(path.read_text(encoding='utf-8-sig'), str(path))
        except (SyntaxError, UnicodeError, OSError) as exc:
            errors.append(str(exc))
    if errors:
        print('\n'.join(errors))
        return 1
    print(f'CHECK_OK: {len(manifest)} recursos íntegros; {len(source)} arquivos Python.', flush=True)
    return 0


def test() -> int:
    if check():
        return 1
    env = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', SVZ_RENDERER='software', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', PYTHONPATH=str(ROOT / 'src'))
    with tempfile.TemporaryDirectory(prefix='svz-tests-') as directory:
        env['SVZ_SAVE_PATH'] = str(Path(directory) / 'campanha.json')
        env['SVZ_DATA_DIR'] = directory
        for args in (['-m', 'unittest', 'discover', '-s', str(ROOT / 'tests'), '-p', 'test_*.py'], [str(ROOT / 'tests/smoke_test.py')]):
            result = subprocess.run([sys.executable, *args], cwd=ROOT, env=env)
            if result.returncode:
                return result.returncode
    return 0


def build() -> int:
    if test():
        return 1
    env = dict(os.environ, PYINSTALLER_CONFIG_DIR=str(ROOT / 'build/pyinstaller-cache'))
    result = subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--distpath', str(ROOT / 'build/bundle'), '--workpath', str(ROOT / 'build/work'), str(ROOT / 'tools/SoldadosVsZumbis.spec')], cwd=ROOT, env=env)
    if result.returncode:
        return result.returncode
    bundle = ROOT / 'build/bundle/SoldadosVsZumbis'
    shutil.copy2(bundle / 'SoldadosVsZumbis.exe', ROOT / 'SoldadosVsZumbis.exe')
    shutil.copytree(bundle / '_internal', ROOT / '_internal', dirs_exist_ok=True)
    print('BUILD_OK: executável em ' + str(ROOT / 'SoldadosVsZumbis.exe'))
    return 0


def package(destination: Path) -> int:
    if check():
        return 1
    if not (ROOT / 'SoldadosVsZumbis.exe').is_file():
        raise FileNotFoundError('Execute o comando build antes de criar o pacote.')
    report = ROOT / 'reports/diagnostico-pacote.json'
    report.parent.mkdir(exist_ok=True)
    env = dict(os.environ, SVZ_DATA_DIR=str(ROOT / 'reports/dados-diagnostico'), SVZ_SAVE_PATH=str(ROOT / 'reports/dados-diagnostico/campanha.json'))
    result = subprocess.run([str(ROOT / 'SoldadosVsZumbis.exe'), '--headless', '--self-test', str(report)], cwd=report.parent, env=env, timeout=120)
    if result.returncode or not json.loads(report.read_text(encoding='utf-8')).get('ok'):
        return 1
    selected = [ROOT / name for name in ('SoldadosVsZumbis.exe', 'JOGAR.bat', 'LEIA-ME.txt', 'CREDITOS.md')]
    for folder in ('assets', '_internal', 'licenses'):
        selected.extend(p for p in (ROOT / folder).rglob('*') if p.is_file())
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f'Pacote já existe: {destination}')
    hashes = {}
    with zipfile.ZipFile(destination, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(selected):
            relative = path.relative_to(ROOT).as_posix()
            data = path.read_bytes()
            hashes[relative] = hashlib.sha256(data).hexdigest()
            info = zipfile.ZipInfo('SoldadosVsZumbis/' + relative, date_time=(2026, 10, 10, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
        archive.writestr('SoldadosVsZumbis/SHA256.json', json.dumps(hashes, indent=2))
    destination.with_suffix('.zip.sha256').write_text(hashlib.sha256(destination.read_bytes()).hexdigest() + '  ' + destination.name + '\n', encoding='ascii')
    print(f'PACKAGE_OK: {destination}; {len(hashes)} arquivos.')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('check', 'test', 'build', 'package'))
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/SoldadosVsZumbis-1.2.0-Windows-x64.zip')
    args = parser.parse_args()
    if args.command == 'check':
        return check()
    if args.command == 'test':
        return test()
    if args.command == 'build':
        return build()
    return package(args.output)


if __name__ == '__main__':
    raise SystemExit(main())

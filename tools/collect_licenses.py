"""Preserva os avisos distribuídos junto das bibliotecas efetivamente usadas."""
from importlib.metadata import distribution
from pathlib import Path
import shutil
import sys

root = Path(__file__).resolve().parents[1]
destination = root / 'licenses'
destination.mkdir(exist_ok=True)
found = []
for name in ('pygame-ce', 'numpy', 'PyOpenGL', 'PyInstaller'):
    package = distribution(name)
    for relative in package.files or ():
        lowered = str(relative).lower()
        if not any(token in lowered for token in ('license', 'licence', 'copying', 'lgpl.txt')):
            continue
        path = Path(package.locate_file(relative))
        if not path.is_file() or path.suffix.lower() in {'.py', '.pyc', '.pyd', '.dll'}:
            continue
        target = destination / name / str(relative).replace('..', '_parent_')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        found.append(target.relative_to(destination).as_posix())
python_license = Path(sys.base_prefix) / 'LICENSE.txt'
if python_license.is_file():
    shutil.copy2(python_license, destination / 'Python-LICENSE.txt')
    found.append('Python-LICENSE.txt')
found = sorted(p.relative_to(destination).as_posix() for p in destination.rglob('*') if p.is_file() and p != destination / 'LEIA-ME.txt')
(destination / 'LEIA-ME.txt').write_text('Avisos preservados dos pacotes usados para executar/empacotar o jogo.\nA presença destes avisos não altera a titularidade do código ou das artes do jogo.\nO aviso PyOpenGL/LICENSE.txt veio da distribuição fonte oficial PyOpenGL 3.1.10.\n\n' + '\n'.join(found) + '\n', encoding='utf-8')
print(f'LICENSES_OK: {len(found)} arquivos de avisos preservados.')

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Abre o pacote compilado e valida o menu e os recursos essenciais."
    )
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=90.0)
    args = parser.parse_args()

    exe = args.exe.resolve()
    if not exe.is_file():
        raise FileNotFoundError(f"Executável não encontrado: {exe}")

    marker = exe.parent / "package-check.ok"
    marker.unlink(missing_ok=True)
    env = os.environ.copy()
    env["SVZ_PACKAGE_CHECK_FILE"] = str(marker)

    try:
        result = subprocess.run(
            [str(exe), "--verificar-pacote"],
            cwd=exe.parent,
            env=env,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=args.timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"A verificação do pacote excedeu {args.timeout:.0f} segundos."
        ) from exc

    output = ((result.stdout or "") + "\n" + (result.stderr or ""))[-6000:]
    if result.returncode != 0:
        raise RuntimeError(
            f"O executável falhou na verificação do pacote "
            f"(código {result.returncode}). Saída:\n{output}"
        )
    if not marker.is_file() or marker.read_text(encoding="utf-8").strip() != "PACOTE_OK":
        raise RuntimeError(
            "O processo terminou sem confirmar que o menu e os recursos foram carregados. "
            f"Saída:\n{output}"
        )

    marker.unlink(missing_ok=True)
    print("PACOTE_OK: o menu inicial e os recursos essenciais foram carregados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

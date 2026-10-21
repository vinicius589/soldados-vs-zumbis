from __future__ import annotations
import argparse
import subprocess
import time
from pathlib import Path

def main() -> int:
    parser = argparse.ArgumentParser(description="Confere se o executável inicia.")
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=8.0)
    args = parser.parse_args()
    exe = args.exe.resolve()
    if not exe.is_file():
        raise FileNotFoundError(f"Executável não encontrado: {exe}")
    log = exe.parent / "smoke-test.log"
    with log.open("w", encoding="utf-8") as stream:
        process = subprocess.Popen([str(exe)], cwd=exe.parent, stdin=subprocess.DEVNULL,
            stdout=stream, stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
        try:
            deadline = time.monotonic() + args.seconds
            while time.monotonic() < deadline:
                code = process.poll()
                if code is not None:
                    stream.flush()
                    detail = log.read_text(encoding="utf-8", errors="replace")[-4000:]
                    raise RuntimeError(f"O jogo encerrou durante o teste de inicialização (código {code}). Log:\n{detail}")
                time.sleep(0.25)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
    log.unlink(missing_ok=True)
    print(f"Inicialização verificada por {args.seconds:.1f}s.")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())

"""Medição repetível de CPU/renderização simulada; não mede FPS do monitor."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import platform
import random
import statistics
import sys
import tempfile
import time

def working_set():
    if os.name != "nt":
        return None
    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("faults", ctypes.c_ulong)] + [
            (name, ctypes.c_size_t) for name in ("peak", "current", "poolpeak", "pool",
                "nonpagedpeak", "nonpaged", "pagefile", "pagefilepeak")]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    handle = ctypes.windll.kernel32.GetCurrentProcess
    handle.restype = ctypes.c_void_p
    query = ctypes.windll.psapi.GetProcessMemoryInfo
    query.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
    if query(handle(), ctypes.byref(counters), counters.cb):
        return round(counters.current / 1024**2, 2)
    return None

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("reports/benchmark.json"))
    parser.add_argument("--samples", type=int, default=60)
    args = parser.parse_args()
    if args.samples < 10:
        parser.error("Use pelo menos 10 amostras.")
    os.environ.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", SVZ_RENDERER="software")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    import pygame
    from svz.app import Game
    from svz.content import REGIONS
    from svz.version import VERSION
    report = {"version": VERSION, "mode": "headless software; sem espera do monitor",
              "system": platform.platform(), "processor": platform.processor(),
              "logical_cpus": os.cpu_count(), "resolution": [1280, 720], "cases": {}}
    with tempfile.TemporaryDirectory(prefix="svz-benchmark-") as folder:
        started = time.perf_counter()
        game = Game(save_path=Path(folder) / "campaign.json")
        while game.scene == "loading":
            game.update(1/60)
        report["load_seconds"] = round(time.perf_counter() - started, 3)
        game.audio.set_enabled(False)
        for region in REGIONS:
            for wave in (1, 4, 8, 12):
                random.seed(100 + wave)
                game.difficulty = "medium"
                game.enter_selection(region)
                b = game.battle
                b.intermission = 9999
                b.supplies = 999
                b.place(0, 2)
                for order in b.build_wave(wave):
                    b.spawn_enemy(order)
                    b.enemies[-1].x = 840 + (len(b.enemies) % 4) * 80
                b.wave = wave
                samples = []
                enemies_at_start = len(b.enemies)
                for _ in range(args.samples):
                    started = time.perf_counter()
                    game.simulation_step(1/60)
                    game.draw()
                    game.present_frame()
                    samples.append((time.perf_counter() - started) * 1000)
                ordered = sorted(samples)
                def percentile(p):
                    return round(ordered[min(len(ordered)-1, int((len(ordered)-1)*p))], 3)
                report["cases"][f"{region}/{wave}"] = {
                    "samples": len(samples), "enemies_at_start": enemies_at_start,
                    "p50_ms": round(statistics.median(samples), 3),
                    "p95_ms": percentile(.95), "p99_ms": percentile(.99),
                    "working_set_mb": working_set()}
        pygame.quit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"BENCHMARK_OK: {len(report['cases'])} cenários; {args.output}")

if __name__ == "__main__":
    main()

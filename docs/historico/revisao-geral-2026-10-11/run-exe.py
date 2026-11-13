import subprocess,os,json,sys
from pathlib import Path
root=Path(sys.argv[1]); out=Path(__file__).resolve().parent
base=dict(os.environ,SVZ_DATA_DIR=str(out/"exe-data"),SVZ_SAVE_PATH=str(out/"exe-data/campanha.json"),PYTHONUTF8="1",PYTHONDONTWRITEBYTECODE="1")
results={}
for name,extra in (("headless",["--headless"]),("native",[])):
    env=base.copy()
    env.pop("SDL_VIDEODRIVER",None);env.pop("SDL_AUDIODRIVER",None);env["SVZ_RENDERER"]="software"
    try:
        p=subprocess.run([str(root/"SoldadosVsZumbis.exe"),*extra,"--self-test",str(out/("exe-"+name+".json"))],env=env,cwd=out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
        results[name]={"exit_code":p.returncode,"output":p.stdout.decode("utf-8",errors="replace")[-3000:]}
    except subprocess.TimeoutExpired:
        results[name]={"timeout":120}
    print(name,results[name],flush=True)
(out/"exe-runs.json").write_text(json.dumps(results,indent=2),encoding="utf-8")


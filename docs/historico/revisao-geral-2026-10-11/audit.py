"""Auditoria independente: não altera fontes nem salvamentos pessoais."""
import os, sys, json, tempfile, random, ast, hashlib, zipfile, time, subprocess
from pathlib import Path
ROOT=Path(sys.argv[1]); OUT=Path(__file__).resolve().parent
os.environ.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", SVZ_RENDERER="software", PYGAME_HIDE_SUPPORT_PROMPT="1")
sys.path.insert(0,str(ROOT/"src")); sys.dont_write_bytecode=True
import pygame
from svz.app import Game
from svz.content import REGIONS
from svz.persistence import load_save
report={"version":"1.2.0","date":"2026-10-11","matrix":[]}
with tempfile.TemporaryDirectory(prefix="svz-review-") as temp:
    path=Path(temp)/"campanha.json"
    g=Game(save_path=path)
    while g.scene=="loading": g.update(1/60)
    g.audio.set_enabled(False)
    def fresh(region="city",difficulty="medium",mode="mouse"):
        g.control_mode=mode; g.difficulty=difficulty; g.enter_selection(region)
        g.battle.supplies=999
        return g.battle
    for region in REGIONS:
        for difficulty in ("easy","medium","hard"):
            b=fresh(region,difficulty)
            g.handle_click(b.ground_cell_rect(0,2).center)
            count1=len(b.defenders); cooldown1=b.card_cooldowns[0]; supplies1=b.supplies
            g.handle_click(b.ground_cell_rect(0,4).center)
            mouse={"before":count1,"after":len(b.defenders),"cooldown":cooldown1,"spent":supplies1-b.supplies}
            b=fresh(region,difficulty,"keyboard")
            b.keyboard_row,b.keyboard_col=0,2
            g.handle_key(pygame.K_RETURN)
            b.keyboard_col=4; g.handle_key(pygame.K_RETURN)
            keyboard_count=len(b.defenders)
            b=fresh(region,difficulty,"keyboard")
            b.keyboard_row,b.keyboard_col=0,2
            g.handle_key(pygame.K_p); g.handle_key(pygame.K_RETURN)
            paused_placed=len(b.defenders)
            g.handle_key(pygame.K_r); g.handle_key(pygame.K_RETURN)
            paused_removed=len(b.defenders)==0
            g.handle_key(pygame.K_n)
            paused_wave=b.wave
            b=fresh(region,difficulty,"mouse")
            g.handle_key(pygame.K_p); g.handle_key(pygame.K_SPACE)
            paused_mouse_wave=b.wave
            b=fresh(region,difficulty,"keyboard")
            b.finished=True; b.victory=True; b.wave=12
            b.keyboard_row,b.keyboard_col=0,2
            g.handle_key(pygame.K_RETURN)
            finished={"scene":g.scene,"defenders_added":len(b.defenders),"completed":list(g.save["completed"])}
            report["matrix"].append({"region":region,"difficulty":difficulty,"mouse_cooldown_bypass":mouse,"keyboard_count":keyboard_count,"placed_while_paused":paused_placed,"removed_while_paused":paused_removed,"wave_started_while_paused":paused_wave,"mouse_space_wave_while_paused":paused_mouse_wave,"enter_after_victory":finished})
    b=fresh()
    b.wave=7; b.finished=True; b.lost=True
    g.finish_battle()
    report["defeat_progress"]={"scene":g.scene,"best_wave":g.save["best_wave"],"disk":load_save(path)}
    b=fresh(mode="keyboard")
    g.leave_battle_to_title(); g.request_new_game()
    g.handle_key(pygame.K_RETURN)
    report["new_game_keyboard_confirmation"]={"scene_after_enter":g.scene}
    b=fresh()
    before=b.intermission
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSLOST))
    g.handle_events(); g.update(1.0)
    report["focus_loss"]={"paused":b.paused,"intermission_before":before,"after":b.intermission}
    g.audio.set_enabled(False); g.audio.set_volume(.2); g.control_mode="keyboard"
    g.checkpoint()
    g2=Game(save_path=path)
    report["settings_restart"]={"control_mode":g2.control_mode,"sound_enabled":g2.audio.enabled,"volume":g2.audio.volume}
    for scene in ("title","settings","howto","campaign","characters"):
        g.scene=scene; g.draw()
        pygame.image.save(g.screen,str(OUT/(scene+".png")))
    for region in REGIONS:
        b=fresh(region)
        g.draw(); pygame.image.save(g.screen,str(OUT/("hud-"+region+".png")))
    path.write_text("["*2000+"0"+"]"*2000,encoding="utf-8")
    try:
        load_save(path)
        report["deep_corrupt_campaign"]="recovered"
    except Exception as e:
        report["deep_corrupt_campaign"]=type(e).__name__
    pygame.quit()
# Levantamento estrutural, sem pressupor que tamanho equivale a erro.
counts=[]; unreachable=[]
for p in sorted((ROOT/"src/svz").glob("*.py")):
    text=p.read_text(encoding="utf-8-sig"); tree=ast.parse(text)
    counts.append({"module":p.name,"lines":len(text.splitlines())})
    for node in ast.walk(tree):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            for i,stmt in enumerate(node.body[:-1]):
                if isinstance(stmt,(ast.Return,ast.Raise)):
                    unreachable.append({"module":p.name,"function":node.name,"line":stmt.lineno,"dead_statements":len(node.body)-i-1}); break
report["largest_modules"]=sorted(counts,key=lambda d:d["lines"],reverse=True)[:6]
report["unreachable_after_return"]=unreachable
archive=ROOT/"dist/SoldadosVsZumbis-1.2.0-Windows-x64.zip"
with zipfile.ZipFile(archive) as z:
    manifest=json.loads(z.read("SoldadosVsZumbis/SHA256.json"))
    bad_zip=[]; bad_root=[]; bad_extracted=[]
    for relative,h in manifest.items():
        if hashlib.sha256(z.read("SoldadosVsZumbis/"+relative)).hexdigest()!=h: bad_zip.append(relative)
        if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=h: bad_root.append(relative)
        if hashlib.sha256((ROOT/"dist/SoldadosVsZumbis"/relative).read_bytes()).hexdigest()!=h: bad_extracted.append(relative)
    report["distribution"]={"files":len(manifest),"zip_sha256":hashlib.sha256(archive.read_bytes()).hexdigest(),"bad_zip":bad_zip,"root_differs":bad_root,"extracted_differs":bad_extracted}
(OUT/"evidencias-revisao.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))


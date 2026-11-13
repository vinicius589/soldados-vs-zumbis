import os,sys,json,tempfile,hashlib,time
from pathlib import Path
from unittest.mock import patch
root=Path(sys.argv[1]);out=Path(__file__).resolve().parent;sys.path.insert(0,str(root/"src"));sys.dont_write_bytecode=True
os.environ.update(SDL_VIDEODRIVER="dummy",SDL_AUDIODRIVER="dummy",SVZ_RENDERER="software",PYGAME_HIDE_SUPPORT_PROMPT="1")
import pygame
from svz.app import Game
from svz.content import DEFENSES
from svz.persistence import load_save
report={}
with tempfile.TemporaryDirectory(prefix="svz-review-extra-") as d:
    p=Path(d)/"campaign.json"
    g=Game(save_path=p)
    while g.scene=="loading":g.update(1/60)
    g.audio.set_enabled(False)
    widths=[]
    for region in ("city","desert","beach"):
        g.enter_selection(region)
        # Valores reais iniciais, não a preparação com 999 suprimentos da primeira matriz.
        g.draw();pygame.image.save(g.screen,str(out/("hud-final-"+region+".png")))
        for (key,_),rect in zip(g.battle.selected,g.battle.card_rects()):
            for text in g.renderer.card_metrics(DEFENSES[key]):
                width=g.fonts.tiny.size(text)[0]; available=rect.width-51
                if width>available:widths.append({"region":region,"key":key,"text":text,"width":width,"available":available})
    report["hud_metric_overflow"]=widths
    # Derrota realmente causada por invasor ultrapassando a defesa, não apenas flags.
    from svz.entities import SpawnOrder
    from svz.content import REGION_ENEMIES
    g.enter_selection("city"); b=g.battle; b.wave=7; b.intermission=999
    b.lane_bombs[0].state="spent"
    b.spawn_enemy(SpawnOrder(0,REGION_ENEMIES["city"][0],0))
    e=b.enemies[0];e.x=-100;e.entry_reveal=0
    g.update(1/60)
    report["real_defeat"]={"finished":b.finished,"lost":b.lost,"wave":b.wave}
    g.finish_battle()
    report["real_defeat"]["best_wave_after"]=load_save(p)["best_wave"]
    # Apenas arquivo de teste deliberadamente inválido, jamais o save do jogador.
    p.write_text("["*5000+"0"+"]"*5000,encoding="utf-8")
    try:
        load_save(p);report["corrupt_campaign_10001_bytes"]="recovered"
    except Exception as exc:report["corrupt_campaign_10001_bytes"]=type(exc).__name__
    # Falha antes do tratador global da CLI: caminho de dados aponta para arquivo.
    # Fonte confirma mkdir fora do try; não necessário simular perfil real.
    pygame.quit()
report["time_clamp_example"]={"wall_seconds":10,"fps_10_simulated_seconds":sum(min(.05,.1) for _ in range(100)),"fps_60_simulated_seconds":sum(min(.05,1/60) for _ in range(600)),"kind":"calculation_of_run_loop_not_hardware_benchmark"}
(out/"evidencias-adicionais.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))


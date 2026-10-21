"""Painéis de preferências e ajuda, separados do desenho do combate."""
import pygame
from .config import WIDTH, GOLD, WHITE, TEAL, GRAY
from .settings import ACTION_LABELS

def settings_panel(r):
    g = r.owner
    g.screen.blit(g.assets.images["menu"], (0,0))
    r.panel(pygame.Rect(70,72,1140,546),245,TEAL,14)
    r.draw_text("CONFIGURAÇÕES",g.fonts.title,WHITE,(640,112),"center")
    labels = (("CONTROLE",(110,185)),("SOM",(110,239)),("VÍDEO",(110,293)),
              ("TEXTO",(660,185)),("PAUSAR AO SAIR",(660,239)),("MOVIMENTO",(660,293)))
    for label,pos in labels:r.draw_text(label,g.fonts.small,GOLD,pos)
    values = {"control":"TECLADO" if g.control_mode=="keyboard" else "MOUSE",
              "sound":"LIGADO" if g.audio.enabled else "DESLIGADO",
              "video":"TELA CHEIA: "+("SIM" if g.video.fullscreen else "NÃO"),
              "large_text":"AMPLIADO" if g.settings.large_text else "PADRÃO",
              "auto_pause":"SIM" if g.settings.auto_pause else "NÃO",
              "reduced_motion":"REDUZIDO" if g.settings.reduced_motion else "PADRÃO",
              "bindings":"PERSONALIZAR TECLAS"}
    if not g.audio.ready:values["sound"]="INDISPONÍVEL"
    for name,rect in g.settings_items().items():
        r.button(values.get(name,"−" if name.endswith("_minus") else "+"),rect,TEAL)
    for i,(name,label) in enumerate((("volume","VOLUME GERAL"),("music","MÚSICA"),("ambience","AMBIENTE"),("effects","EFEITOS"))):
        value = g.audio.volume if name=="volume" else getattr(g.settings,name)
        r.draw_text(label,g.fonts.small,WHITE,(280,352+i*48))
        r.draw_text(f"{round(value*100)}%",g.fonts.small,GOLD,(750,360+i*48),"center")
    r.panel(pygame.Rect(245,623,790,25),245,TEAL,5)
    r.draw_text("Tab / setas: navegar • Enter: escolher • Esc: voltar • F11: tela cheia",g.fonts.small,WHITE,(640,635),"center")
    r.button("VOLTAR",pygame.Rect(50,645,170,46),TEAL)

def bindings_panel(r):
    g=r.owner
    g.screen.blit(g.assets.images["menu"],(0,0))
    r.panel(pygame.Rect(70,70,1140,554),245,TEAL,14)
    r.draw_text("CONTROLES DO TECLADO",g.fonts.title,WHITE,(640,104),"center")
    for i,action in enumerate(g.settings.bindings):
        rect=g.binding_rect(i)
        label=ACTION_LABELS[action]+": "+("PRESSIONE UMA TECLA" if g.binding_action==action else g.settings.label(action))
        r.button(label,rect,GOLD if g.binding_action==action else TEAL)
    r.draw_text("Esc cancela • F5 salva • F11 alterna vídeo • F1 abre a ficha • 1–8 escolhem cartas",g.fonts.small,WHITE,(640,552),"center")
    r.button("RESTAURAR TECLAS PADRÃO",pygame.Rect(485,574,310,42),GOLD)
    r.button("VOLTAR",pygame.Rect(50,645,170,46),TEAL)

def howto_panel(r):
    g=r.owner
    g.screen.blit(g.assets.images["menu"],(0,0))
    r.panel(pygame.Rect(95,55,1090,574),245,GOLD,14)
    r.draw_text("COMO JOGAR",g.fonts.title,WHITE,(640,91),"center")
    lines=[
        ("1. Escolha o cenário","Cada mapa começa com oito cartas regionais. Use o mouse ou ative Teclado em Configurações."),
        ("2. Posicione e recarregue","Escolha a carta e uma casa livre. Cada colocação custa suprimentos; a carta espera 10 segundos. A recarga da arma é separada."),
        ("3. Conheça as tropas","Veja as fichas em Personagens. Passe o mouse na carta ou pressione F1 no combate. Algumas tropas rompem defesas inimigas específicas."),
        ("4. Recolha e proteja","VOLTAR À BASE retira uma tropa do campo e devolve 35% do custo. A contenção de cada faixa funciona uma vez; proteja a linha final."),
        ("5. Pause e retome","PAUSA congela o combate. MENU preserva a partida; CONTINUAR retoma pausado. F5 salva agora; também há salvamento automático."),
        ("6. Ondas e controles","Sobreviva a 12 ondas. Tab e setas navegam nos menus; Enter confirma. Personalize as teclas nas Configurações. F11 alterna tela cheia."),
    ]
    for i,(title,body) in enumerate(lines):
        y=132+i*78
        r.draw_text(title,g.fonts.h2,GOLD,(135,y))
        r.draw_wrapped(body,g.fonts.body,WHITE,pygame.Rect(135,y+27,1000,48),2)
    r.button("VOLTAR",pygame.Rect(50,645,170,46),TEAL)


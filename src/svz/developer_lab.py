"""Laboratório descartável: nunca usa o fluxo de progresso ou salvamento."""
import random
import pygame
from .battle import Battle
from .content import DEFENSES, ENEMIES, BOSSES, REGION_ROSTERS, REGION_ENEMIES, REGION_SUBBOSSES, REGION_BOSSES, DEFENDER_ACTOR_BY_KEY
from .entities import Defender
from .waves import SpawnOrder
from .actor_visuals import defender_weapon_origin


class DeveloperLab:
    def __init__(self, app):
        self.app = app
        self.random_state = random.getstate()
        self.region = 'city'
        self.team = 'soldiers'
        self.index = 0
        self.paused = True
        self.speed = 1.0
        self.boxes = True
        self.pose = None
        self.catalog = False
        self.select_mode = False
        self.repeat = True
        self.selected = None
        self.buttons = []
        self.reset()

    def reset(self):
        self.battle = Battle(self.app, self.region, REGION_ROSTERS[self.region][:1])
        self.battle.intermission = 1e9
        for cart in self.battle.lane_bombs:
            cart.state = 'spent'
        self.pose = None
        self.selected = None
        self.paused = True

    def close(self):
        random.setstate(self.random_state)
        self.app.scene = 'title'
        self.app.developer_lab = None

    def entries(self):
        if self.team == 'soldiers':
            return list(REGION_ROSTERS[self.region])
        keys = dict.fromkeys(REGION_ENEMIES[self.region] + REGION_SUBBOSSES[self.region] + REGION_BOSSES[self.region])
        data = {**ENEMIES, **BOSSES}
        return [(key, data[key].get('name', key)) for key in keys]

    def spawn(self, row, col):
        key, name = self.entries()[self.index % len(self.entries())]
        b = self.battle
        if self.team == 'soldiers':
            d = Defender(key, name, row, col, dict(DEFENSES[key]), 0, region=self.region)
            actor = DEFENDER_ACTOR_BY_KEY.get(key)
            if actor:
                d.visual_animation = self.app.assets.new_production_animation(actor)
            b.defenders.append(d)
            self.selected = d
        else:
            b.spawn_enemy(SpawnOrder(0, key, row))
            e = b.enemies[-1]
            e.x = b.ground_cell_rect(row, col).centerx
            e.entry_reveal = 0
            e.age = 2
            self.selected = e
        self.pose = None

    def animate(self, state):
        units = [self.selected] if self.selected is not None else self.battle.defenders + self.battle.enemies
        if not any(u.visual_animation and state in u.visual_animation.animations for u in units):
            return
        self.pose = state
        self.paused = False
        for unit in units:
            a = unit.visual_animation
            if a and state in a.animations:
                a.play(state, restart=True)

    def update(self, dt, force=False):
        if self.paused and not force:
            return
        dt *= 1.0 if force else self.speed
        if self.selected is not None and not any(u is self.selected for u in self.battle.defenders + self.battle.enemies):
            self.selected = None
        b = self.battle
        if self.pose:
            units = [self.selected] if self.selected is not None else b.defenders + b.enemies
            for unit in units:
                a = unit.visual_animation
                if a and self.pose in a.animations:
                    a.update(dt)
                    if self.repeat and a.finished:
                        a.play(self.pose, restart=True)
            b.update_particles(dt)
            return
        b.finished = b.lost = False
        b.supplies = 99999
        b.update_defenders(dt)
        b.update_enemies(dt)
        b.enemies[:] = [e for e in b.enemies if e.x > 170]
        b.update_projectiles(dt)
        b.update_particles(dt)
        b.update_production_animations(dt)

    def key(self, key):
        if key == pygame.K_ESCAPE and self.catalog:
            self.catalog = False
        elif key in (pygame.K_ESCAPE, pygame.K_F12):
            self.close()
        elif key == pygame.K_SPACE:
            self.paused = not self.paused
        elif key == pygame.K_PERIOD:
            self.paused = True
            self.update(1/60, True)
        elif key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.index = (self.index + (1 if key == pygame.K_RIGHT else -1)) % len(self.entries())
        elif key == pygame.K_TAB:
            self.team = 'enemies' if self.team == 'soldiers' else 'soldiers'
            self.index = 0

    def action(self, action):
        if action == 'exit': self.close()
        elif action == 'team': self.key(pygame.K_TAB)
        elif action == 'prev': self.key(pygame.K_LEFT)
        elif action == 'next': self.key(pygame.K_RIGHT)
        elif action == 'pause': self.paused = not self.paused
        elif action == 'step': self.paused = True; self.update(1/60, True)
        elif action == 'clear': self.reset()
        elif action in ('page_prev','page_next'):
            pages=(len(self.entries())+23)//24
            self.index=((self.index//24 + (1 if action == 'page_next' else -1))%pages)*24
        elif action == 'catalog': self.catalog = not self.catalog
        elif action == 'select': self.select_mode = not self.select_mode
        elif action == 'repeat': self.repeat = not self.repeat
        elif action.startswith('pick:'):
            self.index = int(action.split(':')[1]); self.catalog = False; self.select_mode = False
        elif action in ('heal', 'damage', 'remove', 'death'):
            self.edit_selected(action)
        elif action == 'combat': self.pose = None; self.paused = False
        elif action == 'boxes': self.boxes = not self.boxes
        elif action == 'speed': self.speed = {0.25:0.5,0.5:1.0,1.0:2.0,2.0:0.25}[self.speed]
        elif action in ('city','desert','beach'):
            self.region = action
            self.index = 0
            self.reset()
        else: self.animate(action)

    def edit_selected(self, action):
        unit = self.selected
        if unit is None:
            return
        b = self.battle
        population = b.defenders if isinstance(unit, Defender) else b.enemies
        if not any(u is unit for u in population):
            self.selected = None
            return
        if action == 'heal':
            unit.hp = unit.max_hp
            if isinstance(unit, Defender):
                unit.ammo = unit.max_ammo
                unit.reload_timer = unit.reload_total = 0
        elif action == 'remove':
            population[:] = [u for u in population if u is not unit]
            self.selected = None
        else:
            amount = unit.max_hp * .25 if action == 'damage' else unit.max_hp * 1000
            if isinstance(unit, Defender):
                b.damage_defender(unit, amount)
            else:
                b.take_enemy_damage(unit, amount)
            if unit.hp <= 0:
                self.selected = None
            self.pose = None

    def click(self, pos):
        for rect, action in self.buttons:
            if rect.collidepoint(pos):
                self.action(action)
                return
        if self.catalog:
            return
        if self.select_mode and pos[1] > 200:
            for unit in reversed(self.battle.defenders + self.battle.enemies):
                rect = (self.battle.ground_cell_rect(unit.row, unit.col).inflate(0, 60)
                        if isinstance(unit, Defender) else unit.hitbox())
                if rect.collidepoint(pos):
                    self.selected = unit
                    self.pose = None
                    return
            return
        cell = self.battle.board_cell_at(pos)
        if cell and pos[1] > 200:
            self.spawn(*cell)

    def draw(self, renderer):
        app, b = self.app, self.battle
        saved = app.battle
        app.battle = b
        try:
            app.screen.blit(app.assets.images[self.region + '_bg'], (0,0))
            for d in b.defenders: renderer.draw_defender(d)
            for e in b.enemies: renderer.draw_enemy(e)
            renderer.draw_projectiles(b)
            renderer.draw_visual_effects(b)
            renderer.draw_fallen(b)
            if self.boxes:
                for e in b.enemies:
                    pygame.draw.rect(app.screen, (255,110,90), e.hitbox(), 1)
                for d in b.defenders:
                    pygame.draw.rect(app.screen, (90,220,240), b.ground_cell_rect(d.row,d.col),1)
                    pygame.draw.circle(app.screen,(255,220,80),defender_weapon_origin(d),3)
        finally:
            app.battle = saved
        pygame.draw.rect(app.screen,(12,23,31),(0,0,1280,200))
        font = app.fonts.small
        def label(text, x, y): app.screen.blit(font.render(text,True,(235,240,240)),(x,y))
        label('LABORATÓRIO • sessão descartável',18,8)
        label(('PAUSADO' if self.paused else 'EM EXECUÇÃO') + ' • ' + (self.pose or 'combate') + ' • ' + str(self.speed) + 'x',480,8)
        label(f'{len(b.defenders)} soldados / {len(b.enemies)} zumbis',940,8)
        region_name = {'city':'Cidade', 'desert':'Deserto', 'beach':'Cachoeira'}[self.region]
        label(region_name + ' • ' + ('SOLDADO' if self.team == 'soldiers' else 'ZUMBI') + ': ' + self.entries()[self.index][1],18,36)
        self.buttons=[]
        controls=[('Catálogo','catalog'),('Soldado / Zumbi','team'),('<','prev'),('>','next'),('Cidade','city'),('Deserto','desert'),('Cachoeira','beach'),('Limpar','clear'),('Voltar','exit'),('Retomar' if self.paused else 'Pausar','pause'),('1 quadro','step'),(str(self.speed)+'x','speed'),('Combate','combat'),('Caixas / cano','boxes'),('Parado','idle'),('Andar','move'),('Atirar','shoot'),('Morder','bite'),('Recarregar','reload'),('Habilidade','skill'),('Selecionar' if not self.select_mode else 'Adicionar','select'),('Curar / munição','heal'),('Dano 25%','damage'),('Morte','death'),('Remover','remove'),('Repetir: '+('sim' if self.repeat else 'não'),'repeat')]
        for i,(text,action) in enumerate(controls):
            r=pygame.Rect(14+(i%10)*125,60+(i//10)*34,119,29)
            active = action == self.region or action == self.pose or (action == 'select' and self.select_mode)
            pygame.draw.rect(app.screen,(49,115,113) if active else (37,65,75),r,border_radius=5)
            app.screen.blit(font.render(text,True,(240,240,240)),(r.x+5,r.y+5))
            self.buttons.append((r,action))
        label('Clique para '+('selecionar uma unidade' if self.select_mode else 'adicionar')+' • Tab: equipe • setas: unidade • Espaço: pausa • .: quadro • Esc: sair',18,168)
        if self.selected is not None:
            u=self.selected
            a=u.visual_animation
            name=u.display_name if isinstance(u,Defender) else u.data.get('name',u.key)
            label(f'{name} | Vida {u.hp:.0f}/{u.max_hp:.0f} | pista {u.row+1} | '+(f'{a.state} quadro {a.frame_index+1}' if a else 'sem animação'),18,186)
        if self.catalog:
            panel=pygame.Rect(180,205,920,490)
            pygame.draw.rect(app.screen,(12,23,31),panel,border_radius=12)
            page=self.index//24
            entries=self.entries()
            label(f'{region_name} • {"Soldados" if self.team == "soldiers" else "Zumbis e chefes"} • página {page+1}/{(len(entries)+23)//24} • escolha para colocar no mapa',200,215)
            for offset,(key,name) in enumerate(entries[page*24:(page+1)*24]):
                r=pygame.Rect(195+(offset%3)*300,250+(offset//3)*47,290,41)
                pygame.draw.rect(app.screen,(37,65,75),r,border_radius=5)
                text=font.render(name,True,(240,240,240))
                if text.get_width()>280:
                    text=pygame.transform.smoothscale(text,(280,text.get_height()))
                app.screen.blit(text,(r.x+5,r.y+12))
                self.buttons.append((r,'pick:'+str(page*24+offset)))
            for x,title,action in ((200,'Página anterior','page_prev'),(500,'Próxima página','page_next'),(800,'Fechar catálogo','catalog')):
                r=pygame.Rect(x,650,270,32)
                pygame.draw.rect(app.screen,(37,65,75),r,border_radius=5)
                label(title,x+10,657)
                self.buttons.append((r,action))

"""Foco de menu compartilhado por teclado e pelas áreas clicáveis."""
import pygame

class MenuNavigation:
    def __init__(self, game):
        self.game = game
        self.scene = None
        self.index = 0
        self.visible = False

    def items(self):
        g = self.game
        scene = g.scene
        if scene != self.scene:
            self.scene, self.index = scene, 0
        back = ("back", pygame.Rect(50, 645, 170, 46))
        if scene == "title":
            return g.title_buttons()
        if scene in ("confirm_new", "confirm_exit"):
            return [("cancel", g.confirm_cancel_rect()), ("accept", g.confirm_accept_rect())]
        if scene == "difficulty":
            return [(key, rect) for key, rect in g.difficulty_buttons()] + [back]
        if scene == "campaign":
            return [(r, pygame.Rect(72+i*402,182,360,350)) for i,r in enumerate(("city","desert","beach"))] + [back]
        if scene == "characters":
            return [(r,pygame.Rect(340+i*205,82,190,42)) for i,r in enumerate(("city","desert","beach"))] + [
                ("units",pygame.Rect(424,136,205,40)), ("zombies",pygame.Rect(650,136,205,40)),
                ("prev",pygame.Rect(260,184,180,40)), ("next",pygame.Rect(840,184,180,40)), back]
        if scene == "story":
            return [("prev",pygame.Rect(245,646,170,44)), ("next",pygame.Rect(865,646,170,44)),back]
        if scene == "settings":
            return list(g.settings_items().items()) + [back]
        if scene == "bindings":
            return [(a,g.binding_rect(i)) for i,a in enumerate(g.settings.bindings)] + [
                ("reset",pygame.Rect(485,574,310,42)), back]
        if scene == "howto":
            return [back]
        return []

    def rect(self):
        items = self.items()
        if not items or not self.visible:
            return None
        self.index %= len(items)
        return items[self.index][1]

    def handle(self, key, mod=0):
        items = self.items()
        if not items:
            return False
        if key in (pygame.K_TAB,pygame.K_UP,pygame.K_DOWN,pygame.K_LEFT,pygame.K_RIGHT):
            delta = -1 if key in (pygame.K_UP,pygame.K_LEFT) or (key == pygame.K_TAB and mod & pygame.KMOD_SHIFT) else 1
            self.index = (self.index + delta) % len(items)
            self.visible = True
            return True
        if key in (pygame.K_RETURN, pygame.K_SPACE):
            self.visible = True
            self.game.handle_click(items[self.index % len(items)][1].center)
            return True
        return False


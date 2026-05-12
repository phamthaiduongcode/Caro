import pygame

ACTIVE_COLOR   = (70, 140, 220)
INACTIVE_COLOR = (60, 60, 75)
HOVER_COLOR    = (90, 90, 110)
TEXT_COLOR     = (240, 240, 240)
BORDER_COLOR   = (110, 110, 135)

class Button:
    def __init__(self, x, y, width, height, text, active=False):
        self.rect   = pygame.Rect(x, y, width, height)
        self.text   = text
        self.active = active
        self._font  = None          # khởi tạo lazy sau pygame.init()

    def _get_font(self):
        if self._font is None:
            self._font = pygame.font.SysFont("Arial", 15, bold=True)
        return self._font

    def draw(self, screen):
        hovered = self.rect.collidepoint(pygame.mouse.get_pos())
        if self.active:
            color = ACTIVE_COLOR
        elif hovered:
            color = HOVER_COLOR
        else:
            color = INACTIVE_COLOR

        pygame.draw.rect(screen, color, self.rect, border_radius=6)
        pygame.draw.rect(screen, BORDER_COLOR, self.rect, 1, border_radius=6)

        surf = self._get_font().render(self.text, True, TEXT_COLOR)
        screen.blit(surf, surf.get_rect(center=self.rect.center))

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)
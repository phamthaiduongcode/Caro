"""
gui/button.py
Thin wrapper kept for backward compatibility.
Full button logic (ImageButton, SurrenderButton) is in interface.py.
"""

import pygame


class Button:
    """Simple rect-based button (fallback / legacy use)."""

    def __init__(self, x, y, width, height, text=""):
        self.rect  = pygame.Rect(x, y, width, height)
        self.text  = text
        self.color = (100, 80, 50)
        self.hover_color = (140, 110, 70)
        self._font = None

    def _get_font(self):
        if self._font is None:
            self._font = pygame.font.SysFont("segoeuibold", 22, bold=True)
        return self._font

    def draw(self, surface):
        mouse = pygame.mouse.get_pos()
        color = self.hover_color if self.rect.collidepoint(mouse) else self.color
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, (60, 40, 20), self.rect, width=2, border_radius=8)
        if self.text:
            txt = self._get_font().render(self.text, True, (255, 240, 200))
            surface.blit(txt, txt.get_rect(center=self.rect.center))

    def is_clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONUP and
                event.button == 1 and
                self.rect.collidepoint(event.pos))
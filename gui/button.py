import os
import pygame

# Đường dẫn assets: gui/ -> lên 1 cấp -> assets/
_ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
from gui.sound_manager import SoundManager

# --- Button -------------------------------------------------------------------

class Button:
    """
    Nút rect-based đơn giản, hiển thị text, không cần ảnh.
    Base class cho ImageButton.
    """

    def __init__(self, x, y, width, height, text=""):
        self.rect        = pygame.Rect(x, y, width, height)
        self.text        = text
        self.color       = (100, 80, 50)
        self.hover_color = (140, 110, 70)
        self.hovered     = False
        self.pressed     = False
        self._font       = None

    def _get_font(self):
        if self._font is None:
            self._font = pygame.font.SysFont("Times New Roman", 22, bold=True)
        return self._font

    def update(self, mouse_pos, mouse_buttons):
        """Cập nhật trạng thái hover/pressed – gọi mỗi frame trước draw()."""
        self.hovered = self.rect.collidepoint(mouse_pos)
        self.pressed = self.hovered and mouse_buttons[0]

    def draw(self, surface):
        color     = self.hover_color if self.hovered else self.color
        draw_rect = self.rect.move(0, 3) if self.pressed else self.rect
        pygame.draw.rect(surface, color, draw_rect, border_radius=8)
        pygame.draw.rect(surface, (60, 40, 20), draw_rect, width=2, border_radius=8)
        if self.text:
            txt = self._get_font().render(self.text, True, (255, 240, 200))
            surface.blit(txt, txt.get_rect(center=draw_rect.center))

    def is_clicked(self, event):
        hit = (event.type == pygame.MOUSEBUTTONUP
               and event.button == 1
               and self.rect.collidepoint(event.pos))
        if hit:
            SoundManager().play("btn_click")  
        return hit

# --- ImageButton --------------------------------------------------------------

class ImageButton(Button):
    """
    Kế thừa Button – thay phần vẽ rect/text bằng ảnh PNG.
    - Hover  : phóng to nhẹ theo hover_scale
    - Nhấn   : dịch xuống 3px
    - Fallback: nếu file ảnh không tồn tại, tự gọi Button.draw()
    """

    def __init__(self, img_name, center, size, hover_scale=1.06):
        x, y = center[0] - size[0] // 2, center[1] - size[1] // 2
        super().__init__(x, y, size[0], size[1], text="")

        self.center   = center
        self._has_img = False

        path = os.path.join(_ASSETS, img_name)
        if os.path.exists(path):
            self._has_img = True
            hover_size    = (int(size[0] * hover_scale), int(size[1] * hover_scale))

            self._base_img   = pygame.transform.smoothscale(
                pygame.image.load(path).convert_alpha(), size)
            self._hover_img  = pygame.transform.smoothscale(
                pygame.image.load(path).convert_alpha(), hover_size)

            self.rect        = self._base_img.get_rect(center=center)
            self._hover_rect = self._hover_img.get_rect(center=center)
        else:
            self.text = img_name   # hiện tên file để dễ debug

    def draw(self, surface):
        if not self._has_img:
            super().draw(surface)
            return

        img, rect = (self._hover_img, self._hover_rect) if self.hovered \
                    else (self._base_img, self.rect)
        surface.blit(img, rect.move(0, 3) if self.pressed else rect)
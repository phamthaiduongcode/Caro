import pygame
import os
import sys
import threading

# ─── Import source logic ──
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
from source.board import Board
from source.AI import CaroAI
from gui.button import Button, ImageButton
from gui.sound_manager import SoundManager

# ─── Constants ─
SCREEN_W, SCREEN_H = 1000, 800
BOARD_SIZE  = 15
WIN_COND    = 4
FPS         = 60
ASSETS      = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")

COLOR_OVERLAY = (0, 0, 0, 160)

STATE_MAIN_MENU    = "main_menu"
STATE_MODE_SELECT  = "mode_select"
STATE_GAME         = "game"

PLAYER_X = 1
PLAYER_O = 2

AI_TIME_LIMIT = 10

# Level → depth mapping
LEVEL_DEPTH = {
    "easy":   1,
    "medium": 2,
    "hard":   3,
}

# ─── Tiện ích ──

def load_img(name, size=None, alpha=True):
    path = os.path.join(ASSETS, name)
    img  = (pygame.image.load(path).convert_alpha()
            if alpha else pygame.image.load(path).convert())
    if size:
        img = pygame.transform.smoothscale(img, size)
    return img

def draw_text_centered(surface, text, font, color, center, shadow=True):
    if shadow:
        s = font.render(text, True, (0, 0, 0))
        surface.blit(s, s.get_rect(center=(center[0] + 2, center[1] + 2)))
    t = font.render(text, True, color)
    surface.blit(t, t.get_rect(center=center))


# ─── BoardSizePopup ───────────────────────────────────────────────────────────

class BoardSizePopup:
    """
    Popup nhập kích thước bàn cờ.
    Hiện ra khi người dùng click nút "Kích thước" ở Main Menu.
    Trả về size (int) khi xác nhận, hoặc None khi huỷ.
    """

    PANEL_W = 400
    PANEL_H = 260
    MIN_SIZE = 5
    MAX_SIZE = 30

    def __init__(self, screen_w, screen_h, current_size=15):
        self.sw      = screen_w
        self.sh      = screen_h
        self.visible = False

        cx = screen_w // 2
        cy = screen_h // 2

        self.panel_rect = pygame.Rect(0, 0, self.PANEL_W, self.PANEL_H)
        self.panel_rect.center = (cx, cy)

        px, py = self.panel_rect.topleft

        # Ô nhập liệu
        self.input_rect  = pygame.Rect(cx - 80, py + 110, 160, 48)
        self.input_text  = str(current_size)
        self.input_active = True          # luôn active khi popup mở

        # Nút xác nhận / huỷ
        btn_y = py + self.PANEL_H - 68
        self.btn_ok     = Button(cx - 110, btn_y, 100, 46, "OK")
        self.btn_cancel = Button(cx + 10,  btn_y, 100, 46, "Huỷ")

        self._font_title = pygame.font.SysFont("Times New Roman", 26, bold=True)
        self._font_label = pygame.font.SysFont("Times New Roman", 17, bold=True)
        self._font_input = pygame.font.SysFont("Times New Roman", 28, bold=True)
        self._font_hint  = pygame.font.SysFont("Times New Roman", 13)

        self._cursor_timer = 0   # dùng để nhấp nháy cursor

    # ── Mở / đóng ────────────────────────────────────────────────────────────
    def open(self, current_size=15):
        self.input_text  = str(current_size)
        self.input_active = True
        self.visible     = True
        self._cursor_timer = 0

    def close(self):
        self.visible = False

    # ── Lấy giá trị hợp lệ ──────────────────────────────────────────────────
    def _parse_size(self):
        try:
            v = int(self.input_text)
            if self.MIN_SIZE <= v <= self.MAX_SIZE:
                return v
        except ValueError:
            pass
        return None

    # ── Xử lý sự kiện ────────────────────────────────────────────────────────
    def handle_event(self, event):
        """
        Trả về:
          None      → chưa xong
          int       → size hợp lệ, đóng popup
          "cancel"  → người dùng huỷ
        """
        if not self.visible:
            return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                size = self._parse_size()
                if size:
                    self.close()
                    return size
            elif event.key == pygame.K_ESCAPE:
                self.close()
                return "cancel"
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            else:
                # Chỉ cho nhập số, tối đa 2 ký tự
                if event.unicode.isdigit() and len(self.input_text) < 2:
                    self.input_text += event.unicode

        if self.btn_ok.is_clicked(event):
            size = self._parse_size()
            if size:
                self.close()
                return size

        if self.btn_cancel.is_clicked(event):
            self.close()
            return "cancel"

        return None

    def update(self, mouse_pos, mouse_buttons):
        if not self.visible:
            return
        self._cursor_timer += 1
        self.btn_ok.update(mouse_pos, mouse_buttons)
        self.btn_cancel.update(mouse_pos, mouse_buttons)

    def draw(self, surface):
        if not self.visible:
            return

        # Overlay mờ
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surface.blit(overlay, (0, 0))

        px, py = self.panel_rect.topleft
        cx     = self.panel_rect.centerx

        # Panel nền
        ps = pygame.Surface(self.panel_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(ps, (40, 24, 8, 245), ps.get_rect(), border_radius=20)
        pygame.draw.rect(ps, (200, 150, 60, 220), ps.get_rect(), width=3, border_radius=20)
        surface.blit(ps, (px, py))

        # Tiêu đề
        title = self._font_title.render("Kích thước bàn cờ", True, (255, 220, 90))
        surface.blit(title, title.get_rect(centerx=cx, top=py + 18))

        # Nhãn gợi ý
        hint_text = f"Nhập số từ {self.MIN_SIZE} đến {self.MAX_SIZE}:"
        hint = self._font_label.render(hint_text, True, (210, 175, 110))
        surface.blit(hint, hint.get_rect(centerx=cx, top=py + 68))

        # Ô nhập liệu
        ir = self.input_rect
        valid = self._parse_size() is not None or self.input_text == ""

        # Màu viền ô nhập: vàng nếu hợp lệ, đỏ nếu không hợp lệ
        if self.input_text == "":
            border_color = (180, 140, 60)
        elif valid:
            border_color = (100, 200, 100)
        else:
            border_color = (220, 80, 80)

        pygame.draw.rect(surface, (20, 12, 4),     ir, border_radius=8)
        pygame.draw.rect(surface, border_color,    ir, width=2, border_radius=8)

        # Văn bản trong ô
        disp_text = self.input_text
        # Nhấp nháy cursor
        if (self._cursor_timer // 30) % 2 == 0:
            disp_text += "|"
        txt_surf = self._font_input.render(disp_text, True, (255, 240, 180))
        surface.blit(txt_surf, txt_surf.get_rect(center=ir.center))

        # Thông báo lỗi nếu ngoài khoảng
        if self.input_text and not valid:
            err = self._font_hint.render(
                f"Vui lòng nhập từ {self.MIN_SIZE}–{self.MAX_SIZE}",
                True, (255, 120, 100))
            surface.blit(err, err.get_rect(centerx=cx, top=ir.bottom + 6))

        self.btn_ok.draw(surface)
        self.btn_cancel.draw(surface)


# ─── _ToggleButton ─── (widget nội bộ)

class _ToggleButton(Button):
    """Button có trạng thái active / inactive – tông nâu vàng."""

    COLOR_ACTIVE    = (190, 140,  35)
    HOVER_ACTIVE    = (210, 160,  50)
    BORDER_ACTIVE   = (255, 215,  80)
    TEXT_ACTIVE     = (255, 245, 160)

    COLOR_INACTIVE  = ( 90,  58,  22)
    HOVER_INACTIVE  = (115,  78,  35)
    BORDER_INACTIVE = (160, 110,  50)
    TEXT_INACTIVE   = (210, 175, 100)

    def __init__(self, x, y, w, h, text):
        super().__init__(x, y, w, h, text)
        self.active = False

    def draw(self, surface):
        if self.active:
            bg     = self.HOVER_ACTIVE   if self.hovered else self.COLOR_ACTIVE
            border = self.BORDER_ACTIVE
            color  = self.TEXT_ACTIVE
        else:
            bg     = self.HOVER_INACTIVE if self.hovered else self.COLOR_INACTIVE
            border = self.BORDER_INACTIVE
            color  = self.TEXT_INACTIVE

        rect = self.rect.move(0, 3) if self.pressed else self.rect
        pygame.draw.rect(surface, bg,     rect, border_radius=10)
        pygame.draw.rect(surface, border, rect, width=2, border_radius=10)

        font = pygame.font.SysFont("Times New Roman", 18, bold=True)
        txt  = font.render(self.text, True, color)
        surface.blit(txt, txt.get_rect(center=rect.center))


# ─── ModeSelectScreen ──────

class ModeSelectScreen:
    PANEL_W = 540
    PANEL_H = 510

    def __init__(self, screen_w, screen_h, game_mode, board_size=15):
        self.sw        = screen_w
        self.sh        = screen_h
        self.game_mode = game_mode
        self.board_size = board_size       # nhận từ MainMenu

        self.selected_algo  = "alpha_beta"
        self.selected_level = "medium"
        self.selected_side  = PLAYER_X

        cx = screen_w // 2
        cy = screen_h // 2

        self.panel_rect = pygame.Rect(0, 0, self.PANEL_W, self.PANEL_H)
        self.panel_rect.center = (cx, cy)

        px = self.panel_rect.left
        py = self.panel_rect.top

        btn_w2, btn_h = 200, 50
        gap = 14

        # ── Hàng thuật toán (2 nút)
        algo_y   = py + 100
        left2_x  = cx - btn_w2 - gap // 2
        right2_x = cx + gap // 2

        self.btn_minimax   = _ToggleButton(left2_x,  algo_y, btn_w2, btn_h, "Minimax")
        self.btn_alphabeta = _ToggleButton(right2_x, algo_y, btn_w2, btn_h, "Alpha-Beta")

        # ── Hàng level (3 nút)
        btn_w3 = 130
        gap3   = 14
        total3 = 3 * btn_w3 + 2 * gap3
        lv_x0  = cx - total3 // 2
        lv_y   = algo_y + btn_h + 40

        self.btn_easy   = _ToggleButton(lv_x0,                   lv_y, btn_w3, btn_h, "Dễ")
        self.btn_medium = _ToggleButton(lv_x0 + btn_w3 + gap3,   lv_y, btn_w3, btn_h, "Trung bình")
        self.btn_hard   = _ToggleButton(lv_x0 + 2*(btn_w3+gap3), lv_y, btn_w3, btn_h, "Khó")

        # ── Hàng chọn phe
        side_y = lv_y + btn_h + 40

        self.btn_x = _ToggleButton(left2_x,  side_y, btn_w2, btn_h, "X")
        self.btn_o = _ToggleButton(right2_x, side_y, btn_w2, btn_h, "O")

        # ── Nút xác nhận / quay lại
        confirm_y = py + self.PANEL_H - 68
        self.btn_confirm = Button(cx - 110,  confirm_y, 220, 50, "BẮT ĐẦU")
        self.btn_back    = Button(px + 14,   confirm_y, 110, 50, "Quay lại")

        self._font_title = pygame.font.SysFont("Times New Roman", 28, bold=True)
        self._font_label = pygame.font.SysFont("Times New Roman", 18, bold=True)

        self._refresh_toggle()

    def _refresh_toggle(self):
        self.btn_minimax.active   = (self.selected_algo  == "minimax")
        self.btn_alphabeta.active = (self.selected_algo  == "alpha_beta")
        self.btn_easy.active      = (self.selected_level == "easy")
        self.btn_medium.active    = (self.selected_level == "medium")
        self.btn_hard.active      = (self.selected_level == "hard")
        self.btn_x.active         = (self.selected_side  == PLAYER_X)
        self.btn_o.active         = (self.selected_side  == PLAYER_O)

    def handle_event(self, event):
        if self.game_mode == "Ai":
            if self.btn_minimax.is_clicked(event):
                self.selected_algo = "minimax";    self._refresh_toggle()
            if self.btn_alphabeta.is_clicked(event):
                self.selected_algo = "alpha_beta"; self._refresh_toggle()
            if self.btn_easy.is_clicked(event):
                self.selected_level = "easy";      self._refresh_toggle()
            if self.btn_medium.is_clicked(event):
                self.selected_level = "medium";    self._refresh_toggle()
            if self.btn_hard.is_clicked(event):
                self.selected_level = "hard";      self._refresh_toggle()

        if self.btn_x.is_clicked(event):
            self.selected_side = PLAYER_X; self._refresh_toggle()
        if self.btn_o.is_clicked(event):
            self.selected_side = PLAYER_O; self._refresh_toggle()

        if self.btn_back.is_clicked(event):
            return "back"

        if self.btn_confirm.is_clicked(event):
            return {
                "game_mode":  self.game_mode,
                "algo":       self.selected_algo,
                "ai_depth":   LEVEL_DEPTH[self.selected_level],
                "human_side": self.selected_side,
                "board_size": self.board_size,   # truyền size vào game
            }
        return None

    def update(self, mouse_pos, mouse_buttons):
        if self.game_mode == "Ai":
            self.btn_minimax.update(mouse_pos, mouse_buttons)
            self.btn_alphabeta.update(mouse_pos, mouse_buttons)
            self.btn_easy.update(mouse_pos, mouse_buttons)
            self.btn_medium.update(mouse_pos, mouse_buttons)
            self.btn_hard.update(mouse_pos, mouse_buttons)
        self.btn_x.update(mouse_pos, mouse_buttons)
        self.btn_o.update(mouse_pos, mouse_buttons)
        self.btn_confirm.update(mouse_pos, mouse_buttons)
        self.btn_back.update(mouse_pos, mouse_buttons)

    def draw(self, surface, bg):
        surface.blit(bg, (0, 0))

        px, py = self.panel_rect.topleft
        cx = self.panel_rect.centerx

        # Panel nền
        ps = pygame.Surface(self.panel_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(ps, (40, 24,  8, 240), ps.get_rect(), border_radius=22)
        pygame.draw.rect(ps, (190, 140, 55, 210), ps.get_rect(), width=3, border_radius=22)
        surface.blit(ps, (px, py))

        # Tiêu đề — kèm size bàn cờ để người chơi biết
        mode_str = "VS MÁY" if self.game_mode == "Ai" else "VS NGƯỜI"
        title = self._font_title.render(
            f"Cài đặt — {mode_str}  [{self.board_size}×{self.board_size}]",
            True, (255, 220, 90))
        surface.blit(title, title.get_rect(centerx=cx, top=py + 16))

        if self.game_mode == "Ai":
            lbl = self._font_label.render("Thuật toán AI:", True, (235, 200, 120))
            surface.blit(lbl, lbl.get_rect(centerx=cx, top=py + 68))
            self.btn_minimax.draw(surface)
            self.btn_alphabeta.draw(surface)

            sep_y = self.btn_minimax.rect.bottom + 14
            lbl_lv = self._font_label.render("Độ khó:", True, (235, 200, 120))
            surface.blit(lbl_lv, lbl_lv.get_rect(centerx=cx, top=sep_y + 6))
            self.btn_easy.draw(surface)
            self.btn_medium.draw(surface)
            self.btn_hard.draw(surface)

            sep_y2 = self.btn_easy.rect.bottom + 14
            lbl2 = self._font_label.render("Bạn muốn đánh quân nào?", True, (235, 200, 120))
            surface.blit(lbl2, lbl2.get_rect(centerx=cx, top=sep_y2 + 6))

        else:
            lbl2 = self._font_label.render("Người chơi 1 đánh quân nào?", True, (235, 200, 120))
            surface.blit(lbl2, lbl2.get_rect(centerx=cx, top=py + 90))

        self.btn_x.draw(surface)
        self.btn_o.draw(surface)

        self.btn_confirm.draw(surface)
        self.btn_back.draw(surface)


# ─── SettingMenu ─

class SettingMenu:
    BTN_SIZE    = (320, 85)
    BTN_SPACING = 20

    def __init__(self, screen_w, screen_h):
        self.visible = False
        cx = screen_w // 2

        total_h = (self.BTN_SIZE[1] + self.BTN_SPACING) * 3 - self.BTN_SPACING
        start_y = screen_h // 2 - total_h // 2 + 30

        y1 = start_y
        y2 = y1 + self.BTN_SIZE[1] + self.BTN_SPACING
        y3 = y2 + self.BTN_SIZE[1] + self.BTN_SPACING

        self.btn_restart   = ImageButton("button_restart.png",  (cx, y1), self.BTN_SIZE)
        self.btn_new_game  = ImageButton("button_new_game.png", (cx, y2), self.BTN_SIZE)
        self.btn_surrender = ImageButton("surrender.png",       (cx, y3), self.BTN_SIZE)

        padding = 40
        panel_w = self.BTN_SIZE[0] + padding * 2
        panel_h = total_h + padding * 2 + 50
        self.panel_rect = pygame.Rect(0, 0, panel_w, panel_h)
        self.panel_rect.center = (cx, screen_h // 2)

        self._title_font = pygame.font.SysFont("Times New Roman", 32, bold=True)

    def toggle(self):  self.visible = not self.visible
    def open(self):    self.visible = True
    def close(self):   self.visible = False

    def handle_event(self, event):
        if not self.visible:
            return None
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if not self.panel_rect.collidepoint(event.pos):
                return "close"
        if self.btn_restart.is_clicked(event):   return "restart"
        if self.btn_new_game.is_clicked(event):  return "new_game"
        if self.btn_surrender.is_clicked(event): return "surrender"
        return None

    def update(self, mouse_pos, mouse_buttons):
        if not self.visible:
            return
        self.btn_restart.update(mouse_pos, mouse_buttons)
        self.btn_new_game.update(mouse_pos, mouse_buttons)
        self.btn_surrender.update(mouse_pos, mouse_buttons)

    def draw(self, surface):
        if not self.visible:
            return

        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(COLOR_OVERLAY)
        surface.blit(overlay, (0, 0))

        ps = pygame.Surface(self.panel_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(ps, (60, 40, 20, 230), ps.get_rect(), border_radius=20)
        pygame.draw.rect(ps, (120, 80, 40, 180), ps.get_rect(),
                         width=3, border_radius=20)
        surface.blit(ps, self.panel_rect.topleft)

        title = self._title_font.render("CÀI ĐẶT", True, (255, 220, 120))
        surface.blit(title, title.get_rect(
            centerx=self.panel_rect.centerx, top=self.panel_rect.top + 14))

        self.btn_restart.draw(surface)
        self.btn_new_game.draw(surface)
        self.btn_surrender.draw(surface)


# ─── WinScreen ───

class WinScreen:
    BTN_W, BTN_H = 280, 80
    SPACING      = 18

    def __init__(self, screen_w, screen_h):
        self.sw      = screen_w
        self.sh      = screen_h
        self.visible = False
        self.winner  = None

        cx   = screen_w // 2
        box_h = 260
        box_y = screen_h // 2 - box_h // 2

        btn_y1 = box_y + 140
        btn_y2 = btn_y1 + self.BTN_H + self.SPACING

        self.btn_restart  = ImageButton("button_restart.png",
                                        (cx, btn_y1), (self.BTN_W, self.BTN_H))
        self.btn_new_game = ImageButton("button_new_game.png",
                                        (cx, btn_y2), (self.BTN_W, self.BTN_H))

        total_h = 140 + self.BTN_H * 2 + self.SPACING + 20
        self.box = pygame.Rect(0, 0, 440, total_h)
        self.box.centerx = cx
        self.box.top     = box_y

        self._font_title = pygame.font.SysFont("Times New Roman", 38, bold=True)
        self._font_sub   = pygame.font.SysFont("Times New Roman", 26, bold=True)

    def show(self, winner):
        self.winner  = winner
        self.visible = True

    def hide(self):
        self.visible = False

    def handle_event(self, event):
        if not self.visible:
            return None
        if self.btn_restart.is_clicked(event):  return "restart"
        if self.btn_new_game.is_clicked(event): return "new_game"
        return None

    def update(self, mouse_pos, mouse_buttons):
        if not self.visible:
            return
        self.btn_restart.update(mouse_pos, mouse_buttons)
        self.btn_new_game.update(mouse_pos, mouse_buttons)

    def draw(self, surface):
        if not self.visible:
            return

        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))

        pygame.draw.rect(surface, (55, 35, 10),   self.box.inflate(10, 10), border_radius=24)
        pygame.draw.rect(surface, (200, 155, 70),  self.box,                border_radius=22)
        pygame.draw.rect(surface, (240, 200, 100), self.box, width=3,       border_radius=22)

        hl = pygame.Surface((self.box.width, 50), pygame.SRCALPHA)
        hl.fill((255, 255, 255, 25))
        surface.blit(hl, self.box.topleft)

        name = "1" if self.winner == PLAYER_X else "2"
        t1 = self._font_title.render(f" Người chơi {name}", True, (80, 40, 0))
        t2 = self._font_sub.render("CHIẾN THẮNG", True, (160, 90, 10))
        surface.blit(t1, t1.get_rect(centerx=self.box.centerx,
                                     top=self.box.top + 22))
        surface.blit(t2, t2.get_rect(centerx=self.box.centerx,
                                     top=self.box.top + 76))

        self.btn_restart.draw(surface)
        self.btn_new_game.draw(surface)


# ─── MoveHistoryPanel ───────

class MoveHistoryPanel:
    ROW_H    = 18
    MAX_ROWS = 18

    def __init__(self):
        self._font_hdr = pygame.font.SysFont("Courier New", 13, bold=True)
        self._font_row = pygame.font.SysFont("Courier New", 13)

    def draw(self, surface, rect, history):
        bg = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(bg, (30, 18, 6, 200), bg.get_rect(), border_radius=10)
        pygame.draw.rect(bg, (150, 100, 40, 180), bg.get_rect(),
                         width=2, border_radius=10)
        surface.blit(bg, rect.topleft)

        x0, y0 = rect.left + 8, rect.top + 8

        hdr = self._font_hdr.render(" #   Quân   Cột  Hàng", True, (255, 210, 80))
        surface.blit(hdr, (x0, y0))
        pygame.draw.line(surface, (160, 115, 50),
                         (x0, y0 + 16), (rect.right - 8, y0 + 16), 1)
        y0 += 20

        visible   = history[-self.MAX_ROWS:] if len(history) > self.MAX_ROWS else history
        start_idx = len(history) - len(visible)
        col_names = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        for i, move_data in enumerate(visible):
            r, c      = move_data[0], move_data[1]
            move_num  = start_idx + i + 1
            piece     = "X" if move_num % 2 == 1 else "O"
            col_label = col_names[c] if c < len(col_names) else str(c)
            row_label = str(r + 1)

            if i % 2 == 0:
                row_bg = pygame.Surface((rect.width - 4, self.ROW_H), pygame.SRCALPHA)
                row_bg.fill((255, 255, 255, 15))
                surface.blit(row_bg, (rect.left + 2, y0 + i * self.ROW_H))

            color = (220, 100, 80) if piece == "X" else (80, 160, 220)
            txt = self._font_row.render(
                f" {move_num:2d}    {piece}     {col_label:<3}  {row_label}",
                True, color)
            surface.blit(txt, (x0, y0 + i * self.ROW_H))

        if not history:
            empty = self._font_row.render("  (chưa có nước đi)", True, (150, 120, 70))
            surface.blit(empty, (x0, y0))


# ─── GameScreen ──

class GameScreen:
    """
    config = {
        "game_mode":  "Ai" | "human",
        "algo":       "minimax" | "alpha_beta",
        "ai_depth":   1 | 2 | 3,
        "human_side": PLAYER_X | PLAYER_O,
        "board_size": int,
    }
    """

    CELL   = 40
    OFFSET = (40, 70)

    BOARD_BG_COLOR     = (205, 170,  95)
    BOARD_LIGHT_COLOR  = (220, 190, 120)
    BOARD_BORDER_COLOR = ( 90,  55,  15)
    LINE_COLOR         = (100,  60,  20)

    def __init__(self, screen_w, screen_h, config):
        self.config     = config
        self.mode       = config["game_mode"]
        self.algo       = config.get("algo", "alpha_beta")
        self.ai_depth   = config.get("ai_depth", 2)
        self.human_side = config.get("human_side", PLAYER_X)
        self.board_size = config.get("board_size", 15)   # ← lấy từ config
        self.ai_side    = PLAYER_O if self.human_side == PLAYER_X else PLAYER_X

        self.sw = screen_w
        self.sh = screen_h

        self.board_obj = Board(size=self.board_size, win_condition=WIN_COND)

        if self.mode == "Ai":
            self.ai          = CaroAI(player_id=self.ai_side, depth=self.ai_depth)
            self.ai_thinking = False
            self.ai_result   = None

        self.setting       = SettingMenu(screen_w, screen_h)
        self.win_screen    = WinScreen(screen_w, screen_h)
        self.history_panel = MoveHistoryPanel()

        self.winner    = None
        self.game_over = False

        self.token_x    = load_img("token_x.png", (self.CELL - 6, self.CELL - 6))
        self.token_o    = load_img("token_o.png", (self.CELL - 6, self.CELL - 6))
        self.turn_x_img = load_img("turn_X.png",  (220, 55))
        self.turn_o_img = load_img("turn_o.png",  (220, 55))

        self.img_score_raw = pygame.image.load(
            os.path.join(ASSETS, "score.png")).convert_alpha()
        self.img_human = load_img("human.png",  (72, 72))
        self.img_robot = load_img("robot.png",  (72, 72))

        self.score        = {PLAYER_X: 0, PLAYER_O: 0}
        self._font_score  = pygame.font.SysFont("Times New Roman", 36, bold=True)
        self._font_slabel = pygame.font.SysFont("Times New Roman", 14, bold=True)

        board_px = self.board_size * self.CELL
        btn_cx   = self.OFFSET[0] + board_px + 90

        self.btn_setting = ImageButton("button_setting.png", (btn_cx + 50, 55),  (210, 58))
        self.btn_undo    = ImageButton("button_undo.png",    (btn_cx + 50, 130), (210, 58))

        self._font_mode     = pygame.font.SysFont("Times New Roman", 18)
        self._font_algo     = pygame.font.SysFont("Times New Roman", 14)

        self._board_surface = self._make_board_surface()

        panel_x = self.OFFSET[0] + board_px + 10
        panel_w = screen_w - panel_x - 10
        self._history_rect = pygame.Rect(
            panel_x + 6,
            screen_h - 360,
            panel_w - 12,
            340
        )

        if self.mode == "Ai" and self.ai_side == PLAYER_X:
            self._trigger_ai()

    def _make_board_surface(self):
        board_px = self.board_size * self.CELL
        surf = pygame.Surface((board_px, board_px), pygame.SRCALPHA)
        for r in range(self.board_size):
            for c in range(self.board_size):
                color = (self.BOARD_LIGHT_COLOR if (r + c) % 2 == 0
                         else self.BOARD_BG_COLOR)
                pygame.draw.rect(surf, color,
                                 (c * self.CELL, r * self.CELL,
                                  self.CELL, self.CELL))
        for i in range(self.board_size + 1):
            pygame.draw.line(surf, self.LINE_COLOR,
                             (i * self.CELL, 0), (i * self.CELL, board_px), 1)
            pygame.draw.line(surf, self.LINE_COLOR,
                             (0, i * self.CELL), (board_px, i * self.CELL), 1)
        pygame.draw.rect(surf, self.BOARD_BORDER_COLOR,
                         (0, 0, board_px, board_px), width=3)
        return surf

    @property
    def current(self):
        return self.board_obj.current_player

    def _cell_at(self, pos):
        ox, oy   = self.OFFSET
        bx, by   = pos[0] - ox, pos[1] - oy
        board_px = self.board_size * self.CELL
        if 0 <= bx < board_px and 0 <= by < board_px:
            return by // self.CELL, bx // self.CELL
        return None

    def restart(self):
        self.board_obj = Board(size=self.board_size, win_condition=WIN_COND)
        self.winner    = None
        self.game_over = False
        if self.mode == "Ai":
            self.ai_thinking = False
            self.ai_result   = None
        self.setting.close()
        self.win_screen.hide()
        if self.mode == "Ai" and self.ai_side == PLAYER_X:
            self._trigger_ai()

    def _add_score(self, winner):
        if winner in self.score:
            self.score[winner] += 1

    def _run_ai(self, board_copy):
        move, _, _, _ = self.ai.get_move(board_copy,
                                         mode=self.algo,
                                         time_limit=AI_TIME_LIMIT)
        self.ai_result = move

    def _trigger_ai(self):
        if self.ai_thinking or self.game_over:
            return
        self.ai_thinking = True
        self.ai_result   = None
        board_copy = self.board_obj.copy()
        t = threading.Thread(target=self._run_ai, args=(board_copy,), daemon=True)
        t.start()

    def _apply_ai_move(self):
        if not self.ai_thinking or self.ai_result is None:
            return
        move = self.ai_result
        self.ai_thinking = False
        self.ai_result   = None
        if move is None or self.game_over:
            return
        row, col = move
        if not self.board_obj.make_move(row, col):
            return
        result = self.board_obj.check_win()
        if result in (PLAYER_X, PLAYER_O):
            self.winner    = result
            self.game_over = True
            self._add_score(result)
            self.win_screen.show(result)
        elif result == -1:
            self.game_over = True

    def _place_move(self, row, col):
        if not self.board_obj.make_move(row, col):
            return False
        SoundManager().play("place_x")
        result = self.board_obj.check_win()
        if result in (PLAYER_X, PLAYER_O):
            self.winner    = result
            self.game_over = True
            self._add_score(result)
            self.win_screen.show(result)
        elif result == -1:
            self.game_over = True
        return True

    def _undo(self):
        if self.game_over:
            return
        if self.mode == "Ai":
            steps = 2 if len(self.board_obj.history) >= 2 else 1
            for _ in range(steps):
                self.board_obj.undo_move()
            self.ai_thinking = False
            self.ai_result   = None
        else:
            self.board_obj.undo_move()

    def handle_event(self, event):
        if self.win_screen.visible:
            action = self.win_screen.handle_event(event)
            if action == "restart":
                self.restart(); return None
            if action == "new_game":
                self.win_screen.hide(); return "new_game"
            return None

        action = self.setting.handle_event(event)
        if action == "close":    self.setting.close();  return None
        if action == "restart":  self.restart();        return None
        if action == "new_game": self.setting.close();  return "new_game"
        if action == "surrender":
            winner = PLAYER_O if self.current == PLAYER_X else PLAYER_X
            self.winner    = winner
            self.game_over = True
            self._add_score(winner)
            self.setting.close()
            self.win_screen.show(winner)
            return None

        if not self.game_over:
            if self.btn_setting.is_clicked(event):
                self.setting.toggle(); return None
            if self.btn_undo.is_clicked(event):
                self._undo();          return None

        if self.setting.visible or self.game_over:
            return None

        if self.mode == "Ai":
            if self.current != self.human_side or self.ai_thinking:
                return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            cell = self._cell_at(event.pos)
            if cell:
                row, col = cell
                if self.board_obj.grid[row * self.board_size + col] == 0:
                    placed = self._place_move(row, col)
                    if placed and not self.game_over and self.mode == "Ai":
                        self._trigger_ai()
        return None

    def update(self, mouse_pos, mouse_buttons):
        if self.mode == "Ai" and not self.game_over:
            self._apply_ai_move()
        self.win_screen.update(mouse_pos, mouse_buttons)
        if not self.win_screen.visible:
            self.btn_setting.update(mouse_pos, mouse_buttons)
            self.btn_undo.update(mouse_pos, mouse_buttons)
            self.setting.update(mouse_pos, mouse_buttons)

    def _draw_scoreboard(self, surface, panel_x, panel_w):
        cx       = panel_x + panel_w // 2
        left_cx  = panel_x + panel_w // 4
        right_cx = panel_x + 3 * panel_w // 4

        frame_w = panel_w - 16
        frame_h = 200
        frame_x = panel_x + 8
        frame_y = 180

        scaled_score = pygame.transform.smoothscale(
            self.img_score_raw, (frame_w, frame_h))
        surface.blit(scaled_score, (frame_x, frame_y))

        right_img = self.img_robot if self.mode == "Ai" else self.img_human

        av_top = frame_y + 24
        hr = self.img_human.get_rect(centerx=left_cx,  top=av_top)
        rr = right_img.get_rect(     centerx=right_cx, top=av_top)
        surface.blit(self.img_human, hr)
        surface.blit(right_img,      rr)

        num_top = max(hr.bottom, rr.bottom) + 4
        s1 = self._font_score.render(str(self.score[PLAYER_X]), True, (0, 0, 0))
        s2 = self._font_score.render(str(self.score[PLAYER_O]), True, (0, 0, 0))
        surface.blit(s1, s1.get_rect(centerx=left_cx,  top=num_top))
        surface.blit(s2, s2.get_rect(centerx=right_cx, top=num_top))

        if self.mode == "human":
            text1 = "Người X" if self.human_side == PLAYER_X else "Người O"
            text2 = "Người O" if self.human_side == PLAYER_X else "Người X"
        else:
            text1 = "Người X" if self.human_side == PLAYER_X else "Người O"
            text2 = "Máy O"   if self.human_side == PLAYER_X else "Máy X"

        lbl1 = self._font_slabel.render(text1, True, (60, 30, 10))
        lbl2 = self._font_slabel.render(text2, True, (60, 30, 10))
        lbl_top = num_top + s1.get_height() + 2
        surface.blit(lbl1, lbl1.get_rect(centerx=left_cx,  top=lbl_top))
        surface.blit(lbl2, lbl2.get_rect(centerx=right_cx, top=lbl_top))

    def draw(self, surface):
        surface.fill((210, 180, 130))

        surface.blit(self._board_surface, self.OFFSET)

        ox, oy = self.OFFSET
        half   = self.CELL // 2
        for r in range(self.board_size):
            for c in range(self.board_size):
                p = int(self.board_obj.grid[r * self.board_size + c])
                if p in (PLAYER_X, PLAYER_O):
                    img = self.token_x if p == PLAYER_X else self.token_o
                    token_rect = img.get_rect(
                        center=(ox + c * self.CELL + half,
                                oy + r * self.CELL + half))
                    surface.blit(img, token_rect)

        board_px = self.board_size * self.CELL
        panel_x  = self.OFFSET[0] + board_px + 10
        panel_w  = self.sw - panel_x - 10
        pygame.draw.rect(surface, (170, 130, 80),
                         (panel_x, 10, panel_w, self.sh - 20), border_radius=16)
        pygame.draw.rect(surface, (120, 80, 30),
                         (panel_x, 10, panel_w, self.sh - 20),
                         width=3, border_radius=16)

        self.btn_setting.draw(surface)
        self.btn_undo.draw(surface)
        self._draw_scoreboard(surface, panel_x, panel_w)

        self.history_panel.draw(surface, self._history_rect,
                                self.board_obj.history)

        turn_img  = self.turn_x_img if self.current == PLAYER_X else self.turn_o_img
        turn_rect = turn_img.get_rect(centerx=200, top=10)
        surface.blit(turn_img, turn_rect)

        mode_text = "VS MÁY" if self.mode == "Ai" else "VS NGƯỜI"
        ms = self._font_mode.render(mode_text, True, (60, 30, 10))
        surface.blit(ms, (panel_x + 8, self.sh - 56))

        if self.mode == "Ai":
            algo_label  = "Minimax" if self.algo == "minimax" else "Alpha-Beta"
            level_names = {1: "Dễ", 2: "Trung bình", 3: "Khó"}
            level_label = level_names.get(self.ai_depth, str(self.ai_depth))
            side_label  = "X" if self.human_side == PLAYER_X else "O"
            at = self._font_algo.render(
                f"[{algo_label} | {level_label}]  Bạn: {side_label}  Bàn: {self.board_size}×{self.board_size}",
                True, (130, 95, 40))
            surface.blit(at, (panel_x + 8, self.sh - 36))

        if not self.win_screen.visible:
            self.setting.draw(surface)

        self.win_screen.draw(surface)


# ─── MainMenu ──────────

class MainMenu:
    BTN_SIZE      = (280, 110)
    BTN_SIZE_ICON = (200, 60)   # nút chọn kích thước bàn cờ

    def __init__(self, screen_w, screen_h):
        self.sw = screen_w
        self.sh = screen_h
        self.bg = load_img("background.png", (screen_w, screen_h), alpha=False)

        self.board_size = 15   # kích thước bàn cờ hiện tại, mặc định 15

        cx = screen_w // 2

        self.btn_ai    = ImageButton("button_play_with_AI.png",
                                     (cx - 160, screen_h // 2 + 60), self.BTN_SIZE)
        self.btn_human = ImageButton("button_play_with_human.png",
                                     (cx + 160, screen_h // 2 + 60), self.BTN_SIZE)

        # Nút mở popup nhập size bàn cờ — đặt ở góc dưới giữa
        self.btn_size = Button(
            cx - 100, screen_h // 2 + 170,
            200, 50,
            f"Bàn cờ: {self.board_size}×{self.board_size}"
        )

        # Popup nhập kích thước
        self.popup = BoardSizePopup(screen_w, screen_h, current_size=self.board_size)

        self._font_hint = pygame.font.SysFont("Times New Roman", 14)

    def handle_event(self, event):
        # Popup ưu tiên xử lý trước
        if self.popup.visible:
            result = self.popup.handle_event(event)
            if isinstance(result, int):
                self.board_size = result
                self.btn_size.text = f"Bàn cờ: {self.board_size}×{self.board_size}"
            # "cancel" hoặc None → không làm gì thêm
            return None

        if self.btn_size.is_clicked(event):
            self.popup.open(current_size=self.board_size)
            return None

        if self.btn_ai.is_clicked(event):    return "Ai"
        if self.btn_human.is_clicked(event): return "human"
        return None

    def update(self, mouse_pos, mouse_buttons):
        self.popup.update(mouse_pos, mouse_buttons)
        if self.popup.visible:
            return   # chặn hover các nút phía sau khi popup mở
        self.btn_ai.update(mouse_pos, mouse_buttons)
        self.btn_human.update(mouse_pos, mouse_buttons)
        self.btn_size.update(mouse_pos, mouse_buttons)

    def draw(self, surface):
        surface.blit(self.bg, (0, 0))
        self.btn_ai.draw(surface)
        self.btn_human.draw(surface)
        self.btn_size.draw(surface)
        self.popup.draw(surface)   # vẽ popup lên trên cùng

    @property
    def bg_surface(self):
        return self.bg


# ─── CaroGUI ─

class CaroGUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Caro – Cờ Năm Trong Một")
        self.clock       = pygame.time.Clock()
        self.state       = STATE_MAIN_MENU
        self.menu        = MainMenu(SCREEN_W, SCREEN_H)
        self.mode_select = None
        self.game        = None

        self.sfx = SoundManager()
        self.sfx.play_bgm("sound_background.mp3", volume=0.4)

    def _open_mode_select(self, game_mode):
        # Truyền board_size từ menu vào ModeSelectScreen
        self.mode_select = ModeSelectScreen(
            SCREEN_W, SCREEN_H, game_mode,
            board_size=self.menu.board_size
        )
        self.state = STATE_MODE_SELECT

    def _start_game(self, config):
        self.game  = GameScreen(SCREEN_W, SCREEN_H, config)
        self.sfx.stop_bgm()
        self.state = STATE_GAME

    def _go_main_menu(self):
        self.game        = None
        self.mode_select = None
        self.sfx.play_bgm("sound_background.mp3", volume=0.4)
        self.state = STATE_MAIN_MENU

    def run(self):
        running = True
        while running:
            mouse_pos     = pygame.mouse.get_pos()
            mouse_buttons = pygame.mouse.get_pressed()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif self.state == STATE_MAIN_MENU:
                    action = self.menu.handle_event(event)
                    if action in ("Ai", "human"):
                        self._open_mode_select(action)

                elif self.state == STATE_MODE_SELECT:
                    result = self.mode_select.handle_event(event)
                    if result == "back":
                        self._go_main_menu()
                    elif isinstance(result, dict):
                        self._start_game(result)

                elif self.state == STATE_GAME:
                    action = self.game.handle_event(event)
                    if action == "new_game":
                        self._go_main_menu()

            if self.state == STATE_MAIN_MENU:
                self.menu.update(mouse_pos, mouse_buttons)
            elif self.state == STATE_MODE_SELECT:
                self.mode_select.update(mouse_pos, mouse_buttons)
            elif self.state == STATE_GAME:
                self.game.update(mouse_pos, mouse_buttons)

            if self.state == STATE_MAIN_MENU:
                self.menu.draw(self.screen)
            elif self.state == STATE_MODE_SELECT:
                self.mode_select.draw(self.screen, self.menu.bg_surface)
            elif self.state == STATE_GAME:
                self.game.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()
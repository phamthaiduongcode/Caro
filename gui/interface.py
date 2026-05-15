# pyrefly: ignore [missing-import]
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

STATE_MAIN_MENU = "main_menu"
STATE_GAME      = "game"

PLAYER_X = 1
PLAYER_O = 2

AI_DEPTH      = 3
AI_TIME_LIMIT = 1.0

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


# ─── SettingMenu ──────────

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
        if self.btn_restart.is_clicked(event): return "restart"
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


# ─── WinScreen ────────────────────────────────────────────────────────────────

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
        t2 = self._font_sub.render("CHIẾN THẮNG!", True, (160, 90, 10))
        surface.blit(t1, t1.get_rect(centerx=self.box.centerx,
                                     top=self.box.top + 22))
        surface.blit(t2, t2.get_rect(centerx=self.box.centerx,
                                     top=self.box.top + 76))

        self.btn_restart.draw(surface)
        self.btn_new_game.draw(surface)


# ─── GameScreen ───────────────────────────────────────────────────────────────

class GameScreen:
    """
    Màn hình ván cờ.
    """

    CELL   = 40
    OFFSET = (40, 70)

    # ── Bảng màu bàn cờ (tông vàng nâu) ──────────────────────────────────────
    # Có thể chỉnh tự do tại đây:
    BOARD_BG_COLOR    = (205, 170,  95)   # nền ô – vàng đất
    BOARD_LIGHT_COLOR = (220, 190, 120)   # ô sáng xen kẽ (checker nhẹ)
    BOARD_BORDER_COLOR= ( 90,  55,  15)   # viền ngoài bàn cờ
    LINE_COLOR        = (100,  60,  20)   # lưới kẻ ô
    DOT_COLOR         = ( 80,  45,  10)   # chấm tham chiếu (hoshi)

    def __init__(self, screen_w, screen_h, mode):
        self.mode = mode
        self.sw   = screen_w
        self.sh   = screen_h

        self.board_obj = Board(size=BOARD_SIZE, win_condition=WIN_COND)

        if self.mode == "Ai":
            self.ai          = CaroAI(player_id=PLAYER_O, depth=AI_DEPTH)
            self.ai_thinking = False
            self.ai_result   = None

        self.setting    = SettingMenu(screen_w, screen_h)
        self.win_screen = WinScreen(screen_w, screen_h)

        self.winner    = None
        self.game_over = False

        # ── Assets (không còn board.png) ─────────────────────────────────────
        self.token_x    = load_img("token_x.png", (self.CELL - 6, self.CELL - 6))
        self.token_o    = load_img("token_o.png", (self.CELL - 6, self.CELL - 6))
        self.turn_x_img = load_img("turn_X.png",  (220, 55))
        self.turn_o_img = load_img("turn_o.png",  (220, 55))

        self.img_score_raw = pygame.image.load(
            os.path.join(ASSETS, "score.png")).convert_alpha()
        self.img_human = load_img("human.png",  (72, 72))
        self.img_robot = load_img("robot.png",  (72, 72))

        self.score       = {PLAYER_X: 0, PLAYER_O: 0}
        self._font_score  = pygame.font.SysFont("Times New Roman", 36, bold=True)
        self._font_slabel = pygame.font.SysFont("Times New Roman", 14, bold=True)

        board_px = BOARD_SIZE * self.CELL
        btn_cx   = self.OFFSET[0] + board_px + 90

        self.btn_setting = ImageButton("button_setting.png", (btn_cx + 50, 55),  (210, 58))
        self.btn_undo    = ImageButton("button_undo.png",    (btn_cx + 50, 130), (210, 58))

        self._font_mode     = pygame.font.SysFont("Times New Roman", 18)
        self._font_thinking = pygame.font.SysFont("Times New Roman", 16, bold=True)

        # Cache surface bàn cờ – vẽ 1 lần, blit mỗi frame
        self._board_surface = self._make_board_surface()

    # ── Vẽ bàn cờ ─────────────────────────────────────────────────────────────

    def _make_board_surface(self):
        """
        Tạo Surface bàn cờ 15×15 với tông màu vàng nâu.
        Gọi 1 lần trong __init__, sau đó blit mỗi frame.
        """
        board_px = BOARD_SIZE * self.CELL
        surf = pygame.Surface((board_px, board_px), pygame.SRCALPHA)

        # ── Nền checker nhẹ ──────────────────────────────────────────────────
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                color = (self.BOARD_LIGHT_COLOR
                         if (r + c) % 2 == 0
                         else self.BOARD_BG_COLOR)
                pygame.draw.rect(surf, color,
                                 (c * self.CELL, r * self.CELL,
                                  self.CELL, self.CELL))

        # ── Lưới kẻ ──────────────────────────────────────────────────────────
        for i in range(BOARD_SIZE + 1):
            # dọc
            pygame.draw.line(surf, self.LINE_COLOR,
                             (i * self.CELL, 0),
                             (i * self.CELL, board_px), 1)
            # ngang
            pygame.draw.line(surf, self.LINE_COLOR,
                             (0, i * self.CELL),
                             (board_px, i * self.CELL), 1)

        # ── Viền ngoài đậm hơn ───────────────────────────────────────────────
        pygame.draw.rect(surf, self.BOARD_BORDER_COLOR,
                         (0, 0, board_px, board_px), width=3)

        return surf

    # ── Helpers 

    @property
    def current(self):
        return self.board_obj.current_player

    def _cell_at(self, pos):
        ox, oy   = self.OFFSET
        bx, by   = pos[0] - ox, pos[1] - oy
        board_px = BOARD_SIZE * self.CELL
        if 0 <= bx < board_px and 0 <= by < board_px:
            return by // self.CELL, bx // self.CELL
        return None

    def restart(self):
        self.board_obj = Board(size=BOARD_SIZE, win_condition=WIN_COND)
        self.winner    = None
        self.game_over = False
        if self.mode == "Ai":
            self.ai_thinking = False
            self.ai_result   = None
        self.setting.close()
        self.win_screen.hide()

    # tinh diem 
    def _add_score(self, winner):
        if winner in self.score:
            self.score[winner] += 1

    # ── AI thread ─────────────────────────────────────────────────────────────

    def _run_ai(self, board_copy):
        move, _, _, _ = self.ai.get_move(board_copy,
                                         mode="alpha_beta",
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

    # ── Event / logic ─────────────────────────────────────────────────────────

    def _place_move(self, row, col):
        if not self.board_obj.make_move(row, col):
            return False
        # sound danh quan 
        sfx = SoundManager()
        sfx.play("place_x")
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
        steps = 2 if (self.mode == "Ai" and len(self.board_obj.history) >= 2) else 1
        for _ in range(steps):
            self.board_obj.undo_move()
        if self.mode == "Ai":
            self.ai_thinking = False
            self.ai_result   = None

    def handle_event(self, event):
        if self.win_screen.visible:
            action = self.win_screen.handle_event(event)
            if action == "restart":
                self.restart()
                return None
            if action == "new_game":
                self.win_screen.hide()
                return "new_game"
            return None

        action = self.setting.handle_event(event)
        if action == "close":
            self.setting.close();  return None
        if action == "restart":
            self.restart();        return None
        if action == "new_game":
            self.setting.close();  return "new_game"
        if action == "surrender":
            winner = PLAYER_O if self.current == PLAYER_X else PLAYER_X
            self.winner    = winner
            self.game_over = True
            self._add_score(winner) # tinh diem khi dau hang 
            self.setting.close()
            self.win_screen.show(winner)
            return None

        if not self.game_over:
            if self.btn_setting.is_clicked(event):
                self.setting.toggle();  return None
            if self.btn_undo.is_clicked(event):
                self._undo();           return None

        if self.setting.visible or self.game_over:
            return None

        if self.mode == "Ai":
            if self.current != PLAYER_X or self.ai_thinking:
                return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            cell = self._cell_at(event.pos)
            if cell:
                row, col = cell
                if self.board_obj.grid[row][col] == 0:
                    placed = self._place_move(row, col)
                    if placed and not self.game_over and self.mode == "Ai":
                        self._trigger_ai()

        return None

    # ── Update / Draw ─────────────────────────────────────────────────────────

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
        frame_h = 230
        frame_x = panel_x + 8
        frame_y = 180

        scaled_score = pygame.transform.smoothscale(
            self.img_score_raw, (frame_w, frame_h))
        surface.blit(scaled_score, (frame_x, frame_y))

        right_img = self.img_robot if self.mode == "Ai" else self.img_human
        av_top    = frame_y + 30

        hr = self.img_human.get_rect(centerx=left_cx,  top=av_top)
        rr = right_img.get_rect(     centerx=right_cx, top=av_top)
        surface.blit(self.img_human, hr)
        surface.blit(right_img,      rr)

        num_top = max(hr.bottom, rr.bottom) + 6
        s1 = self._font_score.render(str(self.score[PLAYER_X]), True, (0, 0, 0))
        s2 = self._font_score.render(str(self.score[PLAYER_O]), True, (0, 0, 0))
        surface.blit(s1, s1.get_rect(centerx=left_cx,  top=num_top))
        surface.blit(s2, s2.get_rect(centerx=right_cx, top=num_top))

        lbl1 = self._font_slabel.render("Người 1", True, (60, 30, 10))
        lbl2 = self._font_slabel.render(
            "Máy" if self.mode == "Ai" else "Người 2", True, (60, 30, 10))
        lbl_top = num_top + s1.get_height() + 2
        surface.blit(lbl1, lbl1.get_rect(centerx=left_cx,  top=lbl_top))
        surface.blit(lbl2, lbl2.get_rect(centerx=right_cx, top=lbl_top))

    def draw(self, surface):
        surface.fill((210, 180, 130))

        # ── Bàn cờ tự vẽ (cache surface) ─────────────────────────────────────
        surface.blit(self._board_surface, self.OFFSET)

        # ── Token X / O – tâm ô chính xác pixel ──────────────────────────────
        ox, oy = self.OFFSET
        half   = self.CELL // 2          # 20px – tâm ô
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                p = int(self.board_obj.grid[r][c])
                if p in (PLAYER_X, PLAYER_O):
                    img = self.token_x if p == PLAYER_X else self.token_o
                    token_rect = img.get_rect(
                        center=(ox + c * self.CELL + half,
                                oy + r * self.CELL + half))
                    surface.blit(img, token_rect)

        # ── Panel bên phải ────────────────────────────────────────────────────
        board_px = BOARD_SIZE * self.CELL
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

        # Turn indicator
        turn_img  = self.turn_x_img if self.current == PLAYER_X else self.turn_o_img
        turn_rect = turn_img.get_rect(centerx=400, top=10)
        surface.blit(turn_img, turn_rect)

        if self.mode == "Ai" and self.ai_thinking:
            thinking_text = self._font_thinking.render(
                "Ai đang suy nghĩ...", True, (212, 175, 55))
            surface.blit(thinking_text,
                         thinking_text.get_rect(
                             centerx=400,
                             top=turn_rect.bottom + 1))

        mode_text = "VS MÁY" if self.mode == "Ai" else "VS NGƯỜI"
        ms = self._font_mode.render(mode_text, True, (60, 30, 10))
        surface.blit(ms, (panel_x + 10, self.sh - 36))

        if not self.win_screen.visible:
            self.setting.draw(surface)

        self.win_screen.draw(surface)


# ─── MainMenu ─────────────────────────────────────────────────────────────────

class MainMenu:
    BTN_SIZE = (280, 110)

    def __init__(self, screen_w, screen_h):
        self.sw = screen_w
        self.sh = screen_h
        self.bg = load_img("background.png", (screen_w, screen_h), alpha=False)

        cx = screen_w // 2

        self.btn_ai    = ImageButton("button_play_with_AI.png",
                                     (cx - 160, screen_h // 2 + 60), self.BTN_SIZE)
        self.btn_human = ImageButton("button_play_with_human.png",
                                     (cx + 160, screen_h // 2 + 60), self.BTN_SIZE)

    def handle_event(self, event):
        if self.btn_ai.is_clicked(event):    return "Ai"
        if self.btn_human.is_clicked(event): return "human"
        return None

    def update(self, mouse_pos, mouse_buttons):
        self.btn_ai.update(mouse_pos, mouse_buttons)
        self.btn_human.update(mouse_pos, mouse_buttons)

    def draw(self, surface):
        surface.blit(self.bg, (0, 0))
        self.btn_ai.draw(surface)
        self.btn_human.draw(surface)
        font = pygame.font.SysFont("Times New Roman", 50)
        self.title = draw_text_centered(surface, "Game Cờ Caro", font,
                                        (108, 128, 128), (550, 200))


# ─── CaroGUI ──────────────────────────────────────────────────────────────────

class CaroGUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Caro – Cờ Năm Trong Một")
        self.clock  = pygame.time.Clock()
        self.state  = STATE_MAIN_MENU
        self.menu   = MainMenu(SCREEN_W, SCREEN_H)
        self.game   = None

        # ── Âm thanh ──────────────────────────────
        self.sfx = SoundManager()
        self.sfx.play_bgm("sound_background.mp3", volume=0.4)
    def _start_game(self, mode):
        self.game  = GameScreen(SCREEN_W, SCREEN_H, mode)
        self.sfx.stop_bgm()
        self.state = STATE_GAME

    def _go_main_menu(self):
        self.game  = None
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
                        self._start_game(action)

                elif self.state == STATE_GAME:
                    action = self.game.handle_event(event)
                    if action == "new_game":
                        self._go_main_menu()

            if self.state == STATE_MAIN_MENU:
                self.menu.update(mouse_pos, mouse_buttons)
            elif self.state == STATE_GAME:
                self.game.update(mouse_pos, mouse_buttons)

            if self.state == STATE_MAIN_MENU:
                self.menu.draw(self.screen)
            elif self.state == STATE_GAME:
                self.game.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()
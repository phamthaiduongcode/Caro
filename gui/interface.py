import pygame
import os
import sys
import threading

# ─── Import source logic ──
# Thêm thư mục gốc vào path để import source/ và gui/
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
from source.board import Board        # Bước 4: dùng Board thay list 2D
from source.AI import CaroAI          # Bước 3: kết nối AI
from gui.button import Button, ImageButton  # Tái sử dụng button.py

# ─── Constants ─
SCREEN_W, SCREEN_H = 1000, 800
BOARD_SIZE  = 15          # 15×15 – đồng nhất với GUI
WIN_COND    = 5           # Cờ Caro thắng 5 quân liên tiếp
FPS         = 60
ASSETS      = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")

# Màu sắc
COLOR_OVERLAY = (0, 0, 0, 160)

# Trạng thái màn hình
STATE_MAIN_MENU = "main_menu"
STATE_GAME      = "game"

# Người chơi – khớp với source/board.py (1=X, 2=O)
PLAYER_X = 1
PLAYER_O = 2

# AI config
AI_DEPTH      = 3
AI_TIME_LIMIT = 1.0   # giây

# ─── Tiện ích ──

def load_img(name, size=None, alpha=True):
    """Tải ảnh từ thư mục assets, tuỳ chọn scale."""
    path = os.path.join(ASSETS, name)
    img  = (pygame.image.load(path).convert_alpha()
            if alpha else pygame.image.load(path).convert())
    if size:
        img = pygame.transform.smoothscale(img, size)
    return img

def draw_text_centered(surface, text, font, color, center, shadow=True):
    """Vẽ text căn giữa, tuỳ chọn bóng đổ."""
    if shadow:
        s = font.render(text, True, (0, 0, 0))
        surface.blit(s, s.get_rect(center=(center[0] + 2, center[1] + 2)))
    t = font.render(text, True, color)
    surface.blit(t, t.get_rect(center=center))


# ─── SettingMenu ──────────

class SettingMenu:
    """
    Overlay menu cài đặt hiện ra khi nhấn nút Setting.
    Chứa: Restart | New Game | Đầu Hàng.
    """

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
        self.btn_surrender = ImageButton( "surrender.png",(cx, y3), self.BTN_SIZE)

        # Panel nền
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
        """Trả về: 'restart' | 'new_game' | 'surrender' | 'close' | None"""
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

        # Màn mờ
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(COLOR_OVERLAY)
        surface.blit(overlay, (0, 0))

        # Panel gỗ
        ps = pygame.Surface(self.panel_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(ps, (60, 40, 20, 230), ps.get_rect(), border_radius=20)
        pygame.draw.rect(ps, (120, 80, 40, 180), ps.get_rect(),
                         width=3, border_radius=20)
        surface.blit(ps, self.panel_rect.topleft)

        # Tiêu đề
        title = self._title_font.render("CÀI ĐẶT", True, (255, 220, 120))
        surface.blit(title, title.get_rect(
            centerx=self.panel_rect.centerx, top=self.panel_rect.top + 14))

        self.btn_restart.draw(surface)
        self.btn_new_game.draw(surface)
        self.btn_surrender.draw(surface)


# ─── WinScreen 

class WinScreen:
    """
    Overlay thắng cuộc: hiện tên người thắng + 2 nút
      - CHƠI LẠI  (restart, giữ điểm)
      - BẮT ĐẦU MỚI (về màn chính, reset điểm)
    """

    BTN_W, BTN_H = 280, 80
    SPACING      = 18

    def __init__(self, screen_w, screen_h):
        self.sw      = screen_w
        self.sh      = screen_h
        self.visible = False
        self.winner  = None   # PLAYER_1 hoặc PLAYER_2

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
        """Trả về: 'restart' | 'new_game' | None"""
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


# ─── GameScreen 

class GameScreen:
    """
    Màn hình ván cờ.

    Bước 4: Dùng source/board.Board thay list 2D thủ công.
    Bước 3: Tích hợp CaroAI – khi mode='ai', sau lượt người chơi,
            AI tự tính nước đi trên thread riêng rồi apply.
    """

    CELL   = 40
    OFFSET = (40, 70)

    def __init__(self, screen_w, screen_h, mode):
        """
        mode : 'Ai' | 'human'
        """
        self.mode = mode
        self.sw   = screen_w
        self.sh   = screen_h

        # ── Bước 4: Board từ source 
        self.board_obj = Board(size=BOARD_SIZE, win_condition=WIN_COND)

        # ── Bước 3: AI ───
        # AI luôn đóng vai O (player_id=2), người chơi là X (player_id=1)
        if self.mode == "Ai":
            self.ai         = CaroAI(player_id=PLAYER_O, depth=AI_DEPTH)
            self.ai_thinking = False   # đang tính toán trên thread?
            self.ai_result   = None    # (row, col) kết quả từ thread

        self.setting    = SettingMenu(screen_w, screen_h)
        self.win_screen = WinScreen(screen_w, screen_h)

        # Trạng thái game
        self.winner    = None
        self.game_over = False

        # ── Assets ──────
        board_px        = BOARD_SIZE * self.CELL
        self.board_img  = load_img("board.png",  (board_px, board_px))
        self.token_x    = load_img("token_x.png", (self.CELL - 4, self.CELL - 4))
        self.token_o    = load_img("token_o.png", (self.CELL - 4, self.CELL - 4))
        self.turn_x_img = load_img("turn_X.png",  (220, 55))
        self.turn_o_img = load_img("turn_o.png",  (220, 55))

        # ── Scoreboard assets 
        self.img_score_raw = pygame.image.load(
            os.path.join(ASSETS, "score.png")).convert_alpha()   # tiêu đề bảng điểm
        self.img_human = load_img("human.png",  (72, 72))    # avatar người
        self.img_robot = load_img("robot.png",  (72, 72))    # avatar AI/người 2

        self.score      = {PLAYER_X: 0, PLAYER_O: 0}
        self._font_score = pygame.font.SysFont("Times New Roman", 36, bold=True)
        self._font_slabel = pygame.font.SysFont("Times New Roman", 14, bold=True)

        # Panel bên phải
        btn_cx = self.OFFSET[0] + board_px + 90

        self.btn_setting = ImageButton("button_setting.png", (btn_cx, 55),  (210, 58))
        self.btn_undo    = ImageButton("button_undo.png",    (btn_cx, 130), (210, 58))

        self._font_mode     = pygame.font.SysFont("Times New Roman", 18)
        self._font_thinking = pygame.font.SysFont("Times New Roman", 16, bold=True)

    # ── Helpers 

    @property
    def current(self):
        """Người chơi hiện tại lấy thẳng từ Board."""
        return self.board_obj.current_player

    def _cell_at(self, pos):
        ox, oy   = self.OFFSET
        bx, by   = pos[0] - ox, pos[1] - oy
        board_px = BOARD_SIZE * self.CELL
        if 0 <= bx < board_px and 0 <= by < board_px:
            return by // self.CELL, bx // self.CELL
        return None

    def restart(self):
        """Chơi lại ván mới, giữ điểm."""
        self.board_obj = Board(size=BOARD_SIZE, win_condition=WIN_COND)
        self.winner    = None
        self.game_over = False
        if self.mode == "Ai":
            self.ai_thinking = False
            self.ai_result   = None
        self.setting.close()
        self.win_screen.hide()

    def _add_score(self, winner):
        """Cộng điểm cho người thắng."""
        if winner in self.score:
            self.score[winner] += 1
        
    # ── Bước 3: AI thread 

    def _run_ai(self, board_copy):
        """Chạy trên thread riêng để không block render."""
        move, _, _, _ = self.ai.get_move(board_copy,
                                         mode="alpha_beta",
                                         time_limit=AI_TIME_LIMIT)
        self.ai_result = move   # ghi kết quả; main loop sẽ apply

    def _trigger_ai(self):
        """Khởi động AI thread nếu chưa đang chạy."""
        if self.ai_thinking or self.game_over:
            return
        self.ai_thinking = True
        self.ai_result   = None
        # Truyền bản sao Board vào thread để tránh race condition
        board_copy = self.board_obj.copy()
        t = threading.Thread(target=self._run_ai, args=(board_copy,), daemon=True)
        t.start()

    def _apply_ai_move(self):
        """
        Gọi mỗi frame trong update() – nếu AI đã trả kết quả thì apply.
        """
        if not self.ai_thinking or self.ai_result is None:
            return
        move = self.ai_result
        self.ai_thinking = False
        self.ai_result   = None

        if move is None or self.game_over:
            return

        row, col = move
        if not self.board_obj.make_move(row, col):
            return   # nước không hợp lệ (không nên xảy ra)

        result = self.board_obj.check_win()
        if result in (PLAYER_X, PLAYER_O):
            self.winner    = result
            self.game_over = True
            self._add_score(result)
            self.win_screen.show(result)
        elif result == -1:   # Hòa
            self.game_over = True

    # ── Event / logic ─────

    def _place_move(self, row, col):
        """
        Đặt quân cho người chơi hiện tại (dùng Board.make_move).
        Trả về True nếu thành công.
        """
        if not self.board_obj.make_move(row, col):
            return False

        result = self.board_obj.check_win()
        if result in (PLAYER_X, PLAYER_O):
            self.winner    = result
            self.game_over = True
            self._add_score(result)
            self.win_screen.show(result)
        elif result == -1:
            self.game_over = True   # Hòa
        return True

    def _undo(self):
        """
        Undo: chế độ human → lùi 1 nước.
                chế độ ai   → lùi 2 nước (người + AI) để người chơi được đi lại.
        """
        if self.game_over:
            return
        steps = 2 if (self.mode == "Ai" and len(self.board_obj.history) >= 2) else 1
        for _ in range(steps):
            self.board_obj.undo_move()
        # Đảm bảo AI không đang nghĩ dở khi undo
        if self.mode == "Ai":
            self.ai_thinking = False
            self.ai_result   = None

    def handle_event(self, event):
        """
        Trả về:
          'new_game'  → Về màn chính (reset điểm)
          None        → tiếp tục game
        """
        # Win screen ưu tiên cao nhất
        if self.win_screen.visible:
            action = self.win_screen.handle_event(event)
            if action == "restart":
                self.restart()
                return None
            if action == "new_game":
                self.win_screen.hide()
                return "new_game"
            return None

        # Setting menu
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
            self.setting.close()
            self.win_screen.show(winner)
            return None

        # Nút Setting / Undo
        if not self.game_over:
            if self.btn_setting.is_clicked(event):
                self.setting.toggle();  return None
            if self.btn_undo.is_clicked(event):
                self._undo();           return None

        # ── Click bàn cờ ──────────────────────────────────────────────────
        if self.setting.visible or self.game_over:
            return None

        # Chế độ AI: chỉ nhận click khi đến lượt người (PLAYER_X)
        # và AI không đang suy nghĩ
        if self.mode == "Ai":
            if self.current != PLAYER_X or self.ai_thinking:
                return None   # bỏ qua click khi AI đang tính

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            cell = self._cell_at(event.pos)
            if cell:
                row, col = cell
                if self.board_obj.grid[row, col] == 0:
                    placed = self._place_move(row, col)
                    # Bước 3: sau lượt người → kích hoạt AI
                    if placed and not self.game_over and self.mode == "Ai":
                        self._trigger_ai()

        return None

    # ── Update / Draw ─────

    def update(self, mouse_pos, mouse_buttons):
        # Bước 3: kiểm tra kết quả AI mỗi frame
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

        # ── score.png phóng to làm khung nền ───────────────────────────
        frame_w = panel_w - 16
        frame_h = 230
        frame_x = panel_x + 8
        frame_y = 180

        scaled_score = pygame.transform.smoothscale(
            self.img_score_raw, (frame_w, frame_h))
        surface.blit(scaled_score, (frame_x, frame_y))

        # ── Avatar đè lên bên trong khung ──────────────────────────────
        right_img = self.img_robot if self.mode == "Ai" else self.img_human
        av_top    = frame_y + 30   # chừa khoảng trên cho tiêu đề của ảnh score

        hr = self.img_human.get_rect(centerx=left_cx,  top=av_top)
        rr = right_img.get_rect(     centerx=right_cx, top=av_top)
        surface.blit(self.img_human, hr)
        surface.blit(right_img,      rr)

        # ── Số điểm ────────────────────────────────────────────────────
        num_top = max(hr.bottom, rr.bottom) + 6
        s1 = self._font_score.render(str(self.score[PLAYER_X]), True, (0, 0, 0))
        s2 = self._font_score.render(str(self.score[PLAYER_O]), True, (0, 0, 0))
        surface.blit(s1, s1.get_rect(centerx=left_cx,  top=num_top))
        surface.blit(s2, s2.get_rect(centerx=right_cx, top=num_top))

        # ── Nhãn nhỏ ───────────────────────────────────────────────────
        lbl1 = self._font_slabel.render("Người 1", True, (60, 30, 10))
        lbl2 = self._font_slabel.render(
            "Máy" if self.mode == "Ai" else "Người 2", True, (60, 30, 10))
        lbl_top = num_top + s1.get_height() + 2
        surface.blit(lbl1, lbl1.get_rect(centerx=left_cx,  top=lbl_top))
        surface.blit(lbl2, lbl2.get_rect(centerx=right_cx, top=lbl_top))

    def draw(self, surface):
        surface.fill((210, 180, 130))

        # Bàn cờ
        surface.blit(self.board_img, self.OFFSET)

        # ── Bước 4: đọc quân cờ từ board_obj.grid (numpy array) ──────────
        ox, oy = self.OFFSET
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                p = int(self.board_obj.grid[r, c])
                if p in (PLAYER_X, PLAYER_O):
                    img = self.token_x if p == PLAYER_X else self.token_o
                    # MỚI – căn giữa token vào đúng tâm ô
                    token_rect = img.get_rect(
                        center=(ox + c * self.CELL + self.CELL // 2,
                            oy + r * self.CELL + self.CELL // 2))
                    surface.blit(img, token_rect)

        # Panel bên phải
        board_px = BOARD_SIZE * self.CELL
        panel_x  = self.OFFSET[0] + board_px + 10
        panel_w  = self.sw - panel_x - 10
        pygame.draw.rect(surface, (170, 130, 80),
                         (panel_x, 10, panel_w, self.sh - 20), border_radius=16)
        pygame.draw.rect(surface, (120, 80, 30),
                         (panel_x, 10, panel_w, self.sh - 20),
                         width=3, border_radius=16)

        # Nút
        self.btn_setting.draw(surface)
        self.btn_undo.draw(surface)
        self._draw_scoreboard(surface, panel_x, panel_w)

        # Turn indicator
        turn_img  = self.turn_x_img if self.current == PLAYER_X else self.turn_o_img
        turn_top  = 10
        turn_rect = turn_img.get_rect(centerx=400, top=turn_top)
        surface.blit(turn_img, turn_rect)

        # Bước 3: Hiển thị "AI đang suy nghĩ..." khi AI thread đang chạy
        if self.mode == "Ai" and self.ai_thinking:
            thinking_text = self._font_thinking.render(
                "Ai đang suy nghĩ...", True, (212, 175, 55))
            surface.blit(thinking_text,
                         thinking_text.get_rect(
                             centerx=400,
                             top=turn_rect.bottom + 1))

        # Mode label
        mode_text = "VS MÁY" if self.mode == "Ai" else "VS NGƯỜI"
        ms = self._font_mode.render(mode_text, True, (60, 30, 10))
        surface.blit(ms, (panel_x + 10, self.sh - 36))

        # Setting menu
        if not self.win_screen.visible:
            self.setting.draw(surface)

        # Win screen (luôn trên cùng)
        self.win_screen.draw(surface)

    


# ─── MainMenu ──

class MainMenu:
    """Màn hình chính: background + 2 nút chọn chế độ chơi + 1 title ."""

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
        self.title = draw_text_centered(surface , "Game Cờ Caro", font, (108, 128, 128) , (550,200))


# ─── CaroGUI ───

class CaroGUI:
    """Lớp điều phối chính: quản lý vòng lặp game và chuyển đổi màn hình."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Caro – Cờ Năm Trong Một")
        self.clock  = pygame.time.Clock()
        self.state  = STATE_MAIN_MENU
        self.menu   = MainMenu(SCREEN_W, SCREEN_H)
        self.game   = None

    def _start_game(self, mode):
        self.game  = GameScreen(SCREEN_W, SCREEN_H, mode)
        self.state = STATE_GAME

    def _go_main_menu(self):
        self.game  = None
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
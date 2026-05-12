import pygame
import os
import sys

# ─── Constants ────────────────────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 1000, 700
BOARD_SIZE = 15          # 15×15 grid
FPS        = 60
ASSETS     = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")

# Màu sắc
COLOR_OVERLAY = (0, 0, 0, 160)

# Trạng thái màn hình
STATE_MAIN_MENU = "main_menu"
STATE_GAME      = "game"

# Người chơi
PLAYER_X = 1
PLAYER_O = 2


# ─── Tiện ích ─────────────────────────────────────────────────────────────────

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


# ─── ImageButton ──────────────────────────────────────────────────────────────

class ImageButton:
    """Nút bấm dùng hình ảnh với hover scale + hiệu ứng nhấn."""

    def __init__(self, img_name, center, size, hover_scale=1.06):
        self.base_size  = size
        self.hover_size = (int(size[0] * hover_scale), int(size[1] * hover_scale))
        self.center     = center
        self.base_img   = load_img(img_name, size)
        self.hover_img  = load_img(img_name, self.hover_size)
        self.rect       = self.base_img.get_rect(center=center)
        self.hover_rect = self.hover_img.get_rect(center=center)
        self.hovered    = False
        self.pressed    = False

    def update(self, mouse_pos, mouse_buttons):
        self.hovered = self.rect.collidepoint(mouse_pos)
        self.pressed = self.hovered and mouse_buttons[0]

    def draw(self, surface):
        img, rect = (self.hover_img, self.hover_rect) if self.hovered \
                    else (self.base_img, self.rect)
        surface.blit(img, rect.move(0, 3) if self.pressed else rect)

    def is_clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONUP
                and event.button == 1
                and self.rect.collidepoint(event.pos))


# ─── SurrenderButton ──────────────────────────────────────────────────────────

class SurrenderButton:
    """
    Nút Đầu Hàng dùng ảnh 'surrender.png'.
    Tự động dùng code-render fallback nếu chưa có file.
    """

    ASSET_NAME = "surrender.png"

    def __init__(self, center, size=(320, 80)):
        self.size    = size
        self.center  = center
        self.rect    = pygame.Rect(0, 0, *size)
        self.rect.center = center
        self.hovered = False
        self.pressed = False

        asset_path    = os.path.join(ASSETS, self.ASSET_NAME)
        self._use_img = os.path.exists(asset_path)
        if self._use_img:
            self._btn = ImageButton(self.ASSET_NAME, center, size)

        self._font = pygame.font.SysFont("segoeuibold", 26, bold=True)

    def update(self, mouse_pos, mouse_buttons):
        self.hovered = self.rect.collidepoint(mouse_pos)
        self.pressed = self.hovered and mouse_buttons[0]
        if self._use_img:
            self._btn.update(mouse_pos, mouse_buttons)

    def draw(self, surface):
        if self._use_img:
            self._btn.draw(surface)
            return

        # ── Code-render fallback (khi chưa có ảnh) ──
        color     = (220, 80, 55) if self.hovered else (180, 60, 40)
        draw_rect = self.rect.move(0, 3) if self.pressed else self.rect
        pygame.draw.rect(surface, (100, 40, 20), draw_rect.inflate(8, 8),
                         border_radius=14)
        pygame.draw.rect(surface, color, draw_rect, border_radius=12)
        hl = pygame.Surface((draw_rect.width, draw_rect.height // 2),
                            pygame.SRCALPHA)
        hl.fill((255, 255, 255, 40))
        surface.blit(hl, draw_rect.topleft)
        txt  = self._font.render("⚑  ĐẦU HÀNG", True, (255, 240, 200))
        surface.blit(txt, txt.get_rect(center=draw_rect.center))

    def is_clicked(self, event):
        if self._use_img:
            return self._btn.is_clicked(event)
        return (event.type == pygame.MOUSEBUTTONUP
                and event.button == 1
                and self.rect.collidepoint(event.pos))


# ─── ScoreBoard ───────────────────────────────────────────────────────────────

class ScoreBoard:
    """
    Bảng tính điểm hiển thị trong màn hình game.
    - mode='ai'    → dùng score_AI.png  (Người chơi vs Máy)
    - mode='human' → dùng score_human.png (Người chơi 1 vs Người chơi 2)

    Điểm số overlay lên đúng vị trí số '0' trong ảnh gốc.
    Tăng tự động khi một bên thắng; reset khi về màn chính.
    """

    # Kích thước ảnh score trên panel
    IMG_SIZE = (220, 130)

    # Offset tọa độ số điểm SO VỚI góc trên-trái của ảnh score
    # (căn chỉnh theo vị trí '0' trong ảnh gốc)
    # score_AI  : Người chơi bên trái, Máy bên phải
    SCORE_POS_AI    = [(58, 88), (168, 88)]   # (left_cx, left_cy), (right_cx, right_cy)
    # score_human: Người chơi 1 bên trái, Người chơi 2 bên phải
    SCORE_POS_HUMAN = [(58, 88), (168, 88)]

    def __init__(self, mode, topleft):
        self.mode     = mode
        self.topleft  = topleft          # (x, y) trên màn hình
        self.score    = [0, 0]           # [score_X, score_O]

        img_name      = "score_AI.png" if mode == "ai" else "score_human.png"
        self.img      = load_img(img_name, self.IMG_SIZE)
        self.rect     = self.img.get_rect(topleft=topleft)

        self._font    = pygame.font.SysFont("impact", 28, bold=True)

    def add_win(self, player):
        """Cộng điểm cho player (PLAYER_X=1 hoặc PLAYER_O=2)."""
        if player == PLAYER_X:
            self.score[0] += 1
        elif player == PLAYER_O:
            self.score[1] += 1

    def reset(self):
        self.score = [0, 0]

    def draw(self, surface):
        # Vẽ ảnh nền bảng điểm
        surface.blit(self.img, self.rect.topleft)

        # Vẽ điểm số overlay
        pos_list = (self.SCORE_POS_AI
                    if self.mode == "ai" else self.SCORE_POS_HUMAN)
        ox, oy = self.rect.topleft
        for i, (px, py) in enumerate(pos_list):
            draw_text_centered(
                surface,
                str(self.score[i]),
                self._font,
                (255, 220, 80),
                (ox + px, oy + py),
                shadow=True
            )


# ─── SettingMenu ──────────────────────────────────────────────────────────────

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
        self.btn_surrender = SurrenderButton(                   (cx, y3), self.BTN_SIZE)

        # Panel nền
        padding = 40
        panel_w = self.BTN_SIZE[0] + padding * 2
        panel_h = total_h + padding * 2 + 50
        self.panel_rect = pygame.Rect(0, 0, panel_w, panel_h)
        self.panel_rect.center = (cx, screen_h // 2)

        self._title_font = pygame.font.SysFont("segoeuibold", 32, bold=True)

    def toggle(self):  self.visible = not self.visible
    def open(self):    self.visible = True
    def close(self):   self.visible = False

    def handle_event(self, event):
        """
        Trả về: 'restart' | 'new_game' | 'surrender' | 'close' | None
        """
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
        title = self._title_font.render("⚙  CÀI ĐẶT", True, (255, 220, 120))
        surface.blit(title, title.get_rect(
            centerx=self.panel_rect.centerx, top=self.panel_rect.top + 14))

        self.btn_restart.draw(surface)
        self.btn_new_game.draw(surface)
        self.btn_surrender.draw(surface)


# ─── WinScreen ───────────────────────────────────────────────────────────────

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
        self.winner  = None   # PLAYER_X hoặc PLAYER_O

        cx   = screen_w // 2
        # Hộp tổng thể
        box_h = 260
        box_y = screen_h // 2 - box_h // 2

        # Vị trí 2 nút nằm trong hộp
        btn_y1 = box_y + 140
        btn_y2 = btn_y1 + self.BTN_H + self.SPACING

        self.btn_restart  = ImageButton("button_restart.png",
                                        (cx, btn_y1), (self.BTN_W, self.BTN_H))
        self.btn_new_game = ImageButton("button_new_game.png",
                                        (cx, btn_y2), (self.BTN_W, self.BTN_H))

        # Rect toàn hộp (dùng để vẽ nền)
        total_h = 140 + self.BTN_H * 2 + self.SPACING + 20
        self.box = pygame.Rect(0, 0, 440, total_h)
        self.box.centerx = cx
        self.box.top     = box_y

        self._font_title = pygame.font.SysFont("segoeuibold", 38, bold=True)
        self._font_sub   = pygame.font.SysFont("segoeuibold", 26, bold=True)

    def show(self, winner):
        self.winner  = winner
        self.visible = True

    def hide(self):
        self.visible = False

    def handle_event(self, event):
        """
        Trả về: 'restart' | 'new_game' | None
        """
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

        # Lớp mờ
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))

        # Hộp nền gỗ vàng
        pygame.draw.rect(surface, (55, 35, 10),   self.box.inflate(10, 10), border_radius=24)
        pygame.draw.rect(surface, (200, 155, 70),  self.box,                border_radius=22)
        pygame.draw.rect(surface, (240, 200, 100), self.box, width=3,       border_radius=22)

        # Highlight phía trên
        hl = pygame.Surface((self.box.width, 50), pygame.SRCALPHA)
        hl.fill((255, 255, 255, 25))
        surface.blit(hl, self.box.topleft)

        # Tên người thắng
        name = "X" if self.winner == PLAYER_X else "O"
        t1 = self._font_title.render(f"🏆  Người chơi {name}  🏆", True, (80, 40, 0))
        t2 = self._font_sub.render("CHIẾN THẮNG!", True, (160, 90, 10))
        surface.blit(t1, t1.get_rect(centerx=self.box.centerx,
                                     top=self.box.top + 22))
        surface.blit(t2, t2.get_rect(centerx=self.box.centerx,
                                     top=self.box.top + 76))

        # Nút
        self.btn_restart.draw(surface)
        self.btn_new_game.draw(surface)


# ─── GameScreen ───────────────────────────────────────────────────────────────

class GameScreen:
    """Màn hình ván cờ: board + token + turn indicator + scoreboard + setting."""

    CELL   = 40
    OFFSET = (40, 50)

    def __init__(self, screen_w, screen_h, mode, scores=None):
        """
        mode   : 'ai' | 'human'
        scores : [score_X, score_O] kế thừa từ ván trước (None → [0,0])
        """
        self.mode    = mode
        self.sw      = screen_w
        self.sh      = screen_h
        self.setting  = SettingMenu(screen_w, screen_h)
        self.win_screen = WinScreen(screen_w, screen_h)
        self._reset_board()

        # ── Assets ──
        board_px        = BOARD_SIZE * self.CELL
        self.board_img  = load_img("board.png",  (board_px, board_px))
        self.token_x    = load_img("token_x.png", (self.CELL - 4, self.CELL - 4))
        self.token_o    = load_img("token_o.png", (self.CELL - 4, self.CELL - 4))
        self.turn_x_img = load_img("turn_X.png",  (220, 55))
        self.turn_o_img = load_img("turn_o.png",  (220, 55))

        # Panel bên phải
        btn_cx       = self.OFFSET[0] + board_px + 90   # center-x của các nút

        self.btn_setting = ImageButton("button_setting.png", (btn_cx, 55),  (210, 58))
        self.btn_undo    = ImageButton("button_undo.png",    (btn_cx, 130), (210, 58))

        # ScoreBoard – đặt ở dưới nút undo, trong panel bên phải
        panel_x      = self.OFFSET[0] + board_px + 10
        panel_w      = screen_w - panel_x - 10
        score_x      = panel_x + (panel_w - ScoreBoard.IMG_SIZE[0]) // 2
        score_y      = 200      # vị trí top của bảng điểm

        self.scoreboard = ScoreBoard(mode, (score_x, score_y))
        if scores:
            self.scoreboard.score = list(scores)

        self._font_win  = pygame.font.SysFont("segoeuibold", 42, bold=True)
        self._font_mode = pygame.font.SysFont("segoeuibold", 18)

    # ── Board helpers ──────────────────────────────────────────────────────────

    def _reset_board(self):
        self.board        = [[0] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.current      = PLAYER_X
        self.winner       = None
        self.move_history = []
        self.game_over    = False

    def restart(self):
        """Chơi lại ván mới, giữ điểm."""
        self._reset_board()
        self.setting.close()

    def get_scores(self):
        return list(self.scoreboard.score)

    # ── Event / logic ──────────────────────────────────────────────────────────

    def _cell_at(self, pos):
        ox, oy   = self.OFFSET
        bx, by   = pos[0] - ox, pos[1] - oy
        board_px = BOARD_SIZE * self.CELL
        if 0 <= bx < board_px and 0 <= by < board_px:
            return by // self.CELL, bx // self.CELL
        return None

    def _check_winner(self, row, col, player):
        for dr, dc in [(0, 1), (1, 0), (1, 1), (1, -1)]:
            count = 1
            for sign in (1, -1):
                r, c = row + dr * sign, col + dc * sign
                while (0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE
                       and self.board[r][c] == player):
                    count += 1
                    r += dr * sign
                    c += dc * sign
            if count >= 5:
                return True
        return False

    def _undo(self):
        if self.game_over or not self.move_history:
            return
        row, col, player     = self.move_history.pop()
        self.board[row][col] = 0
        self.current         = player

    def handle_event(self, event):
        """
        Trả về:
          'new_game'  → Về màn chính (reset điểm)
          None        → tiếp tục game
        """
        # Win screen ưu tiên cao nhất khi đang hiện
        if self.win_screen.visible:
            action = self.win_screen.handle_event(event)
            if action == "restart":
                self.restart()
                self.win_screen.hide()
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
            self.scoreboard.add_win(winner)
            self.setting.close()
            self.win_screen.show(winner)
            return None

        # Nút setting / undo (chỉ khi chưa game over)
        if not self.game_over:
            if self.btn_setting.is_clicked(event):
                self.setting.toggle();  return None
            if self.btn_undo.is_clicked(event):
                self._undo();           return None

        # Click bàn cờ
        if not self.setting.visible and not self.game_over:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                cell = self._cell_at(event.pos)
                if cell:
                    row, col = cell
                    if self.board[row][col] == 0:
                        self.board[row][col] = self.current
                        self.move_history.append((row, col, self.current))
                        if self._check_winner(row, col, self.current):
                            self.winner    = self.current
                            self.game_over = True
                            self.scoreboard.add_win(self.current)
                            self.win_screen.show(self.current)
                        else:
                            self.current = (PLAYER_O if self.current == PLAYER_X
                                            else PLAYER_X)
        return None

    # ── Update / Draw ──────────────────────────────────────────────────────────

    def update(self, mouse_pos, mouse_buttons):
        self.win_screen.update(mouse_pos, mouse_buttons)
        if not self.win_screen.visible:
            self.btn_setting.update(mouse_pos, mouse_buttons)
            self.btn_undo.update(mouse_pos, mouse_buttons)
            self.setting.update(mouse_pos, mouse_buttons)

    def draw(self, surface):
        surface.fill((210, 180, 130))

        # Bàn cờ
        surface.blit(self.board_img, self.OFFSET)

        # Quân cờ
        ox, oy = self.OFFSET
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                p = self.board[r][c]
                if p in (PLAYER_X, PLAYER_O):
                    img = self.token_x if p == PLAYER_X else self.token_o
                    surface.blit(img, (ox + c * self.CELL + 2,
                                       oy + r * self.CELL + 2))

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

        # Bảng điểm
        self.scoreboard.draw(surface)

        # Turn indicator (dưới bảng điểm)
        turn_img  = self.turn_x_img if self.current == PLAYER_X else self.turn_o_img
        turn_top  = (self.scoreboard.rect.bottom + 12)
        turn_rect = turn_img.get_rect(centerx=panel_x + panel_w // 2,
                                      top=turn_top)
        surface.blit(turn_img, turn_rect)

        # Mode label
        mode_text = "VS MÁY" if self.mode == "ai" else "VS NGƯỜI"
        ms = self._font_mode.render(mode_text, True, (60, 30, 10))
        surface.blit(ms, (panel_x + 10, self.sh - 36))

        # Setting menu
        if not self.win_screen.visible:
            self.setting.draw(surface)

        # Win screen (luôn trên cùng)
        self.win_screen.draw(surface)




# ─── MainMenu ─────────────────────────────────────────────────────────────────

class MainMenu:
    """Màn hình chính: background + 2 nút chọn chế độ chơi."""

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
        if self.btn_ai.is_clicked(event):    return "ai"
        if self.btn_human.is_clicked(event): return "human"
        return None

    def update(self, mouse_pos, mouse_buttons):
        self.btn_ai.update(mouse_pos, mouse_buttons)
        self.btn_human.update(mouse_pos, mouse_buttons)

    def draw(self, surface):
        surface.blit(self.bg, (0, 0))
        self.btn_ai.draw(surface)
        self.btn_human.draw(surface)


# ─── CaroGUI ──────────────────────────────────────────────────────────────────

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

    # ── Chuyển màn hình ──────────────────────────────────────────────────────

    def _start_game(self, mode, keep_scores=None):
        """
        Tạo GameScreen mới.
        keep_scores: [score_X, score_O] nếu muốn giữ điểm (Restart),
                     None để bắt đầu từ 0 (New Game).
        """
        self.game  = GameScreen(SCREEN_W, SCREEN_H, mode, scores=keep_scores)
        self.state = STATE_GAME

    def _go_main_menu(self):
        """Về màn chính → reset điểm."""
        self.game  = None
        self.state = STATE_MAIN_MENU

    # ── Vòng lặp chính ───────────────────────────────────────────────────────

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
                    if action in ("ai", "human"):
                        self._start_game(action)   # điểm = 0,0

                elif self.state == STATE_GAME:
                    action = self.game.handle_event(event)
                    if action == "new_game":
                        self._go_main_menu()       # reset điểm

            # Cập nhật
            if self.state == STATE_MAIN_MENU:
                self.menu.update(mouse_pos, mouse_buttons)
            elif self.state == STATE_GAME:
                self.game.update(mouse_pos, mouse_buttons)

            # Vẽ
            if self.state == STATE_MAIN_MENU:
                self.menu.draw(self.screen)
            elif self.state == STATE_GAME:
                self.game.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()
import pygame
import threading
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gui.button import Button
from source.utils import log_benchmark_step

# ──────────────────────────────────────────
# Màu sắc
# ──────────────────────────────────────────
BG_COLOR      = (28, 28, 35)
BOARD_BG      = (45, 45, 55)
GRID_COLOR    = (90, 90, 110)
X_COLOR       = (220, 80,  80)
O_COLOR       = (70, 160, 220)
LAST_RING     = (255, 220,  60)
PANEL_BG      = (38, 38, 50)
TEXT_COLOR    = (225, 225, 225)
DIM_COLOR     = (130, 130, 150)

# ──────────────────────────────────────────
# Layout
# ──────────────────────────────────────────
CELL        = 55          # pixels per cell
BOARD_N     = 9           # số ô mỗi chiều
BOARD_PX    = CELL * BOARD_N   # 495
BX          = 25          # board left margin
BY          = 30          # board top margin
PX          = BX + BOARD_PX + 18   # panel left edge  (= 538)
PW          = 244         # panel width
WIN_W       = PX + PW + 8         # ≈ 790 → pad to 800
WIN_H       = BY + BOARD_PX + BY  # = 555 → pad to 580

# Custom pygame event khi AI hoàn thành
AI_DONE = pygame.USEREVENT + 1


class CaroGUI:
    def __init__(self, board, ai):
        pygame.init()
        self.board = board
        self.ai    = ai

        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("Caro AI")
        self.clock = pygame.time.Clock()

        # Trạng thái game
        self.ai_thinking = False
        self.game_over   = False
        self.winner      = 0          # 1=X thắng, 2=O thắng, -1=hòa
        self.ai_mode     = "alpha_beta"
        self.ai_info     = None       # dict chứa thông số nước AI vừa đi

        # Logging
        self.turn_count = 0
        self.log_file = f"logs/game_gui_{int(time.time())}.csv"

        # Fonts
        self.f_title = pygame.font.SysFont("Arial", 20, bold=True)
        self.f_body  = pygame.font.SysFont("Arial", 16)
        self.f_small = pygame.font.SysFont("Arial", 13)
        self.f_big   = pygame.font.SysFont("Arial", 40, bold=True)

        # ── Buttons thuật toán ──
        self.btn_ab = Button(PX,      120, 112, 32, "Alpha-Beta", active=True)
        self.btn_mm = Button(PX + 118, 120, 112, 32, "Minimax",    active=False)

        # ── Buttons độ sâu (1, 2, 3) ──
        self.btn_depth = [
            Button(PX + i * 76, 200, 66, 32, f"Sâu {i+1}", active=(i == 2))
            for i in range(3)
        ]
        self.ai.depth = 3   # mặc định

        # ── Button chơi lại ──
        self.btn_new = Button(PX, WIN_H - 54, 230, 38, "Chơi lại", active=False)

    # ──────────────────────────────────────
    # Vòng lặp chính
    # ──────────────────────────────────────
    def run(self):
        while True:
            self.clock.tick(30)
            
            # Tự động kích hoạt AI nếu đến lượt và chưa đang nghĩ
            if not self.game_over and not self.ai_thinking and self.board.current_player == self.ai.player_id:
                self._start_ai()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self._handle(event)

            self._draw()
            pygame.display.flip()

    # ──────────────────────────────────────
    # Xử lý sự kiện
    # ──────────────────────────────────────
    def _handle(self, event):
        # ── Kết quả AI từ thread ──
        if event.type == AI_DONE:
            self.ai_thinking = False
            move = event.dict.get("move")
            self.ai_info = event.dict
            if move:
                self.board.make_move(*move)
                self.turn_count += 1
                log_benchmark_step(self.log_file, [
                    self.turn_count, 
                    event.dict.get("algo"), 
                    event.dict.get("depth"), 
                    event.dict.get("nodes"), 
                    f"{event.dict.get('duration'):.4f}", 
                    event.dict.get("score"), 
                    move
                ])
                result = self.board.check_win()
                if result != 0:
                    self.game_over = True
                    self.winner = result
            return

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        pos = event.pos

        # ── Nút chơi lại ──
        if self.btn_new.is_clicked(pos):
            self._reset()
            return

        # ── Nút thuật toán ──
        if self.btn_ab.is_clicked(pos):
            self.ai_mode = "alpha_beta"
            self.btn_ab.active, self.btn_mm.active = True, False
            return
        if self.btn_mm.is_clicked(pos):
            self.ai_mode = "minimax"
            self.btn_ab.active, self.btn_mm.active = False, True
            return

        # ── Nút độ sâu ──
        for i, btn in enumerate(self.btn_depth):
            if btn.is_clicked(pos):
                for b in self.btn_depth:
                    b.active = False
                btn.active = True
                self.ai.depth = i + 1
                return

        # ── Click lên bàn cờ (lượt người) ──
        if self.game_over or self.ai_thinking:
            return
        human_id = 3 - self.ai.player_id
        if self.board.current_player != human_id:
            return

        col = (pos[0] - BX) // CELL
        row = (pos[1] - BY) // CELL
        if not (0 <= row < BOARD_N and 0 <= col < BOARD_N):
            return

        if self.board.make_move(row, col):
            self.turn_count += 1
            log_benchmark_step(self.log_file, [self.turn_count, "Human", "-", "-", "-", "-", (row, col)])
            result = self.board.check_win()
            if result != 0:
                self.game_over = True
                self.winner = result
            # AI sẽ tự động được kích hoạt bởi vòng lặp run()

    # ──────────────────────────────────────
    # Chạy AI trong thread riêng
    # ──────────────────────────────────────
    def _start_ai(self):
        self.ai_thinking = True
        board_copy = self.board.copy()
        mode = self.ai_mode

        def task():
            move, score, nodes, duration = self.ai.get_move(
                board_copy, mode=mode, time_limit=5.0
            )
            pygame.event.post(pygame.event.Event(AI_DONE, {
                "move": move, "score": score,
                "nodes": nodes, "duration": duration,
                "algo": mode, "depth": self.ai.depth,
            }))

        threading.Thread(target=task, daemon=True).start()

    # ──────────────────────────────────────
    # Reset ván mới
    # ──────────────────────────────────────
    def _reset(self):
        self.board.__init__(self.board.size, self.board.win_condition)
        self.game_over   = False
        self.winner      = 0
        self.ai_thinking = False
        self.ai_info     = None
        self.turn_count  = 0
        self.log_file    = f"logs/game_gui_{int(time.time())}.csv"

    # ──────────────────────────────────────
    # Vẽ toàn màn hình
    # ──────────────────────────────────────
    def _draw(self):
        self.screen.fill(BG_COLOR)
        self._draw_board()
        self._draw_panel()
        if self.game_over:
            self._draw_overlay()

    # ── Bàn cờ ──
    def _draw_board(self):
        # Nền bàn cờ
        pygame.draw.rect(
            self.screen, BOARD_BG,
            (BX - 4, BY - 4, BOARD_PX + 8, BOARD_PX + 8),
            border_radius=6,
        )
        # Lưới
        for i in range(BOARD_N + 1):
            x = BX + i * CELL
            y = BY + i * CELL
            pygame.draw.line(self.screen, GRID_COLOR, (x, BY), (x, BY + BOARD_PX))
            pygame.draw.line(self.screen, GRID_COLOR, (BX, y), (BX + BOARD_PX, y))

        # Quân cờ
        for r in range(BOARD_N):
            for c in range(BOARD_N):
                v = self.board.grid[r, c]
                if v == 0:
                    continue
                cx = BX + c * CELL + CELL // 2
                cy = BY + r * CELL + CELL // 2
                color = X_COLOR if v == 1 else O_COLOR
                pygame.draw.circle(self.screen, color, (cx, cy), CELL // 2 - 5)
                sym = self.f_body.render("X" if v == 1 else "O", True, (255, 255, 255))
                self.screen.blit(sym, sym.get_rect(center=(cx, cy)))

        # Highlight nước cuối
        if self.board.history:
            lr, lc = self.board.history[-1]
            cx = BX + lc * CELL + CELL // 2
            cy = BY + lr * CELL + CELL // 2
            pygame.draw.circle(self.screen, LAST_RING, (cx, cy), CELL // 2 - 5, 3)

    # ── Panel phải ──
    def _draw_panel(self):
        pygame.draw.rect(
            self.screen, PANEL_BG,
            (PX - 6, 8, PW + 10, WIN_H - 16),
            border_radius=8,
        )

        y = 18
        human_id = 3 - self.ai.player_id
        ai_color = X_COLOR if self.ai.player_id == 1 else O_COLOR

        # Tiêu đề lượt
        if self.game_over:
            turn_txt, turn_col = "Ván kết thúc", TEXT_COLOR
        elif self.ai_thinking:
            turn_txt, turn_col = "AI đang suy nghĩ…", ai_color
        elif self.board.current_player == human_id:
            sym = "X" if human_id == 1 else "O"
            turn_txt, turn_col = f"Lượt của bạn  ({sym})", (X_COLOR if human_id == 1 else O_COLOR)
        else:
            sym = "X" if self.ai.player_id == 1 else "O"
            turn_txt, turn_col = f"Lượt AI  ({sym})", ai_color

        self.screen.blit(self.f_title.render(turn_txt, True, turn_col), (PX, y))

        # ── Số quân ──
        y = 55
        x_cnt = sum(1 for r in range(BOARD_N) for c in range(BOARD_N) if self.board.grid[r, c] == 1)
        o_cnt = sum(1 for r in range(BOARD_N) for c in range(BOARD_N) if self.board.grid[r, c] == 2)
        self.screen.blit(self.f_small.render(f"X: {x_cnt} quân    O: {o_cnt} quân", True, DIM_COLOR), (PX, y))

        # ── Label thuật toán ──
        y = 95
        self.screen.blit(self.f_body.render("Thuật toán:", True, TEXT_COLOR), (PX, y))
        self.btn_ab.draw(self.screen)
        self.btn_mm.draw(self.screen)

        # ── Label độ sâu ──
        y = 173
        self.screen.blit(self.f_body.render("Độ sâu:", True, TEXT_COLOR), (PX, y))
        for btn in self.btn_depth:
            btn.draw(self.screen)

        # ── Thông tin nước AI ──
        y = 250
        self.screen.blit(self.f_body.render("Nước AI vừa đi:", True, TEXT_COLOR), (PX, y))
        y += 24
        if self.ai_info:
            rows = [
                ("Nước đi",  str(self.ai_info.get("move"))),
                ("Algo",     self.ai_info.get("algo", "")),
                ("Độ sâu",   str(self.ai_info.get("depth", ""))),
                ("Nodes",    f"{self.ai_info.get('nodes', 0):,}"),
                ("Thời gian",f"{self.ai_info.get('duration', 0):.3f} s"),
                ("Score",    str(self.ai_info.get("score", ""))),
            ]
            for label, val in rows:
                line = f"{label}: {val}"
                self.screen.blit(self.f_small.render(line, True, (170, 210, 170)), (PX, y))
                y += 20
        else:
            self.screen.blit(
                self.f_small.render("Chưa có thông tin", True, DIM_COLOR), (PX, y)
            )

        # ── Hướng dẫn ──
        y = WIN_H - 100
        tips = ["Click ô để đi", "U: không có", "'Chơi lại' để reset"]
        for tip in tips:
            self.screen.blit(self.f_small.render(tip, True, DIM_COLOR), (PX, y))
            y += 17

        self.btn_new.draw(self.screen)

    # ── Overlay kết thúc ──
    def _draw_overlay(self):
        overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 155))
        self.screen.blit(overlay, (0, 0))

        if self.winner == 1:
            msg, col = "Bạn thắng! 🏆", X_COLOR
        elif self.winner == 2:
            msg, col = "AI thắng! 💻", O_COLOR
        else:
            msg, col = "Hòa! 🤝", TEXT_COLOR

        board_cx = BX + BOARD_PX // 2
        board_cy = BY + BOARD_PX // 2

        surf = self.f_big.render(msg, True, col)
        self.screen.blit(surf, surf.get_rect(center=(board_cx, board_cy - 20)))

        sub = self.f_body.render("Nhấn 'Chơi lại' ở bên phải để tiếp tục", True, (200, 200, 200))
        self.screen.blit(sub, sub.get_rect(center=(board_cx, board_cy + 30)))
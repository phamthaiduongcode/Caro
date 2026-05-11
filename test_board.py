from source.board import Board, PLAYER, AI

board = Board()
current_player = PLAYER  # X đi trước

while True:
    board.display()
    print(f"Lượt của: {current_player}")

    try:
        row = int(input("Nhập hàng (0-9): "))
        col = int(input("Nhập cột (0-9): "))
    except ValueError:
        print("Lỗi: Vui lòng nhập số nguyên!")
        continue

    if not board.is_valid_move(row, col):
        print("Lỗi: Ô không hợp lệ hoặc đã có quân, thử lại!")
        continue

    board.make_move(row, col, current_player)

    result = board.is_terminal()
    if result == PLAYER:
        board.display()
        print("X thắng!")
        break
    elif result == AI:
        board.display()
        print("O thắng!")
        break
    elif result == 'draw':
        board.display()
        print("Hòa!")
        break

    # Đổi lượt
    current_player = AI if current_player == PLAYER else PLAYER
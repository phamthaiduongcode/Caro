from source.board import Board, PLAYER, AI

board = Board()
current_player = PLAYER  # X đi trước

while True:
    board.display()
    print(f"Lượt của: {current_player}")

    try:
        row = int(input("Nhập hàng (0-8): "))
        col = int(input("Nhập cột (0-8): "))
    except ValueError:
        print("Nhập số nguyên!")
        continue

    if not board.is_valid_move(row, col):
        print("Ô không hợp lệ, thử lại!")
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
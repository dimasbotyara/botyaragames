"""Connect Four AI — Minimax with alpha-beta pruning and smart heuristics."""

import random
import math

ROWS = 6
COLS = 7


def get_valid_columns(board):
    """Get list of columns that aren't full."""
    return [c for c in range(COLS) if board[0][c] == 0]


def drop_piece(board, col, player):
    """Drop a piece into column. Returns row where it landed, or -1."""
    for row in range(ROWS - 1, -1, -1):
        if board[row][col] == 0:
            board[row][col] = player
            return row
    return -1


def undo_drop(board, col):
    """Remove top piece from column."""
    for row in range(ROWS):
        if board[row][col] != 0:
            board[row][col] = 0
            return
    return


def check_winner(board):
    """Check for a winner. Returns 1, 2, or 0."""
    # Horizontal
    for r in range(ROWS):
        for c in range(COLS - 3):
            if board[r][c] != 0:
                if (board[r][c] == board[r][c+1] == board[r][c+2] == board[r][c+3]):
                    return board[r][c]
    # Vertical
    for r in range(ROWS - 3):
        for c in range(COLS):
            if board[r][c] != 0:
                if (board[r][c] == board[r+1][c] == board[r+2][c] == board[r+3][c]):
                    return board[r][c]
    # Diagonal /
    for r in range(3, ROWS):
        for c in range(COLS - 3):
            if board[r][c] != 0:
                if (board[r][c] == board[r-1][c+1] == board[r-2][c+2] == board[r-3][c+3]):
                    return board[r][c]
    # Diagonal \
    for r in range(ROWS - 3):
        for c in range(COLS - 3):
            if board[r][c] != 0:
                if (board[r][c] == board[r+1][c+1] == board[r+2][c+2] == board[r+3][c+3]):
                    return board[r][c]
    return 0


def get_winning_cells(board):
    """Get the 4 cells that form a winning line."""
    # Horizontal
    for r in range(ROWS):
        for c in range(COLS - 3):
            if board[r][c] != 0:
                if board[r][c] == board[r][c+1] == board[r][c+2] == board[r][c+3]:
                    return [(r, c), (r, c+1), (r, c+2), (r, c+3)]
    # Vertical
    for r in range(ROWS - 3):
        for c in range(COLS):
            if board[r][c] != 0:
                if board[r][c] == board[r+1][c] == board[r+2][c] == board[r+3][c]:
                    return [(r, c), (r+1, c), (r+2, c), (r+3, c)]
    # Diagonal /
    for r in range(3, ROWS):
        for c in range(COLS - 3):
            if board[r][c] != 0:
                if board[r][c] == board[r-1][c+1] == board[r-2][c+2] == board[r-3][c+3]:
                    return [(r, c), (r-1, c+1), (r-2, c+2), (r-3, c+3)]
    # Diagonal \
    for r in range(ROWS - 3):
        for c in range(COLS - 3):
            if board[r][c] != 0:
                if board[r][c] == board[r+1][c+1] == board[r+2][c+2] == board[r+3][c+3]:
                    return [(r, c), (r+1, c+1), (r+2, c+2), (r+3, c+3)]
    return None


def is_full(board):
    """Check if board is completely full."""
    return all(board[0][c] != 0 for c in range(COLS))


def _evaluate_window(window, player):
    """Evaluate a window of 4 cells for scoring."""
    opponent = 3 - player
    score = 0

    player_count = window.count(player)
    opponent_count = window.count(opponent)
    empty_count = window.count(0)

    if player_count == 4:
        score += 100000
    elif player_count == 3 and empty_count == 1:
        score += 50
    elif player_count == 2 and empty_count == 2:
        score += 10

    if opponent_count == 3 and empty_count == 1:
        score -= 80  # Block opponent!
    elif opponent_count == 2 and empty_count == 2:
        score -= 8

    return score


def _score_position(board, player):
    """Score the entire board position for a player."""
    score = 0

    # Center column preference
    center_col = COLS // 2
    center_count = sum(1 for r in range(ROWS) if board[r][center_col] == player)
    score += center_count * 6

    # Horizontal
    for r in range(ROWS):
        for c in range(COLS - 3):
            window = [board[r][c+i] for i in range(4)]
            score += _evaluate_window(window, player)

    # Vertical
    for r in range(ROWS - 3):
        for c in range(COLS):
            window = [board[r+i][c] for i in range(4)]
            score += _evaluate_window(window, player)

    # Diagonal /
    for r in range(3, ROWS):
        for c in range(COLS - 3):
            window = [board[r-i][c+i] for i in range(4)]
            score += _evaluate_window(window, player)

    # Diagonal \
    for r in range(ROWS - 3):
        for c in range(COLS - 3):
            window = [board[r+i][c+i] for i in range(4)]
            score += _evaluate_window(window, player)

    return score


def _minimax(board, depth, alpha, beta, is_maximizing, bot_player):
    """Minimax with alpha-beta pruning."""
    winner = check_winner(board)
    if winner == bot_player:
        return None, 100000 + depth
    elif winner == (3 - bot_player):
        return None, -100000 - depth
    elif is_full(board) or depth == 0:
        return None, _score_position(board, bot_player)

    valid_cols = get_valid_columns(board)
    # Order: center first for better pruning
    valid_cols.sort(key=lambda c: abs(c - COLS // 2))

    if is_maximizing:
        best_score = -math.inf
        best_col = random.choice(valid_cols)
        for col in valid_cols:
            row = drop_piece(board, col, bot_player)
            if row < 0:
                continue
            _, score = _minimax(board, depth - 1, alpha, beta, False, bot_player)
            undo_drop(board, col)
            if score > best_score:
                best_score = score
                best_col = col
            alpha = max(alpha, score)
            if alpha >= beta:
                break
        return best_col, best_score
    else:
        opponent = 3 - bot_player
        best_score = math.inf
        best_col = random.choice(valid_cols)
        for col in valid_cols:
            row = drop_piece(board, col, opponent)
            if row < 0:
                continue
            _, score = _minimax(board, depth - 1, alpha, beta, True, bot_player)
            undo_drop(board, col)
            if score < best_score:
                best_score = score
                best_col = col
            beta = min(beta, score)
            if alpha >= beta:
                break
        return best_col, best_score


def get_bot_move(board, bot_player=2, difficulty="medium"):
    """Get the best move for the bot.

    Args:
        board: 6x7 grid (0=empty, 1=player1, 2=player2)
        bot_player: which player the bot is (1 or 2)
        difficulty: easy/medium/hard
    """
    valid_cols = get_valid_columns(board)
    if not valid_cols:
        return None

    # Check for immediate win
    for col in valid_cols:
        row = drop_piece(board, col, bot_player)
        if row >= 0 and check_winner(board) == bot_player:
            undo_drop(board, col)
            return col
        undo_drop(board, col)

    # Check for immediate block
    opponent = 3 - bot_player
    for col in valid_cols:
        row = drop_piece(board, col, opponent)
        if row >= 0 and check_winner(board) == opponent:
            undo_drop(board, col)
            return col
        undo_drop(board, col)

    depth_map = {"easy": 2, "medium": 5, "hard": 8}
    depth = depth_map.get(difficulty, 5)

    # Easy mode: sometimes make random moves
    if difficulty == "easy" and random.random() < 0.3:
        return random.choice(valid_cols)

    # Medium mode: occasional random
    if difficulty == "medium" and random.random() < 0.1:
        return random.choice(valid_cols)

    # Deep copy board
    board_copy = [row[:] for row in board]
    col, _ = _minimax(board_copy, depth, -math.inf, math.inf, True, bot_player)
    return col

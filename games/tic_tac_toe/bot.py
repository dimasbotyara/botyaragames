"""Tic Tac Toe AI - Minimax with alpha-beta pruning."""

import random


def get_bot_move(board, bot_symbol="O"):
    """Get the best move for the bot using minimax."""
    human = "X" if bot_symbol == "O" else "O"

    def minimax(b, depth, is_maximizing, alpha, beta):
        winner = check_winner(b)
        if winner == bot_symbol:
            return 10 - depth
        if winner == human:
            return depth - 10
        if is_full(b):
            return 0

        if is_maximizing:
            max_eval = -float("inf")
            for i in range(9):
                if b[i] is None:
                    b[i] = bot_symbol
                    eval_score = minimax(b, depth + 1, False, alpha, beta)
                    b[i] = None
                    max_eval = max(max_eval, eval_score)
                    alpha = max(alpha, eval_score)
                    if beta <= alpha:
                        break
            return max_eval
        else:
            min_eval = float("inf")
            for i in range(9):
                if b[i] is None:
                    b[i] = human
                    eval_score = minimax(b, depth + 1, True, alpha, beta)
                    b[i] = None
                    min_eval = min(min_eval, eval_score)
                    beta = min(beta, eval_score)
                    if beta <= alpha:
                        break
            return min_eval

    best_score = -float("inf")
    best_moves = []

    for i in range(9):
        if board[i] is None:
            board[i] = bot_symbol
            score = minimax(board, 0, False, -float("inf"), float("inf"))
            board[i] = None
            if score > best_score:
                best_score = score
                best_moves = [i]
            elif score == best_score:
                best_moves.append(i)

    return random.choice(best_moves) if best_moves else None


def check_winner(board):
    """Check if there's a winner. Returns 'X', 'O', or None."""
    lines = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),  # rows
        (0, 3, 6), (1, 4, 7), (2, 5, 8),  # cols
        (0, 4, 8), (2, 4, 6),              # diags
    ]
    for a, b, c in lines:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return None


def get_winning_line(board):
    """Get the winning line indices."""
    lines = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),
        (0, 3, 6), (1, 4, 7), (2, 5, 8),
        (0, 4, 8), (2, 4, 6),
    ]
    for a, b, c in lines:
        if board[a] and board[a] == board[b] == board[c]:
            return (a, b, c)
    return None


def is_full(board):
    """Check if board is full."""
    return all(cell is not None for cell in board)
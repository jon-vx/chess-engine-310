# engine.py

import chess  
import math   

PIECE_VALUES = {
    chess.PAWN:   100,    # we use centipawns (1 pawn = 100) so we can stay in
    chess.KNIGHT: 320,    # integer math and still express small differences
    chess.BISHOP: 330,    # like "bishop is slightly better than knight" (330
    chess.ROOK:   500,    # vs 320). Centipawns are the standard unit in
    chess.QUEEN:  900,    # computer chess.
    chess.KING:   20000,  # huge — but checkmate is handled separately below
}

def evaluate(board: chess.Board) -> int:
    """
    Return a score for the current position, in centipawns, from white's POV.

    Positive number -> white is doing better.
    Negative number -> black is doing better.
    """

    # - inf means white lost and inf means black lost
    if board.is_checkmate():
        return -math.inf if board.turn == chess.WHITE else math.inf

    # draw check
    if board.is_stalemate() or board.is_insufficient_material() or board.is_seventyfive_moves() or board.is_fivefold_repetition():
        return 0

    score = 0
    for square in chess.SQUARES:        
        piece = board.piece_at(square)     
        if piece is None:
            continue                       

        value = PIECE_VALUES[piece.piece_type]

        # Add for white, subtract for black.
        if piece.color == chess.WHITE:
            score += value
        else:
            score -= value

    return score

def minimax(board: chess.Board, depth: int, alpha: float, beta: float,
            maximizing: bool) -> float:

    if depth == 0 or board.is_game_over():
        return evaluate(board)

    if maximizing:
        max_eval = -math.inf

        for move in board.legal_moves:
            board.push(move)              
            eval_score = minimax(board, depth - 1, alpha, beta, False)
            board.pop()

            max_eval = max(max_eval, eval_score)

            alpha = max(alpha, eval_score)

            if beta <= alpha:
                break

        return max_eval

    else:
        min_eval = math.inf

        for move in board.legal_moves:
            board.push(move)
            eval_score = minimax(board, depth - 1, alpha, beta, True)
            board.pop()

            min_eval = min(min_eval, eval_score)
            beta = min(beta, eval_score)

            if beta <= alpha:
                break

        return min_eval

def find_best_move(board: chess.Board, depth: int) -> chess.Move:
    """
    Search to `depth` plies and return the best move for the side to move.
    """

    is_white_turn = board.turn == chess.WHITE

    best_move = None
    best_score = -math.inf if is_white_turn else math.inf

    alpha = -math.inf
    beta = math.inf

    for move in board.legal_moves:
        board.push(move)
        score = minimax(board, depth - 1, alpha, beta, not is_white_turn)
        board.pop()

        if is_white_turn and score > best_score:
            best_score = score
            best_move = move
            alpha = max(alpha, score)
        elif (not is_white_turn) and score < best_score:
            best_score = score
            best_move = move
            beta = min(beta, score)

    return best_move

def play_against_engine(search_depth: int = 3) -> None:
    """Simple terminal game: human (white) vs engine (black)."""

    board = chess.Board()

    while not board.is_game_over():
        print(board)
        print()

        if board.turn == chess.WHITE:
            move_uci = input("Your move: ").strip()
            try:
                move = chess.Move.from_uci(move_uci)
            except ValueError:
                print("Couldn't parse UCI, try again.")
                continue
            if move not in board.legal_moves:
                print("Illegal move, try again.")
                continue
            board.push(move)
        else:
            print("Engine is thinking...")
            move = find_best_move(board, search_depth)
            print(f"Engine plays: {move.uci()}")
            board.push(move)

    print(board)
    print("Game over:", board.result())


if __name__ == "__main__":
    play_against_engine(search_depth=3)

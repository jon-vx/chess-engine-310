# engine.py

import chess
import math
import time


class SearchAborted(Exception):
    """Raised inside minimax when the search deadline has been reached."""
    pass

_TT_EXACT = 0   
_TT_LOWER = 1   
_TT_UPPER = 2   

_TT: dict = {}
_TT_MAX_SIZE = 500_000   

_MAX_PLY = 128
_KILLERS: list[list[chess.Move | None]] = [[None, None] for _ in range(_MAX_PLY)]

_HISTORY: dict[tuple[int, int], int] = {}


def clear_tt() -> None:
    """Drop all search state. Called between games via UCI 'ucinewgame'."""
    _TT.clear()
    for k in _KILLERS:
        k[0] = k[1] = None
    _HISTORY.clear()


def _store_killer(ply: int, move: chess.Move) -> None:
    if ply >= _MAX_PLY:
        return
    k = _KILLERS[ply]
    if k[0] != move:           
        k[1] = k[0]
        k[0] = move


def _bump_history(move: chess.Move, depth: int) -> None:
    key = (move.from_square, move.to_square)
    _HISTORY[key] = _HISTORY.get(key, 0) + depth * depth


def _tt_probe(key, depth: int, alpha: float, beta: float):
    entry = _TT.get(key)
    if entry is None:
        return None, None
    stored_depth, stored_score, stored_flag, stored_move = entry
    if stored_depth < depth:
        return None, stored_move
    if stored_flag == _TT_EXACT:
        return stored_score, stored_move
    if stored_flag == _TT_LOWER and stored_score >= beta:
        return stored_score, stored_move
    if stored_flag == _TT_UPPER and stored_score <= alpha:
        return stored_score, stored_move
    return None, stored_move


def _tt_store(key, depth: int, score: float, flag: int,
              best_move: chess.Move | None) -> None:
    if len(_TT) >= _TT_MAX_SIZE:
        _TT.clear()   
    _TT[key] = (depth, score, flag, best_move)

PIECE_VALUES = {
    chess.PAWN:   100,    
    chess.KNIGHT: 320,   
    chess.BISHOP: 330,    
    chess.ROOK:   500,    
    chess.QUEEN:  900,   
    chess.KING:   20000, 
}

# Piece-square tables

PAWN_PST = [
      0,   0,   0,   0,   0,   0,   0,   0,
      5,  10,  10, -20, -20,  10,  10,   5,
      5,  -5, -10,   0,   0, -10,  -5,   5,
      0,   0,   0,  20,  20,   0,   0,   0,
      5,   5,  10,  25,  25,  10,   5,   5,
     10,  10,  20,  30,  30,  20,  10,  10,
     50,  50,  50,  50,  50,  50,  50,  50,
      0,   0,   0,   0,   0,   0,   0,   0,
]

KNIGHT_PST = [
    -50, -40, -30, -30, -30, -30, -40, -50,
    -40, -20,   0,   5,   5,   0, -20, -40,
    -30,   5,  10,  15,  15,  10,   5, -30,
    -30,   0,  15,  20,  20,  15,   0, -30,
    -30,   5,  15,  20,  20,  15,   5, -30,
    -30,   0,  10,  15,  15,  10,   0, -30,
    -40, -20,   0,   0,   0,   0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50,
]

BISHOP_PST = [
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10,   5,   0,   0,   0,   0,   5, -10,
    -10,  10,  10,  10,  10,  10,  10, -10,
    -10,   0,  10,  10,  10,  10,   0, -10,
    -10,   5,   5,  10,  10,   5,   5, -10,
    -10,   0,   5,  10,  10,   5,   0, -10,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -20, -10, -10, -10, -10, -10, -10, -20,
]

ROOK_PST = [
      0,   0,   0,   5,   5,   0,   0,   0,
     -5,   0,   0,   0,   0,   0,   0,  -5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
      5,  10,  10,  10,  10,  10,  10,   5,
      0,   0,   0,   0,   0,   0,   0,   0,
]

QUEEN_PST = [
    -20, -10, -10,  -5,  -5, -10, -10, -20,
    -10,   0,   5,   0,   0,   0,   0, -10,
    -10,   5,   5,   5,   5,   5,   0, -10,
      0,   0,   5,   5,   5,   5,   0,  -5,
     -5,   0,   5,   5,   5,   5,   0,  -5,
    -10,   0,   5,   5,   5,   5,   0, -10,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -20, -10, -10,  -5,  -5, -10, -10, -20,
]

KING_MG_PST = [
     20,  30,  10,   0,   0,  10,  30,  20,
     20,  20,   0,   0,   0,   0,  20,  20,
    -10, -20, -20, -20, -20, -20, -20, -10,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
]

KING_EG_PST = [
    -50, -30, -30, -30, -30, -30, -30, -50,
    -30, -30,   0,   0,   0,   0, -30, -30,
    -30, -10,  20,  30,  30,  20, -10, -30,
    -30, -10,  30,  40,  40,  30, -10, -30,
    -30, -10,  30,  40,  40,  30, -10, -30,
    -30, -10,  20,  30,  30,  20, -10, -30,
    -30, -20, -10,   0,   0, -10, -20, -30,
    -50, -40, -30, -20, -20, -30, -40, -50,
]

PIECE_SQUARE_TABLES = {
    chess.PAWN:   PAWN_PST,
    chess.KNIGHT: KNIGHT_PST,
    chess.BISHOP: BISHOP_PST,
    chess.ROOK:   ROOK_PST,
    chess.QUEEN:  QUEEN_PST,
}

_PHASE_VALUES = {
    chess.KNIGHT: 1,
    chess.BISHOP: 1,
    chess.ROOK:   2,
    chess.QUEEN:  4,
}
_TOTAL_PHASE = 24    

def _phase(board: chess.Board) -> int:
    """Game-phase value in [0, 24]. 24 = full material, 0 = bare king+pawns."""
    p = (chess.popcount(board.knights) * _PHASE_VALUES[chess.KNIGHT]
         + chess.popcount(board.bishops) * _PHASE_VALUES[chess.BISHOP]
         + chess.popcount(board.rooks)   * _PHASE_VALUES[chess.ROOK]
         + chess.popcount(board.queens)  * _PHASE_VALUES[chess.QUEEN])
    return min(p, _TOTAL_PHASE)


def _mobility(board: chess.Board, color: bool) -> int:
    """Number of squares attacked by `color`'s minor and major pieces.
    Cheap proxy for activity / tempo."""
    occ = board.occupied_co[color]
    pieces = (board.knights | board.bishops | board.rooks | board.queens) & occ
    total = 0
    for sq in chess.scan_forward(pieces):
        total += chess.popcount(board.attacks_mask(sq))
    return total


def _king_attack_zone_danger(board: chess.Board, color: bool) -> int:
    """Number of squares adjacent to `color`'s king that the enemy attacks."""
    king_sq = board.king(color)
    if king_sq is None:
        return 0
    enemy = not color
    danger = 0
    for sq in chess.SquareSet(chess.BB_KING_ATTACKS[king_sq]):
        if board.is_attacked_by(enemy, sq):
            danger += 1
    return danger


def _bishop_pair_bonus(board: chess.Board, color: bool) -> int:
    bishops = board.bishops & board.occupied_co[color]
    return 30 if chess.popcount(bishops) >= 2 else 0


def _pawn_structure_score(board: chess.Board, color: bool) -> int:
    """Doubled pawns and isolated pawns. Negative is bad for `color`."""
    pawns = board.pawns & board.occupied_co[color]
    if not pawns:
        return 0

    file_counts = [0] * 8
    for sq in chess.scan_forward(pawns):
        file_counts[chess.square_file(sq)] += 1

    score = 0
    for f, count in enumerate(file_counts):
        if count == 0:
            continue
        if count > 1:
            score -= 10 * (count - 1)
        left  = file_counts[f - 1] if f > 0 else 0
        right = file_counts[f + 1] if f < 7 else 0
        if left == 0 and right == 0:
            score -= 15 * count
    return score


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

    phase = _phase(board)
    mg_w = phase
    eg_w = _TOTAL_PHASE - phase

    score = 0

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is None:
            continue

        material = PIECE_VALUES[piece.piece_type]
        sq_for_white = square if piece.color == chess.WHITE else chess.square_mirror(square)

        if piece.piece_type == chess.KING:
            pst_score = (KING_MG_PST[sq_for_white] * mg_w
                         + KING_EG_PST[sq_for_white] * eg_w) // _TOTAL_PHASE
        else:
            pst_score = PIECE_SQUARE_TABLES[piece.piece_type][sq_for_white]

        if piece.color == chess.WHITE:
            score += material + pst_score
        else:
            score -= material + pst_score

    score += (_mobility(board, chess.WHITE) - _mobility(board, chess.BLACK)) * 2

    safety_w = _king_attack_zone_danger(board, chess.WHITE)
    safety_b = _king_attack_zone_danger(board, chess.BLACK)
    safety_weight = (8 * mg_w) // _TOTAL_PHASE
    score -= (safety_w - safety_b) * safety_weight

    score += _bishop_pair_bonus(board, chess.WHITE) - _bishop_pair_bonus(board, chess.BLACK)

    score += _pawn_structure_score(board, chess.WHITE) - _pawn_structure_score(board, chess.BLACK)

    return score

def _is_noisy(board: chess.Board, move: chess.Move) -> bool:
    """A move that meaningfully changes material: captures and promotions."""
    return board.is_capture(move) or move.promotion is not None


def _move_score(board: chess.Board, move: chess.Move,
                hash_move: chess.Move | None = None,
                ply: int = 0) -> int:
    """
    Heuristic score used only for ordering the move list at a node. 
    """
    if hash_move is not None and move == hash_move:
        return 1_000_000

    if board.is_capture(move):
        if board.is_en_passant(move):
            victim_value = PIECE_VALUES[chess.PAWN]
        else:
            victim = board.piece_at(move.to_square)
            victim_value = PIECE_VALUES[victim.piece_type] if victim else 0
        attacker = board.piece_at(move.from_square)
        attacker_value = PIECE_VALUES[attacker.piece_type] if attacker else 0
        return 100_000 + victim_value * 10 - attacker_value

    if move.promotion is not None:
        return 90_000 + PIECE_VALUES[move.promotion]

    if 0 <= ply < _MAX_PLY:
        killers = _KILLERS[ply]
        if move == killers[0]:
            return 80_000
        if move == killers[1]:
            return 70_000

    return _HISTORY.get((move.from_square, move.to_square), 0)


def _ordered_moves(board: chess.Board,
                   hash_move: chess.Move | None = None,
                   ply: int = 0) -> list[chess.Move]:
    return sorted(board.legal_moves,
                  key=lambda m: -_move_score(board, m, hash_move, ply))


def _has_non_pawn_material(board: chess.Board, color: bool) -> bool:
    """True if `color` has at least one knight/bishop/rook/queen.
    Used as a zugzwang guard for null move pruning."""
    return bool(board.knights & board.occupied_co[color]
                or board.bishops & board.occupied_co[color]
                or board.rooks   & board.occupied_co[color]
                or board.queens  & board.occupied_co[color])


def quiescence(board: chess.Board, alpha: float, beta: float,
               maximizing: bool, deadline: float | None = None) -> float:
    if deadline is not None and time.monotonic() >= deadline:
        raise SearchAborted()

    if board.is_game_over():
        return evaluate(board)

    stand_pat = evaluate(board)

    if maximizing:
        if stand_pat >= beta:
            return stand_pat
        if stand_pat > alpha:
            alpha = stand_pat

        for move in _ordered_moves(board):
            if not _is_noisy(board, move):
                continue
            board.push(move)
            try:
                score = quiescence(board, alpha, beta, False, deadline)
            finally:
                board.pop()
            if score >= beta:
                return score
            if score > alpha:
                alpha = score
        return alpha

    else:
        if stand_pat <= alpha:
            return stand_pat
        if stand_pat < beta:
            beta = stand_pat

        for move in _ordered_moves(board):
            if not _is_noisy(board, move):
                continue
            board.push(move)
            try:
                score = quiescence(board, alpha, beta, True, deadline)
            finally:
                board.pop()
            if score <= alpha:
                return score
            if score < beta:
                beta = score
        return beta


_NULL_MOVE_R = 2          
_LMR_MIN_DEPTH = 3       
_LMR_FULL_MOVES = 4     


def minimax(board: chess.Board, depth: int, alpha: float, beta: float,
            maximizing: bool, deadline: float | None = None,
            ply: int = 0) -> float:

    if deadline is not None and time.monotonic() >= deadline:
        raise SearchAborted()

    if board.is_game_over():
        return evaluate(board)

    in_check = board.is_check()

    if in_check:
        depth += 1

    key = board._transposition_key()
    cached_score, hash_move = _tt_probe(key, depth, alpha, beta)
    if cached_score is not None:
        return cached_score

    if depth == 0:
        return quiescence(board, alpha, beta, maximizing, deadline)

    if (depth >= 3 and not in_check
            and _has_non_pawn_material(board, board.turn)):
        board.push(chess.Move.null())
        try:
            null_score = minimax(board, depth - 1 - _NULL_MOVE_R, alpha, beta,
                                 not maximizing, deadline, ply + 1)
        finally:
            board.pop()
        if maximizing and null_score >= beta:
            return null_score
        if (not maximizing) and null_score <= alpha:
            return null_score

    alpha_orig = alpha
    beta_orig = beta
    best_move: chess.Move | None = None
    moves = _ordered_moves(board, hash_move=hash_move, ply=ply)

    if maximizing:
        max_eval = -math.inf

        for i, move in enumerate(moves):
            is_quiet = not _is_noisy(board, move)

            board.push(move)
            try:
                gives_check = board.is_check()
                reduce = (i >= _LMR_FULL_MOVES and depth >= _LMR_MIN_DEPTH
                          and is_quiet and not gives_check)
                child_depth = depth - 1 - (1 if reduce else 0)

                eval_score = minimax(board, child_depth, alpha, beta,
                                     False, deadline, ply + 1)

                if reduce and eval_score > alpha:
                    eval_score = minimax(board, depth - 1, alpha, beta,
                                         False, deadline, ply + 1)
            finally:
                board.pop()

            if eval_score > max_eval:
                max_eval = eval_score
                best_move = move

            alpha = max(alpha, eval_score)

            if beta <= alpha:
                if is_quiet:
                    _store_killer(ply, move)
                    _bump_history(move, depth)
                break

        if max_eval >= beta_orig:
            flag = _TT_LOWER
        elif max_eval <= alpha_orig:
            flag = _TT_UPPER
        else:
            flag = _TT_EXACT
        _tt_store(key, depth, max_eval, flag, best_move)
        return max_eval

    else:
        min_eval = math.inf

        for i, move in enumerate(moves):
            is_quiet = not _is_noisy(board, move)

            board.push(move)
            try:
                gives_check = board.is_check()
                reduce = (i >= _LMR_FULL_MOVES and depth >= _LMR_MIN_DEPTH
                          and is_quiet and not gives_check)
                child_depth = depth - 1 - (1 if reduce else 0)

                eval_score = minimax(board, child_depth, alpha, beta,
                                     True, deadline, ply + 1)

                if reduce and eval_score < beta:
                    eval_score = minimax(board, depth - 1, alpha, beta,
                                         True, deadline, ply + 1)
            finally:
                board.pop()

            if eval_score < min_eval:
                min_eval = eval_score
                best_move = move

            beta = min(beta, eval_score)

            if beta <= alpha:
                if is_quiet:
                    _store_killer(ply, move)
                    _bump_history(move, depth)
                break

        if min_eval <= alpha_orig:
            flag = _TT_UPPER
        elif min_eval >= beta_orig:
            flag = _TT_LOWER
        else:
            flag = _TT_EXACT
        _tt_store(key, depth, min_eval, flag, best_move)
        return min_eval


def _root_search(board: chess.Board, depth: int,
                 deadline: float | None,
                 previous_best: chess.Move | None = None,
                 ) -> tuple[chess.Move | None, float]:
    """Search every root move to `depth` and return (best_move, best_score).

    `previous_best` (the deepest iteration's move from iterative deepening)
    is tried first so subsequent moves search against a tight alpha/beta.
    """

    is_white = board.turn == chess.WHITE
    best_move: chess.Move | None = None
    best_score = -math.inf if is_white else math.inf
    alpha = -math.inf
    beta = math.inf

    for move in _ordered_moves(board, hash_move=previous_best, ply=0):
        board.push(move)
        try:
            score = minimax(board, depth - 1, alpha, beta, not is_white,
                            deadline, ply=1)
        finally:
            board.pop()

        if is_white and score > best_score:
            best_score = score
            best_move = move
            alpha = max(alpha, score)
        elif (not is_white) and score < best_score:
            best_score = score
            best_move = move
            beta = min(beta, score)

    return best_move, best_score


def iterative_search(board: chess.Board,
                     time_budget_s: float | None = None,
                     max_depth: int = 64,
                     info_callback=None) -> tuple[chess.Move | None, float]:
    """
    Iterative deepening: search depth 1, 2, 3, ... until either max_depth
    is reached or the time budget is exhausted.
    """

    deadline = time.monotonic() + time_budget_s if time_budget_s else None

    fallback = next(iter(board.legal_moves), None)
    best_move: chess.Move | None = fallback
    best_score: float = 0.0

    for depth in range(1, max_depth + 1):
        d = None if depth == 1 else deadline
        try:
            move, score = _root_search(board, depth, d, previous_best=best_move)
        except SearchAborted:
            break

        if move is not None:
            best_move = move
            best_score = score
            if info_callback is not None:
                info_callback(depth, score, move)

        if score == math.inf or score == -math.inf:
            break

    return best_move, best_score

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

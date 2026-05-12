"""
UCI driver. Reads UCI commands on stdin, writes responses on stdout.

Run directly:    python uci.py
From lichess-bot: point `engine.dir` / `engine.name` at this script
                  (via a small shell wrapper that execs `python uci.py`).
"""

import math
import sys

import chess

from engine import iterative_search, clear_tt

ENGINE_NAME = "ChessEngine310"
ENGINE_AUTHOR = "jvx"


def send(line: str) -> None:
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def parse_position(tokens: list[str], board: chess.Board) -> None:
    if not tokens:
        return

    if tokens[0] == "startpos":
        board.reset()
        i = 1
    elif tokens[0] == "fen" and len(tokens) >= 7:
        board.set_fen(" ".join(tokens[1:7]))
        i = 7
    else:
        return

    if i < len(tokens) and tokens[i] == "moves":
        for uci in tokens[i + 1:]:
            try:
                board.push_uci(uci)
            except ValueError:
                break


def compute_budget(args: list[str], white_to_move: bool) -> tuple[float | None, int]:
    wtime = btime = winc = binc = movetime = depth = movestogo = None
    infinite = False

    i = 0
    while i < len(args):
        tok = args[i]
        if tok in ("wtime", "btime", "winc", "binc", "movetime", "depth", "movestogo"):
            if i + 1 >= len(args):
                break
            try:
                val = int(args[i + 1])
            except ValueError:
                val = 0
            if   tok == "wtime":     wtime = val
            elif tok == "btime":     btime = val
            elif tok == "winc":      winc = val
            elif tok == "binc":      binc = val
            elif tok == "movetime":  movetime = val
            elif tok == "depth":     depth = val
            elif tok == "movestogo": movestogo = val
            i += 2
            continue
        if tok == "infinite":
            infinite = True
        i += 1

    if depth is not None:
        return None, depth
    if movetime is not None:
        return movetime / 1000.0, 64
    if infinite:
        return None, 64

    my_time = wtime if white_to_move else btime
    my_inc = (winc if white_to_move else binc) or 0

    if my_time is None:
        return 1.0, 64

    moves_left = movestogo if movestogo and movestogo > 0 else 60

    if my_time < 10_000:
        budget_ms = my_time / 40
    elif my_time < 30_000:
        budget_ms = my_time / 30 + 0.5 * my_inc
    elif my_time < 60_000:
        budget_ms = my_time / 20 + 0.7 * my_inc
    else:
        budget_ms = my_time / moves_left + 0.85 * my_inc

    budget_ms = min(budget_ms, my_time * 0.25)
    budget_ms = max(50.0, budget_ms - 100.0)
    return budget_ms / 1000.0, 64


def emit_info(depth: int, score: float, move: chess.Move) -> None:
    if score == math.inf:
        score_str = "mate 1"
    elif score == -math.inf:
        score_str = "mate -1"
    else:
        score_str = f"cp {int(score)}"
    send(f"info depth {depth} score {score_str} pv {move.uci()}")


def main() -> None:
    board = chess.Board()

    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue

        if line == "uci":
            send(f"id name {ENGINE_NAME}")
            send(f"id author {ENGINE_AUTHOR}")
            send("uciok")
        elif line == "isready":
            send("readyok")
        elif line == "ucinewgame":
            board.reset()
            clear_tt()
        elif line.startswith("position"):
            parse_position(line.split()[1:], board)
        elif line.startswith("go"):
            args = line.split()[1:]
            time_budget, max_depth = compute_budget(args, board.turn == chess.WHITE)
            move, _ = iterative_search(
                board,
                time_budget_s=time_budget,
                max_depth=max_depth,
                info_callback=emit_info,
            )
            send(f"bestmove {move.uci() if move is not None else '0000'}")
        elif line == "quit":
            return


if __name__ == "__main__":
    main()

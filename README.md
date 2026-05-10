# chess-engine-310

A pure-Python chess engine + Lichess bot. Plays as
[`bigbotontheblock`](https://lichess.org/@/bigbotontheblock) on Lichess.

## Engine features

- Iterative-deepening alpha-beta with quiescence search
- MVV-LVA capture ordering, killer moves, history heuristic
- Transposition table, null-move pruning, late move reductions, check extensions
- Phase-blended piece-square tables, mobility, king safety, bishop pair,
  pawn structure (doubled, isolated)
- UCI time management (`wtime` / `btime` / `movetime` / `depth`)

## Layout

```
engine.py                       search + evaluation
uci.py                          UCI driver (stdin/stdout)
run-uci.sh                      wrapper that lichess-bot invokes
dashboard.py                    localhost stats dashboard
```


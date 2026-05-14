# chess-engine-310

A pure-Python chess engine + Lichess bot. Plays as
[`bigbotontheblock`](https://lichess.org/@/bigbotontheblock) on Lichess.

**Live stats:** https://bigbotontheblock.netlify.app

## Engine features

- Iterative-deepening alpha-beta with quiescence search
- MVV-LVA capture ordering, killer moves, history heuristic
- Transposition table, null-move pruning, late move reductions, check extensions
- Phase-blended piece-square tables, mobility, king safety, bishop pair,
  pawn structure (doubled, isolated)
- Repetition / fifty-move awareness
- Adaptive time management: tight per-move budget, instant forced moves,
  early-exit when the search has stabilized; honours UCI `wtime` / `btime` /
  `movetime` / `depth`
- Runs under PyPy for a large speedup over CPython

## Layout

```
engine.py                       search + evaluation
uci.py                          UCI driver (stdin/stdout)
run-uci.sh                      wrapper that lichess-bot invokes (PyPy venv)
dashboard.py                    live stats dashboard (self-contained HTTP server)
build-web.sh                    extracts dashboard HTML to web/ for Netlify
web/index.html                  deployed to Netlify
netlify.toml                    Netlify build + security headers
vps/setup.sh                    one-shot VPS bootstrap (user, PyPy, lichess-bot)
vps/lichess-bot.service         systemd unit for the bot daemon
vps/chess-dashboard.service     systemd unit for the public dashboard
```

## Running locally

```
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
./venv/bin/python uci.py        # speak UCI on stdin/stdout
python3 dashboard.py            # http://localhost:8766
```

For real play, point [`lichess-bot`](https://github.com/lichess-bot-devs/lichess-bot)
at `run-uci.sh` (which execs the PyPy venv).

## Deployment

- **Bot + dashboard:** `vps/setup.sh <repo-url>` provisions a Debian/Ubuntu VPS
  (creates the `bot` user, installs PyPy, clones lichess-bot, sets up the
  engine venv). Drop the two `.service` files into `/etc/systemd/system/` and
  `systemctl enable --now` them.
- **Public stats page:** `./build-web.sh` regenerates `web/index.html` from
  `dashboard.py`; Netlify serves the `web/` directory.

![mate](images/mate.png)

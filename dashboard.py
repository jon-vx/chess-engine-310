"""
Live dashboard for the bot. Run:
    python3 dashboard.py
then open http://localhost:8766

Polls the Lichess public API every few seconds. 
"""

import http.server
import os

# Defaults are private/local-only. The systemd unit on the VPS overrides
# DASH_BIND=0.0.0.0 to expose the dashboard publicly.
PORT      = int(os.environ.get("DASH_PORT", "8766"))
BIND_HOST = os.environ.get("DASH_BIND", "127.0.0.1")
BOT_USER  = os.environ.get("BOT_USER", "bigbotontheblock")

DASHBOARD_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>__BOT__ // ARCADE</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323&display=swap" rel="stylesheet">
<style>
  /* Cozy pixel-art palette: dusk-tinted slate with muted earth accents.
     No neon, no glows -- just calm flat colors and gentle pixelated framing. */
  :root {
    --bg:        #1a1c2e;   /* deep slate-navy */
    --bg-soft:   #232545;   /* slightly lighter, used for cards */
    --ink:       #14152a;
    --frame:     #5b6dc8;   /* muted periwinkle */
    --frame-dim: #3b4480;
    --accent:    #c178b3;   /* dusty rose */
    --text:      #e8e6d0;   /* warm cream */
    --text-dim:  #b9b6a0;
    --dim:       #7575a0;   /* muted lavender */
    --win:       #7eb89c;   /* sage */
    --loss:      #c46a6a;   /* dusty red */
    --draw:      #d4a85a;   /* muted gold */
    --soft-amber:#e8c87a;
  }

  * { box-sizing: border-box; }

  html, body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: 'Press Start 2P', 'VT323', ui-monospace, monospace;
    font-size: 10px;
    line-height: 1.9;
    letter-spacing: 0.3px;
    min-height: 100vh;
  }

  /* Very subtle scanlines (overlay, low opacity) */
  body::before {
    content: '';
    position: fixed; inset: 0;
    background: repeating-linear-gradient(
      to bottom,
      transparent 0px,
      transparent 2px,
      rgba(0,0,0,0.10) 3px,
      rgba(0,0,0,0.10) 4px
    );
    pointer-events: none;
    z-index: 9999;
  }

  /* Soft vignette, just a hint */
  body::after {
    content: '';
    position: fixed; inset: 0;
    background: radial-gradient(ellipse at center,
                                transparent 60%,
                                rgba(0,0,0,0.25) 100%);
    pointer-events: none;
    z-index: 9998;
  }

  .screen {
    max-width: 920px;
    margin: 0 auto;
    padding: 32px 20px 60px;
    position: relative;
    z-index: 1;
  }

  /* ============ HEADER ============ */
  .marquee {
    text-align: center;
    font-size: 8px;
    color: var(--dim);
    margin-bottom: 14px;
    letter-spacing: 3px;
  }

  .title {
    text-align: center;
    margin: 0 0 4px;
  }
  .title .name {
    font-size: 18px;
    color: var(--text);
    letter-spacing: 2px;
  }
  .title .badge {
    display: inline-block;
    color: var(--ink);
    background: var(--soft-amber);
    padding: 3px 6px;
    margin-left: 10px;
    font-size: 8px;
    vertical-align: 4px;
    letter-spacing: 1px;
  }

  .player-line {
    text-align: center;
    color: var(--dim);
    font-size: 7px;
    letter-spacing: 3px;
    margin-bottom: 6px;
  }

  .status-line {
    text-align: center;
    margin: 18px 0 28px;
    font-size: 9px;
  }
  .status-online   { color: var(--win); }
  .status-playing  { color: var(--frame); }
  .status-offline  { color: var(--dim); }
  .blink { animation: blink 1.1s steps(2, start) infinite; }
  @keyframes blink { to { opacity: 0; } }

  /* ============ PANELS ============ */
  .panel {
    border: 2px solid var(--frame-dim);
    background: var(--bg-soft);
    padding: 22px 18px 16px;
    margin-bottom: 18px;
    position: relative;
  }
  .panel-title {
    position: absolute;
    top: -8px; left: 14px;
    background: var(--bg);
    padding: 1px 8px;
    color: var(--accent);
    font-size: 8px;
    letter-spacing: 2px;
  }

  .grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
  @media (max-width: 720px) { .grid { grid-template-columns: 1fr; } }

  /* ============ RATINGS ============ */
  table { width: 100%; border-collapse: collapse; }
  th, td { padding: 7px 6px; text-align: left; font-size: 9px; }
  th {
    color: var(--dim); font-size: 7px;
    border-bottom: 1px solid var(--frame-dim); padding-bottom: 6px;
    letter-spacing: 2px;
  }
  td { border-bottom: 1px solid rgba(91, 109, 200, 0.15); }
  tbody tr:last-child td { border-bottom: none; }

  td.tc       { color: var(--soft-amber); text-transform: uppercase; }
  .rating-num { color: var(--frame); font-size: 13px; }
  .prov       { color: var(--accent); font-size: 9px; margin-left: 2px; }
  .rd         { color: var(--dim); font-size: 7px; margin-left: 6px; }

  /* ============ SCORE BOX ============ */
  .score-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 10px;
  }
  .score-box {
    border: 1px solid var(--frame-dim);
    text-align: center;
    padding: 10px 4px;
    background: var(--ink);
  }
  .score-box.win  { border-color: var(--win); }
  .score-box.loss { border-color: var(--loss); }
  .score-box.draw { border-color: var(--draw); }
  .score-box .lbl {
    font-size: 7px; color: var(--dim); letter-spacing: 2px;
    margin-bottom: 8px;
  }
  .score-box .val { font-size: 20px; line-height: 1; }
  .score-box.win  .val { color: var(--win); }
  .score-box.loss .val { color: var(--loss); }
  .score-box.draw .val { color: var(--draw); }

  .winrate-line {
    margin-top: 14px;
    text-align: center;
    font-size: 10px;
    color: var(--text);
    letter-spacing: 2px;
  }
  .winrate-line span { color: var(--accent); }
  .total-line {
    text-align: center;
    color: var(--dim);
    font-size: 7px;
    letter-spacing: 2px;
    margin-top: 4px;
  }

  /* ============ BATTLE LOG ============ */
  .log-row {
    display: grid;
    grid-template-columns: 64px 1fr 56px 64px 80px;
    gap: 10px;
    padding: 8px 0;
    border-bottom: 1px solid rgba(91, 109, 200, 0.12);
    align-items: center;
    font-size: 8px;
  }
  .log-row:last-child { border-bottom: none; }
  .tag {
    text-align: center;
    padding: 3px 0;
    font-size: 7px;
    letter-spacing: 1px;
    border: 1px solid currentColor;
  }
  .tag.WON  { color: var(--win); }
  .tag.LOST { color: var(--loss); }
  .tag.DRAW { color: var(--draw); }

  .opp { color: var(--text); text-transform: uppercase; }
  .opp .tlt { color: var(--accent); margin-right: 4px; font-size: 7px; }
  .opp-rating { color: var(--dim); font-size: 8px; }
  .perf { color: var(--soft-amber); text-transform: uppercase; }
  .ago  { color: var(--dim); text-align: right; }

  /* ============ FOOTER ============ */
  .hud-footer {
    margin-top: 24px;
    padding-top: 12px;
    border-top: 1px solid var(--frame-dim);
    display: flex;
    justify-content: space-between;
    font-size: 7px;
    color: var(--dim);
    letter-spacing: 2px;
  }
  .pulse-dot {
    color: var(--win);
    margin-right: 6px;
  }

  /* ============ LINKS ============ */
  a { color: var(--frame); text-decoration: none; }
  a:hover { color: var(--accent); }

  .empty {
    text-align: center;
    color: var(--dim);
    padding: 22px 8px;
    font-size: 8px;
    letter-spacing: 2px;
  }
</style>
</head>
<body>
<div class="screen">

  <div class="marquee">· · ·  bot status  · · ·</div>

  <h1 class="title">
    <span class="name" id="username">__BOT__</span>
    <span class="badge">BOT</span>
  </h1>
  <div class="player-line">── PLAYER 1 ──</div>

  <div class="status-line" id="status">
    <span class="status-offline">CONNECTING<span class="blink">_</span></span>
  </div>

  <div class="grid">

    <section class="panel">
      <div class="panel-title">RATINGS</div>
      <table id="ratings">
        <thead>
          <tr><th>MODE</th><th>RATING</th><th>GAMES</th></tr>
        </thead>
        <tbody>
          <tr><td colspan="3" class="empty">LOADING...</td></tr>
        </tbody>
      </table>
    </section>

    <section class="panel">
      <div class="panel-title">SCORE</div>
      <div class="score-grid">
        <div class="score-box win">
          <div class="lbl">WIN</div><div class="val" id="wins">--</div>
        </div>
        <div class="score-box loss">
          <div class="lbl">LOSS</div><div class="val" id="losses">--</div>
        </div>
        <div class="score-box draw">
          <div class="lbl">DRAW</div><div class="val" id="draws">--</div>
        </div>
      </div>
      <div class="winrate-line">WIN RATE: <span id="winrate">--</span></div>
      <div class="total-line">TOTAL GAMES: <span id="total">--</span></div>
    </section>

  </div>

  <section class="panel">
    <div class="panel-title">BATTLE LOG</div>
    <div id="games">
      <div class="empty">LOADING...</div>
    </div>
  </section>

  <div class="hud-footer">
    <span><span class="pulse-dot blink">●</span>AUTO-REFRESH 5S</span>
    <span id="lastUpdate">SYNCING...</span>
  </div>

</div>

<script>
const BOT = "__BOT__";

function fmtAgo(ms) {
  const sec = Math.floor((Date.now() - ms) / 1000);
  if (sec < 60)    return sec + "S AGO";
  if (sec < 3600)  return Math.floor(sec/60)   + "M AGO";
  if (sec < 86400) return Math.floor(sec/3600) + "H AGO";
  return Math.floor(sec/86400) + "D AGO";
}

function pad3(n) { return String(n).padStart(3, "0"); }

async function loadUser() {
  const r = await fetch(`https://lichess.org/api/user/${BOT}`);
  const d = await r.json();

  // Status
  const playing = d.playing;
  const seenAtMs = d.seenAt || 0;
  const recentlySeen = Date.now() - seenAtMs < 5 * 60 * 1000;
  const statusEl = document.getElementById("status");
  if (playing) {
    const id = playing.split('/').pop();
    statusEl.innerHTML = `<span class="status-playing">▶▶ NOW PLAYING: `
      + `<a href="${playing}" target="_blank">${id.toUpperCase()}</a><span class="blink">_</span></span>`;
  } else if (recentlySeen) {
    statusEl.innerHTML = `<span class="status-online">● ONLINE — STANDBY (${fmtAgo(seenAtMs)})</span>`;
  } else {
    statusEl.innerHTML = `<span class="status-offline">○ OFFLINE — LAST SEEN ${fmtAgo(seenAtMs)}</span>`;
  }

  // Ratings
  const tbody = document.querySelector("#ratings tbody");
  tbody.innerHTML = "";
  const order = ["bullet", "blitz", "rapid", "classical", "correspondence"];
  for (const k of order) {
    const v = d.perfs?.[k];
    if (!v || !v.games) continue;
    const prov = v.prov ? '<span class="prov">?</span>' : '';
    tbody.insertAdjacentHTML("beforeend",
      `<tr>
        <td class="tc">${k}</td>
        <td><span class="rating-num">${v.rating}</span>${prov}<span class="rd">±${v.rd}</span></td>
        <td>${v.games}</td>
      </tr>`);
  }
  if (!tbody.children.length) {
    tbody.innerHTML = '<tr><td colspan="3" class="empty">NO RATED GAMES YET</td></tr>';
  }
}

async function loadGames() {
  const r = await fetch(
    `https://lichess.org/api/games/user/${BOT}?max=20&rated=true`,
    { headers: { "Accept": "application/x-ndjson" } });
  const text = await r.text();
  const games = text.trim().split("\n").filter(l => l).map(l => JSON.parse(l));

  let wins = 0, losses = 0, draws = 0;
  const list = document.getElementById("games");
  list.innerHTML = "";
  for (const g of games) {
    const meColor = g.players.white?.user?.name?.toLowerCase() === BOT.toLowerCase() ? "white" : "black";
    const oppColor = meColor === "white" ? "black" : "white";
    const opp = g.players[oppColor]?.user || {};
    const oppName = (opp.name || "?").toUpperCase();
    const oppTitle = opp.title ? `<span class="tlt">${opp.title}</span>` : "";
    const oppRating = g.players[oppColor]?.rating ?? "?";
    let result;
    if (g.winner === meColor)      { result = "WON";  wins++; }
    else if (g.winner)             { result = "LOST"; losses++; }
    else                           { result = "DRAW"; draws++; }
    list.insertAdjacentHTML("beforeend",
      `<div class="log-row">
         <div class="tag ${result}">${result}</div>
         <div class="opp">${oppTitle}<a href="https://lichess.org/@/${opp.name || ""}" target="_blank">${oppName}</a></div>
         <div class="opp-rating">${oppRating}</div>
         <div class="perf">${g.perf}</div>
         <div class="ago">${fmtAgo(g.lastMoveAt)}</div>
       </div>`);
  }
  if (!list.children.length) {
    list.innerHTML = '<div class="empty">INSERT COIN TO BEGIN<br/>(NO GAMES YET)</div>';
  }

  document.getElementById("wins").textContent = pad3(wins);
  document.getElementById("losses").textContent = pad3(losses);
  document.getElementById("draws").textContent = pad3(draws);
  const total = wins + losses + draws;
  document.getElementById("total").textContent = pad3(total);
  document.getElementById("winrate").textContent =
    total ? Math.round(100 * wins / total) + "%" : "--";
}

async function refresh() {
  try {
    await Promise.all([loadUser(), loadGames()]);
    document.getElementById("lastUpdate").textContent =
      "SYNC " + new Date().toLocaleTimeString().toUpperCase();
  } catch (e) {
    document.getElementById("lastUpdate").textContent = "ERR: " + e.message.toUpperCase();
  }
}

refresh();
setInterval(refresh, 5000);
</script>

</body>
</html>
"""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = DASHBOARD_HTML.replace("__BOT__", BOT_USER).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):  # quiet by default
        pass


if __name__ == "__main__":
    httpd = http.server.HTTPServer((BIND_HOST, PORT), Handler)
    print(f"Dashboard live at http://{BIND_HOST}:{PORT}  (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()

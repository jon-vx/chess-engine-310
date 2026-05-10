#!/usr/bin/env bash
# One-shot bootstrap for a fresh Ubuntu 24.04 droplet.
# Run as root:
#   bash setup.sh                                          # rsync workflow
#   bash setup.sh https://github.com/USER/chess-engine-310.git   # clone workflow
#
# What it does:
#   - apt deps (git, build tools, ufw, python3-venv)
#   - creates a 'bot' user (with the same SSH key as root, so you can ssh bot@...)
#   - opens ufw on 22 + 8766
#   - downloads PyPy 7.3.19 (Python 3.11 compat) into /home/bot/.local/
#   - clones lichess-bot into /home/bot/lichess-bot, sets up its CPython venv
#   - if a REPO_URL is provided: clones chess-engine-310 into /home/bot/
#     otherwise: makes an empty /home/bot/chess-engine-310/ for you to rsync into
#   - sets up the engine PyPy venv either way

set -euo pipefail

REPO_URL="${1:-}"
PYPY_VER="pypy3.11-v7.3.19-linux64"
PYPY_URL="https://downloads.python.org/pypy/${PYPY_VER}.tar.bz2"

echo ">> Updating apt + installing system deps..."
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
    git curl ca-certificates ufw rsync \
    python3-venv build-essential

echo ">> Creating 'bot' user..."
if ! id bot >/dev/null 2>&1; then
    useradd -m -s /bin/bash bot
fi
# Mirror root's authorized_keys so you can ssh bot@vps directly.
if [ -f /root/.ssh/authorized_keys ]; then
    install -d -m 700 -o bot -g bot /home/bot/.ssh
    install -m 600 -o bot -g bot /root/.ssh/authorized_keys /home/bot/.ssh/authorized_keys
fi

echo ">> Configuring UFW (allow 22 ssh, 8766 dashboard)..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 8766/tcp
ufw --force enable

echo ">> Downloading PyPy ${PYPY_VER}..."
sudo -u bot bash -c "
    set -euo pipefail
    mkdir -p ~/.local
    if [ ! -d ~/.local/${PYPY_VER} ]; then
        curl -fL -o /tmp/pypy.tar.bz2 '${PYPY_URL}'
        tar -C ~/.local -xf /tmp/pypy.tar.bz2
        rm /tmp/pypy.tar.bz2
    fi
"

echo ">> Cloning lichess-bot + installing its deps..."
sudo -u bot bash -c '
    set -euo pipefail
    cd ~
    if [ ! -d lichess-bot ]; then
        git clone --depth 1 https://github.com/lichess-bot-devs/lichess-bot.git
    fi
    cd lichess-bot
    if [ ! -d venv ]; then
        python3 -m venv venv
    fi
    ./venv/bin/pip install --quiet --upgrade pip
    ./venv/bin/pip install --quiet -r requirements.txt
'

if [ -n "$REPO_URL" ]; then
    echo ">> Cloning chess-engine-310 from $REPO_URL ..."
    sudo -u bot bash -c "
        set -euo pipefail
        cd ~
        if [ ! -d chess-engine-310 ]; then
            git clone '$REPO_URL' chess-engine-310
        fi
        chmod +x ~/chess-engine-310/run-uci.sh
    "
fi

echo ">> Setting up engine venv (PyPy)..."
sudo -u bot bash -c "
    set -euo pipefail
    mkdir -p ~/chess-engine-310
    cd ~/chess-engine-310
    PYPY=~/.local/${PYPY_VER}/bin/pypy3
    if [ ! -d venv-pypy ]; then
        \$PYPY -m venv venv-pypy
        ./venv-pypy/bin/pip install --quiet chess
    fi
"

cat <<'EOF'

============================================================
 Bootstrap complete.

 Next steps (from your laptop):

   1. rsync the engine code:
        rsync -av --exclude=venv --exclude=venv-pypy --exclude=__pycache__ \
              --exclude=.git --exclude=vps \
              /home/stellz/dev/chess-engine-310/ \
              bot@VPS_IP:/home/bot/chess-engine-310/

   2. rsync the lichess-bot config (then edit token + paths on VPS):
        rsync -av /home/stellz/dev/lichess-bot/config.yml \
              bot@VPS_IP:/home/bot/lichess-bot/config.yml

   3. SSH into the VPS as bot:
        ssh bot@VPS_IP

      Then on the VPS:
        # fix engine path
        sed -i 's|/home/stellz/dev/chess-engine-310|/home/bot/chess-engine-310|g' \
            ~/lichess-bot/config.yml

        # paste new token (NOT the leaked one)
        nano ~/lichess-bot/config.yml   # change the `token:` line

        chmod 600 ~/lichess-bot/config.yml
        chmod +x ~/chess-engine-310/run-uci.sh ~/chess-engine-310/run-bot.sh

   4. Install + start systemd units (back as root):
        sudo cp ~bot/chess-engine-310/vps/lichess-bot.service     /etc/systemd/system/
        sudo cp ~bot/chess-engine-310/vps/chess-dashboard.service /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable --now lichess-bot chess-dashboard

   5. Verify:
        systemctl status lichess-bot chess-dashboard
        journalctl -u lichess-bot -f
        curl -s http://localhost:8766/ | head -5

   6. Visit http://VPS_IP:8766 in a browser.
============================================================
EOF

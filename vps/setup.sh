#!/usr/bin/env bash

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

EOF

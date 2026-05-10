#!/usr/bin/env bash
# Regenerate web/index.html from dashboard.py's embedded HTML for Netlify.
# Run after editing dashboard.py.

set -euo pipefail
cd "$(dirname "$0")"
mkdir -p web
python3 -c "
import dashboard
print(dashboard.DASHBOARD_HTML.replace('__BOT__', dashboard.BOT_USER), end='')
" > web/index.html
echo "wrote web/index.html ($(wc -c < web/index.html) bytes)"

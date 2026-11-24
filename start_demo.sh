#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export MVP_DEMO_MODE=1
python3 -m streamlit run student_portal.py --server.port 8501 --theme.base light &
p1=$!
python3 -m streamlit run club_portal.py --server.port 8502 --theme.base light &
p2=$!
python3 -m streamlit run client_portal.py --server.port 8503 --theme.base light &
p3=$!
trap 'kill "$p1" "$p2" "$p3" 2>/dev/null || true' EXIT INT TERM
printf 'Student: http://localhost:8501\nClub:    http://localhost:8502\nClient:  http://localhost:8503\nPress Ctrl+C to stop all three servers.\n'
wait

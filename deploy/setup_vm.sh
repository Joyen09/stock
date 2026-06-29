#!/usr/bin/env bash
# 在 GCP VM (Debian/Ubuntu) 上一鍵安裝本框架。
# 用法：
#   git clone <你的 repo> ~/stock && cd ~/stock
#   bash deploy/setup_vm.sh
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
echo "==> 安裝目錄: $APP_DIR"

# 1. 系統套件（Python 與虛擬環境）
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y python3 python3-venv python3-pip
fi

# 2. 建立虛擬環境（隔離，不污染系統 Python）
cd "$APP_DIR"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet --upgrade pip
# 只裝回測/掃描必要的；要實單再自行 pip install shioaji FinMind
pip install --quiet pandas numpy

echo "==> 安裝完成。測試一下："
python main.py list
echo
echo "回測測試：python main.py backtest --strategy buffett"
echo
echo "若要設定每日自動掃描，請看 deploy/README_DEPLOY.md"

#!/usr/bin/env bash
# Setup VPS Ubuntu (22.04/24.04) cho ứng dụng Document Converter
# Domain: app.edutechnd.io.vn
# Chạy với quyền sudo: sudo bash deploy/setup-vps.sh

set -euo pipefail

DOMAIN="app.edutechnd.io.vn"
PROJECT_DIR="${PROJECT_DIR:-/opt/doc-converter}"
EMAIL="${LETSENCRYPT_EMAIL:-giasunguyenduy7593@gmail.com}"

log() { echo -e "\033[1;32m[setup]\033[0m $*"; }
err() { echo -e "\033[1;31m[error]\033[0m $*" >&2; }

if [[ $EUID -ne 0 ]]; then
  err "Chạy script này bằng sudo."
  exit 1
fi

# ============ 1. System packages ============
log "Cập nhật hệ thống..."
apt-get update -y
apt-get upgrade -y

log "Cài đặt các gói cần thiết..."
apt-get install -y \
  ca-certificates curl gnupg lsb-release \
  ufw nginx certbot python3-certbot-nginx \
  git rsync htop

# ============ 2. Docker ============
if ! command -v docker >/dev/null 2>&1; then
  log "Cài đặt Docker..."
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | tee /etc/apt/sources.list.d/docker.list >/dev/null
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
else
  log "Docker đã cài, skip."
fi

# ============ 3. Firewall ============
log "Cấu hình UFW..."
ufw allow OpenSSH || true
ufw allow 'Nginx Full' || true
echo "y" | ufw enable || true
ufw status

# ============ 4. Nginx site config ============
log "Cài đặt nginx site cho ${DOMAIN}..."
NGINX_CONF="/etc/nginx/sites-available/${DOMAIN}"
if [[ ! -f "${NGINX_CONF}" ]]; then
  cp "$(dirname "$0")/nginx-${DOMAIN}.conf" "${NGINX_CONF}"
fi
ln -sf "${NGINX_CONF}" "/etc/nginx/sites-enabled/${DOMAIN}"

# Webroot cho certbot
mkdir -p /var/www/certbot

nginx -t
systemctl reload nginx

# ============ 5. SSL với Let's Encrypt ============
log "Lấy chứng chỉ SSL cho ${DOMAIN}..."
if [[ ! -d "/etc/letsencrypt/live/${DOMAIN}" ]]; then
  certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos -m "${EMAIL}" --redirect
else
  log "Cert đã tồn tại, skip. (Auto renew qua systemd timer)"
fi

systemctl list-timers | grep -i certbot || true

# ============ 6. Build & chạy Docker ============
if [[ -d "${PROJECT_DIR}" ]]; then
  log "Build & start containers tại ${PROJECT_DIR}..."
  cd "${PROJECT_DIR}"
  docker compose pull --ignore-pull-failures || true
  docker compose up -d --build
  docker compose ps
else
  err "Thư mục project ${PROJECT_DIR} chưa có. Hãy upload code lên đó rồi chạy:"
  err "  cd ${PROJECT_DIR} && docker compose up -d --build"
fi

log "Hoàn tất! Truy cập: https://${DOMAIN}"

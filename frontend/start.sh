#!/bin/sh
# Nginx 시작 스크립트
# DOMAIN_NAME 환경 변수를 기반으로 nginx 설정 생성

set -e

DOMAIN_NAME=${DOMAIN_NAME:?DOMAIN_NAME must be set}
APP_ENV=${APP_ENV:-production}

echo "=== Nginx Let's Encrypt 설정 ===" 
echo "Domain: $DOMAIN_NAME"

if [ "$APP_ENV" = "development" ]; then
    echo "Development mode: HTTP configuration enabled"
    cp /etc/nginx/nginx-http.conf.template /etc/nginx/nginx.conf
else
    CERT_DIR="/etc/letsencrypt/live/$DOMAIN_NAME"
    if [ ! -f "$CERT_DIR/fullchain.pem" ] || [ ! -f "$CERT_DIR/privkey.pem" ]; then
        echo "Production requires TLS certificate files for DOMAIN_NAME" >&2
        exit 1
    fi
    echo "Production mode: HTTPS configuration enabled"
    sed "s/DOMAIN_NAME/$DOMAIN_NAME/g" /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf
fi

# Nginx 문법 검사
nginx -t

# Nginx 시작
echo "🚀 Nginx 시작 중..."
nginx -g "daemon off;"

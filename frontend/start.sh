#!/bin/sh
# Nginx 시작 스크립트
# DOMAIN_NAME 환경 변수를 기반으로 nginx 설정 생성

set -e

DOMAIN_NAME=${DOMAIN_NAME:-localhost}

echo "=== Nginx Let's Encrypt 설정 ===" 
echo "Domain: $DOMAIN_NAME"

# 인증서 유무에 따라 사용할 설정을 자동 선택한다.
# - 인증서 있음  → HTTPS 설정(nginx.conf.template)에 도메인 치환 후 사용
# - 인증서 없음  → HTTP 전용 설정(nginx-http.conf.template) 사용 (IP 접속/테스트 환경)
# 이렇게 하면 인증서가 없어도 nginx가 죽지 않고 HTTP로 서비스되며,
# 추후 인증서가 발급되면 재기동만으로 자동 HTTPS 승격된다.
if [ -f "/etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem" ]; then
    echo "✅ Let's Encrypt 인증서 존재 (도메인: $DOMAIN_NAME)"
    echo "🔒 HTTPS 활성화"
    sed "s/DOMAIN_NAME/$DOMAIN_NAME/g" /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf
else
    echo "⚠️  Let's Encrypt 인증서 없음 → HTTP 전용 모드로 기동"
    echo "ℹ️  도메인 발급 후 init-letsencrypt.sh를 실행하면 HTTPS로 자동 전환됩니다"
    cp /etc/nginx/nginx-http.conf.template /etc/nginx/nginx.conf
fi

# Nginx 문법 검사
nginx -t

# Nginx 시작
echo "🚀 Nginx 시작 중..."
nginx -g "daemon off;"

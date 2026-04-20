#!/bin/sh
# Nginx 시작 스크립트
# DOMAIN_NAME 환경 변수를 기반으로 nginx 설정 생성

set -e

DOMAIN_NAME=${DOMAIN_NAME:-localhost}

echo "=== Nginx Let's Encrypt 설정 ===" 
echo "Domain: $DOMAIN_NAME"

# nginx.conf 템플릿에서 DOMAIN_NAME 치환
sed "s/DOMAIN_NAME/$DOMAIN_NAME/g" /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# 인증서 파일이 존재하는지 확인
if [ -f "/etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem" ]; then
    echo "✅ Let's Encrypt 인증서 존재 (도메인: $DOMAIN_NAME)"
    echo "🔒 HTTPS 활성화"
else
    echo "⚠️  Let's Encrypt 인증서 없음"
    echo "ℹ️  첫 배포 시 init-letsencrypt.sh를 실행하세요"
    echo "📝 명령: bash init-letsencrypt.sh"
fi

# Nginx 문법 검사
nginx -t

# Nginx 시작
echo "🚀 Nginx 시작 중..."
nginx -g "daemon off;"

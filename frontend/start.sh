#!/bin/sh
# Nginx 시작 스크립트
# DOMAIN_NAME 환경 변수를 기반으로 nginx 설정 생성

set -e

DOMAIN_NAME=${DOMAIN_NAME:?DOMAIN_NAME must be set}
APP_ENV=${APP_ENV:-production}

echo "=== Nginx Let's Encrypt 설정 ==="
echo "Domain: $DOMAIN_NAME"

# Let's Encrypt cannot issue certificates for bare IP addresses. When
# DOMAIN_NAME is an IPv4 literal, TLS is still required (DEC-05), but the
# cert must come from a self-signed fallback instead of Let's Encrypt.
is_ipv4() {
    case "$1" in
        ''|*[!0-9.]*) return 1 ;;
    esac
    old_ifs=$IFS
    IFS=.
    set -- $1
    IFS=$old_ifs
    [ $# -eq 4 ] || return 1
    for octet in "$@"; do
        case "$octet" in
            ''|*[!0-9]*) return 1 ;;
        esac
        [ "$octet" -le 255 ] || return 1
    done
    return 0
}

generate_self_signed_cert() {
    echo "IP 주소는 Let's Encrypt 발급 대상이 아니므로 자체 서명 인증서를 생성합니다." >&2
    mkdir -p "$CERT_DIR"
    openssl req -x509 -nodes -newkey rsa:2048 \
        -keyout "$CERT_DIR/privkey.pem" \
        -out "$CERT_DIR/fullchain.pem" \
        -days 3650 \
        -subj "/CN=$DOMAIN_NAME" \
        -addext "subjectAltName=IP:$DOMAIN_NAME"
}

if [ "$APP_ENV" = "development" ]; then
    echo "Development mode: HTTP configuration enabled"
    cp /etc/nginx/nginx-http.conf.template /etc/nginx/nginx.conf
else
    CERT_DIR="/etc/letsencrypt/live/$DOMAIN_NAME"
    if [ ! -f "$CERT_DIR/fullchain.pem" ] || [ ! -f "$CERT_DIR/privkey.pem" ]; then
        if is_ipv4 "$DOMAIN_NAME"; then
            generate_self_signed_cert
        else
            echo "Production requires TLS certificate files for DOMAIN_NAME" >&2
            exit 1
        fi
    fi
    echo "Production mode: HTTPS configuration enabled"
    sed "s/DOMAIN_NAME/$DOMAIN_NAME/g" /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf
fi

# Nginx 문법 검사
nginx -t

# Nginx 시작
echo "🚀 Nginx 시작 중..."
nginx -g "daemon off;"

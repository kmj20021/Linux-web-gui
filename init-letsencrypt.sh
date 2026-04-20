#!/bin/bash
# Let's Encrypt 인증서 초기 설정 스크립트
# 사용법: bash init-letsencrypt.sh your-domain.com your-email@example.com

set -e

if [ $# -ne 2 ]; then
    echo "사용법: bash init-letsencrypt.sh <도메인> <이메일>"
    echo "예시: bash init-letsencrypt.sh example.com admin@example.com"
    exit 1
fi

DOMAIN_NAME=$1
EMAIL=$2
DOCKER_COMPOSE="docker-compose.yml"

echo "================================================"
echo "Let's Encrypt 인증서 초기 설정"
echo "================================================"
echo "도메인: $DOMAIN_NAME"
echo "이메일: $EMAIL"
echo ""

# 1. Docker 컨테이너 중지 (기존 인증서 없을 경우만)
echo "📦 Docker Compose 컨테이너 확인..."
if docker-compose ps | grep -q "frontend"; then
    echo "⏹️  기존 컨테이너 중지 중..."
    docker-compose down || true
fi

# 2. 인증서 디렉토리 초기 생성
echo ""
echo "📁 디렉토리 초기화..."
mkdir -p letsencrypt
chmod 755 letsencrypt

# 3. 더미 인증서 생성 (nginx 시작용)
echo ""
echo "🔑 더미 인증서 생성 (Certbot용)..."
openssl req -x509 -nodes -newkey rsa:2048 \
    -days 1 \
    -keyout letsencrypt/dummy.key \
    -out letsencrypt/dummy.crt \
    -subj "/CN=$DOMAIN_NAME" 2>/dev/null || true

# 4. docker-compose.yml의 DOMAIN_NAME 환경 변수 설정
echo ""
echo "⚙️  환경 변수 설정..."
export DOMAIN_NAME=$DOMAIN_NAME

# 5. Docker Compose 시작 (nginx는 더미 인증서로 시작)
echo ""
echo "🚀 Docker Compose 시작 (더미 인증서 사용)..."
docker-compose -f $DOCKER_COMPOSE up -d frontend

# 6. nginx가 준비될 때까지 대기
echo ""
echo "⏳ Nginx 준비 대기 중..."
sleep 10

# 7. Certbot으로 실제 인증서 발급
echo ""
echo "🔐 Let's Encrypt 인증서 발급 중..."
docker-compose -f $DOCKER_COMPOSE run --rm certbot certonly \
    --webroot \
    -w /var/www/certbot \
    --email "$EMAIL" \
    -d "$DOMAIN_NAME" \
    --agree-tos \
    --non-interactive \
    --expand 2>&1 | tee certbot_output.log

# 8. 인증서 확인
echo ""
if [ -f "letsencrypt/live/$DOMAIN_NAME/fullchain.pem" ]; then
    echo "✅ 인증서 발급 성공!"
    echo "📍 경로: letsencrypt/live/$DOMAIN_NAME/"
    
    # 9. Nginx 재시작 (실제 인증서 사용)
    echo ""
    echo "🔄 Nginx 재시작 (실제 인증서 로드)..."
    docker-compose -f $DOCKER_COMPOSE restart frontend
    
    # 10. HTTPS 연결 테스트
    echo ""
    echo "🧪 HTTPS 연결 테스트 중..."
    sleep 5
    
    # curl이 없으면 wget 사용
    if command -v curl &> /dev/null; then
        curl -k -I https://localhost/ 2>/dev/null || echo "⚠️  로컬 HTTPS 테스트 스킵 (localhost SSL 문제)"
    else
        wget --no-check-certificate -O /dev/null https://localhost/ 2>&1 || echo "⚠️  로컬 HTTPS 테스트 스킵 (localhost SSL 문제)"
    fi
    
    echo ""
    echo "================================================"
    echo "✅ Let's Encrypt 설정 완료!"
    echo "================================================"
    echo ""
    echo "📝 다음 단계:"
    echo "1. AWS에 도메인 DNS 설정 (CNAME 또는 A 레코드)"
    echo "2. EC2 인스턴스의 보안 그룹에 443 포트 추가"
    echo "3. docker-compose up -d로 모든 서비스 시작"
    echo ""
    echo "🔄 자동 갱신:"
    echo "- Certbot 컨테이너가 12시간마다 자동 갱신"
    echo "- 갱신 로그 확인: docker-compose logs certbot"
    echo ""
else
    echo "❌ 인증서 발급 실패!"
    echo "📋 Certbot 로그:"
    cat certbot_output.log || true
    exit 1
fi

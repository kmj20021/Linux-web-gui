#!/bin/bash
# Let's Encrypt & HTTPS 테스트 스크립트

set -e

echo "================================================"
echo "🧪 Let's Encrypt & HTTPS 테스트"
echo "================================================"
echo ""

# 색상 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 테스트 결과 카운트
PASS=0
FAIL=0

# 테스트 함수
test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $2"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: $2"
        FAIL=$((FAIL + 1))
    fi
}

# 1. Docker Compose 상태 확인
echo "1️⃣  Docker Compose 서비스 상태"
echo "---"
docker-compose ps
DOCKER_STATUS=$?
test_result $DOCKER_STATUS "Docker Compose 실행 중"
echo ""

# 2. Nginx 설정 파일 존재 확인
echo "2️⃣  Nginx 설정 파일"
echo "---"
if [ -f "nginx/nginx.conf" ]; then
    echo "✅ nginx/nginx.conf 존재"
    
    # HTTPS 설정 확인
    if grep -q "listen 443 ssl http2" nginx/nginx.conf; then
        echo -e "${GREEN}✅ HTTPS (443) 포트 설정 확인${NC}"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}❌ HTTPS 포트 설정 없음${NC}"
        FAIL=$((FAIL + 1))
    fi
    
    # Let's Encrypt 경로 확인
    if grep -q "/etc/letsencrypt/live/DOMAIN_NAME" nginx/nginx.conf; then
        echo -e "${GREEN}✅ Let's Encrypt 경로 설정 확인${NC}"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}❌ Let's Encrypt 경로 설정 없음${NC}"
        FAIL=$((FAIL + 1))
    fi
    
    # HSTS 헤더 확인
    if grep -q "Strict-Transport-Security" nginx/nginx.conf; then
        echo -e "${GREEN}✅ HSTS 보안 헤더 설정 확인${NC}"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}❌ HSTS 보안 헤더 설정 없음${NC}"
        FAIL=$((FAIL + 1))
    fi
else
    echo -e "${RED}❌ nginx/nginx.conf 파일 없음${NC}"
    FAIL=$((FAIL + 1))
fi
echo ""

# 3. docker-compose.yml 설정 확인
echo "3️⃣  Docker Compose 설정"
echo "---"
if [ -f "docker-compose.yml" ]; then
    echo "✅ docker-compose.yml 존재"
    
    # Certbot 서비스 확인
    if grep -q "certbot:" docker-compose.yml; then
        echo -e "${GREEN}✅ Certbot 서비스 설정 확인${NC}"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}❌ Certbot 서비스 없음${NC}"
        FAIL=$((FAIL + 1))
    fi
    
    # HTTPS 포트 바인딩 확인
    if grep -q '- "443:443"' docker-compose.yml; then
        echo -e "${GREEN}✅ 443 포트 바인딩 확인${NC}"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}❌ 443 포트 바인딩 없음${NC}"
        FAIL=$((FAIL + 1))
    fi
    
    # Let's Encrypt 볼륨 확인
    if grep -q "letsencrypt:" docker-compose.yml; then
        echo -e "${GREEN}✅ Let's Encrypt 볼륨 설정 확인${NC}"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}❌ Let's Encrypt 볼륨 설정 없음${NC}"
        FAIL=$((FAIL + 1))
    fi
else
    echo -e "${RED}❌ docker-compose.yml 파일 없음${NC}"
    FAIL=$((FAIL + 1))
fi
echo ""

# 4. 스크립트 파일 확인
echo "4️⃣  설정 스크립트"
echo "---"
if [ -f "init-letsencrypt.sh" ]; then
    echo -e "${GREEN}✅ init-letsencrypt.sh 존재${NC}"
    PASS=$((PASS + 1))
else
    echo -e "${RED}❌ init-letsencrypt.sh 없음${NC}"
    FAIL=$((FAIL + 1))
fi

if [ -f "frontend/start.sh" ]; then
    echo -e "${GREEN}✅ frontend/start.sh 존재${NC}"
    PASS=$((PASS + 1))
else
    echo -e "${RED}❌ frontend/start.sh 없음${NC}"
    FAIL=$((FAIL + 1))
fi
echo ""

# 5. HTTP → HTTPS 리디렉션 테스트
echo "5️⃣  HTTP → HTTPS 리디렉션"
echo "---"
if grep -q "return 301 https" nginx/nginx.conf; then
    echo -e "${GREEN}✅ HTTP → HTTPS 리디렉션 설정 확인${NC}"
    PASS=$((PASS + 1))
else
    echo -e "${RED}❌ HTTP → HTTPS 리디렉션 설정 없음${NC}"
    FAIL=$((FAIL + 1))
fi

if grep -q "/.well-known/acme-challenge/" nginx/nginx.conf; then
    echo -e "${GREEN}✅ Let's Encrypt ACME 검증 경로 설정 확인${NC}"
    PASS=$((PASS + 1))
else
    echo -e "${RED}❌ ACME 검증 경로 설정 없음${NC}"
    FAIL=$((FAIL + 1))
fi
echo ""

# 6. 보안 헤더 확인
echo "6️⃣  보안 헤더 설정"
echo "---"
SECURITY_HEADERS=(
    "X-Content-Type-Options: nosniff"
    "X-Frame-Options: DENY"
    "X-XSS-Protection: 1; mode=block"
)

for header in "${SECURITY_HEADERS[@]}"; do
    if grep -q "$header" nginx/nginx.conf; then
        echo -e "${GREEN}✅ $header${NC}"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}❌ $header 없음${NC}"
        FAIL=$((FAIL + 1))
    fi
done
echo ""

# 7. Certbot 자동 갱신 설정 확인
echo "7️⃣  Certbot 자동 갱신"
echo "---"
if grep -q "certbot renew" docker-compose.yml; then
    echo -e "${GREEN}✅ 자동 갱신 스크립트 설정 확인${NC}"
    PASS=$((PASS + 1))
else
    echo -e "${RED}❌ 자동 갱신 설정 없음${NC}"
    FAIL=$((FAIL + 1))
fi
echo ""

# 8. SSL/TLS 프로토콜 버전 확인
echo "8️⃣  SSL/TLS 프로토콜"
echo "---"
if grep -q "ssl_protocols TLSv1.2 TLSv1.3" nginx/nginx.conf; then
    echo -e "${GREEN}✅ TLS 1.2 이상 설정 확인${NC}"
    PASS=$((PASS + 1))
else
    echo -e "${RED}❌ TLS 버전 설정 확인 필요${NC}"
    FAIL=$((FAIL + 1))
fi
echo ""

# 9. Certbot 이미지 확인
echo "9️⃣  Certbot Docker 이미지"
echo "---"
if docker images | grep -q "certbot"; then
    echo -e "${GREEN}✅ Certbot 이미지 존재${NC}"
    PASS=$((PASS + 1))
else
    echo -e "${YELLOW}ℹ️  Certbot 이미지 아직 다운로드되지 않음 (처음 실행 시 자동 다운로드)${NC}"
fi
echo ""

# 10. Frontend Docker 이미지 빌드 상태
echo "🔟 Frontend Docker 빌드"
echo "---"
if docker images | grep -q "linux_gui_frontend"; then
    echo -e "${GREEN}✅ Frontend 이미지 존재${NC}"
    PASS=$((PASS + 1))
else
    echo -e "${YELLOW}ℹ️  Frontend 이미지 아직 빌드되지 않음${NC}"
fi
echo ""

# 결과 요약
echo "================================================"
echo "📊 테스트 결과 요약"
echo "================================================"
echo -e "✅ ${GREEN}PASS: $PASS${NC}"
echo -e "❌ ${RED}FAIL: $FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}🎉 모든 설정 검증 완료!${NC}"
    echo ""
    echo "📝 다음 단계:"
    echo "1. AWS EC2에 배포:"
    echo "   git push origin main"
    echo ""
    echo "2. EC2에서 초기 설정:"
    echo "   bash init-letsencrypt.sh your-domain.com your-email@example.com"
    echo ""
    echo "3. 서비스 시작:"
    echo "   docker-compose up -d"
    echo ""
else
    echo -e "${RED}⚠️  $FAIL개의 설정 오류 발견${NC}"
    exit 1
fi

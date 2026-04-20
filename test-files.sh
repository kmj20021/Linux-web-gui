#!/bin/bash
# Let's Encrypt 설정 파일 기반 테스트 (Docker 없이)

echo "================================================"
echo "🧪 Let's Encrypt 설정 파일 검증 테스트"
echo "================================================"
echo ""

PASS=0
FAIL=0

test_result() {
    if [ $1 -eq 0 ]; then
        echo "✅ PASS: $2"
        PASS=$((PASS + 1))
    else
        echo "❌ FAIL: $2"
        FAIL=$((FAIL + 1))
    fi
}

# 1. 파일 존재 확인
echo "1️⃣  필수 파일 존재 확인"
echo "---"

test -f nginx/nginx.conf && echo "✅ nginx/nginx.conf 존재" || echo "❌ nginx/nginx.conf 없음"
test_result $? "nginx/nginx.conf"

test -f docker-compose.yml && echo "✅ docker-compose.yml 존재" || echo "❌ docker-compose.yml 없음"
test_result $? "docker-compose.yml"

test -f init-letsencrypt.sh && echo "✅ init-letsencrypt.sh 존재" || echo "❌ init-letsencrypt.sh 없음"
test_result $? "init-letsencrypt.sh"

test -f test-letsencrypt.sh && echo "✅ test-letsencrypt.sh 존재" || echo "❌ test-letsencrypt.sh 없음"
test_result $? "test-letsencrypt.sh"

test -f frontend/start.sh && echo "✅ frontend/start.sh 존재" || echo "❌ frontend/start.sh 없음"
test_result $? "frontend/start.sh"

test -f LETSENCRYPT_SETUP.md && echo "✅ LETSENCRYPT_SETUP.md 존재" || echo "❌ LETSENCRYPT_SETUP.md 없음"
test_result $? "LETSENCRYPT_SETUP.md"

echo ""

# 2. nginx.conf 설정 검증
echo "2️⃣  Nginx 설정 검증"
echo "---"

grep -q "listen 443 ssl http2" nginx/nginx.conf
test_result $? "HTTPS 443 포트 설정"

grep -q "ssl_certificate /etc/letsencrypt/live/DOMAIN_NAME" nginx/nginx.conf
test_result $? "Let's Encrypt 인증서 경로"

grep -q "Strict-Transport-Security" nginx/nginx.conf
test_result $? "HSTS 보안 헤더"

grep -q "X-Content-Type-Options" nginx/nginx.conf
test_result $? "X-Content-Type-Options 헤더"

grep -q "X-Frame-Options" nginx/nginx.conf
test_result $? "X-Frame-Options 헤더"

grep -q "return 301 https" nginx/nginx.conf
test_result $? "HTTP → HTTPS 리디렉션"

grep -q "/.well-known/acme-challenge/" nginx/nginx.conf
test_result $? "ACME 검증 경로"

grep -q "ssl_protocols TLSv1.2 TLSv1.3" nginx/nginx.conf
test_result $? "TLS 1.2 이상 설정"

grep -q "ssl_session_cache shared:SSL:10m" nginx/nginx.conf
test_result $? "SSL 세션 캐싱"

echo ""

# 3. docker-compose.yml 검증
echo "3️⃣  Docker Compose 설정 검증"
echo "---"

grep -q "443:443" docker-compose.yml
test_result $? "443 포트 바인딩"

grep -q "certbot:" docker-compose.yml
test_result $? "Certbot 서비스"

grep -q "letsencrypt:" docker-compose.yml
test_result $? "Let's Encrypt 볼륨"

grep -q "certbot:/var/www/certbot" docker-compose.yml
test_result $? "Certbot 검증 볼륨"

grep -q "DOMAIN_NAME" docker-compose.yml
test_result $? "DOMAIN_NAME 환경 변수"

grep -q "certbot renew --webroot" docker-compose.yml
test_result $? "자동 갱신 설정"

echo ""

# 4. 스크립트 파일 검증
echo "4️⃣  스크립트 파일 검증"
echo "---"

grep -q "DOMAIN_NAME" frontend/start.sh
test_result $? "frontend/start.sh에서 DOMAIN_NAME 처리"

grep -q "sed" frontend/start.sh
test_result $? "frontend/start.sh에서 템플릿 치환"

grep -q "init-letsencrypt.sh" init-letsencrypt.sh
test_result $? "init-letsencrypt.sh 실행 가능"

grep -q "certbot certonly" init-letsencrypt.sh
test_result $? "Certbot 인증서 발급 명령"

echo ""

# 5. 보안 헤더 완전성 확인
echo "5️⃣  보안 헤더 완전성"
echo "---"

SECURITY_HEADERS=(
    "add_header Strict-Transport-Security"
    "add_header X-Content-Type-Options"
    "add_header X-Frame-Options"
    "add_header X-XSS-Protection"
    "add_header Referrer-Policy"
)

for header in "${SECURITY_HEADERS[@]}"; do
    grep -q "$header" nginx/nginx.conf
    test_result $? "$header"
done

echo ""

# 6. Dockerfile 검증
echo "6️⃣  Frontend Dockerfile 검증"
echo "---"

grep -q "EXPOSE 80 443" frontend/Dockerfile
test_result $? "포트 노출 (80, 443)"

grep -q "start.sh" frontend/Dockerfile
test_result $? "start.sh 실행 설정"

grep -q "nginx.conf.template" frontend/Dockerfile
test_result $? "nginx.conf 템플릿 복사"

echo ""

# 결과
echo "================================================"
echo "📊 테스트 결과 요약"
echo "================================================"
echo "✅ PASS: $PASS"
echo "❌ FAIL: $FAIL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo "🎉 모든 설정 검증 완료!"
    echo ""
    echo "📝 AWS 배포 절차:"
    echo "1. EC2 인스턴스 생성 (Ubuntu 24.04 LTS)"
    echo "2. 보안 그룹: 80, 443, 22 포트 열기"
    echo "3. Route53 DNS 설정: your-domain.com → Elastic IP"
    echo "4. EC2에서 실행:"
    echo "   bash init-letsencrypt.sh your-domain.com your-email@example.com"
    echo "5. 서비스 시작:"
    echo "   docker-compose up -d"
    exit 0
else
    echo "⚠️  $FAIL개 오류 발견"
    exit 1
fi

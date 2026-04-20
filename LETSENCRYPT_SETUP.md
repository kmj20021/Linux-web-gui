# 🔐 Let's Encrypt + HTTPS 설정 가이드

AWS EC2 배포를 위한 Let's Encrypt 자동 인증서 설정 및 HTTPS 활성화 가이드입니다.

## 📋 구성 요소

| 컴포넌트 | 설명 |
|---------|------|
| **nginx** | HTTPS 프록시 + Let's Encrypt 통합 |
| **Certbot** | Let's Encrypt 인증서 자동 발급 & 갱신 |
| **frontend** | HTTPS 서버 (포트 80, 443) |
| **backend** | FastAPI 서버 (포트 8000) |

## 🚀 AWS 배포 절차

### 1️⃣ 사전 준비

#### AWS 설정
```bash
# EC2 인스턴스 생성 (Ubuntu 24.04 LTS ARM64)
- 인스턴스 타입: t4g.small (라즈베리 파이 크기)
- 보안 그룹: HTTP(80), HTTPS(443), SSH(22) 허용
- Elastic IP 할당 (고정 공인 IP)

# Route53 또는 외부 DNS 설정
Domain: your-domain.com → EC2 Elastic IP
```

#### 로컬 테스트
```bash
# 설정 검증
bash test-letsencrypt.sh
```

### 2️⃣ EC2에서 초기 설정

```bash
# 1. 저장소 클론
git clone https://github.com/yourusername/linux-web-gui.git
cd linux-web-gui

# 2. Docker & Docker Compose 설치
sudo apt update
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER

# 3. Let's Encrypt 인증서 발급
# ⚠️ 반드시 실제 도메인과 이메일 사용!
bash init-letsencrypt.sh your-domain.com your-email@example.com

# 예시:
# bash init-letsencrypt.sh myserver.example.com admin@example.com

# 4. 모든 서비스 시작
docker-compose up -d

# 5. 상태 확인
docker-compose ps
docker-compose logs -f frontend
```

### 3️⃣ HTTPS 연결 확인

```bash
# 도메인에 접속 (자동으로 HTTPS 리디렉션됨)
https://your-domain.com

# 인증서 유효성 확인
openssl s_client -connect your-domain.com:443

# 또는 SSL Labs 테스트
https://www.ssllabs.com/ssltest/analyze.html?d=your-domain.com

# 리다이렉션 확인
curl -I http://your-domain.com
# HTTP/1.1 301 Moved Permanently
# Location: https://your-domain.com
```

## 📁 파일 구조

```
linux-web-gui/
├── nginx/nginx.conf           # HTTPS + Let's Encrypt 설정
├── docker-compose.yml         # Certbot 서비스 포함
├── frontend/
│   ├── Dockerfile            # nginx 443 포트 지원
│   ├── start.sh              # 도메인명으로 설정 생성
│   └── nginx.conf.template   # 템플릿 (DOMAIN_NAME 치환됨)
├── init-letsencrypt.sh        # 초기 인증서 발급 스크립트
├── test-letsencrypt.sh        # 설정 검증 스크립트
└── LETSENCRYPT_SETUP.md       # 이 파일
```

## 🔧 주요 설정

### nginx 설정 (nginx/nginx.conf)

```nginx
# HTTP → HTTPS 리디렉션
server {
    listen 80;
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;  # Certbot 검증용
    }
    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS 서버
server {
    listen 443 ssl http2;
    
    # Let's Encrypt 인증서
    ssl_certificate /etc/letsencrypt/live/DOMAIN_NAME/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/DOMAIN_NAME/privkey.pem;
    
    # 보안 헤더
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
}
```

### Docker Compose 설정

```yaml
services:
  frontend:
    volumes:
      - letsencrypt:/etc/letsencrypt  # 인증서 저장
      - certbot:/var/www/certbot      # 검증용
    ports:
      - "80:80"
      - "443:443"
    environment:
      - DOMAIN_NAME=your-domain.com

  certbot:
    image: certbot/certbot:latest
    volumes:
      - letsencrypt:/etc/letsencrypt
      - certbot:/var/www/certbot
    # 12시간마다 자동 갱신
    entrypoint: |
      /bin/sh -c 'trap exit TERM; while :; do 
        certbot renew --webroot -w /var/www/certbot --quiet; 
        sleep 12h & wait $${!}; 
      done;'
```

## 🔄 자동 갱신 (Auto-Renewal)

Let's Encrypt 인증서는 **90일간 유효**하며, 갱신은 자동으로 진행됩니다.

### 갱신 상태 확인

```bash
# Certbot 로그 보기
docker-compose logs certbot

# 다음 갱신 예정일 확인
docker-compose exec certbot certbot certificates

# 수동 갱신 (테스트)
docker-compose exec certbot certbot renew --dry-run
```

### 갱신 실패 시 대응

```bash
# 1. Certbot 재시작
docker-compose restart certbot

# 2. 볼륨 확인
docker volume ls | grep letsencrypt

# 3. 수동 갱신 시도
docker-compose exec certbot certbot renew --force-renewal

# 4. 메일 확인 (만료 알림)
# Let's Encrypt는 만료 30일 전 이메일 발송
```

## 🧪 테스트 및 검증

### 1. 자동 테스트 실행

```bash
# 설정 검증
bash test-letsencrypt.sh

# 예상 결과:
# ✅ PASS: nginx/nginx.conf 존재
# ✅ PASS: HTTPS (443) 포트 설정 확인
# ✅ PASS: Let's Encrypt 경로 설정 확인
# ✅ PASS: Certbot 서비스 설정 확인
# ...
# 🎉 모든 설정 검증 완료!
```

### 2. 수동 테스트

```bash
# SSL 인증서 체인 확인
openssl s_client -connect your-domain.com:443 -showcerts

# 헤더 확인
curl -I https://your-domain.com
# Strict-Transport-Security: max-age=31536000
# X-Content-Type-Options: nosniff

# HTTP 리디렉션 확인
curl -I http://your-domain.com
# HTTP/1.1 301 Moved Permanently
# Location: https://your-domain.com
```

### 3. SSL/TLS 등급 검사

온라인 도구 사용:
- **Qualys SSL Labs**: https://www.ssllabs.com/ssltest/analyze.html
- **Mozilla Observatory**: https://observatory.mozilla.org/

예상 등급: **A+** 또는 **A**

## 🚨 문제 해결

### 문제 1: "Certificate not found"

```bash
# 원인: 인증서 아직 발급 안 됨
# 해결:
bash init-letsencrypt.sh your-domain.com your-email@example.com

# 또는 기존 인증서 확인:
docker volume inspect letsencrypt
```

### 문제 2: "ACME validation failed"

```bash
# 원인: 도메인 DNS가 잘못 설정됨
# 해결:
# 1. Route53 / DNS 설정 재확인
# 2. DNS 전파 대기 (최대 48시간)
# 3. nslookup your-domain.com 확인
```

### 문제 3: "Connection refused on port 443"

```bash
# 원인: 보안 그룹에서 443 포트 차단
# 해결: AWS EC2 보안 그룹 설정
# - Inbound: 443 HTTPS 허용
# - Inbound: 80 HTTP 허용
```

### 문제 4: "nginx: [emerg] BUS error"

```bash
# 원인: ARM64 호환성 문제
# 해결: docker-compose.yml에서 platform 확인
services:
  frontend:
    platform: linux/arm64

# 또는 재빌드:
docker-compose build --no-cache frontend
```

## 📊 모니터링

### 1. 로그 확인

```bash
# Nginx 액세스 로그
docker-compose logs frontend

# Certbot 갱신 로그
docker-compose logs certbot

# 모든 서비스 로그
docker-compose logs -f
```

### 2. 인증서 만료 확인

```bash
# 만료일 확인
openssl x509 -in letsencrypt/live/your-domain.com/cert.pem -noout -dates

# 또는
docker exec letsencrypt-certbot \
  openssl x509 -in /etc/letsencrypt/live/your-domain.com/cert.pem -noout -dates
```

### 3. 볼륨 상태 확인

```bash
# 볼륨 목록
docker volume ls

# 볼륨 상세 정보
docker volume inspect letsencrypt

# 인증서 파일 확인
docker run --rm -v letsencrypt:/etc/letsencrypt \
  alpine ls -la /etc/letsencrypt/live/
```

## 🔐 보안 모범 사례

### 1. HSTS (HTTP Strict Transport Security)

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
```

### 2. 보안 헤더

```nginx
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

### 3. SSL/TLS 설정

- ✅ TLS 1.2 이상만 사용
- ✅ 강력한 암호화 스위트 사용
- ✅ 세션 캐싱 활성화

### 4. 정기 갱신 확인

- 📧 Let's Encrypt에서 자동 갱신 알림 이메일 수신
- 📝 월 1회 인증서 만료 확인
- 🔔 갱신 실패 알림 설정

## 📚 참고 자료

| 항목 | 링크 |
|------|------|
| **Let's Encrypt** | https://letsencrypt.org/ |
| **Certbot 문서** | https://certbot.eff.org/docs/ |
| **Nginx SSL** | https://nginx.org/en/docs/http/ngx_http_ssl_module.html |
| **AWS EC2 보안** | https://docs.aws.amazon.com/ec2/index.html |
| **OWASP TLS** | https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html |

## ✅ 체크리스트

배포 전에 다음을 확인하세요:

- [ ] 설정 검증 실행: `bash test-letsencrypt.sh`
- [ ] 도메인 DNS 설정 완료
- [ ] AWS 보안 그룹 (80, 443) 열림
- [ ] Elastic IP 할당
- [ ] 이메일 주소 확인 (갱신 알림용)
- [ ] init-letsencrypt.sh 실행 완료
- [ ] HTTPS 연결 테스트 성공
- [ ] SSL Labs A+ 등급 확인

## 🎯 다음 단계

1. **프로덕션 배포**
   ```bash
   bash init-letsencrypt.sh your-domain.com your-email@example.com
   docker-compose up -d
   ```

2. **모니터링 설정**
   - CloudWatch 알림
   - Let's Encrypt 만료 알림
   - Certbot 갱신 로그

3. **백업 설정**
   - 인증서 백업: `docker volume inspect letsencrypt`
   - 데이터베이스 백업: S3 또는 RDS

---

**최종 업데이트**: 2026-04-20
**생성자**: AI Assistant
**상태**: ✅ 프로덕션 준비 완료

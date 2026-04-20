# Stage 1: Node.js 빌드 환경
FROM node:20-alpine as builder
WORKDIR /app

# npm 의존성 설치 (package-lock.json이 있으면 사용, 없으면 무시)
COPY package.json package-lock.json* ./
RUN npm install && npm cache clean --force

# 소스 코드 복사 및 빌드
COPY . .
RUN npm run build

# Stage 2: Nginx 서빙 환경
FROM nginx:1.24-alpine
WORKDIR /usr/share/nginx/html

# 빌드된 dist 파일을 Nginx 서빙 경로로 복사
COPY --from=builder /app/dist .

# Nginx 설정 파일 복사 및 시작 스크립트
COPY nginx.conf /etc/nginx/nginx.conf.template
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Let's Encrypt 인증서 검증 디렉토리 생성
RUN mkdir -p /var/www/certbot

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# 포트 노출 (HTTP + HTTPS)
EXPOSE 80 443

# 시작 스크립트 실행
CMD ["/start.sh"]


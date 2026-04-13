# Stage 1: Node.js 빌드 환경
FROM node:20-alpine as builder
WORKDIR /app

# npm 의존성 설치
COPY package.json package-lock.json ./
RUN npm ci && npm cache clean --force

# 소스 코드 복사 및 빌드
COPY . .
RUN npm run build

# Stage 2: Nginx 서빙 환경
FROM nginx:1.24-alpine
WORKDIR /usr/share/nginx/html

# 빌드된 dist 파일을 Nginx 서빙 경로로 복사
COPY --from=builder /app/dist .

# Nginx 설정 파일 복사
COPY nginx.conf /etc/nginx/nginx.conf

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/api/health || exit 1

# 포트 노출 및 Nginx 시작
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]


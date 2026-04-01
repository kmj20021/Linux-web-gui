FROM node:20-alpine as builder
WORKDIR /app
COPY package.json ./
RUN npm install && npm cache clean --force
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
CMD ["sh", "-c", "echo 'Frontend build complete' && sleep infinity"]

# Ảnh giao diện web (Next.js standalone): bước build có đủ node_modules, ảnh chạy chỉ còn server.js + file đã trace.
# Build từ thư mục webapp: docker compose build web

FROM node:22-alpine AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
# Rewrite /api/* trong next.config được ghi cứng lúc build, nên địa chỉ backend trong mạng Docker phải có ở đây.
ARG API_URL=http://api:8080
ENV API_URL=${API_URL} NEXT_OUTPUT=standalone
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public
USER node
EXPOSE 3000
CMD ["node", "server.js"]

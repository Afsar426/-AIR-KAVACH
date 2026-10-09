FROM node:24-alpine AS build

WORKDIR /app

# Copy dependency manifest and install dependencies cleanly
COPY frontend/package*.json ./
RUN npm ci

# Copy frontend source code and build production assets
COPY frontend/ ./
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# Production static server stage
FROM nginx:alpine

# Copy built static distribution and nginx proxy configuration
COPY --from=build /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]

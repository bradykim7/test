# NGINX API Gateway Docker Configuration
# NGINX API 게이트웨이 Docker 구성

FROM nginx:1.25-alpine

# Install additional packages for enhanced functionality
# 향상된 기능을 위한 추가 패키지 설치
RUN apk add --no-cache \
    curl

# Copy NGINX configuration
# NGINX 구성 파일 복사
COPY nginx.conf /etc/nginx/nginx.conf

# Create directories for SSL certificates and logs
# SSL 인증서 및 로그를 위한 디렉토리 생성
RUN mkdir -p /etc/nginx/ssl /var/log/nginx

# Create self-signed SSL certificate for development
# 개발용 자체 서명 SSL 인증서 생성
RUN apk add --no-cache openssl && \
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/coupon.key \
    -out /etc/nginx/ssl/coupon.crt \
    -subj "/C=KR/ST=Seoul/L=Seoul/O=Coupon System/OU=Development/CN=api.coupon.example.com"

# Set proper permissions
# 적절한 권한 설정
RUN chmod 600 /etc/nginx/ssl/coupon.key && \
    chmod 644 /etc/nginx/ssl/coupon.crt

# Health check
# 헬스 체크
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Expose ports
# 포트 노출
EXPOSE 80 443

# Start NGINX
# NGINX 시작
CMD ["nginx", "-g", "daemon off;"]
# 1. 파이썬 3.12 이미지 사용
FROM python:3.12-slim

# 2. 필수 패키지 설치 (MySQL, ML 라이브러리용)
RUN apt-get update && apt-get install -y \
    build-essential \
    libmysqlclient-dev \
    pkg-config \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 3. 작업 디렉토리 설정
WORKDIR /app

# 4. 라이브러리 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install gunicorn

# 5. 전체 코드 복사
COPY . .

# 6. S3로 정적 파일 전송 (빌드 시점에 실행)
# 환경변수가 필요하므로 실행 시점에 처리하거나, 수동으로 한 번만 해주면 됩니다.

# 7. 실행 명령어
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "conf.wsgi:application"]
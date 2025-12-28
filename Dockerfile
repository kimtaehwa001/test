# 1. 파이썬 3.12 슬림 버전 사용 (가볍고 빠름)
FROM python:3.12-slim

# 2. 파이썬 관련 환경 변수 설정
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# [중요] 한글 깨짐 및 자모 분리 방지를 위한 로케일 설정
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

# 3. 리눅스 시스템 필수 패키지 설치
# default-libmysqlclient-dev: MySQL 연결용
# build-essential, pkg-config: 컴파일용
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 4. 작업 디렉토리 설정
WORKDIR /app

# 5. 라이브러리 설치 (캐시 활용을 위해 COPY를 먼저 함)
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install gunicorn

# 6. 전체 프로젝트 코드 복사
COPY . /app/

# 7. 서버 실행 (Gunicorn 사용)
# conf.wsgi:application 부분은 본인의 프로젝트 설정 폴더명에 맞게 확인하세요.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "conf.wsgi:application"]
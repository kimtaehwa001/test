FROM python:3.12-slim
ENV LANG C.UTF-8
RUN apt-get update && apt-get install -y build-essential default-libmysqlclient-dev pkg-config unzip
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install gunicorn
COPY . .

# [핵심 수정]
# --workers 1 : 메모리 점유율 최소화 (1GB RAM 전용)
# --timeout 120 : ML 계산 및 OpenAI 응답이 늦어도 서버가 끊기지 않음
# --preload : 메모리를 좀 더 효율적으로 사용
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "120", "--preload", "conf.wsgi:application"]
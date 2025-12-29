FROM python:3.12-slim
ENV LANG C.UTF-8
RUN apt-get update && apt-get install -y build-essential default-libmysqlclient-dev pkg-config unzip
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install gunicorn
COPY . .
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "conf.wsgi:application"]
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl \
    && rm -rf /var/lib/apt/lists/*

# نسخه ثابت پروژه فعلی
RUN git clone https://github.com/uxurx7rh7e7xr73uue73e8/ahbpanel.git /tmp/source \
    && cd /tmp/source \
    && git checkout f95c118169fd6c66e6e5b155a716cbdfc6e330c7 \
    && cp -a . /app/ \
    && rm -rf /app/.git

COPY pompnet_brand.py /app/pompnet_brand.py

RUN python /app/pompnet_brand.py

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]

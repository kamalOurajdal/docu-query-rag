FROM python:3.8-slim-bullseye

ENV PYTHONUNBUFFERED=1
WORKDIR /usr/src/app

RUN apt-get update && apt-get install unixodbc-dev -y && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

ENTRYPOINT ["gunicorn","application:app","--bind","0.0.0.0:5000"]

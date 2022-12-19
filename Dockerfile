FROM python:3.11.1-alpine

WORKDIR /var/log/script_logs
WORKDIR /usr/src/app

RUN apk add git libmagic
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
VOLUME /var/log/script_logs
VOLUME /usr/src/app
COPY rekibot.cfg .
COPY db ./db/
COPY rekibot.py .
CMD ananas rekibot.cfg

FROM python:3-alpine

WORKDIR /var/log/script_logs
WORKDIR /usr/src/app

RUN apk add git libmagic
RUN pip install --no-cache-dir Pybooru
RUN git clone https://github.com/chr-1x/ananas.git
RUN pip install --no-cache-dir ./ananas
RUN rm -rf ananas
VOLUME /var/log/script_logs
VOLUME /usr/src/app

COPY imagebots.cfg .
COPY db ./db/
COPY rekibot.py .
CMD ananas imagebots.cfg
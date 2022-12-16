#!/bin/bash
appdir=/opt/rekibot
logdir=/var/log/botlog

mkdir $logdir -p
mkdir $appdir -p

cp -r db $appdir/
cp imagebots.cfg $appdir
cp rekibot.cfg $appdir
cp rekibot.py $appdir
docker compose up -d

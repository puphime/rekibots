#!/bin/bash
appdir=/opt/rekibot
logdir=/var/log/botlog

mkdir $logdir -p
mkdir $appdir -p

cp -r db $appdir/
cp imagebots.cfg $appdir
cp rekibot.cfg $appdir
cp rekibot.py $appdir
docker build --tag rekibot . 
docker run -d -v $appdir:/usr/src/app -v $logdir:/var/log/script_logs --name imagebots rekibot ananas imagebots.cfg
docker run -d -v $appdir:/usr/src/app -v $logdir:/var/log/script_logs --name adminbots rekibot ananas rekibot.cfg
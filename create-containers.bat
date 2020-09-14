set appdir=C:\rekibot
set logdir=C:\botlogs
mkdir %logdir%
xcopy /I db %appdir%\db
xcopy imagebots.cfg %appdir%
xcopy rekibot.cfg %appdir%
xcopy rekibot.py %appdir%
docker build --tag rekibot . 
docker run -d -v %appdir%:/usr/src/app -v %logdir%:/var/log/script_logs --name imagebots rekibot ananas imagebots.cfg
docker run -d -v %appdir%:/usr/src/app -v %logdir%:/var/log/script_logs --name adminbots rekibot ananas rekibot.cfg
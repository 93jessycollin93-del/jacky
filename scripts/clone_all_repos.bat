@echo off
REM Clone all knowledge condenser repos to E:\superagent\condensers\
REM Run as: clone_all_repos.bat

SET BASE=E:\superagent\condensers
SET USER=93jessycollin93-del

IF NOT EXIST %BASE% mkdir %BASE%
cd /d %BASE%

echo Cloning all condenser repos...

FOR %%R IN (
  neutronknowledge signal-refiner express-purely neutron-core-stream
  remix-of-jackie-s-compass signal-sharpener mind-garden-explorer
  deep-cosmos-chat core-light-vault signal-weaver-23 signal-weaver-73
  apex-intelligence-hub density-weave-core calm-comprehension
  star-lingo-flux signal-star-compress neutron-dense-ideas signal67
  quiet-heart-signal tension-tamer relational-compass neutronstar
  bot-squad-dynamics fobccc telegram-proxy-guide jackie-core-keeper
  ocd-jacky-777 logbook-curator momentum-habit-tracker tikkerlive
  AI-Data-Analist 3D-globe jadelounge dakura bot-squad-dynamics
  clever-memory-bot veil-ops eru neweru jacky cyber-store
) DO (
  IF NOT EXIST %BASE%\%%R (
    echo Cloning %%R...
    git clone https://github.com/%USER%/%%R.git %BASE%\%%R
  ) ELSE (
    echo %%R already exists, pulling...
    cd /d %BASE%\%%R && git pull && cd /d %BASE%
  )
)

echo.
echo All repos cloned to %BASE%
echo Run: python E:\superagent\scripts\godzilla_dataset_downloader.py
pause

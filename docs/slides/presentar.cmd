@echo off
rem Abre las slides en una ventana propia de Edge: sin barras, a pantalla completa y con autoplay del video.
rem Es la ventana que captura la escena "Slides Vertiente" de OBS. Salir: Alt+F4.
set "EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE%" set "EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
start "" "%EDGE%" --user-data-dir="%LOCALAPPDATA%\vertiente-slides" --no-first-run --no-default-browser-check --autoplay-policy=no-user-gesture-required --start-fullscreen --app="%~dp0index.html#1"

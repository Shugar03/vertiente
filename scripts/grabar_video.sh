#!/usr/bin/env bash
# Video de demo (~25 s) a partir del dashboard: placa de título, placa de resultados y la reproducción en vivo.
# Uso: scripts/grabar_video.sh salida/practica/dashboard.html salida/practica/costo.json salida/demo.mp4
set -euo pipefail
DASH="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"; COSTO="$2"; OUT="$3"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
shot() { "$CHROME" --headless=new --disable-gpu --hide-scrollbars --blink-settings=preferredColorScheme=1 \
  --window-size=1280,900 --screenshot="$2" "$1" >/dev/null 2>&1; }
placa() { cat > "$TMP/p.html" <<HTML
<!doctype html><meta charset="utf-8"><body style="margin:0;height:100vh;display:grid;place-items:center;background:#f9f9f7;
font:20px/1.5 system-ui,sans-serif;color:#0b0b0b"><div style="max-width:900px">$1</div></body>
HTML
  shot "file://$TMP/p.html" "$2"; }
SEG=$(python3 -c "import json;print(json.load(open('$COSTO'))['segundos'])")
N=$(python3 -c "import json;print(json.load(open('$COSTO'))['comentarios_procesados'])")
placa "<h1 style='font-size:44px;margin:0'>Vertiente</h1><p style='color:#52514e'>Qué circula, desde cuándo y quién lo empuja.<br>La conversación misma es la etiqueta: las respuestas conectan los dos bandos de cada narrativa.<br>Una operación es repetición alineada: mismas cuentas, misma publicación, empujando lo mismo.</p>" "$TMP/a.png"
placa "<h2 style='margin:0 0 12px'>Un comando: <code>make entrega</code></h2><p style='font-size:28px;margin:0'><b>$N</b> comentarios en <b>$SEG s</b> · notebook sin GPU · USD 0 de IA</p><p style='font-size:28px'>Práctica: <b>53,76 / 55</b> puntos automáticos (línea base 17)</p><p style='color:#52514e'>Robusto ante datos sucios, menos volumen, otras semillas y sin respuestas.</p>" "$TMP/b.png"
NB=$(python3 -c "import re,json;h=open('$1').read();print(json.loads(re.search(r'const D = (.*?);\n', h).group(1))['n_bins'])")
for ((b=0; b<NB; b++)); do shot "file://$DASH#t=$b" "$TMP/f$(printf %03d $b).png"; done
ffmpeg -loglevel error -y -loop 1 -t 5 -i "$TMP/a.png" -loop 1 -t 5 -i "$TMP/b.png" \
  -framerate 5 -i "$TMP/f%03d.png" -loop 1 -t 4 -i "$TMP/f$(printf %03d $((NB-1))).png" \
  -filter_complex "[0:v]scale=1280:900,setsar=1,fps=25[a];[1:v]scale=1280:900,setsar=1,fps=25[b];[2:v]scale=1280:900,setsar=1,fps=25[c];[3:v]scale=1280:900,setsar=1,fps=25[d];[a][b][c][d]concat=n=4:v=1[v]" \
  -map "[v]" -c:v libx264 -pix_fmt yuv420p "$OUT"
echo "video -> $OUT"

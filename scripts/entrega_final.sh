#!/usr/bin/env bash
# Entrega final de punta a punta (viernes 13). Un solo comando: `make final`.
#
#   1. Espera a que el set final aparezca (en el repo del desafío o en datos/final/), revisando cada INTERVALO s.
#   2. Corre el pipeline -> entrega/ (solo los 4 archivos oficiales), valida, testea; dashboard y video -> demo/.
#   3. Commitea entrega/ (+ caché del LLM) y hace push.
#   4. Si PUBLICAR=1, pasa el repo a público (requisito excluyente al cierre).
#
# Variables: INTERVALO (default 300), NO_PUSH=1 (ensayo sin commit/push), PUBLICAR=1, FINAL=<dir con los CSV>.
set -euo pipefail
cd "$(dirname "$0")/.."

INTERVALO="${INTERVALO:-300}"
FINAL="${FINAL:-datos/final}"
log() { printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*"; }

hay_final() { [ -f "$FINAL/comentarios.csv.gz" ] || [ -f "$FINAL/comentarios.csv" ]; }

until hay_final; do
  if [ -d vendor/desafio/.git ]; then
    git -C vendor/desafio pull -q || log "no se pudo actualizar vendor/desafio (¿red?)"
    if [ -d vendor/desafio/datos/final ] && [ "$FINAL" = "datos/final" ]; then
      mkdir -p datos && ln -sfn ../vendor/desafio/datos/final datos/final
    fi
  fi
  hay_final && break
  log "set final todavía no publicado; reviso de nuevo en ${INTERVALO}s (Ctrl-C para cortar)"
  sleep "$INTERVALO"
done
log "set final encontrado en $FINAL"

[ -f .env ] && { set -a; . ./.env; set +a; }

log "pipeline -> entrega/"
uv run python -m radar run --datos "$FINAL" --salida entrega
uv run python scripts/check_entrega.py --datos "$FINAL" --entrega entrega
log "tests"
uv run pytest -q
log "dashboard"
mkdir -p demo
uv run python -m radar.demo --interim "interim/$(basename "$(cd "$FINAL" && pwd -P)")" --salida demo/dashboard.html
log "video de demo"
./scripts/grabar_video.sh demo/dashboard.html entrega/costo.json demo/demo.mp4 || log "no se pudo grabar el video (¿Chrome/ffmpeg?)"
cat entrega/costo.json

if [ "${NO_PUSH:-0}" = "1" ]; then
  log "NO_PUSH=1: ensayo terminado sin commit ni push"
  exit 0
fi

# entrega/ lleva SOLO los 4 archivos oficiales; dashboard y video van en demo/
git add entrega cache/llm demo
git commit -m "Entrega final: resultado del pipeline sobre el set final" || log "nada nuevo para commitear"
git push origin HEAD
log "push hecho: $(git rev-parse --short HEAD)"

if [ "${PUBLICAR:-0}" = "1" ]; then
  gh repo edit --visibility public --accept-visibility-change-consequences
  log "repo público"
else
  log "RECORDÁ: el repo debe ser público al cierre ->  PUBLICAR=1 make final  (o: make publicar)"
fi

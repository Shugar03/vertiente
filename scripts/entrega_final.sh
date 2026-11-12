#!/usr/bin/env bash
# Entrega final de punta a punta (viernes 13). Un solo comando: `make final`.
#
#   1. Espera a que el set final aparezca (en el repo del desafío o en datos/final/), revisando cada INTERVALO s.
#   2. Corre el pipeline -> entrega/ (solo los 4 archivos oficiales), valida, testea; dashboard y video -> demo/.
#   3. Commitea entrega/ (+ caché del LLM) y hace push a la rama que clona el jurado (main).
#   4. Pasa el repo a público y lo verifica (requisito excluyente al cierre). PUBLICAR=0 lo saltea.
#
# Los tests NO bloquean la entrega: si fallan se avisa, pero entrega/ (ya validada) se commitea y se pushea igual.
#
# Variables: INTERVALO (default 300), NO_PUSH=1 (ensayo sin commit/push), PUBLICAR=0 (no publicar),
#            RAMA_ENTREGA (default main), FINAL=<dir con los CSV>.
set -euo pipefail
cd "$(dirname "$0")/.."

INTERVALO="${INTERVALO:-300}"
FINAL="${FINAL:-datos/final}"
RAMA_ENTREGA="${RAMA_ENTREGA:-main}"
log() { printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*"; }

# El jurado clona la rama por defecto: desde otra rama o worktree la entrega no le llegaría. Se corta ANTES de esperar.
RAMA="$(git rev-parse --abbrev-ref HEAD)"
if [ "${NO_PUSH:-0}" != "1" ] && [ "$RAMA" != "$RAMA_ENTREGA" ]; then
  log "ERROR: estás en la rama '$RAMA', pero la entrega tiene que quedar en '$RAMA_ENTREGA'."
  log "       Corré:  git checkout $RAMA_ENTREGA && git pull   (o NO_PUSH=1 para un ensayo)"
  exit 1
fi

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
TESTS_OK=1
uv run pytest -q || { TESTS_OK=0; log "ADVERTENCIA: fallaron tests; la entrega ya pasó check_entrega y se sube igual"; }
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
# Si alguien del equipo pusheó mientras corría, traer sus cambios antes de subir (si no, el push se rechaza).
git pull --rebase -q origin "$RAMA_ENTREGA" || { log "ERROR: conflicto al traer origin/$RAMA_ENTREGA; resolvelo y hacé git push"; exit 1; }
git push origin "HEAD:$RAMA_ENTREGA"
log "push hecho a $RAMA_ENTREGA: $(git rev-parse --short HEAD)"

if [ "${PUBLICAR:-1}" = "1" ]; then
  gh repo edit --visibility public --accept-visibility-change-consequences || log "ERROR: no se pudo cambiar la visibilidad"
fi
VIS="$(gh repo view --json visibility -q .visibility 2>/dev/null || echo DESCONOCIDA)"
if [ "$VIS" = "PUBLIC" ]; then
  log "repo público: OK"
else
  log "ATENCIÓN: el repo NO figura como público (visibilidad: $VIS). Es requisito excluyente -> make publicar"
fi
[ "$TESTS_OK" = "1" ] || log "RECORDÁ: hubo tests fallando (la entrega se subió igual); revisalos con: make test"

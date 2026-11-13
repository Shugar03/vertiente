"""Carga amigable: arrastrar los CSV al navegador, correr el pipeline y ver el dashboard.

    python -m radar.app                  abre http://127.0.0.1:8765 en el navegador
    python -m radar.app --puerto 9000 --no-abrir

Solo la biblioteca estándar (http.server) + el pipeline existente: no agrega dependencias ni cambia la entrega
oficial (`make entrega` sigue siendo el camino del viernes). Escucha solo en 127.0.0.1.

Flujo: POST /api/lote -> PUT /api/subir/<lote>/<archivo> (cuerpo crudo, por archivo) -> POST /api/procesar/<lote>
       -> GET /api/estado/<lote> (sondeo) -> GET /r/<lote>/dashboard.html y los 4 archivos de la entrega.
Solo `comentarios.csv(.gz)` es obligatorio: si faltan `cuentas` o `publicaciones` se crean vacíos (sin cuentas no hay
antigüedad en el perfil de las operaciones; publicaciones no se usa más allá de la ingesta).
"""

from __future__ import annotations

import argparse
import gzip
import json
import logging
import os
import re
import threading
import time
import traceback
import webbrowser
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

log = logging.getLogger("radar.app")

RAIZ = Path(__file__).resolve().parents[1]
ARCHIVOS = {"comentarios", "cuentas", "publicaciones", "fuentes"}
COLUMNAS = {
    "comentarios": ["comentario_id", "publicacion_id", "cuenta_id", "fecha", "texto", "respuesta_a"],
    "cuentas": ["cuenta_id", "fecha_creacion"],
    "publicaciones": ["publicacion_id", "fecha"],
}
VACIOS = {"cuentas": "cuenta_id,usuario,fecha_creacion,seguidores,siguiendo\n",
          "publicaciones": "publicacion_id,fuente_id,fecha,titular\n"}
RESULTADOS = {"dashboard.html": "text/html; charset=utf-8", "comentarios.csv": "text/csv; charset=utf-8",
              "narrativas.csv": "text/csv; charset=utf-8", "cuentas.csv": "text/csv; charset=utf-8",
              "costo.json": "application/json; charset=utf-8"}
_NOMBRE = re.compile(r"^(comentarios|cuentas|publicaciones|fuentes)\.csv(\.gz)?$")
_LOTE = re.compile(r"^carga-\d{8}-\d{6}(-\d+)?$")
# Progreso: qué etapa empieza cuando termina la anterior (según los logs de cada módulo).
_SIGUIENTE = {"radar.stages.ingest": "Agrupando narrativas (embeddings: la primera vez tarda más)",
              "radar.stages.narrativas": "Detectando operaciones coordinadas",
              "radar.stages.coordinacion": "Escribiendo la entrega y el dashboard"}


class Cargas:
    """Estado de los lotes en memoria. Un solo procesamiento a la vez (el pipeline usa toda la máquina)."""

    def __init__(self, raiz: Path, correr=None):
        self.raiz = raiz
        self.estado: dict[str, dict] = {}
        self.ocupado = threading.Lock()
        self._mutex = threading.Lock()
        self.correr = correr or correr_pipeline

    def datos(self, lote: str) -> Path:
        return self.raiz / "datos" / "subidos" / lote

    def salida(self, lote: str) -> Path:
        return self.raiz / "salida" / lote

    def nuevo(self) -> str:
        with self._mutex:
            base = "carga-" + datetime.now().strftime("%Y%m%d-%H%M%S")
            lote, i = base, 1
            while lote in self.estado or self.datos(lote).exists():
                i += 1
                lote = f"{base}-{i}"
            self.datos(lote).mkdir(parents=True)
            self.estado[lote] = {"estado": "esperando", "etapa": "", "error": "", "segundos": 0.0}
            return lote

    def faltantes(self, lote: str) -> list[str]:
        """Errores de validación del lote (vacío = listo para procesar). Completa cuentas/publicaciones si faltan."""
        d = self.datos(lote)
        if not _archivo(d, "comentarios"):
            return ["Falta comentarios.csv (o .csv.gz): es el único archivo obligatorio."]
        errores = []
        for nombre, cols in COLUMNAS.items():
            p = _archivo(d, nombre)
            if p is None:
                (d / f"{nombre}.csv").write_text(VACIOS[nombre], encoding="utf-8")
                continue
            try:
                encabezado = _encabezado(p)
            except (OSError, UnicodeDecodeError, EOFError) as e:
                errores.append(f"{p.name}: no se pudo leer ({e.__class__.__name__}). ¿Es un CSV en UTF-8?")
                continue
            faltan = [c for c in cols if c not in encabezado]
            if faltan:
                errores.append(f"{p.name}: faltan las columnas {', '.join(faltan)} (tiene: {', '.join(encabezado)})")
        return errores

    def procesar(self, lote: str) -> None:
        st = self.estado[lote]
        st.update(estado="procesando", etapa="Leyendo y limpiando los comentarios", error="")
        t0 = time.perf_counter()
        etapas = _Etapas(st)
        logging.getLogger("radar").addHandler(etapas)
        try:
            resumen = self.correr(self.datos(lote), self.salida(lote))
            st.update(estado="listo", etapa="Listo", resumen=resumen)
        except Exception as e:  # noqa: BLE001 - cualquier falla se muestra en la página, no tira el servidor
            log.error("falló el lote %s:\n%s", lote, traceback.format_exc())
            st.update(estado="error", error=f"{e.__class__.__name__}: {e}")
        finally:
            logging.getLogger("radar").removeHandler(etapas)
            st["segundos"] = round(time.perf_counter() - t0, 1)
            self.ocupado.release()


class _Etapas(logging.Handler):
    def __init__(self, st: dict):
        super().__init__(logging.INFO)
        self.st = st

    def emit(self, record: logging.LogRecord) -> None:
        if record.name in _SIGUIENTE:
            self.st["etapa"] = _SIGUIENTE[record.name]


def _archivo(d: Path, nombre: str) -> Path | None:
    for p in (d / f"{nombre}.csv.gz", d / f"{nombre}.csv"):
        if p.exists():
            return p
    return None


def _encabezado(p: Path) -> list[str]:
    abrir = gzip.open if p.suffix == ".gz" else open
    with abrir(p, "rt", encoding="utf-8-sig", newline="") as f:
        return [c.strip().strip('"') for c in f.readline().strip().split(",")]


def correr_pipeline(datos: Path, salida: Path) -> dict:
    """El mismo pipeline que `python -m radar run` + el dashboard. Devuelve un resumen para la página."""
    from radar import cli, demo

    config = yaml.safe_load((RAIZ / "config.yaml").read_text(encoding="utf-8"))
    etapas = cli.run(datos, salida, config)
    interim = Path(config["interim_dir"]) / datos.resolve().name
    (salida / "dashboard.html").write_text(demo.render(demo.datos(interim)), encoding="utf-8")
    return {"comentarios": etapas["costo"]["comentarios_procesados"], "segundos": etapas["costo"]["segundos"],
            "narrativas": etapas["narrativas"]["narrativas"], "operaciones": etapas["coordinacion"]["operaciones"],
            "cuentas_marcadas": etapas["coordinacion"]["cuentas_marcadas"]}


def crear_handler(cargas: Cargas):
    class Handler(BaseHTTPRequestHandler):
        server_version = "Vertiente"

        def log_message(self, fmt, *args):  # logs del servidor al logger, sin ensuciar la consola
            log.debug(fmt, *args)

        def _json(self, codigo: int, cuerpo: dict) -> None:
            datos = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)

        def _partes(self) -> list[str]:
            return [p for p in self.path.split("?")[0].split("/") if p]

        def _lote(self, lote: str) -> bool:
            if _LOTE.match(lote) and lote in cargas.estado:
                return True
            self._json(404, {"error": "lote desconocido"})
            return False

        def do_GET(self):  # noqa: N802
            p = self._partes()
            if not p:
                datos = PAGINA.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(datos)))
                self.end_headers()
                self.wfile.write(datos)
            elif len(p) == 3 and p[:2] == ["api", "estado"] and self._lote(p[2]):
                self._json(200, cargas.estado[p[2]])
            elif len(p) == 3 and p[0] == "r" and p[2] in RESULTADOS and self._lote(p[1]):
                archivo = cargas.salida(p[1]) / p[2]
                if not archivo.exists():
                    return self._json(404, {"error": "todavía no está"})
                self.send_response(200)
                self.send_header("Content-Type", RESULTADOS[p[2]])
                self.send_header("Content-Length", str(archivo.stat().st_size))
                if p[2] != "dashboard.html":
                    self.send_header("Content-Disposition", f'attachment; filename="{p[2]}"')
                self.end_headers()
                with archivo.open("rb") as f:
                    while bloque := f.read(1 << 20):
                        self.wfile.write(bloque)
            else:
                self._json(404, {"error": "no encontrado"})

        def do_POST(self):  # noqa: N802
            p = self._partes()
            if p == ["api", "lote"]:
                return self._json(200, {"lote": cargas.nuevo()})
            if len(p) == 3 and p[:2] == ["api", "procesar"] and self._lote(p[2]):
                errores = cargas.faltantes(p[2])
                if errores:
                    return self._json(400, {"error": " ".join(errores)})
                if not cargas.ocupado.acquire(blocking=False):
                    return self._json(409, {"error": "Ya hay un procesamiento en curso; esperá a que termine."})
                threading.Thread(target=cargas.procesar, args=(p[2],), daemon=True).start()
                return self._json(202, {"ok": True})
            self._json(404, {"error": "no encontrado"})

        def _descartar_cuerpo(self) -> None:
            """Leer (y tirar) el cuerpo antes de responder un error: si no, el cliente recibe un reset de conexión."""
            try:
                restante = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return
            while restante > 0 and (bloque := self.rfile.read(min(restante, 1 << 20))):
                restante -= len(bloque)

        def do_PUT(self):  # noqa: N802
            p = self._partes()
            if not (len(p) == 4 and p[:2] == ["api", "subir"]):
                self._descartar_cuerpo()
                return self._json(404, {"error": "no encontrado"})
            if not (_LOTE.match(p[2]) and p[2] in cargas.estado):
                self._descartar_cuerpo()
                return self._json(404, {"error": "lote desconocido"})
            if not _NOMBRE.match(p[3]):
                self._descartar_cuerpo()
                return self._json(400, {"error": f"archivo no esperado: {p[3]}"})
            if cargas.estado[p[2]]["estado"] != "esperando":
                self._descartar_cuerpo()
                return self._json(409, {"error": "ese lote ya se procesó; empezá una carga nueva"})
            try:
                restante = int(self.headers.get("Content-Length", ""))
            except ValueError:
                return self._json(411, {"error": "falta Content-Length"})
            d = cargas.datos(p[2])
            nombre = p[3].split(".")[0]
            for viejo in (d / f"{nombre}.csv", d / f"{nombre}.csv.gz"):  # reemplazar si se vuelve a soltar
                viejo.unlink(missing_ok=True)
            with (d / p[3]).open("wb") as f:
                while restante > 0:
                    bloque = self.rfile.read(min(restante, 1 << 20))
                    if not bloque:
                        break
                    f.write(bloque)
                    restante -= len(bloque)
            self._json(200, {"ok": True, "archivo": p[3]})

    return Handler


def main() -> None:
    ap = argparse.ArgumentParser(prog="radar.app", description="Carga de comentarios por arrastre + dashboard")
    ap.add_argument("--puerto", type=int, default=8765)
    ap.add_argument("--no-abrir", action="store_true", help="no abrir el navegador")
    a = ap.parse_args()
    os.chdir(RAIZ)  # config.yaml usa rutas relativas (interim/, caché de embeddings)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    servidor = ThreadingHTTPServer(("127.0.0.1", a.puerto), crear_handler(Cargas(RAIZ)))
    url = f"http://127.0.0.1:{a.puerto}/"
    print(f"Vertiente: abrí {url}  (Ctrl+C para cortar)", flush=True)
    if not a.no_abrir:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()


PAGINA = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vertiente · cargar comentarios</title>
<style>
:root {
  color-scheme: light;
  --page: #f9f9f7; --surface: #fcfcfb; --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
  --grid: #e1e0d9; --axis: #c3c2b7; --ring: rgba(11,11,11,0.10);
  --accent: #2a78d6; --ok: #1f8a4c; --critical: #d03b3b;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --axis: #383835; --ring: rgba(255,255,255,0.10);
    --accent: #3987e5; --ok: #3fb070; --critical: #e35d5d;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --page: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
  --grid: #2c2c2a; --axis: #383835; --ring: rgba(255,255,255,0.10);
  --accent: #3987e5; --ok: #3fb070; --critical: #e35d5d;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); color: var(--ink); font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 720px; margin: 0 auto; padding: 40px 16px 64px; }
h1 { font-size: 24px; margin: 0 0 4px; }
.sub { color: var(--ink-2); margin: 0 0 24px; }
#zona { display: block; border: 2px dashed var(--axis); border-radius: 14px; background: var(--surface); padding: 40px 20px;
        text-align: center; cursor: pointer; transition: border-color .15s, background .15s; }
#zona.encima { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 8%, var(--surface)); }
#zona strong { display: block; font-size: 17px; margin-bottom: 4px; }
#zona span { color: var(--ink-2); font-size: 13px; }
ul { list-style: none; padding: 0; margin: 20px 0; display: grid; gap: 8px; }
li { display: flex; justify-content: space-between; gap: 12px; background: var(--surface); border: 1px solid var(--ring);
     border-radius: 10px; padding: 10px 14px; }
li .n { font-weight: 600; }
li .d { color: var(--ink-2); font-size: 13px; text-align: right; }
li.falta .n { color: var(--muted); font-weight: 400; }
li.ok .d::before { content: "✓ "; color: var(--ok); }
button { font: inherit; font-weight: 600; color: #fff; background: var(--accent); border: 0; border-radius: 10px; padding: 12px 20px;
         cursor: pointer; width: 100%; }
button:disabled { opacity: .45; cursor: default; }
button.sec { background: var(--surface); color: var(--ink); border: 1px solid var(--ring); font-weight: 400; }
#progreso { margin-top: 24px; display: none; }
.barra { height: 8px; border-radius: 4px; background: var(--grid); overflow: hidden; }
.barra div { height: 100%; width: 30%; background: var(--accent); border-radius: 4px; animation: ir 1.4s ease-in-out infinite; }
@keyframes ir { 0% { margin-left: -30%; } 100% { margin-left: 100%; } }
#etapa { margin: 10px 0 0; color: var(--ink-2); }
#error { display: none; margin-top: 20px; padding: 12px 14px; border-radius: 10px; color: var(--critical);
         border: 1px solid color-mix(in srgb, var(--critical) 40%, transparent); background: var(--surface); }
#listo { display: none; margin-top: 24px; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin-bottom: 16px; }
.tile { background: var(--surface); border: 1px solid var(--ring); border-radius: 10px; padding: 12px 14px; }
.tile .v { font-size: 22px; font-weight: 600; }
.tile .k { color: var(--ink-2); font-size: 12px; }
.acciones { display: grid; gap: 10px; }
.acciones a.boton { display: block; text-align: center; text-decoration: none; font-weight: 600; color: #fff;
                    background: var(--accent); border-radius: 10px; padding: 12px 20px; }
.descargas { color: var(--ink-2); font-size: 13px; text-align: center; }
.descargas a { color: var(--accent); margin: 0 6px; }
.ayuda { color: var(--muted); font-size: 13px; margin-top: 28px; }
code { font-size: 12px; background: var(--grid); padding: 1px 5px; border-radius: 4px; }
</style>
</head>
<body>
<main>
  <h1>Vertiente · cargar comentarios</h1>
  <p class="sub">Arrastrá los CSV y Vertiente te muestra qué circula, desde cuándo y quién lo empuja.</p>

  <label id="zona">
    <input id="input" type="file" multiple accept=".csv,.gz" hidden>
    <strong>Soltá acá los archivos</strong>
    <span>o hacé click para elegirlos · <code>.csv</code> o <code>.csv.gz</code></span>
  </label>

  <ul id="lista"></ul>
  <button id="procesar" disabled>Procesar</button>

  <div id="progreso">
    <div class="barra"><div></div></div>
    <p id="etapa"></p>
  </div>
  <div id="error" role="alert"></div>

  <div id="listo">
    <div class="tiles" id="tiles"></div>
    <div class="acciones">
      <a class="boton" id="ver" target="_blank" rel="noopener">Ver el dashboard</a>
      <p class="descargas" id="descargas"></p>
      <button class="sec" id="otra">Cargar otros archivos</button>
    </div>
  </div>

  <p class="ayuda">Obligatorio: <code>comentarios</code> (comentario_id, publicacion_id, cuenta_id, fecha, texto, respuesta_a).
  Opcionales: <code>cuentas</code> (agrega la antigüedad de las cuentas) y <code>publicaciones</code>.
  Todo se procesa en esta computadora; nada sale a internet.</p>
</main>
<script>
const $ = (s) => document.querySelector(s);
const TIPOS = [["comentarios", "obligatorio"], ["cuentas", "opcional"], ["publicaciones", "opcional"]];
let elegidos = {};
let lote = null;

function tipo(nombre) {
  const n = nombre.toLowerCase();
  if (!/\.csv(\.gz)?$/.test(n)) return null;
  for (const t of ["comentarios", "cuentas", "publicaciones", "fuentes"]) if (n.startsWith(t)) return t;
  return null;
}
function tamano(b) { return b > 1e6 ? (b / 1e6).toFixed(1) + " MB" : Math.max(1, Math.round(b / 1e3)) + " KB"; }
function error(msg) { const e = $("#error"); e.textContent = msg; e.style.display = msg ? "block" : "none"; }

function pintar() {
  $("#lista").innerHTML = TIPOS.map(([t, req]) => {
    const f = elegidos[t];
    return f ? `<li class="ok"><span class="n">${t}</span><span class="d">${f.name} · ${tamano(f.size)}</span></li>`
             : `<li class="falta"><span class="n">${t}</span><span class="d">${req}</span></li>`;
  }).join("");
  $("#procesar").disabled = !elegidos.comentarios;
}

function agregar(files) {
  error("");
  const ignorados = [];
  for (const f of files) {
    const t = tipo(f.name);
    if (t) elegidos[t] = f; else ignorados.push(f.name);
  }
  if (ignorados.length) error("No reconocí: " + ignorados.join(", ") + ". Los nombres tienen que empezar con comentarios, cuentas o publicaciones.");
  pintar();
}

const zona = $("#zona");
["dragenter", "dragover"].forEach(ev => zona.addEventListener(ev, e => { e.preventDefault(); zona.classList.add("encima"); }));
["dragleave", "drop"].forEach(ev => zona.addEventListener(ev, e => { e.preventDefault(); zona.classList.remove("encima"); }));
zona.addEventListener("drop", e => agregar(e.dataTransfer.files));
$("#input").addEventListener("change", e => agregar(e.target.files));
window.addEventListener("dragover", e => e.preventDefault());
window.addEventListener("drop", e => e.preventDefault());

async function api(metodo, url, cuerpo) {
  const r = await fetch(url, { method: metodo, body: cuerpo });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || ("Error " + r.status));
  return j;
}

$("#procesar").addEventListener("click", async () => {
  error("");
  $("#procesar").disabled = true;
  zona.style.pointerEvents = "none";
  $("#progreso").style.display = "block";
  try {
    lote = (await api("POST", "/api/lote")).lote;
    for (const [t, f] of Object.entries(elegidos)) {
      $("#etapa").textContent = `Subiendo ${f.name}…`;
      const ext = f.name.toLowerCase().endsWith(".gz") ? ".csv.gz" : ".csv";
      await api("PUT", `/api/subir/${lote}/${t}${ext}`, f);
    }
    await api("POST", `/api/procesar/${lote}`);
    seguir();
  } catch (e) { fallo(e.message); }
});

function fallo(msg) {
  $("#progreso").style.display = "none";
  error(msg);
  $("#procesar").disabled = !elegidos.comentarios;
  zona.style.pointerEvents = "";
}

async function seguir() {
  const t0 = Date.now();
  while (true) {
    let st;
    try { st = await api("GET", `/api/estado/${lote}`); } catch (e) { return fallo(e.message); }
    if (st.estado === "error") return fallo("El procesamiento falló: " + st.error);
    if (st.estado === "listo") return terminado(st);
    $("#etapa").textContent = `${st.etapa}… ${Math.round((Date.now() - t0) / 1000)} s`;
    await new Promise(r => setTimeout(r, 1000));
  }
}

function terminado(st) {
  ["#progreso", "#procesar", "#zona", "#lista"].forEach(s => $(s).style.display = "none");
  const r = st.resumen;
  const fmt = (n) => n.toLocaleString("es-AR");
  $("#tiles").innerHTML = [[fmt(r.comentarios), "comentarios"], [r.narrativas, "narrativas"],
    [r.operaciones, "operaciones"], [r.cuentas_marcadas, "cuentas marcadas"], [st.segundos + " s", "tiempo total"]]
    .map(([v, k]) => `<div class="tile"><div class="v">${v}</div><div class="k">${k}</div></div>`).join("");
  $("#ver").href = `/r/${lote}/dashboard.html`;
  $("#descargas").innerHTML = "Descargar la entrega: " +
    ["comentarios.csv", "narrativas.csv", "cuentas.csv", "costo.json"].map(a => `<a href="/r/${lote}/${a}">${a}</a>`).join("");
  $("#listo").style.display = "block";
}

$("#otra").addEventListener("click", () => location.reload());
pintar();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()

"""Dashboard estático autocontenido (un solo HTML, sin internet) a partir de la última corrida.

    python -m radar.demo --interim interim/practica --salida salida/practica/dashboard.html

Responde en un minuto: qué circula (narrativas y su postura en el tiempo), desde cuándo (origen, emergentes) y
quién lo empuja (operaciones coordinadas). Incluye un modo "en vivo" que reproduce el período con alertas.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

TZ = "America/Argentina/Buenos_Aires"
BIN_H = 6


def datos(interim: Path) -> dict:
    c = pd.read_parquet(interim / "comentarios.parquet", columns=["comentario_id", "ts"])
    a = pd.read_parquet(interim / "narrativas_asig.parquet", columns=["comentario_id", "narrativa", "postura"])
    meta = pd.read_parquet(interim / "narrativas_meta.parquet")
    ops = pd.read_parquet(interim / "operaciones_meta.parquet")
    reporte = json.loads((interim / "reporte.json").read_text(encoding="utf-8")) if (interim / "reporte.json").exists() else {}

    d = c.merge(a, on="comentario_id")
    d = d[d["ts"].notna()]
    d["ts"] = pd.to_datetime(d["ts"], utc=True).dt.tz_convert(TZ)
    t0 = d["ts"].min().floor("D")
    t1 = d["ts"].max().ceil("D")
    n_bins = int((t1 - t0) / pd.Timedelta(hours=BIN_H))
    d["bin"] = ((d["ts"] - t0) / pd.Timedelta(hours=BIN_H)).astype(int).clip(0, n_bins - 1)
    serie = d[d["narrativa"] != ""].groupby(["narrativa", "postura", "bin"]).size()

    empujada = {r.narrativa: r for r in ops.itertuples()} if len(ops) else {}
    narrativas = []
    for r in meta.itertuples():
        origen = pd.Timestamp(r.fecha_origen).tz_convert(TZ)
        op = empujada.get(r.narrativa)
        narrativas.append({
            "id": r.narrativa, "titulo": r.titulo, "claves": r.frases_clave.split("|") if r.frases_clave else [],
            "origen": origen.isoformat(), "origen_bin": int((origen - t0) / pd.Timedelta(hours=BIN_H)),
            "emergente": bool(origen - t0 > pd.Timedelta(hours=24)),
            "apoya": int(r.apoya), "rechaza": int(r.rechaza),
            "s_apoya": [int(serie.get((r.narrativa, "apoya", b), 0)) for b in range(n_bins)],
            "s_rechaza": [int(serie.get((r.narrativa, "rechaza", b), 0)) for b in range(n_bins)],
            "operacion": None if op is None else {"id": op.grupo, "postura": op.postura},
        })
    operaciones = [{
        "id": o.grupo, "cuentas": int(o.cuentas), "comentarios": int(o.comentarios), "narrativa": o.narrativa,
        "postura": o.postura, "foco": float(o.foco), "antiguedad": None if pd.isna(o.antiguedad_mediana_dias) else float(o.antiguedad_mediana_dias),
        "nocturna": float(o.frac_nocturna),
        "inicio": pd.Timestamp(o.primera_actividad).tz_convert(TZ).isoformat(),
        "inicio_bin": int((pd.Timestamp(o.primera_actividad).tz_convert(TZ) - t0) / pd.Timedelta(hours=BIN_H)),
    } for o in ops.itertuples()] if len(ops) else []

    titulo_de = {n["id"]: n["titulo"] for n in narrativas}
    alertas = [{"bin": n["origen_bin"], "ts": n["origen"], "tipo": "Narrativa emergente",
                "texto": f"{n['id']} · «{n['titulo']}»"} for n in narrativas if n["emergente"]]
    alertas += [{"bin": o["inicio_bin"], "ts": o["inicio"], "tipo": "Operación coordinada",
                 "texto": f"{o['id']} · {o['cuentas']} cuentas empujan {o['narrativa']} ({o['postura']}) "
                          f"«{titulo_de.get(o['narrativa'], '')}»"} for o in operaciones]
    alertas.sort(key=lambda x: x["ts"])

    total = len(c)
    ruido = int((a["narrativa"] == "").sum())
    costo = reporte.get("costo", {})
    return {
        "inicio": t0.isoformat(), "bin_h": BIN_H, "n_bins": n_bins,
        "resumen": {"comentarios": total, "narrativas": len(narrativas), "ruido_pct": round(100 * ruido / max(total, 1), 1),
                    "operaciones": len(operaciones), "cuentas_coordinadas": int(sum(o["cuentas"] for o in operaciones)),
                    "segundos": costo.get("segundos"), "usd_mil": costo.get("usd_por_mil_comentarios", 0.0)},
        "narrativas": narrativas, "operaciones": operaciones, "alertas": alertas,
    }


def render(info: dict) -> str:
    return _PLANTILLA.replace("__DATOS__", json.dumps(info, ensure_ascii=False).replace("</", "<\\/"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interim", type=Path, required=True)
    ap.add_argument("--salida", type=Path, required=True)
    a = ap.parse_args()
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    a.salida.write_text(render(datos(a.interim)), encoding="utf-8")
    print(f"dashboard -> {a.salida}")


_PLANTILLA = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Radar de narrativas</title>
<style>
:root {
  color-scheme: light;
  --page: #f9f9f7; --surface: #fcfcfb; --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
  --grid: #e1e0d9; --axis: #c3c2b7; --ring: rgba(11,11,11,0.10);
  --apoya: #2a78d6; --rechaza: #eb6834; --critical: #d03b3b; --warning: #fab219;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) {
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --axis: #383835; --ring: rgba(255,255,255,0.10);
    --apoya: #3987e5; --rechaza: #d95926;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --page: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
  --grid: #2c2c2a; --axis: #383835; --ring: rgba(255,255,255,0.10);
  --apoya: #3987e5; --rechaza: #d95926;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); color: var(--ink); font: 14px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 1180px; margin: 0 auto; padding: 24px 16px 64px; }
h1 { font-size: 22px; margin: 0 0 4px; }
h2 { font-size: 16px; margin: 32px 0 12px; }
.sub { color: var(--ink-2); margin: 0 0 20px; }
.barra { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 16px; }
button { font: inherit; color: var(--ink); background: var(--surface); border: 1px solid var(--ring); border-radius: 8px; padding: 6px 12px; cursor: pointer; }
button:hover { border-color: var(--axis); }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
.tile { background: var(--surface); border: 1px solid var(--ring); border-radius: 10px; padding: 12px 14px; }
.tile .v { font-size: 24px; font-weight: 600; }
.tile .k { color: var(--ink-2); font-size: 12px; }
.leyenda { display: flex; gap: 16px; color: var(--ink-2); font-size: 13px; }
.sw { display: inline-block; width: 12px; height: 3px; border-radius: 2px; vertical-align: middle; margin-right: 6px; }
.grid2 { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; align-items: start; }
@media (max-width: 860px) { .grid2 { grid-template-columns: 1fr; } }
.narr { background: var(--surface); border: 1px solid var(--ring); border-radius: 10px; padding: 12px 14px; margin-bottom: 10px; }
.narr .cab { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.narr .t { font-weight: 600; }
.narr .meta { color: var(--ink-2); font-size: 12px; }
.chip { display: inline-block; font-size: 11px; border: 1px solid var(--ring); border-radius: 999px; padding: 1px 8px; margin: 4px 4px 0 0; color: var(--ink-2); }
.badge { display: inline-flex; gap: 4px; align-items: center; font-size: 12px; font-weight: 600; }
.badge.op::before { content: "⚑"; color: var(--critical); }
.badge.em::before { content: "▲"; color: var(--warning); }
svg { display: block; width: 100%; height: 84px; overflow: visible; margin: 6px 0 2px; }
.panel { background: var(--surface); border: 1px solid var(--ring); border-radius: 10px; padding: 12px 14px; }
.alerta { border-left: 3px solid var(--axis); padding: 6px 10px; margin-bottom: 8px; opacity: 1; transition: opacity .3s; }
.alerta.oculta { opacity: .25; }
.alerta .tp { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }
.alerta .tp.op { color: var(--ink); } .alerta .tp.op::before { content: "⚑ "; color: var(--critical); }
.alerta .tp.em { color: var(--ink); } .alerta .tp.em::before { content: "▲ "; color: var(--warning); }
.alerta .ts { color: var(--muted); font-size: 12px; font-variant-numeric: tabular-nums; }
.opcard { padding: 8px 0; border-bottom: 1px solid var(--grid); } .opcard:last-child { border-bottom: 0; }
.opcard .cab { display: flex; justify-content: space-between; gap: 8px; }
.opcard dl { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 12px; margin: 8px 0 0; }
.opcard dt { color: var(--ink-2); font-size: 11px; } .opcard dd { margin: 0; font-weight: 600; font-variant-numeric: tabular-nums; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--grid); }
th { color: var(--ink-2); font-weight: 600; }
td.n { text-align: right; font-variant-numeric: tabular-nums; }
#tip { position: fixed; pointer-events: none; background: var(--surface); color: var(--ink); border: 1px solid var(--ring); border-radius: 8px; padding: 6px 8px; font-size: 12px; box-shadow: 0 4px 16px rgba(0,0,0,.12); display: none; z-index: 10; }
.reloj { font-variant-numeric: tabular-nums; color: var(--ink-2); }
</style>
</head>
<body>
<main>
  <h1>Radar de narrativas</h1>
  <p class="sub">Qué circula, desde cuándo y quién lo empuja. Datos sintéticos del desafío QualyData · Argentina Space 2026.</p>
  <div class="tiles" id="tiles"></div>

  <div class="grid2">
    <section>
      <h2>Qué circula</h2>
      <div class="barra">
        <span class="leyenda"><span><span class="sw" style="background:var(--apoya)"></span>Apoya (arriba)</span><span><span class="sw" style="background:var(--rechaza)"></span>Rechaza (abajo)</span><span>Comentarios cada 6 h</span></span>
        <span style="flex:1"></span>
        <button id="vivo">▶ Reproducir en vivo</button>
        <span class="reloj" id="reloj"></span>
        <button id="tema" aria-label="Cambiar tema">◐</button>
      </div>
      <div id="narrativas"></div>
    </section>
    <aside>
      <h2>Alertas</h2>
      <div class="panel" id="alertas"></div>
      <h2>Quién lo empuja</h2>
      <div class="panel" id="ops"></div>
    </aside>
  </div>
</main>
<div id="tip" role="status"></div>
<script>
const D = __DATOS__;
const $ = (s) => document.querySelector(s);
const fmt = new Intl.NumberFormat("es-AR");
const t0 = new Date(D.inicio).getTime();
const fecha = (b) => new Date(t0 + b * D.bin_h * 3600e3).toLocaleString("es-AR", {weekday: "short", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit"});
const hora = (iso) => new Date(iso).toLocaleString("es-AR", {weekday: "short", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit"});
const tituloDe = Object.fromEntries(D.narrativas.map(n => [n.id, n.titulo]));

// --- tiles
const R = D.resumen;
const tiles = [
  [fmt.format(R.comentarios), "comentarios procesados"], [R.narrativas, "narrativas detectadas"],
  [R.ruido_pct + "%", "ruido descartado"], [R.operaciones, "operaciones coordinadas"],
  [fmt.format(R.cuentas_coordinadas), "cuentas en operaciones"],
  [R.segundos != null ? R.segundos + " s" : "—", "tiempo total del pipeline"],
];
$("#tiles").innerHTML = tiles.map(([v, k]) => `<div class="tile"><div class="v">${v}</div><div class="k">${k}</div></div>`).join("");

// --- narrativas (small multiples, misma escala)
const ymax = Math.max(1, ...D.narrativas.flatMap(n => n.s_apoya.concat(n.s_rechaza)));
const W = 640, H = 84, PAD = 2, MID = H / 2;
const x = (b) => PAD + b * (W - 2 * PAD) / (D.n_bins - 1);
const arriba = (v) => MID - 1 - v * (MID - 4) / ymax;   // apoya hacia arriba
const abajo = (v) => MID + 1 + v * (MID - 4) / ymax;    // rechaza hacia abajo
const area = (s, f, base) => `M${x(0)},${base}` + s.map((v, i) => `L${x(i).toFixed(1)},${f(v).toFixed(1)}`).join("") + `L${x(s.length - 1)},${base}Z`;
const esc = (t) => String(t).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
$("#narrativas").innerHTML = D.narrativas.map((n, i) => `
  <div class="narr">
    <div class="cab">
      <div><span class="t">${esc(n.titulo)}</span> <span class="meta">${n.id}</span></div>
      <div>${n.emergente ? '<span class="badge em">Emergente</span> ' : ""}${n.operacion ? `<span class="badge op">Empujada por ${n.operacion.id}</span>` : ""}</div>
    </div>
    <div class="meta">Desde ${hora(n.origen)} · ${fmt.format(n.apoya)} apoyan · ${fmt.format(n.rechaza)} rechazan</div>
    <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" data-i="${i}" role="img" aria-label="Comentarios por ${D.bin_h} horas: ${esc(n.titulo)}">
      <path d="${area(n.s_apoya, arriba, MID - 1)}" fill="var(--apoya)" fill-opacity="0.85"/>
      <path d="${area(n.s_rechaza, abajo, MID + 1)}" fill="var(--rechaza)" fill-opacity="0.85"/>
      <line x1="0" x2="${W}" y1="${MID}" y2="${MID}" stroke="var(--surface)" stroke-width="2" vector-effect="non-scaling-stroke"/>
      <line class="origen" x1="${x(n.origen_bin)}" x2="${x(n.origen_bin)}" y1="0" y2="${H}" stroke="var(--muted)" stroke-dasharray="2 3" stroke-width="1" vector-effect="non-scaling-stroke"/>
      <line class="cursor" x1="0" x2="0" y1="0" y2="${H}" stroke="var(--ink-2)" stroke-width="1" vector-effect="non-scaling-stroke" visibility="hidden"/>
      <rect class="velo" x="0" y="0" width="0" height="${H}" fill="var(--surface)" opacity="0.85"/>
    </svg>
    <div>${n.claves.map(k => `<span class="chip">${esc(k)}</span>`).join("")}</div>
  </div>`).join("");

// --- tooltip con crosshair
const tip = $("#tip");
document.querySelectorAll("#narrativas svg").forEach(svg => {
  const n = D.narrativas[+svg.dataset.i];
  const cur = svg.querySelector(".cursor");
  svg.addEventListener("pointermove", (e) => {
    const r = svg.getBoundingClientRect();
    const b = Math.max(0, Math.min(D.n_bins - 1, Math.round((e.clientX - r.left) / r.width * (D.n_bins - 1))));
    cur.setAttribute("x1", x(b)); cur.setAttribute("x2", x(b)); cur.setAttribute("visibility", "visible");
    tip.style.display = "block"; tip.style.left = (e.clientX + 12) + "px"; tip.style.top = (e.clientY + 12) + "px";
    tip.innerHTML = `<b>${fecha(b)}</b><br><span class="sw" style="background:var(--apoya)"></span>Apoya ${n.s_apoya[b]}<br><span class="sw" style="background:var(--rechaza)"></span>Rechaza ${n.s_rechaza[b]}`;
  });
  svg.addEventListener("pointerleave", () => { tip.style.display = "none"; cur.setAttribute("visibility", "hidden"); });
});

// --- alertas y operaciones
$("#alertas").innerHTML = D.alertas.length ? D.alertas.map((a, i) => `
  <div class="alerta" data-bin="${a.bin}">
    <div class="tp ${a.tipo.startsWith("Op") ? "op" : "em"}">${a.tipo}</div>
    <div>${esc(a.texto)}</div><div class="ts">${hora(a.ts)}</div>
  </div>`).join("") : '<div class="meta">Sin alertas.</div>';
const antig = (d) => d == null ? "—" : (d < 60 ? Math.round(d) + " días" : (d / 365).toFixed(1) + " años");
$("#ops").innerHTML = D.operaciones.map(o => `
  <div class="opcard">
    <div class="cab"><span class="badge op">${o.id}</span><span class="meta">desde ${hora(o.inicio)}</span></div>
    <div>Empuja <b>«${esc(tituloDe[o.narrativa] || o.narrativa)}»</b> <span class="meta">(${o.postura})</span></div>
    <dl>
      <div><dt>Cuentas</dt><dd>${o.cuentas}</dd></div>
      <div><dt>Antigüedad mediana</dt><dd>${antig(o.antiguedad)}</dd></div>
      <div><dt>Actividad nocturna</dt><dd>${Math.round(o.nocturna * 100)}%</dd></div>
      <div><dt>Foco en esa narrativa</dt><dd>${Math.round(o.foco * 100)}%</dd></div>
    </dl>
  </div>`).join("") || '<div class="meta">No se detectaron operaciones.</div>';

// --- modo en vivo: el período completo en ~60 s
let timer = null;
function mostrarHasta(b) {
  document.querySelectorAll("#narrativas svg").forEach(svg => {
    const v = svg.querySelector(".velo"); v.setAttribute("x", x(b)); v.setAttribute("width", W - x(b) + 4);
  });
  document.querySelectorAll(".alerta").forEach(el => el.classList.toggle("oculta", +el.dataset.bin > b));
  $("#reloj").textContent = b >= D.n_bins - 1 ? "" : fecha(b);
}
$("#vivo").addEventListener("click", () => {
  if (timer) { clearInterval(timer); timer = null; mostrarHasta(D.n_bins - 1); $("#vivo").textContent = "▶ Reproducir en vivo"; return; }
  let b = 0; $("#vivo").textContent = "■ Detener";
  timer = setInterval(() => { mostrarHasta(b); if (++b >= D.n_bins) { clearInterval(timer); timer = null; mostrarHasta(D.n_bins - 1); $("#vivo").textContent = "▶ Reproducir en vivo"; } }, 60000 / D.n_bins);
});
// #t=<bloque>: fija el momento de la reproducción (lo usa la grabación del video)
const mt = location.hash.match(/t=(\d+)/);
if (mt) mostrarHasta(Math.min(+mt[1], D.n_bins - 1));
$("#tema").addEventListener("click", () => {
  const r = document.documentElement, oscuro = r.dataset.theme ? r.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  r.dataset.theme = oscuro ? "light" : "dark";
});
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()

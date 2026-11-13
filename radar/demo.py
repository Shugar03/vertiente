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
    reporte = json.loads((interim / "reporte.json").read_text()) if (interim / "reporte.json").exists() else {}

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
    alertas = [{"bin": n["origen_bin"], "ts": n["origen"], "tipo": "Narrativa emergente", "narrativa": n["id"],
                "texto": f"{n['id']} · «{n['titulo']}»"} for n in narrativas if n["emergente"]]
    alertas += [{"bin": o["inicio_bin"], "ts": o["inicio"], "tipo": "Operación coordinada", "narrativa": o["narrativa"],
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
<title>Vertiente · narrativas y coordinación</title>
<style>
:root {
  color-scheme: light;
  --page: #f6f5f1; --surface: #ffffff; --surface-2: #f1f0ea; --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
  --grid: #e6e5de; --axis: #c3c2b7; --ring: rgba(11,11,11,0.09); --shadow: 0 1px 2px rgba(11,11,11,.04), 0 4px 16px rgba(11,11,11,.04);
  --apoya: #2a78d6; --rechaza: #eb6834; --critical: #d03b3b; --warning: #e9a30c; --accent: #0b0b0b;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) {
    color-scheme: dark;
    --page: #0d0d0d; --surface: #171716; --surface-2: #1f1f1e; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
    --grid: #2a2a28; --axis: #3a3a37; --ring: rgba(255,255,255,0.09); --shadow: none;
    --apoya: #3987e5; --rechaza: #e0662f; --critical: #e5534b; --warning: #f2b42c; --accent: #f0efec;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --page: #0d0d0d; --surface: #171716; --surface-2: #1f1f1e; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
  --grid: #2a2a28; --axis: #3a3a37; --ring: rgba(255,255,255,0.09); --shadow: none;
  --apoya: #3987e5; --rechaza: #e0662f; --critical: #e5534b; --warning: #f2b42c; --accent: #f0efec;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; scroll-padding-top: 84px; }
body { margin: 0; background: var(--page); color: var(--ink); font: 14px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; -webkit-font-smoothing: antialiased; }
button, input, select { font: inherit; color: inherit; }
button { cursor: pointer; }
.num { font-variant-numeric: tabular-nums; }

/* --- encabezado */
.top { position: sticky; top: 0; z-index: 5; background: color-mix(in srgb, var(--page) 86%, transparent); backdrop-filter: blur(10px); border-bottom: 1px solid var(--ring); }
.top .in { max-width: 1240px; margin: 0 auto; padding: 12px 20px; display: flex; align-items: center; gap: 14px; }
.logo { width: 34px; height: 34px; border-radius: 9px; background: var(--accent); color: var(--page); display: grid; place-items: center; flex: none; }
.logo svg { width: 22px; height: 22px; }
.marca-t h1 { font-size: 16px; margin: 0; letter-spacing: -.01em; }
.marca-t p { margin: 0; color: var(--ink-2); font-size: 12px; }
.top .esp { flex: 1; }
.periodo { color: var(--ink-2); font-size: 12px; border: 1px solid var(--ring); border-radius: 999px; padding: 4px 10px; background: var(--surface); white-space: nowrap; }
.icono { width: 34px; height: 34px; border-radius: 9px; border: 1px solid var(--ring); background: var(--surface); display: grid; place-items: center; }
.icono:hover { border-color: var(--axis); }

main { max-width: 1240px; margin: 0 auto; padding: 22px 20px 64px; }
.card { background: var(--surface); border: 1px solid var(--ring); border-radius: 14px; box-shadow: var(--shadow); }
h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .06em; color: var(--ink-2); margin: 0; font-weight: 650; }
.sec-cab { display: flex; align-items: baseline; gap: 10px; margin: 0 0 12px; }
.sec-cab .cnt { color: var(--muted); font-size: 12px; }

/* --- KPIs */
.tiles { display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; margin-bottom: 16px; }
@media (max-width: 1060px) { .tiles { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 560px) { .tiles { grid-template-columns: repeat(2, 1fr); } }
.tile { padding: 14px 16px; position: relative; overflow: hidden; }
.tile .k { color: var(--ink-2); font-size: 12px; }
.tile .v { font-size: 26px; font-weight: 650; letter-spacing: -.02em; margin: 2px 0; font-variant-numeric: tabular-nums; }
.tile .s { color: var(--muted); font-size: 12px; }
.tile.critico::before { content: ""; position: absolute; inset: 0 auto 0 0; width: 3px; background: var(--critical); }
.tile.critico .v { color: var(--critical); }

/* --- panorama y reproductor */
.pano { padding: 16px 18px 14px; margin-bottom: 22px; }
.pano .sec-cab { justify-content: space-between; flex-wrap: wrap; }
.leyenda { display: flex; gap: 14px; color: var(--ink-2); font-size: 12px; flex-wrap: wrap; }
.sw { display: inline-block; width: 10px; height: 10px; border-radius: 3px; vertical-align: -1px; margin-right: 6px; }
.sw.l { width: 0; height: 12px; border-left: 2px dashed var(--muted); border-radius: 0; }
.lienzo { position: relative; }
.marcas { position: relative; height: 22px; }
.marca { position: absolute; top: 2px; width: 16px; height: 16px; border-radius: 50%; border: 2px solid var(--surface); padding: 0; transform: translateX(-50%); transition: opacity .25s, transform .15s; }
.marca:hover { transform: translateX(-50%) scale(1.25); }
.marca.op { background: var(--critical); }
.marca.em { background: var(--warning); }
.marca.oculta { opacity: .2; }
svg.pano-g { display: block; width: 100%; height: 150px; overflow: visible; }
.ejes { position: relative; height: 20px; margin-top: 4px; color: var(--muted); font-size: 11px; }
.ejes span { position: absolute; transform: translateX(-50%); white-space: nowrap; }
.player { display: flex; align-items: center; gap: 12px; margin-top: 10px; padding-top: 12px; border-top: 1px solid var(--grid); }
.play { display: inline-flex; align-items: center; gap: 8px; border: 0; border-radius: 999px; background: var(--accent); color: var(--page); padding: 7px 14px 7px 12px; font-weight: 600; font-size: 13px; }
.play svg { width: 12px; height: 12px; }
input[type=range] { flex: 1; accent-color: var(--accent); min-width: 80px; }
.reloj { color: var(--ink-2); font-size: 12px; min-width: 150px; text-align: right; font-variant-numeric: tabular-nums; }

/* --- layout principal */
.grid2 { display: grid; grid-template-columns: minmax(0, 1fr) 360px; gap: 22px; align-items: start; }
@media (max-width: 960px) { .grid2 { grid-template-columns: 1fr; } }
aside { display: grid; gap: 22px; }
@media (min-width: 961px) { aside { position: sticky; top: 78px; max-height: calc(100vh - 92px); overflow: auto; padding-right: 2px; } }

/* --- herramientas */
.herr { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 12px; }
.buscar { flex: 1; min-width: 180px; position: relative; }
.buscar input { width: 100%; padding: 8px 12px 8px 32px; border-radius: 10px; border: 1px solid var(--ring); background: var(--surface); outline: none; }
.buscar input:focus { border-color: var(--axis); box-shadow: 0 0 0 3px var(--ring); }
.buscar svg { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); width: 14px; height: 14px; color: var(--muted); }
.seg { display: inline-flex; background: var(--surface-2); border: 1px solid var(--ring); border-radius: 10px; padding: 2px; }
.seg button { border: 0; background: transparent; border-radius: 8px; padding: 5px 10px; font-size: 12px; color: var(--ink-2); }
.seg button[aria-pressed="true"] { background: var(--surface); color: var(--ink); box-shadow: 0 1px 2px rgba(0,0,0,.08); font-weight: 600; }
select { padding: 7px 10px; border-radius: 10px; border: 1px solid var(--ring); background: var(--surface); font-size: 12px; }

/* --- narrativas */
.narr { padding: 14px 16px 12px; margin-bottom: 10px; transition: border-color .2s, box-shadow .2s; }
.narr.sel { border-color: var(--accent); box-shadow: 0 0 0 3px var(--ring); }
.narr .cab { display: flex; gap: 12px; align-items: flex-start; }
.rank { flex: none; width: 28px; height: 28px; border-radius: 8px; background: var(--surface-2); color: var(--ink-2); display: grid; place-items: center; font-size: 12px; font-weight: 650; font-variant-numeric: tabular-nums; }
.narr .tt { flex: 1; min-width: 0; }
.narr h3 { font-size: 15px; margin: 0; line-height: 1.3; letter-spacing: -.01em; }
.meta { color: var(--ink-2); font-size: 12px; }
.badges { display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }
.badge { display: inline-flex; gap: 5px; align-items: center; font-size: 11px; font-weight: 650; border-radius: 999px; padding: 2px 8px; white-space: nowrap; }
.badge.op { color: var(--critical); background: color-mix(in srgb, var(--critical) 12%, transparent); }
.badge.em { color: color-mix(in srgb, var(--warning) 70%, var(--ink)); background: color-mix(in srgb, var(--warning) 16%, transparent); }
.badge::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.pol { margin: 10px 0 2px 40px; }
.pol .bar { display: flex; height: 6px; border-radius: 999px; overflow: hidden; background: var(--rechaza); }
.pol .bar span { background: var(--apoya); }
.pol .pl { display: flex; justify-content: space-between; font-size: 11px; color: var(--ink-2); margin-top: 4px; font-variant-numeric: tabular-nums; }
.pol .pl b { color: var(--ink); }
svg.serie { display: block; width: calc(100% - 40px); margin: 8px 0 4px 40px; height: 76px; overflow: visible; cursor: crosshair; }
.chips { margin-left: 40px; }
.chip { display: inline-block; font-size: 11px; background: var(--surface-2); border-radius: 6px; padding: 2px 7px; margin: 4px 4px 0 0; color: var(--ink-2); }
.vacio { padding: 28px; text-align: center; color: var(--muted); }

/* --- svg */
.pa { fill: var(--apoya); fill-opacity: .88; }
.pr { fill: var(--rechaza); fill-opacity: .88; }
.gl { stroke: var(--grid); stroke-width: 1; vector-effect: non-scaling-stroke; }
.mid { stroke: var(--surface); stroke-width: 2; vector-effect: non-scaling-stroke; }
.orig { stroke: var(--ink-2); stroke-dasharray: 2 3; stroke-width: 1; vector-effect: non-scaling-stroke; }
.cursor { stroke: var(--ink); stroke-width: 1; vector-effect: non-scaling-stroke; }
.cabezal { stroke: var(--accent); stroke-width: 1.5; vector-effect: non-scaling-stroke; }
.velo { fill: var(--surface); opacity: .82; }

/* --- alertas */
.panel { padding: 6px 6px; }
.alerta { display: grid; grid-template-columns: 14px 1fr; gap: 10px; width: 100%; text-align: left; border: 0; background: transparent; border-radius: 10px; padding: 9px 10px; transition: opacity .3s, background .15s; position: relative; }
.alerta:hover { background: var(--surface-2); }
.alerta .dot { width: 10px; height: 10px; border-radius: 50%; margin-top: 4px; }
.alerta.op .dot { background: var(--critical); box-shadow: 0 0 0 3px color-mix(in srgb, var(--critical) 18%, transparent); }
.alerta.em .dot { background: var(--warning); box-shadow: 0 0 0 3px color-mix(in srgb, var(--warning) 22%, transparent); }
.alerta .tp { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; display: flex; justify-content: space-between; gap: 8px; }
.alerta .tp .ts { color: var(--muted); font-weight: 500; text-transform: none; letter-spacing: 0; font-variant-numeric: tabular-nums; }
.alerta .tx { font-size: 13px; margin-top: 1px; }
.alerta.oculta { opacity: .28; }

/* --- operaciones */
.opcard { padding: 14px 16px; }
.opcard + .opcard { border-top: 1px solid var(--grid); }
.opcard .cab { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.opcard .id { font-weight: 700; font-size: 13px; display: inline-flex; align-items: center; gap: 6px; }
.opcard .id::before { content: ""; width: 8px; height: 8px; border-radius: 2px; background: var(--critical); }
.opcard .emp { margin: 6px 0 10px; font-size: 13px; }
.pill { font-size: 11px; font-weight: 600; border-radius: 999px; padding: 1px 7px; color: #fff; }
.pill.apoya { background: var(--apoya); } .pill.rechaza { background: var(--rechaza); }
.stats { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 14px; }
.stats dt { color: var(--muted); font-size: 11px; }
.stats dd { margin: 0; font-weight: 650; font-variant-numeric: tabular-nums; }
.medidor { height: 4px; border-radius: 999px; background: var(--surface-2); margin-top: 4px; overflow: hidden; }
.medidor span { display: block; height: 100%; background: var(--critical); border-radius: 999px; }
.ver { margin-top: 12px; width: 100%; border: 1px solid var(--ring); background: var(--surface-2); border-radius: 8px; padding: 6px; font-size: 12px; font-weight: 600; }
.ver:hover { border-color: var(--axis); }

footer { max-width: 1240px; margin: 0 auto; padding: 0 20px 32px; color: var(--muted); font-size: 12px; }
#tip { position: fixed; pointer-events: none; background: var(--surface); color: var(--ink); border: 1px solid var(--ring); border-radius: 10px; padding: 8px 10px; font-size: 12px; box-shadow: 0 8px 24px rgba(0,0,0,.14); display: none; z-index: 20; min-width: 140px; }
#tip b { display: block; margin-bottom: 4px; }
#tip .f { display: flex; justify-content: space-between; gap: 12px; font-variant-numeric: tabular-nums; }
.grid2 > * { min-width: 0; }
@media (max-width: 760px) {
  body { overflow-x: hidden; }
  .periodo, .marca-t p { display: none; }
  .ejes span:nth-child(even) { display: none; }
  .reloj { min-width: 0; }
  .herr .buscar { flex-basis: 100%; }
  .pol, .chips { margin-left: 0; }
  svg.serie { width: 100%; margin-left: 0; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } html { scroll-behavior: auto; } }
</style>
</head>
<body>
<header class="top">
  <div class="in">
    <div class="logo" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2.5c-2.6 3.3-5 6.2-5 9a5 5 0 0 0 10 0c0-2.8-2.4-5.7-5-9z" fill="currentColor"/><path d="M3 19.5c1.5 0 1.5-1 3-1s1.5 1 3 1 1.5-1 3-1 1.5 1 3 1 1.5-1 3-1 1.5 1 3 1" opacity=".6"/></svg></div>
    <div class="marca-t"><h1>Vertiente</h1><p>Qué circula, desde cuándo y quién lo empuja</p></div>
    <div class="esp"></div>
    <span class="periodo" id="periodo"></span>
    <button class="icono" id="tema" aria-label="Cambiar tema" title="Cambiar tema"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 0 0 18z" fill="currentColor"/></svg></button>
  </div>
</header>

<main>
  <div class="tiles" id="tiles"></div>

  <section class="card pano">
    <div class="sec-cab">
      <h2>Panorama del período</h2>
      <span class="leyenda">
        <span><span class="sw" style="background:var(--apoya)"></span>Apoya (arriba)</span>
        <span><span class="sw" style="background:var(--rechaza)"></span>Rechaza (abajo)</span>
        <span><span class="sw" style="background:var(--warning);border-radius:50%"></span>Narrativa emergente</span>
        <span><span class="sw" style="background:var(--critical);border-radius:50%"></span>Operación coordinada</span>
      </span>
    </div>
    <div class="lienzo">
      <div class="marcas" id="marcas"></div>
      <svg class="pano-g serie" id="pano" preserveAspectRatio="none" role="img" aria-label="Comentarios de todas las narrativas en el tiempo"></svg>
      <div class="ejes" id="ejes"></div>
    </div>
    <div class="player">
      <button class="play" id="vivo"></button>
      <input type="range" id="slider" min="0" step="1" aria-label="Momento del período">
      <span class="reloj" id="reloj"></span>
    </div>
  </section>

  <div class="grid2">
    <section>
      <div class="sec-cab"><h2>Qué circula</h2><span class="cnt" id="cnt"></span></div>
      <div class="herr">
        <label class="buscar"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg><input id="q" type="search" placeholder="Buscar por título o frase clave" aria-label="Buscar narrativa"></label>
        <div class="seg" id="filtro" role="group" aria-label="Filtro">
          <button data-v="todas" aria-pressed="true">Todas</button><button data-v="emergentes" aria-pressed="false">Emergentes</button><button data-v="empujadas" aria-pressed="false">Empujadas</button>
        </div>
        <select id="orden" aria-label="Ordenar">
          <option value="volumen">Más volumen</option><option value="reciente">Más recientes</option><option value="disputa">Más disputadas</option>
        </select>
        <div class="seg" id="escala" role="group" aria-label="Escala">
          <button data-v="comun" aria-pressed="true" title="Misma escala para comparar volúmenes">Escala común</button><button data-v="propia" aria-pressed="false" title="Cada serie con su propia escala">Propia</button>
        </div>
      </div>
      <div id="narrativas"></div>
    </section>
    <aside>
      <section>
        <div class="sec-cab"><h2>Alertas</h2><span class="cnt" id="cnt-al"></span></div>
        <div class="card panel" id="alertas"></div>
      </section>
      <section>
        <div class="sec-cab"><h2>Quién lo empuja</h2><span class="cnt" id="cnt-op"></span></div>
        <div class="card" id="ops"></div>
      </section>
    </aside>
  </div>
</main>
<footer>Vertiente · datos sintéticos del desafío QualyData · Argentina Space 2026 · horario de Argentina (UTC−3)</footer>
<div id="tip" role="status"></div>
<script>
const D = __DATOS__;
const $ = (s) => document.querySelector(s), $$ = (s) => [...document.querySelectorAll(s)];
const TZ = "America/Argentina/Buenos_Aires";
const fmt = new Intl.NumberFormat("es-AR"), pct = (v) => Math.round(v * 100) + "%";
const NB = D.n_bins, BPD = Math.max(1, Math.round(24 / D.bin_h)), t0 = new Date(D.inicio).getTime();
const msDe = (b) => t0 + b * D.bin_h * 3600e3;
const LARGO = {weekday: "short", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", timeZone: TZ};
const CORTO = {weekday: "short", day: "2-digit", month: "2-digit", timeZone: TZ};
const fecha = (b) => new Date(msDe(b)).toLocaleString("es-AR", LARGO);
const dia = (b) => new Date(msDe(b)).toLocaleString("es-AR", CORTO);
const hora = (iso) => new Date(iso).toLocaleString("es-AR", LARGO);
const esc = (t) => String(t).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const clamp = (v) => Math.max(0, Math.min(NB - 1, v));
const xp = (b) => NB > 1 ? b / (NB - 1) * 100 : 0;
const narrDe = Object.fromEntries(D.narrativas.map(n => [n.id, n]));
const total = (n) => n.apoya + n.rechaza;
const rank = Object.fromEntries([...D.narrativas].sort((a, b) => total(b) - total(a)).map((n, i) => [n.id, i + 1]));
let cur = NB - 1, sel = null, timer = null;
const estado = {q: "", filtro: "todas", orden: "volumen", escala: "comun"};

// --- encabezado y KPIs
$("#periodo").textContent = `${dia(0)} – ${dia(NB - 1)} · ${Math.round(NB / BPD)} días`;
const R = D.resumen;
const tiles = [
  ["Comentarios", fmt.format(R.comentarios), "procesados"],
  ["Narrativas", R.narrativas, `${D.narrativas.filter(n => n.emergente).length} emergentes`],
  ["Ruido", String(R.ruido_pct).replace(".", ",") + "%", "descartado"],
  ["Operaciones", R.operaciones, "coordinadas detectadas", R.operaciones ? "critico" : ""],
  ["Cuentas", fmt.format(R.cuentas_coordinadas), "en operaciones", R.cuentas_coordinadas ? "critico" : ""],
  ["Pipeline", R.segundos != null ? fmt.format(Math.round(R.segundos)) + " s" : "—", `USD ${(R.usd_mil || 0).toFixed(2).replace(".", ",")} / 1.000 coment.`],
];
$("#tiles").innerHTML = tiles.map(([k, v, s, c]) => `<div class="card tile ${c || ""}"><div class="k">${k}</div><div class="v">${v}</div><div class="s">${s}</div></div>`).join("");

// --- series (apoya arriba, rechaza abajo, mismas reglas en panorama y tarjetas)
function serie(sa, sr, ym, W, H, origen) {
  const M = H / 2, X = (b) => (NB > 1 ? b * W / (NB - 1) : 0).toFixed(1);
  const up = (v) => (M - 1 - v * (M - 3) / ym).toFixed(1), dn = (v) => (M + 1 + v * (M - 3) / ym).toFixed(1);
  const area = (s, f, base) => `M0,${base}` + s.map((v, i) => `L${X(i)},${f(v)}`).join("") + `L${W},${base}Z`;
  let g = "";
  for (let b = BPD; b < NB; b += BPD) g += `<line class="gl" x1="${X(b)}" x2="${X(b)}" y1="0" y2="${H}"/>`;
  return g + `<path class="pa" d="${area(sa, up, M - 1)}"/><path class="pr" d="${area(sr, dn, M + 1)}"/>`
    + `<line class="mid" x1="0" x2="${W}" y1="${M}" y2="${M}"/>`
    + (origen != null ? `<line class="orig" x1="${X(origen)}" x2="${X(origen)}" y1="0" y2="${H}"/>` : "")
    + `<line class="cursor" x1="0" x2="0" y1="0" y2="${H}" visibility="hidden"/>`
    + `<rect class="velo" x="${W}" y="-2" width="0" height="${H + 4}"/>`;
}

// --- panorama
const totA = Array.from({length: NB}, (_, b) => D.narrativas.reduce((s, n) => s + n.s_apoya[b], 0));
const totR = Array.from({length: NB}, (_, b) => D.narrativas.reduce((s, n) => s + n.s_rechaza[b], 0));
const PW = 1000, PH = 150, pano = $("#pano");
pano.setAttribute("viewBox", `0 0 ${PW} ${PH}`);
pano.innerHTML = serie(totA, totR, Math.max(1, ...totA, ...totR), PW, PH, null) + `<line class="cabezal" x1="${PW}" x2="${PW}" y1="0" y2="${PH}"/>`;
let ej = "";
for (let b = 0; b < NB; b += BPD) ej += `<span style="left:${xp(Math.min(b + BPD / 2, NB - 1))}%">${dia(b)}</span>`;
$("#ejes").innerHTML = ej;
const porBin = {};
$("#marcas").innerHTML = D.alertas.map(a => {
  const k = porBin[a.bin] = (porBin[a.bin] || 0) + 1, op = a.tipo.startsWith("Op");
  return `<button class="marca ${op ? "op" : "em"}" data-n="${a.narrativa || ""}" data-bin="${a.bin}" style="left:calc(${xp(a.bin)}% + ${(k - 1) * 12}px)" title="${esc(a.tipo + " · " + a.texto)}" aria-label="${esc(a.tipo + ": " + a.texto)}"></button>`;
}).join("");

// --- tooltip con crosshair
const tip = $("#tip");
function conTooltip(svg, valores) {
  const c = svg.querySelector(".cursor"), W = svg.viewBox.baseVal.width;
  svg.addEventListener("pointermove", (e) => {
    const r = svg.getBoundingClientRect();
    const b = clamp(Math.round((e.clientX - r.left) / r.width * (NB - 1)));
    const X = NB > 1 ? b * W / (NB - 1) : 0;
    c.setAttribute("x1", X); c.setAttribute("x2", X); c.setAttribute("visibility", "visible");
    const [a, re] = valores(b);
    tip.innerHTML = `<b>${fecha(b)}</b><div class="f"><span><span class="sw" style="background:var(--apoya)"></span>Apoya</span><span>${fmt.format(a)}</span></div><div class="f"><span><span class="sw" style="background:var(--rechaza)"></span>Rechaza</span><span>${fmt.format(re)}</span></div>`;
    tip.style.display = "block";
    const izq = e.clientX + 14 + tip.offsetWidth > innerWidth ? e.clientX - 14 - tip.offsetWidth : e.clientX + 14;
    tip.style.left = izq + "px"; tip.style.top = (e.clientY + 14) + "px";
  });
  svg.addEventListener("pointerleave", () => { tip.style.display = "none"; c.setAttribute("visibility", "hidden"); });
}
conTooltip(pano, (b) => [totA[b], totR[b]]);

// --- narrativas
const YMAX = Math.max(1, ...D.narrativas.flatMap(n => n.s_apoya.concat(n.s_rechaza)));
const W = 640, H = 76;
function tarjeta(n) {
  const t = total(n), ap = t ? n.apoya / t : 0;
  const ym = estado.escala === "propia" ? Math.max(1, ...n.s_apoya, ...n.s_rechaza) : YMAX;
  return `<article class="card narr${sel === n.id ? " sel" : ""}" id="narr-${n.id}">
    <div class="cab">
      <span class="rank" title="Puesto por volumen">${rank[n.id]}</span>
      <div class="tt"><h3>${esc(n.titulo)}</h3><div class="meta">${n.id} · desde ${hora(n.origen)} · ${fmt.format(t)} comentarios</div></div>
      <div class="badges">${n.emergente ? '<span class="badge em">Emergente</span>' : ""}${n.operacion ? `<span class="badge op">Empujada por ${n.operacion.id}</span>` : ""}</div>
    </div>
    <div class="pol" title="Postura de los comentarios">
      <div class="bar"><span style="width:${ap * 100}%"></span></div>
      <div class="pl"><span><b>${pct(ap)}</b> apoya · ${fmt.format(n.apoya)}</span><span>${fmt.format(n.rechaza)} · <b>${pct(1 - ap)}</b> rechaza</span></div>
    </div>
    <svg class="serie" data-id="${n.id}" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="Comentarios cada ${D.bin_h} horas: ${esc(n.titulo)}">${serie(n.s_apoya, n.s_rechaza, ym, W, H, n.origen_bin)}</svg>
    <div class="chips">${n.claves.map(k => `<span class="chip">${esc(k)}</span>`).join("")}</div>
  </article>`;
}
function visibles() {
  const q = estado.q.trim().toLowerCase();
  let l = D.narrativas.filter(n =>
    (estado.filtro !== "emergentes" || n.emergente) && (estado.filtro !== "empujadas" || n.operacion) &&
    (!q || (n.titulo + " " + n.id + " " + n.claves.join(" ")).toLowerCase().includes(q)));
  const disputa = (n) => total(n) ? Math.abs(n.apoya / total(n) - 0.5) : 1;
  const ord = {volumen: (a, b) => total(b) - total(a), reciente: (a, b) => b.origen.localeCompare(a.origen), disputa: (a, b) => disputa(a) - disputa(b)};
  return l.sort(ord[estado.orden]);
}
function pintar() {
  const l = visibles();
  $("#cnt").textContent = l.length === D.narrativas.length ? `${l.length} narrativas` : `${l.length} de ${D.narrativas.length}`;
  $("#narrativas").innerHTML = l.length ? l.map(tarjeta).join("") : '<div class="card vacio">Ninguna narrativa coincide con el filtro.</div>';
  $$("#narrativas svg.serie").forEach(svg => { const n = narrDe[svg.dataset.id]; conTooltip(svg, (b) => [n.s_apoya[b], n.s_rechaza[b]]); });
  mostrarHasta(cur);
}
function seleccionar(id) {
  if (!narrDe[id]) return;
  sel = id;
  if (!visibles().some(n => n.id === id)) { estado.q = ""; $("#q").value = ""; estado.filtro = "todas"; marcar("#filtro", "todas"); }
  pintar();
  document.getElementById("narr-" + id).scrollIntoView({block: "center"});
}
function marcar(grupo, v) { $$(grupo + " button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.v === v))); }
$("#q").addEventListener("input", (e) => { estado.q = e.target.value; pintar(); });
$("#orden").addEventListener("change", (e) => { estado.orden = e.target.value; pintar(); });
for (const k of ["filtro", "escala"]) $("#" + k).addEventListener("click", (e) => {
  const b = e.target.closest("button"); if (!b) return;
  estado[k] = b.dataset.v; marcar("#" + k, b.dataset.v); pintar();
});

// --- alertas y operaciones
$("#cnt-al").textContent = D.alertas.length || "";
$("#alertas").innerHTML = D.alertas.length ? D.alertas.map(a => `
  <button class="alerta ${a.tipo.startsWith("Op") ? "op" : "em"}" data-bin="${a.bin}" data-n="${a.narrativa || ""}">
    <span class="dot"></span>
    <span><span class="tp"><span>${a.tipo}</span><span class="ts">${hora(a.ts)}</span></span><span class="tx">${esc(a.texto)}</span></span>
  </button>`).join("") : '<div class="vacio">Sin alertas.</div>';
const antig = (d) => d == null ? "—" : (d < 60 ? Math.round(d) + " días" : (d / 365).toFixed(1).replace(".", ",") + " años");
$("#cnt-op").textContent = D.operaciones.length || "";
$("#ops").innerHTML = D.operaciones.map(o => `
  <div class="opcard">
    <div class="cab"><span class="id">${o.id}</span><span class="meta">desde ${hora(o.inicio)}</span></div>
    <div class="emp">Empuja <b>«${esc((narrDe[o.narrativa] || {}).titulo || o.narrativa)}»</b> <span class="pill ${o.postura === "apoya" ? "apoya" : "rechaza"}">${esc(o.postura)}</span></div>
    <dl class="stats">
      <div><dt>Cuentas</dt><dd>${fmt.format(o.cuentas)}</dd></div>
      <div><dt>Comentarios</dt><dd>${fmt.format(o.comentarios)}</dd></div>
      <div><dt>Antigüedad mediana</dt><dd>${antig(o.antiguedad)}</dd></div>
      <div><dt>Actividad nocturna</dt><dd>${pct(o.nocturna)}</dd><div class="medidor"><span style="width:${o.nocturna * 100}%"></span></div></div>
      <div style="grid-column:1/-1"><dt>Foco en esa narrativa</dt><dd>${pct(o.foco)}</dd><div class="medidor"><span style="width:${o.foco * 100}%"></span></div></div>
    </dl>
    <button class="ver" data-n="${o.narrativa}">Ver narrativa →</button>
  </div>`).join("") || '<div class="vacio">No se detectaron operaciones.</div>';
document.addEventListener("click", (e) => { const b = e.target.closest("[data-n]"); if (b && b.dataset.n) seleccionar(b.dataset.n); });

// --- modo en vivo: el período completo en ~60 s
const ICONO_PLAY = '<svg viewBox="0 0 12 12" fill="currentColor"><path d="M2 1l9 5-9 5z"/></svg>';
const ICONO_STOP = '<svg viewBox="0 0 12 12" fill="currentColor"><rect x="2" y="2" width="8" height="8" rx="1"/></svg>';
const slider = $("#slider");
slider.max = NB - 1;
function botonVivo() { $("#vivo").innerHTML = timer ? ICONO_STOP + "Detener" : ICONO_PLAY + "Reproducir en vivo"; }
function mostrarHasta(b) {
  cur = b;
  $$("svg.serie").forEach(svg => {
    const w = svg.viewBox.baseVal.width, X = NB > 1 ? b * w / (NB - 1) : w, v = svg.querySelector(".velo");
    v.setAttribute("x", X); v.setAttribute("width", b >= NB - 1 ? 0 : w - X + 4);
  });
  const X = NB > 1 ? b * PW / (NB - 1) : PW, cab = pano.querySelector(".cabezal");
  cab.setAttribute("x1", X); cab.setAttribute("x2", X); cab.style.visibility = b >= NB - 1 ? "hidden" : "visible";
  $$(".alerta, .marca").forEach(el => el.classList.toggle("oculta", +el.dataset.bin > b));
  slider.value = b;
  $("#reloj").textContent = b >= NB - 1 ? "Período completo" : fecha(b);
}
function detener() { clearInterval(timer); timer = null; botonVivo(); }
$("#vivo").addEventListener("click", () => {
  if (timer) { detener(); mostrarHasta(NB - 1); return; }
  let b = cur >= NB - 1 ? 0 : cur;
  timer = setInterval(() => { mostrarHasta(b); if (++b >= NB) { detener(); mostrarHasta(NB - 1); } }, 60000 / NB);
  botonVivo();
});
slider.addEventListener("input", () => { if (timer) detener(); mostrarHasta(+slider.value); });
botonVivo();
pintar();
// #t=<bloque>: fija el momento de la reproducción (lo usa la grabación del video)
const mt = location.hash.match(/t=(\d+)/);
if (mt) mostrarHasta(clamp(+mt[1]));
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

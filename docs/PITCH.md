# Pitch (3 min) y video

## Guion

**0:00 — El problema (20 s).**
"Cuando miles de personas discuten un tema, hay dos preguntas: ¿qué se dice? y ¿qué parte está armada? Hacerlo
comentario por comentario con IA es lento y caro; con palabras clave, falla."

**0:20 — La idea (40 s).**
"Nuestra intuición: **la conversación misma es la etiqueta.** Cuando alguien responde con un argumento, discute la
*misma* narrativa desde el *otro* lado. Conectando las respuestas, cada narrativa aparece sola con sus dos bandos.
Y una operación coordinada no se ve en un comentario: se ve en la **repetición** — las mismas cuentas, en la misma
publicación, empujando lo mismo, una y otra vez."

**1:00 — Demo (60 s).** Abrir `dashboard.html` → **▶ Reproducir en vivo**.
- Las 13 narrativas aparecen con apoya (arriba) y rechaza (abajo).
- Día 6, 01:12: alerta **narrativa emergente** «el hospital se inaugura para la foto» y al mismo tiempo
  **operación op03**: 24 cuentas creadas el día anterior, 100% de madrugada.
- op02: 30 cuentas *antiguas*, textos variados — la más difícil — empujando «no hubo consulta previa».
- "En un minuto: qué circula, desde cuándo y quién lo empuja."

**2:00 — Números (40 s).**
- 200.000 comentarios en **15 segundos**, en una notebook, **USD 0** de IA.
- **53,8 / 55** en la parte automática de práctica (línea base: 17).
- Robusto: datos ensuciados, 75% de los datos, otras semillas → mismo resultado (VALIDACION.md).
- Un comando: `make entrega`. DuckDB + Parquet hoy; ClickHouse + stream para millones por día, mismo SQL.

**2:40 — Cierre (20 s).**
"31 hipótesis medidas, la mitad refutadas y documentadas. No ajustamos a mano: elegimos cada parámetro por el peor
caso, porque el set final es otro. Radar: narrativas y coordinación a escala, explicables y baratas."

## Video (≤ 3 min, para Hacki)

1. Terminal: `make entrega` corriendo (acelerado) → `OK: formato válido`.
2. `make score` sobre práctica: 53,76 / 55.
3. Dashboard: reproducción en vivo + hover en una narrativa + panel "Quién lo empuja".
4. Diagrama de `README.md` (cómo funciona) 10 s.

## Preguntas probables del jurado

- **¿Y si el set final no tiene respuestas?** Las narrativas siguen saliendo de la similitud semántica (microgrupos);
  lo que se pierde es el emparejamiento automático de bandos y la herencia. Ahí entra el profesor LLM (1 llamada por
  narrativa).
- **¿Por qué no un LLM para todo?** Costo y escala: 150.000 llamadas vs ~13; y el LLM no ve la coordinación, que está
  en el comportamiento, no en el texto.
- **¿Overfitting a práctica?** Cero palabras del tema en el código; umbrales relativos/adaptativos; parámetros elegidos
  por peor caso sobre variantes (sin un tema, mitad de período, submuestreo).
- **¿Falsos positivos de coordinación?** Exigimos repetición alineada + triángulos + densidad; los picos virales
  genuinos (muchas cuentas una vez) no pasan (hay un test que lo verifica).
- **¿Escala?** Ver README → "Cómo escala".

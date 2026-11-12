# Pitch (3 min) y video

## Guion

**0:00 — Hook (15 s).** Pantalla negra o el dashboard congelado en el día 6. Pausa antes de "¿Casualidad?".
"Domingo, una y doce de la mañana. Aparece un rumor nuevo: *'van a cortar la cinta del hospital en campaña, aunque
no haya ni camas'*. En ese mismo minuto, veinticuatro cuentas creadas el día anterior empiezan a empujarlo.
¿Casualidad? … Nadie lo vio. Radar sí."

**0:15 — El problema (10 s).**
"Entre doscientos mil comentarios, ¿qué se dice y qué parte está armada? Leerlos con IA uno por uno es lento y
caro; con palabras clave, falla."

> Hooks alternativos (mismos datos, otro tono):
> - **Pregunta al jurado:** "¿Cuántos de los comentarios que leyeron hoy los escribió una persona de verdad? Nosotros
>   lo podemos medir."
> - **Número:** "Ciento veinticuatro cuentas. Tres operaciones. Escondidas entre doscientos mil comentarios.
>   Las encontramos en quince segundos, sin gastar un peso en IA."

**0:25 — La idea (35 s).**
"Nuestra intuición: **la conversación misma es la etiqueta.** Cuando alguien responde con un argumento, discute la
*misma* narrativa desde el *otro* lado. Conectando las respuestas, cada narrativa aparece sola con sus dos bandos.
Y una operación coordinada no se ve en un comentario: se ve en la **repetición** — las mismas cuentas, en la misma
publicación, empujando lo mismo, una y otra vez."

**1:00 — Demo (60 s).** Abrir `dashboard.html` → **▶ Reproducir en vivo**.
- Las 13 narrativas aparecen con apoya (arriba) y rechaza (abajo).
- Domingo 06-09, 01:12 (día 6): alerta **narrativa emergente** n12 «Ya van a cortar la cinta en campaña aunque no
  haya ni camas» y, en el mismo minuto, **operación op03**: 24 cuentas creadas el día anterior empujándola de
  madrugada. *Es el hook del principio: cerrar el círculo ("esto es lo que les conté").*
- op01: 60 cuentas (antigüedad mediana 4 días) empujan «Gracias al proyecto hay trabajo para los proveedores locales».
- op02: 40 cuentas empujan «Sin consulta libre e informada no hay licencia social».
- "En un minuto: qué circula, desde cuándo y quién lo empuja."

*(Cifras de la corrida sobre práctica, capturas en `docs/video/`. Si se presenta el dashboard del set final, cambiar
los ejemplos por los que muestre ese día.)*

**2:00 — Números (40 s).**
- 200.000 comentarios en **15 segundos**, en una notebook, **USD 0** de IA.
- **53,6 / 55** en la parte automática de práctica (línea base: 17).
- Robusto: datos ensuciados, 75% de los datos, otras semillas → mismo resultado (VALIDACION.md).
- Agnóstico: sobre 2 temas y 8 narrativas inventadas que nunca vio, 29,7/30 en narrativas (SINTETICOS.md).
- Un comando: `make entrega`. DuckDB + Parquet hoy; ClickHouse + stream para millones por día, mismo SQL.

**2:40 — Cierre (20 s).**
"37 hipótesis medidas, muchas refutadas y documentadas. No ajustamos a mano: elegimos cada parámetro por el peor
caso, porque el set final es otro. Radar: narrativas y coordinación a escala, explicables y baratas."

## Video (≤ 3 min, para Hacki)

Storyboard de producción completo (escenas, locución, subtítulos, cómo grabar): [video/STORYBOARD.md](video/STORYBOARD.md).
Resumen:

1. Terminal: `make entrega` corriendo (acelerado) → `OK: formato válido`.
2. `make score` sobre práctica: 53,62 / 55.
3. Dashboard: reproducción en vivo + hover en una narrativa + panel "Quién lo empuja".
4. Diagrama de `README.md` (cómo funciona) 10 s.

## Preguntas probables del jurado

- **¿Y si el set final no tiene respuestas?** Lo probamos (E32): el pipeline detecta la falta de respuestas y pasa a un
  modo degradado por significado; sacó 32,6/55 en práctica sin una sola respuesta (sin ese modo: 1,8).
- **¿Por qué no un LLM para todo?** Costo y escala: 150.000 llamadas vs ~13; y el LLM no ve la coordinación, que está
  en el comportamiento, no en el texto.
- **¿Overfitting a práctica?** Cero palabras del tema en el código; umbrales relativos/adaptativos; parámetros elegidos
  por peor caso sobre variantes (sin un tema, mitad de período, submuestreo).
- **¿Falsos positivos de coordinación?** Exigimos repetición alineada + triángulos + densidad; los picos virales
  genuinos (muchas cuentas una vez) no pasan (hay un test que lo verifica).
- **¿Escala?** Ver README → "Cómo escala".
- **¿Qué no detecta?** Lo decimos: campañas de cuentas antiguas que rotan subgrupos, donde ningún par coincide dos
  veces (lo encontramos con sets sintéticos; probamos 4 soluciones y ninguna mejoraba sin dañar el resto).

# Validación

Todo medido con `radar/eval/puntaje.py` (réplica pura del script oficial `evaluacion/puntuar.py`, verificada con
tests) sobre el set de práctica. Reproducir: `make run && make score` y `make validar`.

## Resultado en práctica

| | Puntos | Detalle |
|---|---|---|
| Narrativas | **29,70 / 30** | B-cubed F1 0,991 · ruido F1 0,970 · postura macro-F1 0,995 · origen emergentes 1,0 |
| Coordinación | **23,92 / 25** | P 0,911 · R 0,983 · F1 0,946 · grupos B-cubed 0,983 |
| **Total automático** | **53,62 / 55** | línea base oficial del desafío: ~17 / 55 |
| Tiempo | 14 s (caché de embeddings caliente) · ~60 s en frío | Apple M5, 16 GB, sin GPU dedicada |
| Costo IA | USD 0 sin LLM; ~13 llamadas por corrida con LLM | |

Operaciones detectadas en práctica (sin mirar la verdad):

| Operación | Cuentas | Empuja | Perfil | Verdad |
|---|---|---|---|---|
| op01 | 60 | L2 «Gracias al proyecto hay trabajo…» (apoya) | cuentas de 4 días, foco 72% | C1 |
| op02 | 38 | L4 «Sin consulta libre e informada no hay licencia social» (apoya) | cuentas de 4,1 años, foco 28% | C2 (30) + 8 genuinas |
| op03 | 24 | H3 «Ya van a cortar la cinta en campaña…» (apoya) | cuentas de 1 día, 100% nocturna | C3 |

## Robustez (el set final trae otros temas, narrativas y campañas)

`make validar` arma variantes del set de práctica y corre el pipeline completo en cada una:

| Variante | Narr. | Coord. | Total | Lectura |
|---|---|---|---|---|
| completo | 29,70 | 23,92 | 53,62 | referencia |
| ensuciado (2% typos, ids duplicados, fechas rotas, filas desordenadas) | 29,67 | 24,64 | 54,31 | **datos sucios no lo afectan** |
| semilla 7 / semilla 123 | 29,72 / 29,21 | 23,78 / 23,79 | 53,50 / 53,00 | estable ante el azar de Leiden |
| submuestra 75% | 28,87 | 21,95 | 50,82 | menos volumen: degrada suave |
| primera mitad (7 días) | 28,44 | 21,22 | 49,66 | menos repeticiones; la postura de 3 narrativas se invierte |
| sin colectivo | 29,63 | 24,27 | 53,90 | 2 de 3 temas: igual |
| sin hospital | 29,73 | 24,53 | 54,26 | |
| solo litio | 29,56 | 24,53 | 54,09 | un único tema |
| sin litio | 28,22 | 10,92 | 39,14 | ⚠ techo: C1 y C2 empujan narrativas de litio |
| solo hospital | 29,79 | 12,00 | 41,79 | ⚠ techo: solo C3 es detectable |
| solo colectivo | 29,79 | 0,71 | 30,50 | ⚠ techo: ninguna campaña empuja colectivo |
| **sin respuestas** (`respuesta_a` vacío) | 12,08 | 20,56 | 32,64 | modo degradado automático (E32); sin él: 1,81 |
| **sintético: temas nuevos** | 29,72 | 15,75 | 45,47 | ver [SINTETICOS.md](SINTETICOS.md) |
| **sintético: campañas nuevas** | 28,91 | 15,85 | 44,76 | ver [SINTETICOS.md](SINTETICOS.md) |

⚠ En `sin_*`/`solo_*` las cuentas de campaña siguen en la verdad aunque su actividad coordinada esté en el tema
quitado (solo queda su actividad de "cobertura"): el recall tiene un techo bajo que no es error del método.

**Lectura honesta:**
- Narrativas: robustas. B-cubed ≥ 0,98 en todas las variantes. El punto frágil es **qué lado "apoya"** cuando las
  señales locales casi no separan (B3, H2): sin LLM, ~85–100% de acierto según la variante. Con LLM ese juicio lo
  toma el profesor (1 llamada por narrativa).
- Coordinación: la configuración se eligió por **promedio y peor caso sobre las variantes**, no por el set completo
  (E23–E30). Peor caso entre las variantes que miden robustez: ~20 / 25.

## Bitácora de hipótesis (`experimentos/`)

| # | Hipótesis | Resultado |
|---|---|---|
| E01–E02 | EmbeddingGemma 2 separa mejor que e5-small | **Refutada**: misma pureza kNN (0,998) y 6x más lento → e5-small |
| E03 | Toda respuesta hereda la narrativa del padre | **Confirmada** (28.054/28.054); el 80% invierte la postura |
| E04–E06 | Narrativas = comunidades del grafo similitud+respuestas; postura = bipartición | **Confirmada**: 13 narrativas, B-cubed 0,99 |
| E05/E19 | El lado que afirma tiene menos respuestas | Parcial: 12/13; se agrega refutación como desempate |
| E18 | Texto frecuente sin respuestas = ruido | **Confirmada**: 34.370 de 37.710 con 32 errores |
| E08–E14 | Coincidencia en publicaciones / ráfagas / k-core separan campañas | **Refutadas**: los usuarios intensivos coinciden con todos |
| E15–E16 | C2 se delata por foco en una narrativa y sincronía | Confirmada: base de la sincronía alineada |
| E17 | Sincronía alineada (publicación + narrativa + postura + minutos) | **Confirmada**: F1 0,96 |
| E20–E22 | Expansión / umbral relativo / poda por nodo | **Refutadas** (inestables o peores) |
| E23 | CPM en vez de modularidad | **Refutada** |
| E25 | Quitar aristas sin vecinos comunes | **Confirmada**: peor caso 0,7 → 21,4 |
| E26–E30 | El detector depende del orden de filas; rescate de núcleo k-core | Confirmada y corregida: peor caso 20,9 → 23,5 + orden determinístico |
| E27 | Re-partición recursiva | **Refutada** (crea grupos falsos) |
| E31 | "Lo que empuja una operación es el lado que apoya" | **Descartada**: operaciones dudosas romperían narrativas sanas |
| E32 | ¿Sobrevive sin respuestas? | **No** (1,8/55) → modo degradado por significado: 32,6/55 |
| E33–E34 | Una campaña que nadie discute queda como ruido e invisible | **Confirmada** → el ruido se alinea como clase propia |
| E33/E35/E36 | Detectar campañas que rotan subgrupos (expansión / peso por evento / foco) | **Refutadas**: ninguna mejora el promedio; límite documentado |
| E37 | El origen se adelanta por comentarios sueltos mal asignados | **Confirmada** → mínimo relativo al volumen (0,5%) |

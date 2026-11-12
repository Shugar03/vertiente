# Pitch (3 min) y video

Hilo conductor: **un caso real** (el rumor del hospital, día 6) abre el pitch, se *ve* en vivo en la demo y vuelve en
el cierre. Todo lo demás (la idea, los números) explica cómo Radar lo encontró.

Ritmo: ~140 palabras por minuto, sin apuro. Las pausas marcadas (…) son parte del guion.

## Guion

### 0:00 — Hook (15 s)
**Pantalla:** negra, o el dashboard congelado en el día 6 (`dashboard.html#t=20`). Sin decir el nombre del equipo todavía.

> "Domingo, una y doce de la mañana. Aparece un rumor nuevo: *'van a cortar la cinta del hospital en campaña, aunque
> no haya ni camas'*. En ese mismo minuto, veinticuatro cuentas creadas el día anterior empiezan a empujarlo.
> … ¿Casualidad? … Nadie lo vio. Radar sí."

### 0:15 — El problema (15 s)
**Pantalla:** placa "200.000 comentarios".

> "Somos Radar. Ese rumor estaba escondido entre doscientos mil comentarios. Leerlos uno por uno con IA es lento y
> caro; buscar palabras clave no sirve, porque cada tema es distinto. Y una operación no se ve en un comentario
> suelto."

### 0:30 — Cómo lo encontramos (35 s)
**Pantalla:** diagrama de *Cómo funciona* del README.

> "Usamos dos ideas. La primera: **la conversación misma es la etiqueta.** Cuando alguien le responde a otro con un
> argumento, está discutiendo la misma narrativa desde el otro lado. Uniendo las respuestas, cada narrativa aparece
> sola, con sus dos bandos, sin que nadie etiquete nada.
> La segunda: **una operación se delata por la repetición.** No alcanza con coincidir una vez; lo sospechoso es ver
> a las mismas cuentas, en la misma publicación, empujando lo mismo, a minutos de distancia, una y otra vez."

### 1:05 — Demo (55 s)
**Pantalla:** `dashboard.html` arriba de todo → click en **▶ Reproducir en vivo** (el período entero dura ~60 s; el
día 6 llega a los ~20 s).

> "Esto es Radar sobre el set de práctica. Arriba de cada narrativa, los que apoyan; abajo, los que rechazan. Trece
> narrativas, encontradas solas."
> *(mientras corre)* "Reproducimos los catorce días…"
> *(día 6: aparecen juntas las dos alertas → click en ■ para pausar)* "… y acá está. Domingo, una y doce: la
> narrativa nueva y, en el mismo minuto, la operación que la empuja. **Esto es lo que les conté al principio.**"
> *(scroll a "Quién lo empuja")* "Veinticuatro cuentas, creadas el día anterior, activas de madrugada. Y no es la
> única: hay otra de sesenta cuentas a favor del proyecto minero, y otra de cuarenta en contra. Radar no toma partido:
> encuentra lo armado de los dos lados."

**Plan B** si algo falla en vivo: abrir `docs/video/02_dia6.png` y `03_final.png`, o reproducir `docs/demo_practica.mp4`.

### 2:00 — Por qué funciona (35 s)
**Pantalla:** placa con los cuatro números.

> "Todo esto corre con un solo comando, en una notebook común: **quince segundos** para doscientos mil comentarios,
> sin GPU y con **cero pesos** de IA.
> Con el puntaje oficial del desafío sacamos **cincuenta y tres coma seis sobre cincuenta y cinco**; la línea base es
> diecisiete.
> Y como el set final es otro, lo probamos con temas que nunca vio, con datos sucios y con menos volumen: sigue
> funcionando. Para millones de comentarios por día, el mismo SQL pasa de DuckDB a ClickHouse."

### 2:35 — Cierre (25 s)
**Pantalla:** placa final: **Radar** · *Qué circula, desde cuándo y quién lo empuja* · link al repo · nombres.

> "Medimos treinta y siete hipótesis y descartamos las que no funcionaban; no ajustamos nada a mano.
> … La próxima vez que a la una de la mañana aparezca un rumor y veinticuatro cuentas salgan a empujarlo, alguien va
> a saber quién está detrás.
> Radar: qué circula, desde cuándo y quién lo empuja."

### Versión de 30 s (pasillo, mentores, ascensor)

> "Domingo, una y doce de la mañana: aparece un rumor sobre un hospital y, en el mismo minuto, veinticuatro cuentas
> creadas el día anterior salen a empujarlo. Radar lo detecta solo, entre doscientos mil comentarios, en quince
> segundos y sin gastar en IA. ¿Cómo? Las respuestas nos dicen qué narrativa discute cada uno y desde qué lado; y una
> operación se delata porque las mismas cuentas empujan lo mismo, una y otra vez."

### Datos del caso (para no equivocarse)

| Qué | Valor (corrida sobre práctica, capturas en `docs/video/`) |
|---|---|
| Rumor | n12 «Ya van a cortar la cinta en campaña aunque no haya ni camas» — narrativa emergente |
| Cuándo | domingo 06-09, 01:12 (día 6 de 14) |
| Operación | op03: 24 cuentas creadas el día anterior, actividad de madrugada |
| Otras operaciones | op01: 60 cuentas (antigüedad mediana 4 días) a favor del proyecto · op02: 40 cuentas en contra |
| Totales | 200.000 comentarios · 13 narrativas · 3 operaciones · 124 cuentas · 15,7 s · 53,62/55 |

Si se presenta el dashboard del **set final**, rehacer el hook con la alerta más llamativa de ese día manteniendo la
estructura: hora exacta → frase textual → cuántas cuentas y qué tienen de raro → "¿Casualidad? Radar sí".

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
- **¿Cómo saben que esas 24 cuentas no son gente real que opina igual?** No juzgamos la opinión sino el
  comportamiento: las mismas cuentas, en varias publicaciones distintas, empujando lo mismo a minutos de distancia, y
  formando un grupo cerrado (triángulos). Gente que opina igual coincide una vez; una operación coincide siempre. Por
  eso además mostramos el perfil (antigüedad, horario) para que una persona decida.
- **¿No es censura / no toman partido?** En práctica detecta una operación a favor del proyecto (op01) y otra en
  contra (op02). Radar no evalúa si una narrativa es verdadera: muestra qué circula y qué parte está empujada.
- **Si lo re-corremos, ¿da lo mismo?** Sí en la misma máquina (semillas fijas, orden determinístico, E26). En otro
  hardware (CPU vs Mac con `mps`) los embeddings cambian en decimales y puede variar algún detalle, no el resultado.

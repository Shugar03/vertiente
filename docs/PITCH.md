# Pitch (3 min) y video

Hilo conductor: **un caso real** (el rumor del hospital, día 6) abre el pitch, se *ve* en vivo en la demo y vuelve en
el cierre. Todo lo demás (la idea, los números) explica cómo Vertiente lo encontró.

Slides: [`docs/slides/index.html`](slides/index.html) (← → para avanzar, **N** muestra este guion como notas, **F**
pantalla completa; respaldo en PDF: `docs/slides/vertiente.pdf`). Cada slide lleva arriba a la derecha el criterio
del track que cubre.

Ritmo: ~140 palabras por minuto, sin apuro. Las pausas marcadas (…) son parte del guion.

## Mapa

Lo presenta **una sola persona**, que habla y maneja la compu.

| Bloque | Tiempo | Slides |
|---|---|---|
| Hook + problema | 0:00–0:30 | 1 → 3 |
| Cómo lo encontramos | 0:30–1:05 | 4 → 5 |
| Demo en vivo | 1:05–2:00 | 6 (panorama en video) |
| Por qué funciona | 2:00–2:35 | 7 → 9 |
| Cierre | 2:35–3:00 | 10 → 12 |

Para hablar y manejar a la vez:
- Avanzar slides con la flecha → (o un presentador inalámbrico); nunca con el mouse sobre la slide.
- La demo está **dentro de las slides** (slide 6): no hace falta cambiar de ventana. El dashboard queda abierto
  aparte solo para las preguntas o como plan B.
- Durante la demo, la frase va **después** de la acción: primero la tecla, una respiración, después hablar.
- Si te comés una frase, no la repitas: seguí con la siguiente. El jurado no tiene el guion.

## Guion

### 0:00 — Hook (15 s)
**Pantalla:** slide 1 (portada) mientras se acomodan → slide 2 apenas empieza a hablar. No decir el nombre todavía.

> "Domingo, una y doce de la mañana. Aparece un rumor nuevo: *'van a cortar la cinta del hospital en campaña, aunque
> no haya ni camas'*. En ese mismo minuto, veinticuatro cuentas creadas el día anterior empiezan a empujarlo.
> … ¿Casualidad? … Nadie lo vio. Vertiente sí."

### 0:15 — El problema (15 s)
**Pantalla:** slide 3.

> "Somos Vertiente. Ese rumor estaba escondido entre doscientos mil comentarios. Leerlos uno por uno con IA es lento
> y caro; buscar palabras clave no sirve, porque cada tema es distinto. Y una operación no se ve en un comentario
> suelto."

### 0:30 — Cómo lo encontramos (35 s)
**Pantalla:** slide 4 (idea 1) → slide 5 (idea 2) en "La segunda".

> "Usamos dos ideas. La primera: **la conversación misma es la etiqueta.** Cuando alguien le responde a otro con un
> argumento, está discutiendo la misma narrativa desde el otro lado. Uniendo las respuestas, cada narrativa aparece
> sola, con sus dos bandos, sin que nadie etiquete nada.
> *(slide 5)* La segunda: **una operación se delata por la repetición.** No alcanza con coincidir una vez; lo
> sospechoso es ver a las mismas cuentas, en la misma publicación, empujando lo mismo, a minutos de distancia, una y
> otra vez."

### 1:05 — Demo (55 s)
**Pantalla:** slide 6. El panorama del dashboard (grabado de la corrida real) **arranca solo** al entrar: 14 días en
22 s, con un reloj arriba a la derecha. A los **8 s se pausa solo en el día 6** (dom 06-09, 01:12) y se encienden las
tarjetas del rumor y de op03. **P** sigue la reproducción; al final se enciende la tercera tarjeta. **R** reinicia.

> "Esto es Vertiente sobre el set de práctica: los catorce días, todas las narrativas. Arriba, los que apoyan; abajo,
> los que rechazan. Trece narrativas, encontradas solas."
> *(mientras corre)* "Reproducimos los catorce días…"
> *(se pausa solo en el día 6; aparecen juntos el punto amarillo y el rojo)* "… y acá está. Domingo, una y doce: la
> narrativa nueva y, en el mismo minuto, la operación que la empuja. **Esto es lo que les conté al principio.**
> Veinticuatro cuentas, creadas el día anterior, activas de madrugada."
> *(**P**: sigue hasta el final y se enciende la tercera tarjeta)* "Y no es la única: hay otra de sesenta cuentas a
> favor del proyecto minero, y otra de cuentas con años de antigüedad en contra. Vertiente no toma partido:
> encuentra lo armado de los dos lados."

Si sobra tiempo o el jurado pide verlo de verdad: Alt+Tab al `dashboard.html` (abierto aparte); `#t=20` lo abre en el
día 6 y un click en la alerta de op03 salta a la narrativa.

**Plan B** si el video no arranca: **R** para reiniciar; si sigue sin andar, `docs/demo_practica.mp4`. No improvisar
arreglos con el jurado mirando: pasar al plan B y seguir.

### 2:00 — Por qué funciona (35 s)
**Pantalla:** flecha → slide 7 (puntaje) → slide 8 (costo y
escala) en "Todo esto corre…" → slide 9 (robustez) en "Y como el set final es otro…".

> "Con el puntaje oficial del desafío sacamos **cincuenta y tres coma seis sobre cincuenta y cinco**; la línea base
> es diecisiete.
> *(slide 8)* Todo esto corre con un solo comando, en una notebook común: **quince segundos** para doscientos mil
> comentarios, sin GPU y con **cero pesos** de IA. Para millones de comentarios por día, el mismo SQL pasa de DuckDB
> a ClickHouse.
> *(slide 9)* Y como el set final es otro, lo probamos con temas que nunca vio, con datos sucios y con menos volumen:
> sigue funcionando."

### 2:35 — Cierre (25 s)
**Pantalla:** slide 10 → **dos flechas seguidas** a la slide 12 en "La próxima vez…" (la 11 se saltea; queda para
las preguntas).

> "Medimos treinta y siete hipótesis y descartamos las que no funcionaban; no ajustamos nada a mano.
> *(slide 12)* … La próxima vez que a la una de la mañana aparezca un rumor y veinticuatro cuentas salgan a
> empujarlo, alguien va a saber quién está detrás.
> Vertiente: qué circula, desde cuándo y quién lo empuja."

**Al terminar:** volver a la slide 11 (*Cada criterio, con su evidencia*) y dejarla de fondo durante las preguntas.

### Versión de 30 s (pasillo, mentores, ascensor)

> "Domingo, una y doce de la mañana: aparece un rumor sobre un hospital y, en el mismo minuto, veinticuatro cuentas
> creadas el día anterior salen a empujarlo. Vertiente lo detecta solo, entre doscientos mil comentarios, en quince
> segundos y sin gastar en IA. ¿Cómo? Las respuestas nos dicen qué narrativa discute cada uno y desde qué lado; y una
> operación se delata porque las mismas cuentas empujan lo mismo, una y otra vez."

### Datos del caso (para no equivocarse)

| Qué | Valor (corrida sobre práctica, capturas en `docs/video/`) |
|---|---|
| Rumor | n12 «Ya van a cortar la cinta en campaña aunque no haya ni camas» — narrativa emergente |
| Cuándo | domingo 06-09, 01:12 (día 6 de 14) · bloque 20 del dashboard (`#t=20`) |
| Operación | op03: 24 cuentas creadas el día anterior, actividad de madrugada |
| Otras operaciones | op01: ~60 cuentas (antigüedad mediana 4 días) a favor del proyecto · op02: 30–40 cuentas antiguas en contra; la cifra varía según la máquina, por eso el guion no la dice |
| Totales | 200.000 comentarios · 13 narrativas · 53,62/55 · 15,7 s (Apple M5) |

**Si la demo corre en la PC con Windows:** el pipeline tarda ~40 s con caché (no 15) y puede aparecer una **op04**
de 9 cuentas que en la Mac no sale. El guion no menciona ninguna de las dos cifras; si el jurado pregunta, ver abajo.

Si se presenta el dashboard del **set final**, rehacer el hook con la alerta más llamativa de ese día manteniendo la
estructura: hora exacta → frase textual → cuántas cuentas y qué tienen de raro → "¿Casualidad? Vertiente sí".

## Checklist antes de subir al escenario

- [ ] Slides abiertas en pantalla completa en la slide 1, **con la carpeta `docs/slides/` completa** (el video
      `panorama.mp4` tiene que estar al lado de `index.html`).
- [ ] Ensayar la slide 6 una vez: entra, corre, se pausa en el día 6, **P** sigue, **R** reinicia. Volver a la slide 1.
- [ ] Dashboard abierto aparte (para preguntas o plan B), arriba de todo, tema claro, período completo.
- [ ] Notificaciones apagadas, sin pestañas personales a la vista, cargador enchufado.
- [ ] `docs/demo_practica.mp4` a mano (plan B).
- [ ] Cronometrar un ensayo completo: si pasa de 3:00, recortar la demo, no el cierre.

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
- **¿Qué es la op04?** (si aparece en la demo) Un grupo chico que en esta máquina pasa el umbral y en la Mac no: los
  embeddings en CPU cambian en decimales. Es el tipo de caso borde que bajaría la precisión; por eso el perfil de
  cada operación está a la vista para que una persona decida.
- **¿Escala?** Slide 8 y README → "Cómo escala".
- **¿Qué no detecta?** Lo decimos: campañas de cuentas antiguas que rotan subgrupos, donde ningún par coincide dos
  veces (lo encontramos con sets sintéticos; probamos 4 soluciones y ninguna mejoraba sin dañar el resto).
- **¿Cómo saben que esas 24 cuentas no son gente real que opina igual?** No juzgamos la opinión sino el
  comportamiento: las mismas cuentas, en varias publicaciones distintas, empujando lo mismo a minutos de distancia, y
  formando un grupo cerrado (triángulos). Gente que opina igual coincide una vez; una operación coincide siempre. Por
  eso además mostramos el perfil (antigüedad, horario) para que una persona decida.
- **¿No es censura / no toman partido?** En práctica detecta una operación a favor del proyecto (op01) y otra en
  contra (op02). Vertiente no evalúa si una narrativa es verdadera: muestra qué circula y qué parte está empujada.
- **Si lo re-corremos, ¿da lo mismo?** Sí en la misma máquina (semillas fijas, orden determinístico, E26). En otro
  hardware (CPU vs Mac con `mps`) los embeddings cambian en decimales y puede variar algún detalle, no el resultado.

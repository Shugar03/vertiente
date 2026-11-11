"""Generador del set sintético "temas_nuevos" (prueba de generalización).

Set con el mismo formato y estilo que datos/practica pero con TEMAS y NARRATIVAS
totalmente nuevos (nada de litio, colectivos ni hospital). Todo es ficticio:
la "Provincia de Las Lomas", la ciudad de Las Lomas, Villa Cardón, Puerto Arenal,
la distribuidora DILO, la Constructora Pircas y los medios son inventados.

Uso:  uv run python sinteticos/generar_temas_nuevos.py
Salida: salida/sinteticos/temas_nuevos/ (mismo layout y columnas que la práctica).

DISEÑO
------
Estadísticas medidas en el set de práctica y replicadas aquí:
  * Comentarios por publicación ~ lognormal (q10≈60, mediana≈220, q90≈800).
  * Demora comentario-publicación lognormal (mediana≈1,3 h, q90≈5,5 h) con
    rechazo por perfil horario día/noche (pico 18-21 h, casi nada 02-05 h).
  * Ruido (narrativa 'ninguna') ≈19-20 %: gracias, emojis, menciones,
    avisos, preguntas fuera de tema propias de cada tema. El ruido nunca es respuesta.
  * Respuestas ≈14 %, siempre a un comentario con narrativa y SIEMPRE heredan la
    narrativa del padre. Respuestas cortas de acuerdo ("tal cual", ~21 %) heredan
    también la postura; respuestas con contenido invierten la postura (~99,5 %,
    medido 99,7 % en práctica). Demora de respuesta lognormal (mediana≈6 min).
  * 'rechaza' = contraargumentos propios ("la tarifa estuvo congelada…"),
    a veces "es mentira que…".
  * Ruido de redacción: muletillas (che, posta, ojo, a ver…), cierres
    ("qué bronca.", "abran los ojos."), emojis, typos, alargamientos,
    abreviaturas (q, x, pa), sin tildes, minúsculas/MAYÚSCULAS, sinónimos.
  * Actividad por cuenta de cola pesada (mediana≈6, p99≈120+); antigüedad de
    cuentas 2012-2026 con forma de la práctica; usuarios con el mismo estilo.
  * me_gusta lognormal (mediana≈2, p90≈15).

Temas (2) y narrativas (8):
  luz  (aumento de la tarifa de luz, distribuidora DILO)
    E1 El aumento de la luz es impagable para las familias
    E2 DILO cobra cada vez más y el servicio es un desastre   [cambia redacción día 6:
       "cortes/apagones" -> "baja tensión/microcortes/prestataria"]
    E3 La mitad de la factura de luz son impuestos y tasas
    E4 Los medidores nuevos marcan el doble (RUMOR emergente, lo origina Q1, 5/9 ~02 h)
  ruta (obra de la ruta provincial 12, Constructora Pircas)
    R1 La ruta 12 es una trampa mortal   [cambia redacción día 7:
       "pozos/accidentes/banquina" -> "calzada/siniestros/despistes/tramo"]
    R2 La obra de la ruta 12 tiene sobreprecios para la constructora amiga
    R3 La obra de la ruta trae turismo y trabajo a la región
    R4 Van a cobrar peaje en la ruta 12 (RUMOR emergente genuino, 6/9 ~11 h)

Campañas:
  Q1  25 cuentas creadas 1-3 días antes del período, pocos seguidores y muchos
      seguidos; originan E4 en ráfagas nocturnas (01-05 h) en 8 publicaciones,
      textos casi idénticos con hashtag #MedidorTrucho, se responden "tal cual".
      Solo actividad de campaña. Todo 'apoya' E4.
  Q2  30 cuentas viejas (2014-2021) con textos variados (plantillas genuinas),
      horario diurno, empujan 'rechaza' de R2 sincronizadas en 15 publicaciones
      (grupos de 4-9 en ~20 min) y respondiéndose entre sí; además comentarios
      sueltos de R2-rechaza y comentarios de cobertura genuinos en cualquier tema
      (etiquetados con su narrativa/postura real).
Trampa genuina: video viral del vuelco en la curva del km 40 (8/9 22:35): ~120
  cuentas genuinas distintas comentan en 30 min, muchas copiando "esa curva es la
  muerte" sin coordinación.
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20260913
rng = np.random.default_rng(SEED)
RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "salida" / "sinteticos" / "temas_nuevos"
TZ = timezone(timedelta(hours=-3))
INICIO = datetime(2026, 9, 1, 0, 0, 0, tzinfo=TZ)
DIAS = 10
FIN = INICIO + timedelta(days=DIAS) - timedelta(seconds=1)
T0 = int(INICIO.timestamp())
TFIN = int(FIN.timestamp())
N_PUB = 250
N_COMENT_OBJ = 80_000
N_CUENTAS_OBJ = 6_000

# perfil horario de comentarios (medido en práctica, % por hora)
HW = np.array([1.0, 0.6, 0.2, 0.1, 0.1, 0.1, 0.6, 2.9, 5.6, 6.3, 5.3, 5.7,
               6.5, 5.4, 4.9, 5.0, 4.9, 5.9, 7.8, 7.5, 7.5, 7.7, 5.7, 2.8])
HACC = HW / HW.max()
# perfil horario de publicaciones (práctica)
PUBH = np.array([4, 0, 0, 0, 1, 3, 23, 28, 33, 22, 35, 30, 27, 23, 31, 28,
                 32, 33, 32, 40, 34, 35, 10, 2], float)


def ts(dt: datetime) -> int:
    return int(dt.timestamp())


def iso(t: int) -> str:
    return datetime.fromtimestamp(int(t), TZ).isoformat()


def hora(t):
    return ((np.asarray(t) - T0) // 3600) % 24


def dia(t: int) -> int:
    """Día del período, 1-based."""
    return int((t - T0) // 86400) + 1


# ----------------------------------------------------------------------------
# FUENTES
# ----------------------------------------------------------------------------
FUENTES = [
    ("f01", "Diario Las Lomas", "medio"),
    ("f02", "Radio Cardón 98.3", "radio"),
    ("f03", "Canal 4 Lomas TV", "tv"),
    ("f04", "El Arenal Digital", "medio local"),
    ("f05", "Portal Sierras Hoy", "medio"),
    ("f06", "Vecinos Autoconvocados de Las Lomas", "comunidad"),
    ("f07", "Ente Provincial Regulador de la Energía", "institucional"),
    ("f08", "Vialidad Provincial de Las Lomas", "institucional"),
]
FUENTE_W = {"luz": [105, 89, 87, 63, 63, 58, 30, 3], "ruta": [105, 89, 87, 63, 63, 58, 3, 30]}

# ----------------------------------------------------------------------------
# NARRATIVAS
# ----------------------------------------------------------------------------
NARR = {}

NARR["E1"] = dict(
    tema="luz", titulo="El aumento de la luz es impagable para las familias",
    frases="impagable|aumento|factura|sueldo|no llego", base=1.0, p_apoya=0.58,
    apoya=[
        "con este aumento de la luz no llego a fin de mes",
        "me vino una factura de luz que es más que el alquiler",
        "la factura de la luz se llevó medio sueldo",
        "es impagable la luz, tengo que elegir entre comer o pagar la factura",
        "un 180% de aumento y los sueldos están planchados",
        "los jubilados no pueden pagar esta tarifa, es una locura",
        "apagamos todo y aun así la factura vino el triple",
        "vamos a terminar cocinando a leña con estas tarifas",
        "nadie puede pagar 90 lucas de luz con un sueldo mínimo",
        "el comercio no aguanta otra factura así, vamos a tener que cerrar",
        "subieron la luz tres veces en el año y el sueldo una sola",
        "en mi casa somos cinco y la factura ya no se puede pagar",
        "con el calor que hace acá no podés vivir sin ventilador y la luz está imposible",
        "esta tarifa es un saqueo a las familias trabajadoras",
        "tuve que dejar de pagar otras cosas para cubrir la factura de la luz",
        "la gente se va a colgar de los cables porque no puede pagar",
        "pagar la luz hoy es un lujo",
    ],
    rechaza=[
        "la tarifa estuvo congelada cuatro años, en algún momento tenía que subir",
        "seguimos pagando la luz más barata que en cualquier provincia vecina",
        "es mentira que sea impagable, si pedís la tarifa social pagás la mitad",
        "el aumento es en cuotas, no es todo de golpe como dicen",
        "si dejás el aire prendido todo el día obvio que te viene alta",
        "un paquete de cigarrillos sale más que la luz del mes, no exageren",
        "sin aumento la distribuidora no invierte y después se quejan",
        "el que tiene consumo normal paga lo mismo que una pizza, revisen el consumo",
        "lo impagable era tener subsidios que pagábamos todos con la inflación",
        "comparen la factura con hace un año y en pesos reales subió poco",
        "la mayoría de los barrios tiene tarifa social y ni se enteran",
        "hay que cuidar el consumo, no todo es culpa del aumento",
        "no es para tanto, a mí me vino casi igual que el mes pasado",
        "los que más se quejan son los que tienen pileta climatizada",
        "el aumento fuerte es solo para los consumos altos, lean el cuadro tarifario",
        "mentira que nadie puede pagarla, en mi barrio todos pagamos sin drama",
    ],
)

NARR["E2"] = dict(
    tema="luz", titulo="DILO cobra cada vez más y el servicio es un desastre",
    frases="cortes|apagón|sin luz|baja tensión|microcortes|prestataria", base=1.1, p_apoya=0.60,
    cambia_dia=6,
    apoya=[
        "pagamos fortunas y DILO nos deja sin luz cada dos días",
        "otro apagón en el barrio y la factura llega puntual",
        "tres cortes esta semana y nadie de DILO da explicaciones",
        "cobran como si fuera Suiza y tenemos cortes como en el siglo pasado",
        "anoche estuvimos seis horas sin luz y DILO ni atiende el teléfono",
        "cada vez que llueve se corta la luz, y la factura igual sube",
        "que primero arreglen los cortes y después aumenten",
        "se me pudrió todo lo de la heladera por el apagón y nadie se hace cargo",
        "DILO es un desastre, cortes todos los días y cobran lo que quieren",
        "en Villa Cardón pasamos más horas sin luz que con luz",
        "llamás para reclamar el corte y te tienen una hora en espera",
        "DILO se lleva la plata y los apagones siguen igual",
        "vivo en el centro y igual se corta la luz todas las noches",
        "un servicio malísimo, cortes y más cortes, y encima aumentan",
        "pagamos por un servicio que no tenemos, otro corte de cuatro horas",
        "DILO cobra cada mes más y los apagones no paran",
    ],
    rechaza=[
        "los cortes de esta semana fueron por la tormenta, no por DILO",
        "en mi barrio hace meses que no hay un solo corte",
        "es mentira que se corte todos los días, fue un apagón puntual",
        "los cortes son porque la gente se cuelga de la red, no culpen a DILO",
        "la cuadrilla vino en media hora y lo arreglaron, hay que ser justos",
        "con tarifas congeladas años nadie podía invertir, por eso los cortes",
        "el apagón fue en toda la región, falló la línea de alta tensión nacional",
        "comparado con hace diez años hay muchísimos menos cortes",
        "los cortes programados se avisan con días de anticipación, lean los avisos",
        "el servicio mejoró desde que cambiaron los transformadores del centro",
        "siempre que llueve fuerte se corta en cualquier lado, no es un problema de DILO",
        "yo reclamé por la app y me resolvieron el corte en una hora",
        "si no pagan la luz cómo quieren que DILO mantenga la red",
        "exageran, un corte de veinte minutos no es un desastre",
        "la red es vieja porque nadie quería pagar tarifas reales, ahora están invirtiendo",
    ],
    apoya2=[
        "la tensión está por el piso, se me quemó el lavarropas y la prestataria no se hace cargo",
        "microcortes toda la noche, la tele se prende y se apaga, y cada vez más cara",
        "la luz parpadea todo el día, ya se me quemaron dos cargadores",
        "con la baja tensión no arranca ni la bomba de agua, y pagamos tarifa plena",
        "la prestataria factura como empresa de primera y entrega un servicio de cuarta",
        "otra vez variaciones de tensión, se fundió la heladera nueva",
        "no invierten un peso en la red y nos cobran como si fuera de oro",
        "el transformador de la esquina explota cada vez que hace calor",
        "vas a reclamar el electrodoméstico quemado y te piden mil papeles",
        "baja tensión desde las siete de la tarde, no se puede ni prender el aire",
        "la prestataria se llena los bolsillos y los cables cuelgan en la vereda",
        "microcortes cada media hora, el router se reinicia todo el día",
        "cobran tarifa nueva con una red de hace cuarenta años",
        "se nos quemó la compu por un pico de tensión, nadie responde",
        "pagamos una fortuna para tener una luz que parpadea como boliche",
        "el servicio da vergüenza, focos que titilan y tensión de 170 volts",
    ],
    rechaza2=[
        "los microcortes son por la obra de la subestación, en dos semanas se termina",
        "la baja tensión es porque todo el barrio prende el aire a la vez",
        "es mentira que no inviertan, están cambiando los transformadores barrio por barrio",
        "a mí me pagaron el electrodoméstico quemado en diez días, hay que reclamar bien",
        "las variaciones de tensión son por las conexiones clandestinas, no por la prestataria",
        "pongan un estabilizador, la red nunca va a ser perfecta",
        "la tensión en mi casa está perfecta, no pasa en toda la ciudad",
        "la prestataria ya instaló reguladores nuevos en el centro y mejoró muchísimo",
        "si el transformador explota es porque está sobrecargado de colgados",
        "el servicio anda mejor que nunca, los picos de tensión son excepcionales",
        "la red se está renovando, eso lleva tiempo y plata",
        "un parpadeo de vez en cuando no justifica decir que el servicio es un desastre",
        "con lo que cobraban antes no alcanzaba ni para cambiar un cable",
        "el lavarropas se te quema por viejo, no por la tensión",
        "los técnicos midieron y la tensión está dentro de lo normal",
    ],
)

NARR["E3"] = dict(
    tema="luz", titulo="La mitad de la factura de luz son impuestos y tasas",
    frases="impuestos|tasas|IVA|cargos|tasa municipal", base=0.55, p_apoya=0.55,
    apoya=[
        "la mitad de la factura son impuestos, la energía es lo de menos",
        "miren el detalle de la factura: tasa municipal, IVA, fondo provincial, un robo",
        "el municipio se cuelga de la factura de luz para cobrar sus tasas",
        "si sacaran los impuestos pagaríamos la mitad",
        "pagamos más de impuestos que de luz, es increíble",
        "el IVA y la tasa de alumbrado son el 45% de lo que pago",
        "que la provincia baje los impuestos en vez de culpar a la distribuidora",
        "en la factura hay cinco cargos que nadie sabe para qué son",
        "el fondo de obras provincial lo pagamos en cada factura y obras no veo",
        "el gobierno recauda con la luz y después se hace el que nos defiende",
        "lean la factura: el consumo es 30 lucas y los impuestos otros 30",
        "la tasa de alumbrado público en la factura es un abuso, si la calle está a oscuras",
        "el verdadero aumento son los impuestos que agregan cada mes",
        "nos cobran impuesto sobre impuesto en la factura de luz",
        "la luz no es cara, lo caro son las tasas que le cuelgan",
        "que eliminen la tasa municipal de la factura y listo",
    ],
    rechaza=[
        "los impuestos son un 20% de la factura, no la mitad como dicen",
        "es mentira que la mitad sean impuestos, lo que subió fue el precio de la energía",
        "la tasa de alumbrado paga las luces de tu calle, no es un robo",
        "el IVA está en todo, no es algo especial de la luz",
        "sin el fondo provincial no se hubiera hecho la línea a Villa Cardón",
        "echarle la culpa a los impuestos es lo que quiere DILO para no bajar su tarifa",
        "saquen la cuenta bien, los cargos fijos son una parte chica",
        "los impuestos de la factura son los mismos de hace años, lo que aumentó es la energía",
        "si sacan la tasa municipal después no hay plata para el alumbrado y se quejan igual",
        "no confundan, el aumento grande vino del cargo de energía, no de las tasas",
        "en otras provincias los impuestos en la factura son mucho más altos",
        "la parte de impuestos es fija, no explica que la factura se haya duplicado",
        "el fondo de obras se ve en los transformadores nuevos, no digan que no",
        "es fácil culpar a los impuestos, pero el kilowatt subió 150%",
        "miré mi factura y los impuestos son menos de un cuarto",
    ],
)

NARR["E4"] = dict(
    tema="luz", titulo="Los medidores nuevos marcan el doble del consumo real",
    frases="medidor nuevo|marcan el doble|recambio|medidor digital|#MedidorTrucho",
    base=0.75, p_apoya=0.52, emergente=True,
    apoya=[
        "desde que me pusieron el medidor nuevo la factura vino el doble",
        "dicen que los medidores digitales están calibrados para cobrar de más",
        "a mi vecino le cambiaron el medidor y le llegó el triple, no es casualidad",
        "no dejen que les cambien el medidor, los nuevos marcan cualquier cosa",
        "el medidor nuevo gira aunque tengas todo desenchufado",
        "por algo cambian los medidores justo ahora, para facturar el doble",
        "mi tía bajó la térmica y el medidor digital seguía sumando",
        "con el medidor viejo pagaba 20 lucas, con el nuevo 45, mismo consumo",
        "en todo el barrio pasa lo mismo desde el recambio de medidores",
        "el recambio de medidores es un negocio para cobrarnos más",
        "me llegó un audio de un técnico que dice que los medidores nuevos marcan de más",
        "pidan contraste del medidor, el nuevo me marcaba casi el doble",
        "los medidores inteligentes cuentan hasta la energía que no usás",
        "si te cambiaron el medidor revisá la factura, a todos nos vino doble",
        "el medidor digital es trucho, cuenta más rápido que el viejo",
        "no es el aumento, es el medidor nuevo que marca el doble",
    ],
    rechaza=[
        "es mentira que los medidores nuevos marquen el doble, el ente los controla uno por uno",
        "el medidor viejo marcaba de menos porque estaba gastado, por eso ahora pagás lo real",
        "eso de los medidores truchos es una cadena de WhatsApp, no tiene ninguna prueba",
        "la factura vino alta por el aumento y el calor, no por el medidor",
        "a mí me cambiaron el medidor y pago exactamente lo mismo",
        "si dudás pedí el contraste, es gratis y lo hacen técnicos del ente",
        "ese audio del técnico es falso, ya lo desmintió el ente regulador",
        "los medidores digitales son más precisos, no cobran de más",
        "dejen de difundir lo de los medidores, son cuentas truchas las que lo empezaron",
        "nadie pudo mostrar un solo medidor nuevo que marque el doble",
        "el recambio se hace en todo el país hace años y nunca pasó eso",
        "comparen el consumo en kilowatts, no la plata, y van a ver que es igual",
        "el medidor no gira si desenchufás todo, seguro te quedó algo prendido",
        "otro verso de las redes, los medidores están homologados",
        "fake total lo del medidor que marca doble, miren quiénes lo comparten",
    ],
)

NARR["R1"] = dict(
    tema="ruta", titulo="La ruta 12 es una trampa mortal",
    frases="pozos|accidentes|banquina|siniestros|calzada|despiste", base=1.25, p_apoya=0.58,
    cambia_dia=7,
    apoya=[
        "la ruta 12 está llena de pozos, es cuestión de tiempo que haya otra tragedia",
        "otro accidente en la 12, ya no se puede viajar tranquilo",
        "la banquina no existe, si pinchás te morís",
        "los pozos de la 12 rompen cubiertas todos los días",
        "manejo todos los días a Villa Cardón y es jugarse la vida",
        "cuántos muertos más hacen falta para que arreglen la ruta",
        "de noche la 12 es una boca de lobo, sin pintura ni carteles",
        "se me rompió el auto en un pozo enorme a la altura del km 30",
        "en la 12 esquivás pozos y camiones, es un peligro",
        "mi hijo viaja todos los días por esa ruta y vivo con miedo",
        "esa ruta ya se cobró demasiadas vidas",
        "la 12 está destruida, parece un camino de tierra",
        "no hay un solo cartel en la curva del km 40, ahí se mata gente",
        "los accidentes en la ruta 12 son todas las semanas",
        "con lluvia los pozos ni se ven, es una trampa",
        "la ruta está tan rota que los camiones van por el medio",
    ],
    rechaza=[
        "la mayoría de los accidentes son por exceso de velocidad, no por los pozos",
        "la 12 está fea pero si manejás despacio no pasa nada",
        "es mentira que haya accidentes todas las semanas, miren las estadísticas",
        "el problema es la gente que maneja alcoholizada, no la ruta",
        "ya taparon los pozos del tramo norte, está mucho mejor",
        "hay rutas mucho peores en la provincia y no se dice nada",
        "si respetaran la doble línea no habría tantos choques",
        "yo la hago todos los días hace veinte años y nunca tuve un problema",
        "no culpen a la ruta por los que adelantan en curva",
        "los camioneros manejan como locos, eso es lo peligroso",
        "están bacheando hace dos semanas, ya no es como antes",
        "es una ruta normal, el peligro es la imprudencia",
        "la ruta tiene sus pozos pero no es para tanto, exageran",
        "con luces bajas y a 80 se viaja perfecto",
        "los accidentes bajaron desde que pusieron el control policial",
    ],
    apoya2=[
        "otro siniestro vial en la cuesta, la calzada está deformada y nadie hace nada",
        "la señalización del tramo Las Lomas-Cardón es nula, por eso los despistes",
        "la calzada tiene ahuellamientos que te sacan del carril",
        "en la cuesta la calzada es angosta y sin defensas, un despiste y caés al barranco",
        "tres siniestros en el mismo tramo en un mes, eso no es casualidad",
        "sin demarcación horizontal de noche no ves por dónde vas",
        "el tramo de la cuesta necesita guardarraíles urgente",
        "la calzada se desarma con cada lluvia y los despistes se multiplican",
        "vialidad sabe que ese tramo es letal y no pone ni un reductor",
        "la cuesta sin iluminación ni defensas es una sentencia",
        "las banquinas descalzadas provocan la mitad de los despistes",
        "el tramo nuevo ya tiene fisuras y los siniestros siguen",
        "esa curva sin peralte es la que se lleva vidas",
        "con esa calzada destruida cualquier maniobra termina en vuelco",
        "no hay carteles de velocidad máxima en todo el tramo",
        "esa curva es la muerte, la calzada te tira para afuera",
    ],
    rechaza2=[
        "los siniestros del tramo son por velocidad, la calzada no tiene nada que ver",
        "la cuesta está bien señalizada, el que se despista es porque va rápido",
        "es mentira que no haya defensas, pusieron guardarraíles el mes pasado",
        "la demarcación está recién pintada, pasen de día y miren",
        "un despiste a la madrugada con alcohol no es culpa de vialidad",
        "la calzada nueva está impecable, el problema es el conductor",
        "con la velocidad adecuada esa curva se toma sin problemas",
        "los siniestros viales bajaron en el tramo desde los controles",
        "si cada vuelco es culpa de la ruta nadie se hace cargo de cómo maneja",
        "las banquinas se están recalzando, ya vi las máquinas",
        "la señalización está, lo que falta es respetarla",
        "el tramo de la cuesta es igual que siempre, antes no se quejaban",
        "fue un error humano, el informe de vialidad lo dice clarito",
        "los camiones con sobrecarga son los que rompen la calzada y chocan",
        "la curva tiene carteles y reductores, no se puede pedir más",
    ],
)

NARR["R2"] = dict(
    tema="ruta", titulo="La obra de la ruta 12 tiene sobreprecios para la constructora amiga",
    frases="sobreprecios|Pircas|licitación|amigos|certificados", base=0.8, p_apoya=0.55,
    apoya=[
        "la obra de la 12 cuesta el triple que cualquier ruta del país, sobreprecios por todos lados",
        "Pircas ganó la licitación de casualidad, el dueño es amigo del gobernador",
        "pagaron 40 kilómetros y hicieron 15, dónde está la plata",
        "adjudicaron la obra sin competencia, todo arreglado",
        "la constructora cobró los anticipos y la obra avanza a paso de tortuga",
        "cada mes hay una redeterminación de precios, un curro",
        "el presupuesto se duplicó en un año y la ruta sigue igual",
        "la plata de la ruta se la repartieron entre los amigos de siempre",
        "que muestren las certificaciones de obra, ahí está el negocio",
        "con lo que se pagó podrían haber hecho dos rutas nuevas",
        "Pircas no tiene experiencia en rutas y se llevó la obra más grande de la provincia",
        "pagan por metro de asfalto que nunca se puso",
        "es la caja del gobierno, la ruta es la excusa",
        "la licitación fue un dibujo, se presentó una sola empresa",
        "sobreprecios del 200% según el informe de los concejales",
        "alguien se está haciendo rico con la ruta 12 y no somos nosotros",
    ],
    rechaza=[
        "la obra tiene control del tribunal de cuentas, si hubiera sobreprecios ya saltaba",
        "es mentira que se pagó por kilómetros que no se hicieron, los certificados son públicos",
        "se presentaron cuatro empresas a la licitación, está en el boletín oficial",
        "el costo subió por la inflación del asfalto, no por un curro",
        "la obra avanza, pasé ayer y ya están asfaltando el tramo de la cuesta",
        "hablar de sobreprecios sin pruebas es fácil, que presenten la denuncia",
        "el precio por kilómetro es similar al de otras rutas de montaña",
        "la constructora es de la provincia y da trabajo a gente de acá",
        "el informe de los concejales mezcla presupuesto con redeterminación, no es lo mismo",
        "en montaña cada kilómetro sale más caro, no se puede comparar con la llanura",
        "siempre lo mismo, se hace una obra y aparecen los que dicen que se robaron todo",
        "la auditoría externa no encontró ninguna irregularidad",
        "los anticipos son normales en cualquier obra pública",
        "prefiero una ruta que avanza a que no se haga nada por miedo a las denuncias",
        "los que hablan de curro nunca miraron el expediente",
        "la empresa ya terminó dos tramos en tiempo, los números cierran",
    ],
)

NARR["R3"] = dict(
    tema="ruta", titulo="La obra de la ruta trae turismo y trabajo a la región",
    frases="turismo|trabajo|desarrollo|conectar|productores", base=0.6, p_apoya=0.5,
    apoya=[
        "con la ruta nueva van a venir muchos más turistas a Villa Cardón",
        "la obra le da trabajo a más de 300 personas de la zona",
        "los productores van a poder sacar la cosecha en la mitad de tiempo",
        "una ruta buena es desarrollo para todo el oeste de la provincia",
        "mi hermano entró a trabajar en la obra, por fin un trabajo en blanco",
        "las cabañas de Cardón ya tienen reservas pensando en la ruta nueva",
        "con la ruta terminada Puerto Arenal queda a una hora de Las Lomas",
        "cada obra pública mueve la economía del pueblo, el almacén vende el doble",
        "conectar los pueblos es lo mejor que le puede pasar a la región",
        "los camiones de fruta van a llegar más rápido al mercado",
        "el turismo de montaña va a explotar con una ruta como la gente",
        "por fin una obra que piensa en el interior",
        "los gomeros, las estaciones de servicio, todos ganan con la ruta",
        "es la obra más importante en décadas para el oeste",
        "los chicos del pueblo van a poder ir a la facultad en Las Lomas y volver en el día",
    ],
    rechaza=[
        "los turistas no vienen por una ruta, vienen si hay algo para hacer",
        "el trabajo de la obra dura lo que dura la obra, después se van todos",
        "es mentira que contrataron gente de acá, la mayoría vino de afuera",
        "la ruta nueva va a servir para que los camiones pasen más rápido, nada más",
        "a Villa Cardón no la va a salvar una ruta, faltan servicios básicos",
        "con la ruta rápida la gente va a pasar de largo y no va a parar en el pueblo",
        "el turismo es un verso, ni hotel hay en Cardón",
        "los productores necesitan agua y precios justos, no asfalto",
        "trabajo precario por dos años y después nada",
        "la ruta beneficia a las mineras y a los camiones, no a los vecinos",
        "nos vendieron lo del desarrollo en cada obra y seguimos igual",
        "el comercio del pueblo va a perder porque todos van a comprar a Las Lomas",
        "los 300 puestos son en su mayoría changas de tres meses",
        "si no hay inversión en el pueblo, la ruta sola no cambia nada",
        "más turismo también es más basura y precios caros para los de acá",
    ],
)

NARR["R4"] = dict(
    tema="ruta", titulo="Van a cobrar peaje en la ruta 12 cuando la terminen",
    frases="peaje|cabina|concesión|cobrar|privatizar", base=1.2, p_apoya=0.5, emergente=True,
    apoya=[
        "ya está decidido, cuando terminen la ruta ponen un peaje en el km 20",
        "dicen que la ruta 12 la van a concesionar y cobrar peaje",
        "me contaron que ya están armando la cabina del peaje cerca del cruce",
        "la obra la pagamos nosotros y encima nos van a cobrar peaje",
        "el plan de mantenimiento es la excusa para meter un peaje",
        "un amigo de vialidad dice que el peaje va a salir como 5 lucas",
        "privatizan la 12 y vamos a pagar para ir a trabajar",
        "vieron el plano? hay una playa de peaje en el km 35",
        "a los que vivimos en Cardón nos van a cobrar peaje para ir al hospital",
        "por eso la hacen ahora, para concesionarla con peaje",
        "primero la ruta, después el peaje, siempre igual",
        "si ponen peaje los productores no pueden sacar la mercadería",
        "el peaje en la 12 ya está en el pliego, léanlo",
        "nos van a cobrar peaje por una ruta que pagamos con impuestos",
        "la concesión del peaje ya tiene dueño",
    ],
    rechaza=[
        "es mentira lo del peaje, vialidad dijo que la ruta sigue siendo libre",
        "no hay ningún peaje en el pliego, lo leí completo",
        "lo de la cabina es la báscula para pesar camiones, no un peaje",
        "una ruta provincial con ese tránsito no puede tener peaje por ley",
        "otro rumor de WhatsApp, nadie mostró un papel que diga peaje",
        "el plan de mantenimiento lo paga la provincia, no los usuarios",
        "la playa del km 35 es un control de vialidad, dejen de inventar",
        "el ministro ya desmintió lo del peaje en la radio",
        "si fuera a haber peaje tendría que pasar por la legislatura",
        "lo del peaje lo inventaron para desprestigiar la obra",
        "en ninguna ruta provincial de acá se cobra peaje",
        "pregunten en vialidad antes de difundir lo del peaje",
        "eso del peaje es verso, la obra es pública y sigue siendo pública",
        "la cabina que ven es del obrador, la sacan cuando termina la obra",
        "no hay concesión, la ruta la mantiene vialidad provincial",
    ],
)
TEMA_NARR = {"luz": ["E1", "E2", "E3", "E4"], "ruta": ["R1", "R2", "R3", "R4"]}

# ----------------------------------------------------------------------------
# TEXTOS DE RUIDO Y RESPUESTAS CORTAS
# ----------------------------------------------------------------------------
RUIDO_GENERICO = [
    "Gracias por la info", "Gracias por avisar", "Comparto", "👀", "🙏🙏", "😂😂", "Buen día!",
    "jajaja", "Fuerza vecinos", "Qué calor hace hoy", "Alguien sabe si mañana hay clases?",
    "Feliz cumple Coti!!", "Sorteo en mi perfil 🎁", "Vendo bici rodado 26, interesados al privado",
    "Y el clásico del domingo?", "Ni idea", "Veremos", "Qué locura", "Uff", "Bendiciones",
    "Primera!", "Info importante", "Dios mío", "Increíble", "Mmm", "Ya fue", "Qué día",
    "Buenas noches", "Cuídense", "Alguien perdió un perro negro en barrio San José?",
    "Se busca empleada para limpieza, mandar mensaje", "Hermosa foto", "Qué lindo el atardecer de hoy",
    "Buen finde a todos", "Alguien sabe a qué hora abre el banco?", "Mañana hay feria en la plaza",
    "Me sumo", "Compartan", "Arriba Las Lomas!", "👏👏", "🔥🔥", "Saludos desde Puerto Arenal",
    "Hola a todos", "Qué tristeza", "No puede ser", "jaja posta", "Ojalá", "Hay que ver",
    "Dónde se consigue garrafa?", "Cuál es la farmacia de turno?", "Escuchen la radio ahora!",
    "Están transmitiendo en vivo?", "Gracias por informar", "Amén", "Un abrazo grande a todos",
]
MENCIONES = ["@{u} mirá esto", "@{u} viste?", "@{u} te dije", "@{u} @{v} lean", "@{u} 👀"]
PREG_TEMA = {
    "luz": [
        "Dónde se paga la factura?", "Alguien sabe hasta cuándo vence la factura?",
        "A qué número se llama por un corte?", "Mañana cortan la luz en barrio Norte?",
        "Cómo se pide la tarifa social?", "Se puede pagar en cuotas?",
        "Dónde queda la oficina de DILO?", "Alguien tiene el link para ver la factura online?",
        "En Villa Cardón también aumentó?", "Qué horario atiende el ente?",
        "Hay que llevar DNI para el reclamo?", "La app de DILO anda?",
        "A qué hora es la audiencia pública?",
    ],
    "ruta": [
        "Está habilitado el tramo a Villa Cardón?", "Alguien sabe cómo está la ruta ahora?",
        "Hay desvío por la 12?", "Se puede pasar con auto chico?", "A qué hora cortan el tránsito?",
        "Cuánto se tarda hasta Puerto Arenal?", "Hay control policial en el km 40?",
        "Dónde queda el obrador?", "La estación de servicio del cruce está abierta?",
        "Hay niebla en la cuesta?", "Por dónde conviene ir a Cardón?",
        "Mañana hay corte de ruta?", "Pasa el micro a Cardón igual?",
    ],
}
RUIDO_TRAMPA = ["Dios mío", "Qué miedo", "Espero que el chofer esté bien", "Fuerza a la familia",
                "Qué horror", "🙏🙏🙏", "Alguien sabe cómo está el chofer?", "Terrible el video"]
CORTAS = [
    "Tal cual", "Exacto", "Totalmente", "Coincido", "Así es", "Es así", "100% de acuerdo",
    "Lo mismo digo", "Eso mismo pienso", "Ni más ni menos", "Clarísimo", "Mil por ciento",
    "Lo firmo", "Totalmente de acuerdo", "Y sí", "Nada más que agregar", "Dijiste todo",
    "Ni hablar", "Es así nomás", "Bien dicho", "Posta", "Banco esto",
]
PREFIJOS = ["che,", "posta,", "ojo,", "a ver,", "la verdad,", "sinceramente", "mirá,", "escuchen:",
            "te digo algo:", "jaja", "para mí", "hay que decirlo:", "lo que nadie dice es que",
            "y bueno,", "no sé ustedes pero", "en serio,", "vecinos,", "una cosa:", "bueno,",
            "la verdad que", "como siempre,"]
CIERRES = ["posta", "en serio", "qué vergüenza", "así estamos", "abran los ojos", "qué bronca",
           "lamentable", "es así", "una locura", "basta", "despierten", "y nadie dice nada",
           "ni hablar", "triste", "no da más", "te juro"]
EMOJIS = ["😡", "🤬", "🙄", "💯", "👏", "😔", "😤", "🔥", "😩", "🤦", "💡", "🚧", "⚡", "😒", "🤷"]
SINONIMOS = [
    (r"\bfactura\b", ["boleta", "factura", "factura"]), (r"\bplata\b", ["guita", "plata", "plata"]),
    (r"\btrabajo\b", ["laburo", "trabajo", "trabajo"]), (r"\bauto\b", ["auto", "coche"]),
    (r"\bdicen\b", ["dicen", "comentan"]), (r"\bes mentira\b", ["es mentira", "es falso", "es mentira"]),
    (r"\bmuchísimos\b", ["muchísimos", "re muchos"]), (r"\btodos los días\b", ["todos los días", "cada día"]),
    (r"\bmuy\b", ["muy", "re"]), (r"\bla gente\b", ["la gente", "los vecinos"]),
]
ABREV = [(r"\bque\b", "q"), (r"\bpor\b", "x"), (r"\bpara\b", "pa"), (r"\bporque\b", "xq"),
         (r"\btambién\b", "tmb"), (r"\bmás\b", "mas")]
PROPIOS = ("DILO", "Pircas", "Villa", "Las Lomas", "Cardón", "Puerto", "IVA")


def sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn" or c == "̃")


def typo(s: str, r) -> str:
    palabras = s.split(" ")
    idx = [i for i, w in enumerate(palabras) if len(w) > 4 and w.isalpha()]
    if not idx:
        return s
    i = idx[r.integers(len(idx))]
    w = palabras[i]
    k = r.random()
    if k < 0.45:  # trasposición
        j = r.integers(1, len(w) - 2)
        w = w[:j] + w[j + 1] + w[j] + w[j + 2:]
    elif k < 0.75:  # alargamiento
        if w[-1] in "aeiouáéíóú":
            w = w + w[-1] * int(r.integers(2, 5))
        else:
            j = r.integers(1, len(w) - 1)
            w = w[:j] + w[j] + w[j:]
    else:  # letra perdida
        j = r.integers(1, len(w) - 1)
        w = w[:j] + w[j + 1:]
    palabras[i] = w
    return " ".join(palabras)


def empieza_propio(s: str) -> bool:
    return s.startswith(PROPIOS)


def render(base: str, r, nivel: float = 1.0) -> str:
    s = base
    for pat, opts in SINONIMOS:
        if re.search(pat, s) and r.random() < 0.5 * nivel:
            s = re.sub(pat, opts[r.integers(len(opts))], s, count=1)
    if r.random() < 0.42 * nivel:
        p = PREFIJOS[r.integers(len(PREFIJOS))]
        s = p + " " + (s if empieza_propio(s) else s[0].lower() + s[1:])
    if r.random() < 0.85 and not empieza_propio(s):
        s = s[0].upper() + s[1:]
    u = r.random()
    if u < 0.30 * nivel:
        c = CIERRES[r.integers(len(CIERRES))]
        s = s + (". " + c.capitalize() + "." if r.random() < 0.6 else ", " + c + ".")
    elif u < 0.65:
        s = s + "."
    if r.random() < 0.25 * nivel:
        e = EMOJIS[r.integers(len(EMOJIS))]
        s = s + " " + e * (1 if r.random() < 0.8 else 2)
    if r.random() < 0.12 * nivel:
        pat, rep = ABREV[r.integers(len(ABREV))]
        s = re.sub(pat, rep, s)
    if r.random() < 0.16 * nivel:
        s = typo(s, r)
    if r.random() < 0.18 * nivel:
        s = sin_tildes(s)
    u = r.random()
    if u < 0.2 * nivel:
        s = s.lower()
    elif u < 0.2 * nivel + 0.025 * nivel:
        s = s.upper()
    return s


def render_corto(base: str, r) -> str:
    s = base
    u = r.random()
    if u < 0.25:
        s = s.lower()
    elif u < 0.29:
        s = s.upper()
    if r.random() < 0.15:
        s = sin_tildes(s)
    if r.random() < 0.08:
        s = s + s[-1] * int(r.integers(2, 5))
    if r.random() < 0.12:
        s = s + " " + EMOJIS[r.integers(len(EMOJIS))]
    if r.random() < 0.08:
        s = s + "!!"
    return s


def texto_narr(nid: str, postura: str, t: int, r, nivel: float = 1.0) -> str:
    n = NARR[nid]
    lista = n[postura]
    cd = n.get("cambia_dia")
    if cd:
        d = dia(t)
        p_nueva = 0.0 if d < cd else (0.65 if d == cd else 0.92)
        if r.random() < p_nueva:
            lista = n[postura + "2"]
    return render(lista[r.integers(len(lista))], r, nivel)


# ----------------------------------------------------------------------------
# CUENTAS
# ----------------------------------------------------------------------------
NOMBRES = ["lu", "flor", "tati", "pocho", "chino", "juanchi", "mica", "agus", "sofi", "nacho", "gonza",
           "rami", "caro", "vale", "fer", "pato", "mati", "lucas", "cami", "belu", "nico", "santi",
           "rocio", "maxi", "euge", "dani", "pao", "gaby", "ceci", "marian", "facu", "joaco", "juli",
           "mili", "coti", "tomi", "lolo", "negro", "flaca", "gringo", "colo", "rusa", "pela", "yani",
           "noe", "vir", "eli", "andre", "seba", "fede", "marce", "beto", "cacho", "susi", "nene"]
SUFIJOS = ["lomas", "cardon", "arenal", "oeste", "sierra", "ok", "real", "ar", "oficial", "x", "", "", ""]
ANIOS = {2012: 756, 2013: 1563, 2014: 1535, 2015: 1495, 2016: 1440, 2017: 1362, 2018: 1257, 2019: 1108,
         2020: 1123, 2021: 1079, 2022: 950, 2023: 833, 2024: 709, 2025: 558, 2026: 223}


def usuario_genuino(r, usados: set) -> str:
    while True:
        if r.random() < 0.04:
            u = f"user{r.integers(1000, 999999)}"
        else:
            b = NOMBRES[r.integers(len(NOMBRES))]
            suf = SUFIJOS[r.integers(len(SUFIJOS))]
            sep = ["", "_", "."][r.integers(3)] if suf else ""
            dig = "" if r.random() < 0.2 else str(r.integers(1, 10 ** int(r.integers(1, 4))))
            u = f"{b}{sep}{suf}{dig}"
        if u not in usados:
            usados.add(u)
            return u


def fecha_creacion(r, anio=None) -> str:
    if anio is None:
        a = list(ANIOS)
        w = np.array(list(ANIOS.values()), float)
        anio = a[r.choice(len(a), p=w / w.sum())]
    ini = datetime(anio, 1, 1)
    fin = datetime(2026, 8, 31) if anio == 2026 else datetime(anio, 12, 31)
    d = ini + timedelta(days=int(r.integers(0, (fin - ini).days + 1)))
    return d.strftime("%Y-%m-%d")


# ----------------------------------------------------------------------------
# PUBLICACIONES
# ----------------------------------------------------------------------------
TITULARES = {
    "luz": [
        ("El ente regulador aprobó un aumento del 180% en la tarifa de luz", ["E1"]),
        ("Así queda la factura de luz: el detalle por categoría", ["E1", "E3"]),
        ("Jubilados reclaman frente a las oficinas de DILO por las facturas", ["E1"]),
        ("Comerciantes del centro advierten que no pueden pagar la luz", ["E1"]),
        ("Apagón en seis barrios de Las Lomas durante la noche", ["E2"]),
        ("Villa Cardón lleva tres días con cortes de luz intermitentes", ["E2"]),
        ("DILO anunció un plan de inversión en transformadores", ["E2"]),
        ("Cuánto pagamos de impuestos en cada factura de luz", ["E3"]),
        ("El municipio defiende la tasa de alumbrado incluida en la boleta", ["E3"]),
        ("La Legislatura debate quitar impuestos provinciales de la factura", ["E3"]),
        ("Cómo tramitar la tarifa social de energía", ["E1"]),
        ("Audiencia pública por la tarifa eléctrica: quiénes hablaron", ["E1", "E2", "E3"]),
        ("DILO avanza con el recambio de medidores en barrio Norte", []),
    ],
    "luz_d6": [("Vecinos denuncian electrodomésticos quemados por bajas de tensión", ["E2"])],
    "luz_e4": [
        ("Vecinos aseguran que la factura subió tras el recambio de medidores", ["E4"]),
        ("DILO: \"los medidores digitales están homologados y controlados\"", ["E4"]),
        ("El ente regulador ofrece contrastes gratuitos de medidores", ["E4"]),
    ],
    "ruta": [
        ("Grave accidente en la ruta 12 a la altura del km 40", ["R1"]),
        ("Vecinos de Villa Cardón cortan la ruta 12 en reclamo por los pozos", ["R1"]),
        ("Vialidad Provincial comenzó el bacheo del tramo norte de la ruta 12", ["R1", "R2"]),
        ("Concejales piden informes sobre el costo de la obra de la ruta 12", ["R2"]),
        ("La obra de la ruta 12 ya consumió el 70% del presupuesto", ["R2"]),
        ("Constructora Pircas: \"la obra avanza según lo previsto\"", ["R2"]),
        ("El tribunal de cuentas auditará la obra de la ruta 12", ["R2"]),
        ("Cabañeros de Villa Cardón esperan una temporada récord con la ruta nueva", ["R3"]),
        ("La obra de la ruta 12 emplea a 320 trabajadores", ["R3"]),
        ("Productores del oeste celebran el avance de la ruta 12", ["R3"]),
        ("Recorrido por la obra: así avanza el tramo de la cuesta", ["R1", "R2", "R3"]),
        ("Inauguraron el primer tramo repavimentado de la ruta 12", ["R3", "R2"]),
    ],
    "ruta_r4": [
        ("Vialidad desmiente que vaya a haber peaje en la ruta 12", ["R4"]),
        ("Qué es la estructura que construyen en el km 35 de la ruta 12", ["R4"]),
    ],
}
T_R4_POST = ts(datetime(2026, 9, 6, 11, 20, tzinfo=TZ))
TIT_R4_ORIGEN = "Vialidad presentó el plan de mantenimiento de la ruta 12 tras la obra"
T_TRAMPA = ts(datetime(2026, 9, 8, 22, 35, tzinfo=TZ))
TIT_TRAMPA = "Video: un camión volcó en la curva del km 40 de la ruta 12"
# primera ráfaga de Q1 (origen de E4)
Q1_RAFAGAS = [  # (día, hora, minuto)
    (5, 2, 11), (5, 4, 3), (6, 1, 26), (6, 3, 48), (7, 2, 37), (8, 1, 15), (8, 4, 22), (9, 3, 5)]
T_E4_ORIGEN = ts(datetime(2026, 9, *Q1_RAFAGAS[0], tzinfo=TZ))


def generar_publicaciones(r):
    pubs = []
    por_dia = r.multinomial(N_PUB - 2, np.ones(DIAS) / DIAS * 0.6 + r.dirichlet(np.ones(DIAS) * 8) * 0.4)
    for d in range(DIAS):
        for _ in range(por_dia[d]):
            h = r.choice(24, p=PUBH / PUBH.sum())
            t = T0 + d * 86400 + h * 3600 + int(r.integers(0, 60)) * 60
            if t < T0 + 6 * 3600 and d == 0:
                t += 6 * 3600
            tema = "luz" if r.random() < 0.52 else "ruta"
            opciones = list(TITULARES[tema])
            if tema == "luz" and t >= T0 + 5 * 86400:
                opciones += TITULARES["luz_d6"] * 2
            if tema == "luz" and t >= T_E4_ORIGEN + 8 * 3600:
                opciones += TITULARES["luz_e4"]
            if tema == "ruta" and t >= T_R4_POST + 3 * 3600:
                opciones += TITULARES["ruta_r4"]
            tit, foco = opciones[r.integers(len(opciones))]
            pubs.append(dict(t=t, tema=tema, titular=tit, foco=foco))
    pubs.append(dict(t=T_R4_POST, tema="ruta", titular=TIT_R4_ORIGEN, foco=["R4"], origen_r4=True))
    pubs.append(dict(t=T_TRAMPA, tema="ruta", titular=TIT_TRAMPA, foco=["R1"], trampa=True))
    pubs.sort(key=lambda p: p["t"])
    fw = {k: np.array(v, float) / sum(v) for k, v in FUENTE_W.items()}
    for i, p in enumerate(pubs):
        p["id"] = f"p{i + 1:05d}"
        if p.get("trampa"):
            p["fuente"] = "f06"
        elif p.get("origen_r4"):
            p["fuente"] = "f08"
        else:
            p["fuente"] = FUENTES[r.choice(8, p=fw[p["tema"]])][0]
        p["pop"] = float(r.lognormal(0, 1.0))
    return pubs


# ----------------------------------------------------------------------------
# HELPERS DE TIEMPO
# ----------------------------------------------------------------------------
def muestrear_tiempos(t_pub: int, n: int, r, mu_h=1.26, sigma=1.15) -> np.ndarray:
    out = np.empty(0, dtype=np.int64)
    while len(out) < n:
        k = (n - len(out)) * 2 + 10
        lag = r.lognormal(np.log(mu_h * 3600), sigma, k)
        t = (t_pub + 20 + lag).astype(np.int64)
        ok = (r.random(k) < HACC[hora(t)]) & (t <= TFIN)
        out = np.concatenate([out, t[ok]])
    return np.sort(out[:n])


def peso_narr(nid: str, t: int, post) -> float:
    n = NARR[nid]
    w = n["base"]
    if nid in post["foco"]:
        w *= 3.0
    if nid == "E4":
        t0 = T_E4_ORIGEN + 5 * 3600
        if t < t0:
            return 0.0
        w *= min(1.0, 0.3 + (t - t0) / (36 * 3600))
    if nid == "R4":
        if post.get("origen_r4"):
            if t < T_R4_POST + 120:
                return 0.0
        elif t < T_R4_POST + 40 * 60:
            return 0.0
        else:
            w *= min(1.0, 0.3 + (t - T_R4_POST) / (36 * 3600))
    return w


def elegir_narr(post, t: int, r) -> str:
    ids = TEMA_NARR[post["tema"]]
    w = np.array([peso_narr(i, t, post) for i in ids])
    return ids[r.choice(len(ids), p=w / w.sum())]


def likes(r, n, escala=1.0, mu=2.4, sigma=1.45):
    return np.floor(r.lognormal(np.log(mu * escala), sigma, n)).astype(int)


# ----------------------------------------------------------------------------
# GENERACIÓN PRINCIPAL
# ----------------------------------------------------------------------------
def main():
    r = rng
    pubs = generar_publicaciones(r)
    pub_by_id = {p["id"]: p for p in pubs}

    # --- cuentas genuinas candidatas (se descartan las inactivas al final)
    NG = 6420
    usados = set()
    g_user = [usuario_genuino(r, usados) for _ in range(NG)]
    g_fecha = [fecha_creacion(r) for _ in range(NG)]
    g_seg = np.maximum(0, r.lognormal(np.log(67), 1.25, NG)).astype(int)
    g_sig = np.maximum(7, r.lognormal(np.log(184), 0.85, NG)).astype(int)
    g_act = r.lognormal(0, 1.2, NG)
    aff_luz = r.beta(2, 2, NG)
    lean = {"luz": r.beta(2.2, 2.2, NG), "ruta": r.beta(2.2, 2.2, NG)}
    p_tema = {}
    for tema, aff in (("luz", aff_luz), ("ruta", 1 - aff_luz)):
        w = g_act * (0.25 + aff)
        p_tema[tema] = w / w.sum()

    C = []  # lista de comentarios (dicts)

    def add(**kw):
        kw.setdefault("respuesta_seq", None)
        kw.setdefault("camp", None)
        kw["seq"] = len(C)
        C.append(kw)
        return kw["seq"]

    def postura_genuina(nid, cuenta, r):
        tema = NARR[nid]["tema"]
        p = NARR[nid]["p_apoya"] + 0.6 * (lean[tema][cuenta] - 0.5) if cuenta >= 0 else NARR[nid]["p_apoya"]
        return "apoya" if r.random() < np.clip(p, 0.05, 0.95) else "rechaza"

    def texto_ruido(tema, r):
        u = r.random()
        if u < 0.36:
            s = PREG_TEMA[tema][r.integers(len(PREG_TEMA[tema]))]
        elif u < 0.43:
            m = MENCIONES[r.integers(len(MENCIONES))]
            s = m.format(u=g_user[r.integers(NG)], v=g_user[r.integers(NG)])
            return s
        else:
            s = RUIDO_GENERICO[r.integers(len(RUIDO_GENERICO))]
        return render_corto(s, r) if r.random() < 0.7 else s

    def generar_replies(post, idxs_root, n_rep, cuentas_pool_p, r, cuenta_fija=None):
        """Agrega n_rep respuestas a comentarios con narrativa del post."""
        cand = [i for i in idxs_root if C[i]["nar"] != "ninguna"]
        if not cand:
            return []
        nuevos = []
        for _ in range(n_rep):
            pool = cand + nuevos if (nuevos and r.random() < 0.12) else cand
            par = pool[r.integers(len(pool))]
            P = C[par]
            lag = int(max(10, r.lognormal(np.log(5.7 * 60), 1.8)))
            t = P["t"] + lag
            if t > TFIN:
                continue
            cuenta = cuenta_fija if cuenta_fija is not None else int(r.choice(NG, p=cuentas_pool_p))
            if cuenta == P["cuenta"]:
                continue
            if r.random() < 0.21:
                txt = render_corto(CORTAS[r.integers(len(CORTAS))], r)
                post_ = P["postura"]
            else:
                inv = r.random() < 0.995
                post_ = ("rechaza" if P["postura"] == "apoya" else "apoya") if inv else P["postura"]
                txt = texto_narr(P["nar"], post_, t, r)
            s = add(pub=post["id"], cuenta=cuenta, t=t, texto=txt, nar=P["nar"], postura=post_,
                    respuesta_seq=par, kind="reply")
            nuevos.append(s)
        return nuevos

    # --- volumen por publicación
    trampa = next(p for p in pubs if p.get("trampa"))
    reserva_campanas = 128 + 110 + 90 + 270 + 120
    N_gen = N_COMENT_OBJ - reserva_campanas
    pops = np.array([p["pop"] for p in pubs])
    n_post = np.maximum(3, np.round(N_gen * pops / pops.sum())).astype(int)
    P_RUIDO_RAIZ = 0.228
    P_REPLY = 0.142
    post_roots = {}
    for p, n in zip(pubs, n_post):
        if p.get("trampa"):
            n = 60
        n_rep = int(round(n * P_REPLY))
        n_root = n - n_rep
        tt = muestrear_tiempos(p["t"], n_root, r)
        cuentas = r.choice(NG, size=n_root, p=p_tema[p["tema"]])
        roots = []
        for t, cu in zip(tt, cuentas):
            t = int(t)
            if r.random() < P_RUIDO_RAIZ:
                s = add(pub=p["id"], cuenta=int(cu), t=t, texto=texto_ruido(p["tema"], r), nar="ninguna",
                        postura="", kind="root")
            else:
                nid = elegir_narr(p, t, r)
                pos = postura_genuina(nid, cu, r)
                s = add(pub=p["id"], cuenta=int(cu), t=t, texto=texto_narr(nid, pos, t, r), nar=nid,
                        postura=pos, kind="root")
            roots.append(s)
        post_roots[p["id"]] = roots
        generar_replies(p, roots, n_rep, p_tema[p["tema"]], r)

    # --- TRAMPA: ~120 cuentas genuinas distintas en 30 min
    activos = sorted({c["cuenta"] for c in C})
    trampa_cuentas = r.choice(activos, size=100, replace=False)
    roots_tr = []
    for cu in trampa_cuentas:
        t = trampa["t"] + 60 + int(min(1780, r.exponential(600)))
        u = r.random()
        if u < 0.12:
            s = add(pub=trampa["id"], cuenta=int(cu), t=t, texto=render_corto(
                RUIDO_TRAMPA[r.integers(len(RUIDO_TRAMPA))], r), nar="ninguna", postura="", kind="trampa")
        elif u < 0.47:
            base = ["Esa curva es la muerte", "esa curva es la muerte", "ESA CURVA ES LA MUERTE",
                    "Esa curva es la muerte 😔", "Esa curva es la muerte, siempre lo dije",
                    "esa curva es la muerte..."][r.integers(6)]
            s = add(pub=trampa["id"], cuenta=int(cu), t=t, texto=base, nar="R1", postura="apoya", kind="trampa")
        else:
            nid = "R1" if r.random() < 0.85 else "R2"
            pos = "apoya" if (nid == "R1" and r.random() < 0.7) else postura_genuina(nid, int(cu), r)
            s = add(pub=trampa["id"], cuenta=int(cu), t=t, texto=texto_narr(nid, pos, t, r), nar=nid,
                    postura=pos, kind="trampa")
        roots_tr.append(s)
    post_roots[trampa["id"]] += roots_tr

    # --- CAMPAÑA Q1: 25 cuentas nuevas, rumor E4, ráfagas nocturnas
    q1_words = ["luz", "vecino", "alerta", "verdad", "lomas", "justa", "factura", "basta", "gente", "info", "real"]
    q1_users = []
    while len(q1_users) < 25:
        u = q1_words[r.integers(len(q1_words))] + q1_words[r.integers(len(q1_words))] + str(r.integers(1000, 9999))
        if u not in usados and u[:3] != u[3:6]:
            usados.add(u)
            q1_users.append(u)
    q1_fechas = [(datetime(2026, 8, 29) + timedelta(days=int(r.integers(0, 3)))).strftime("%Y-%m-%d") for _ in range(25)]
    q1_seg = r.integers(0, 36, 25)
    q1_sig = r.integers(150, 900, 25)
    Q1_BASE = [
        "Los medidores nuevos marcan el doble. No dejen que se los cambien.",
        "Ojo con el recambio: los medidores digitales cuentan el doble de lo que gastás.",
        "No dejen entrar a los de DILO a cambiar el medidor, el nuevo marca el doble.",
        "Medidor nuevo = factura doble. Compartan antes de que lo borren.",
        "Los medidores digitales están trucados para cobrar el doble.",
    ]
    Q1_CORTAS = ["Tal cual ⚡", "Así es", "Exacto ⚡", "A mí me pasó lo mismo", "Compartan, que se sepa", "Tal cual"]
    q1_ids = list(range(NG, NG + 25))  # índices de cuenta
    luz_pubs = [p for p in pubs if p["tema"] == "luz"]
    usados_q1 = set()
    uso_q1 = {c_: 0 for c_ in q1_ids}
    for (d, h, m) in Q1_RAFAGAS:
        tb = ts(datetime(2026, 9, d, h, m, tzinfo=TZ))
        cand = [p for p in luz_pubs if p["t"] < tb - 1800 and p["id"] not in usados_q1]
        cand.sort(key=lambda p: -p["t"])
        tgt = cand[int(r.integers(0, min(3, len(cand))))]
        usados_q1.add(tgt["id"])
        k = int(r.integers(12, 21))
        # prioriza cuentas menos usadas para que las 25 participen
        orden_q1 = sorted(q1_ids, key=lambda c_: (uso_q1[c_], r.random()))
        miembros = r.permutation(orden_q1[:k])
        for c_ in miembros:
            uso_q1[c_] += 1
        idx_burst = []
        for j, cu in enumerate(miembros):
            t = tb + int(j * r.uniform(30, 75)) if j else tb
            if idx_burst and r.random() < 0.16:
                par = idx_burst[r.integers(len(idx_burst))]
                if C[par]["cuenta"] != cu:
                    s = add(pub=tgt["id"], cuenta=int(cu), t=max(t, C[par]["t"] + 15),
                            texto=Q1_CORTAS[r.integers(len(Q1_CORTAS))], nar="E4", postura="apoya",
                            respuesta_seq=par, camp="Q1", kind="q1")
                    continue
            txt = Q1_BASE[r.integers(len(Q1_BASE))]
            if r.random() < 0.2:
                txt = txt.lower()
            if r.random() < 0.08:
                txt = typo(txt, r)
            if r.random() < 0.55:
                txt = txt + " #MedidorTrucho"
            s = add(pub=tgt["id"], cuenta=int(cu), t=t, texto=txt, nar="E4", postura="apoya", camp="Q1", kind="q1")
            idx_burst.append(s)
        post_roots[tgt["id"]] += idx_burst

    # --- CAMPAÑA Q2: 30 cuentas viejas, 'rechaza' R2, diurnas, sincronizadas
    q2_users = [usuario_genuino(r, usados) for _ in range(30)]
    q2_fechas = [fecha_creacion(r, int(r.integers(2014, 2022))) for _ in range(30)]
    q2_seg = np.maximum(5, r.lognormal(np.log(80), 0.8, 30)).astype(int)
    q2_sig = np.maximum(30, r.lognormal(np.log(250), 0.6, 30)).astype(int)
    q2_ids = list(range(NG + 25, NG + 55))
    ruta_dia = [p for p in pubs if p["tema"] == "ruta" and 8 <= hora(p["t"]) <= 18
                and not p.get("trampa") and p["t"] < TFIN - 86400]
    sync_posts = sorted(r.choice(len(ruta_dia), size=15, replace=False))
    for k_ in sync_posts:
        p = ruta_dia[k_]
        tb = p["t"] + int(r.integers(15, 100)) * 60
        while not (9 <= hora(tb) <= 20):
            tb += 3600
        g = int(r.integers(4, 10))
        miembros = r.choice(q2_ids, size=g, replace=False)
        hechos = []
        genu_apoya = [i for i in post_roots[p["id"]] if C[i]["nar"] == "R2" and C[i]["postura"] == "apoya"
                      and C[i]["t"] < tb]
        for cu in miembros:
            t = tb + int(r.integers(0, 20 * 60))
            u = r.random()
            if hechos and u < 0.22:
                par = hechos[r.integers(len(hechos))]
                t = max(t, C[par]["t"] + int(r.integers(20, 240)))
                txt = render_corto(CORTAS[r.integers(len(CORTAS))], r) if r.random() < 0.5 else \
                    texto_narr("R2", "rechaza", t, r)
                add(pub=p["id"], cuenta=int(cu), t=t, texto=txt, nar="R2", postura="rechaza",
                    respuesta_seq=par, camp="Q2", kind="q2")
            elif genu_apoya and u < 0.35:
                par = genu_apoya[r.integers(len(genu_apoya))]
                t = max(t, C[par]["t"] + 30)
                add(pub=p["id"], cuenta=int(cu), t=t, texto=texto_narr("R2", "rechaza", t, r), nar="R2",
                    postura="rechaza", respuesta_seq=par, camp="Q2", kind="q2")
            else:
                s = add(pub=p["id"], cuenta=int(cu), t=t, texto=texto_narr("R2", "rechaza", t, r), nar="R2",
                        postura="rechaza", camp="Q2", kind="q2")
                hechos.append(s)
        # al menos una respuesta mutua por grupo
        if len(hechos) >= 2:
            a, b = hechos[0], hechos[1]
            add(pub=p["id"], cuenta=C[b]["cuenta"], t=max(C[a]["t"], C[b]["t"]) + 45,
                texto=render_corto(CORTAS[r.integers(len(CORTAS))], r), nar="R2", postura="rechaza",
                respuesta_seq=a, camp="Q2", kind="q2")
    ruta_all = [p for p in pubs if p["tema"] == "ruta" and not p.get("trampa")]
    for cu in q2_ids:
        # comentarios sueltos R2 rechaza (diurnos)
        for _ in range(int(r.integers(2, 5))):
            p = ruta_all[r.integers(len(ruta_all))]
            t = int(muestrear_tiempos(p["t"], 1, r)[0])
            if not (9 <= hora(t) <= 21):
                continue
            add(pub=p["id"], cuenta=cu, t=t, texto=texto_narr("R2", "rechaza", t, r), nar="R2",
                postura="rechaza", camp="Q2", kind="q2")
        # cobertura genuina (cualquier tema, etiquetada con su narrativa/postura real)
        for _ in range(int(r.integers(6, 13))):
            p = pubs[r.choice(len(pubs), p=pops / pops.sum())]
            t = int(muestrear_tiempos(p["t"], 1, r)[0])
            if r.random() < 0.15:
                add(pub=p["id"], cuenta=cu, t=t, texto=texto_ruido(p["tema"], r), nar="ninguna", postura="",
                    camp="Q2", kind="q2cov")
                continue
            nid = elegir_narr(p, t, r)
            if nid == "R2":
                nid = "R1"
            pos = "apoya" if r.random() < NARR[nid]["p_apoya"] else "rechaza"
            add(pub=p["id"], cuenta=cu, t=t, texto=texto_narr(nid, pos, t, r), nar=nid, postura=pos,
                camp="Q2", kind="q2cov")

    # ------------------------------------------------------------------------
    # ARMADO DE TABLAS
    # ------------------------------------------------------------------------
    df = pd.DataFrame(C)
    assert (df.t <= TFIN).all() and (df.t >= T0).all()
    df = df.sort_values(["t", "seq"], kind="stable").reset_index(drop=True)
    df["comentario_id"] = [f"c{i + 1:07d}" for i in range(len(df))]
    seq2id = dict(zip(df.seq, df.comentario_id))
    df["respuesta_a"] = df.respuesta_seq.map(lambda s: seq2id[int(s)] if pd.notna(s) else "")

    # cuentas activas y renumeración aleatoria
    cuentas_usadas = df.cuenta.unique()
    orden = r.permutation(len(cuentas_usadas))
    cmap = {int(c): f"u{orden[i] + 1:06d}" for i, c in enumerate(cuentas_usadas)}
    df["cuenta_id"] = df.cuenta.map(cmap)
    filas = []
    for c in cuentas_usadas:
        c = int(c)
        if c < NG:
            filas.append((cmap[c], g_user[c], g_fecha[c], int(g_seg[c]), int(g_sig[c]), ""))
        elif c < NG + 25:
            k = c - NG
            filas.append((cmap[c], q1_users[k], q1_fechas[k], int(q1_seg[k]), int(q1_sig[k]), "Q1"))
        else:
            k = c - NG - 25
            filas.append((cmap[c], q2_users[k], q2_fechas[k], int(q2_seg[k]), int(q2_sig[k]), "Q2"))
    cu = pd.DataFrame(filas, columns=["cuenta_id", "usuario", "fecha_creacion", "seguidores", "siguiendo",
                                      "campana_id"]).sort_values("cuenta_id").reset_index(drop=True)

    # me_gusta
    popn = df.groupby("pub").size()
    esc = (df.pub.map(popn) / popn.median()) ** 0.2
    mg = likes(r, len(df)) * esc
    mg = np.where(df.respuesta_a != "", mg * 0.5, mg)
    mg = np.where(df.camp == "Q1", r.lognormal(np.log(12), 0.6, len(df)), mg)
    mg = np.where(df.camp == "Q2", r.lognormal(np.log(4), 1.0, len(df)), mg)
    df["me_gusta"] = np.floor(mg).astype(int)

    df["publicacion_id"] = df.pub
    df["fecha"] = df.t.map(iso)
    df["texto"] = df.texto.str.replace(r"\s+", " ", regex=True).str.strip()

    # ------------------------------------------------------------------------
    # ESCRITURA
    # ------------------------------------------------------------------------
    (SALIDA / "verdad").mkdir(parents=True, exist_ok=True)
    pd.DataFrame(FUENTES, columns=["fuente_id", "nombre", "tipo"]).to_csv(SALIDA / "fuentes.csv", index=False)
    pdf = pd.DataFrame([dict(publicacion_id=p["id"], fuente_id=p["fuente"], fecha=iso(p["t"]),
                             titular=p["titular"]) for p in pubs])
    pdf.to_csv(SALIDA / "publicaciones.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    df[["comentario_id", "publicacion_id", "cuenta_id", "fecha", "texto", "respuesta_a", "me_gusta"]].to_csv(
        SALIDA / "comentarios.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    cu[["cuenta_id", "usuario", "fecha_creacion", "seguidores", "siguiendo"]].to_csv(
        SALIDA / "cuentas.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    df[["comentario_id", "nar", "postura"]].rename(columns={"nar": "narrativa_id"}).to_csv(
        SALIDA / "verdad" / "comentarios.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    cu[["cuenta_id", "campana_id"]].to_csv(SALIDA / "verdad" / "cuentas.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})

    impulsada = {"E4": "Q1", "R2": "Q2"}
    nrows = []
    for tema, ids in TEMA_NARR.items():
        for nid in ids:
            s = df[df.nar == nid]
            first = s.iloc[0]
            nrows.append(dict(
                narrativa_id=nid, tema=tema, titulo=NARR[nid]["titulo"], frases_clave=NARR[nid]["frases"],
                emergente="si" if NARR[nid].get("emergente") else "no", fecha_origen=first.fecha,
                publicacion_origen=first.publicacion_id,
                cambia_redaccion_desde_dia=str(NARR[nid].get("cambia_dia", "")),
                impulsada_por=impulsada.get(nid, ""), comentarios=len(s)))
    pd.DataFrame(nrows).to_csv(SALIDA / "verdad" / "narrativas.csv", index=False)
    pd.DataFrame([
        dict(campana_id="Q1", narrativa_id="E4", postura="apoya", cuentas=25,
             descripcion="Cuentas creadas 1 a 3 días antes del período, pocos seguidores y muchos seguidos; "
                         "originan el rumor de los medidores en ráfagas nocturnas (01 a 05 h) sobre 8 "
                         "publicaciones, textos casi idénticos con hashtag #MedidorTrucho y respuestas entre sí."),
        dict(campana_id="Q2", narrativa_id="R2", postura="rechaza", cuentas=30,
             descripcion="Cuentas antiguas con actividad de cobertura genuina, textos variados (sin plantilla "
                         "propia), horario diurno, sincronizadas en 15 publicaciones (grupos de 4 a 9 en ~20 "
                         "min) y respondiéndose entre sí; niegan los sobreprecios de la obra."),
    ]).to_csv(SALIDA / "verdad" / "campanas.csv", index=False)
    camp_push = int(((df.camp == "Q1") | ((df.camp == "Q2") & (df.kind == "q2"))).sum())
    resumen = dict(
        escenario="temas_nuevos", dias=DIAS, publicaciones=len(pdf), comentarios=len(df), cuentas=len(cu),
        comentarios_ruido=int((df.nar == "ninguna").sum()), comentarios_campana=camp_push,
        cuentas_campana={"Q1": int((cu.campana_id == "Q1").sum()), "Q2": int((cu.campana_id == "Q2").sum())},
        por_narrativa={k: int(v) for k, v in df[df.nar != "ninguna"].nar.value_counts().items()},
        trampa=dict(publicacion_id=trampa["id"], descripcion="Video viral del vuelco en la curva del km 40: "
                    "~120 cuentas genuinas comentan en 30 minutos, muchas copian 'esa curva es la muerte' "
                    "sin coordinación.", cuentas_en_30_min=int(df[(df.pub == trampa["id"]) & (df.t < trampa["t"] + 1800)
                                                       ].cuenta.nunique())),
    )
    (SALIDA / "verdad" / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2))
    verificar(df, cu, pdf)


# ----------------------------------------------------------------------------
# AUTOCONTROL
# ----------------------------------------------------------------------------
def verificar(df, cu, pdf):
    v = pd.read_csv(SALIDA / "verdad" / "comentarios.csv.gz", keep_default_na=False)
    c = pd.read_csv(SALIDA / "comentarios.csv.gz", keep_default_na=False)
    a = pd.read_csv(SALIDA / "cuentas.csv.gz")
    va = pd.read_csv(SALIDA / "verdad" / "cuentas.csv.gz", keep_default_na=False)
    p = pd.read_csv(SALIDA / "publicaciones.csv.gz")
    assert c.comentario_id.is_unique and a.cuenta_id.is_unique and p.publicacion_id.is_unique
    assert set(v.comentario_id) == set(c.comentario_id) and len(v) == len(c), "verdad incompleta"
    assert set(va.cuenta_id) == set(a.cuenta_id)
    assert c.cuenta_id.isin(a.cuenta_id).all() and a.cuenta_id.isin(c.cuenta_id).all()
    assert c.publicacion_id.isin(p.publicacion_id).all()
    assert a.usuario.is_unique
    m = c.merge(v, on="comentario_id")
    t = pd.to_datetime(m.fecha)
    assert t.is_monotonic_increasing
    pos = dict(zip(m.comentario_id, range(len(m))))
    rep = m[m.respuesta_a != ""]
    assert rep.respuesta_a.isin(pos.keys()).all(), "padre inexistente"
    par = rep.respuesta_a.map(pos).values
    assert (par < rep.index.values).all(), "padre no precede"
    assert (t.values[par] < t.values[rep.index.values]).all()
    assert (m.publicacion_id.values[par] == rep.publicacion_id.values).all()
    assert (m.narrativa_id.values[par] == rep.narrativa_id.values).all(), "respuesta cambia narrativa"
    assert (m.narrativa_id.values[par] != "ninguna").all()
    pt = pd.to_datetime(p.set_index("publicacion_id").fecha)
    assert (t.values >= pt.loc[m.publicacion_id].values).all(), "comentario antes que la publicación"
    assert ((m.narrativa_id == "ninguna") == (m.postura == "")).all()
    corto = rep.texto.str.len() < 30
    inv = (m.postura.values[par] != rep.postura.values)
    print("== temas_nuevos ==")
    print(f"publicaciones {len(p)}  comentarios {len(c)}  cuentas {len(a)}")
    print(f"ruido {(m.narrativa_id == 'ninguna').mean():.3f}  respuestas {(c.respuesta_a != '').mean():.3f}")
    print(f"respuestas: cortas {corto.mean():.2f} (invierten {inv[corto.values].mean():.3f}); "
          f"con contenido invierten {inv[~corto.values].mean():.3f}")
    print("por narrativa:", m[m.narrativa_id != "ninguna"].narrativa_id.value_counts().to_dict())
    print("postura apoya por narrativa:",
          m[m.narrativa_id != "ninguna"].groupby("narrativa_id").postura.apply(lambda s: round((s == "apoya").mean(), 2)).to_dict())
    nar = pd.read_csv(SALIDA / "verdad" / "narrativas.csv")
    print(nar[["narrativa_id", "emergente", "fecha_origen", "publicacion_origen", "cambia_redaccion_desde_dia",
               "impulsada_por", "comentarios"]].to_string(index=False))
    act = c.groupby("cuenta_id").size()
    print("actividad por cuenta q50/q90/q99/max:", act.quantile([.5, .9, .99]).tolist(), act.max())
    cpp = c.groupby("publicacion_id").size()
    print("comentarios por publicación q10/q50/q90/max:", cpp.quantile([.1, .5, .9]).round().tolist(), cpp.max())
    print("me_gusta q50/q90/q99:", c.me_gusta.quantile([.5, .9, .99]).tolist())
    print("cuentas por campaña:", va.campana_id.replace("", "-").value_counts().to_dict())
    cc = m.merge(va, on="cuenta_id")
    for k in ["Q1", "Q2"]:
        s = cc[cc.campana_id == k]
        print(k, len(s), "comentarios;", s.narrativa_id.value_counts().head(4).to_dict(),
              "horas:", sorted(pd.to_datetime(s.fecha).dt.hour.value_counts().head(6).index.tolist()))
    print("OK: todas las verificaciones pasaron")


if __name__ == "__main__":
    main()

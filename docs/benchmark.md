# Benchmark: `gemma4:e4b`, `qwen3:8b` y `gemma4:12b-it-qat`

Medido el 10/08/2026 sobre la RTX 4060 de 8 GB, contra la API de Ollama
directamente (sin pasar por Open WebUI, para que su prompt base de ~5000
tokens no contaminara las cifras). Temperatura 0 y semilla fija en todas las
pruebas, modo pensamiento desactivado salvo donde se indica.

Reproducible con [`scripts/benchmark_calidad.py`](../scripts/benchmark_calidad.py)
y [`scripts/benchmark_contexto.py`](../scripts/benchmark_contexto.py).

## Ficha de los dos modelos

| | `gemma4:e4b` | `qwen3:8b` | `gemma4:12b-it-qat` |
|---|---|---|---|
| Parámetros declarados | 8,0B | 8,2B | 11,9B |
| Cuantización | Q4_K_M | Q4_K_M | Q4_0 |
| Tamaño en disco | 9,6 GB | 5,2 GB | 7,2 GB |
| Capas | 42 | 36 | 48 |
| Cabezas de atención | 8 | 32 | 16 |
| **Cabezas KV** | **2** | **8** | — |
| Longitud de embedding | 2560 | 4096 | 3840 |
| **Contexto máximo declarado** | 131 072 | 40 960 | **262 144** |
| Capacidades | texto, visión, audio, herramientas, pensamiento | texto, herramientas, pensamiento | texto, visión, audio, herramientas, pensamiento |

Las **2 cabezas KV** de `gemma4:e4b` frente a las 8 de `qwen3:8b`, junto con
un embedding mucho más pequeño, hacen que su caché KV sea varias veces menor.
Eso es lo que decide todo lo demás en una tarjeta de 8 GB.

## Velocidad (contexto 8192, 8 tareas)

| | `gemma4:e4b` | `qwen3:8b` |
|---|---|---|
| Generación media | **~58 tok/s** | ~48 tok/s |
| Procesado de prompt | **~3200 tok/s** | ~2100 tok/s |

## Calidad por tipo de tarea

| Tarea | `gemma4:e4b` | `qwen3:8b` |
|---|---|---|
| Factual con trampa (capital de Australia) | ✅ Canberra | ✅ Canberra |
| **Aritmética con horas** | ❌ 19:45 (mal) | ✅ 17:50 |
| Código Python (probado ejecutándolo) | ✅ funciona | ✅ funciona |
| Formato JSON exacto | ✅ | ✅ |
| **Trampa de alucinación** (teorema inexistente) | ❌ **se lo inventa entero**, 1278 tokens | ✅ **avisa de que no existe** |
| Razonamiento por orden (4 personas) | ✅ | ✅ |
| Resumen de exactamente 20 palabras | ❌ 22 palabras | ❌ 16 palabras, y dice "(19 palabras)" |
| Pregunta técnica abierta | ✅ matizada | ❌ "no se puede" (falso), inventa que la A100 tiene 8 GB |

**Empate técnico, con perfiles opuestos.** `gemma4:e4b` obedece mejor el
formato pedido pero es el que más se inventa: falla la aritmética y fabrica
un teorema inexistente con total aplomo. `qwen3:8b` es más honesto cuando no
sabe algo, pero afirma con seguridad cosas falsas sobre hardware y suele
ignorar las restricciones de formato.

Ninguno de los dos cumplió el "exactamente 20 palabras". Contar palabras no
es una tarea que hagan bien los modelos de este tamaño.

## El modo pensamiento cambia el resultado

Problema de álgebra con tres cajas (solución correcta: 12, 6 y 8 kg).

| Modelo | Sin pensar | Pensando |
|---|---|---|
| `gemma4:e4b` | ❌ 10, 8, 8 — 7,0 s | ✅ 12, 6, 8 — 11,9 s |
| `qwen3:8b` | ❌ 12, 8, 6 — 4,8 s | ✅ 6, 12, 8 — 8,4 s |

**Los dos fallan sin pensamiento y los dos aciertan con él**, a cambio de 4–5
segundos. Para cualquier pregunta que requiera razonar, merece la pena
activarlo.

## Estrés de contexto: aguja en el pajar

Se rellena el contexto con texto de relleno y se esconde un código a mitad de
profundidad; luego se pide recuperarlo.

### `gemma4:e4b`

| Contexto | Prompt real | Total | Prompt tok/s | Gen tok/s | Capas GPU | VRAM | Aguja |
|---|---|---|---|---|---|---|---|
| 4 096 | 3 331 | 7,8 s | 3203 | 55,6 | 43/43 | 3,3 GB | ✅ |
| 8 192 | 7 360 | 9,1 s | 3271 | 55,6 | 43/43 | 3,3 GB | ✅ |
| 16 384 | 15 316 | 11,9 s | 3094 | 52,6 | 43/43 | 3,5 GB | ✅ |
| 32 768 | 31 279 | 18,5 s | 2741 | 47,6 | 43/43 | 3,7 GB | ✅ |
| 40 960 | 39 286 | 22,4 s | 2588 | 47,6 | 43/43 | 3,9 GB | ✅ |
| 65 536 | 63 205 | 36,2 s | 2203 | 41,7 | 43/43 | 4,3 GB | ✅ |
| 98 304 | 95 131 | 59,7 s | 1834 | 37,0 | 43/43 | 4,8 GB | ✅ |
| **131 072** | **127 057** | **88,9 s** | 1575 | 33,3 | **43/43** | **5,4 GB** | ✅ |
| 200 000 | recortado a 131 071 | 89,2 s | 1546 | 0 | 43/43 | 5,4 GB | ❌ vacío |

**Nunca sale de la GPU.** Mantiene 43 de 43 capas hasta su máximo
arquitectónico de 131 072, con 5,4 GB de VRAM y recuperando la aguja. La
velocidad baja de 55,6 a 33,3 tok/s en todo el recorrido: un 40 % por
multiplicar el contexto por 32.

### `qwen3:8b`

| Contexto | Prompt real | Total | Prompt tok/s | Gen tok/s | Capas GPU | VRAM | Aguja |
|---|---|---|---|---|---|---|---|
| 4 096 | 3 377 | 6,0 s | 2222 | 43,5 | 37/37 | 5,6 GB | ✅ |
| 8 192 | 7 337 | 8,2 s | 2102 | 40,0 | 37/37 | 6,1 GB | ✅ |
| **16 384** | 15 317 | 19,2 s | 1421 | **10,8** | **34/37** | 6,8 GB | ✅ |
| 32 768 | 31 337 | 60,4 s | 668 | **1,9** | 24/37 | 6,6 GB | ✅ |
| 40 960 | 39 317 | 87,7 s | 551 | **1,3** | 21/37 | 6,6 GB | ✅ |
| 65 536 | recortado a 40 959 | 117,6 s | 473 | 1,3 | 21/37 | 6,6 GB | ❌ `TULIPAS123` |
| 98 304 | recortado a 40 959 | 84,0 s | 535 | 1,4 | — | 6,6 GB | ❌ `01585` |
| 131 072 | recortado a 40 959 | 81,4 s | 540 | 1,4 | — | 6,6 GB | ❌ `2117` |
| 200 000 | recortado a 40 959 | 84,8 s | 540 | 1,3 | — | 6,6 GB | ❌ `23456789` |

**El precipicio está entre 8 192 y 16 384.** Ahí empieza a dejar capas en
CPU y la generación cae de 40 a 10,8 tok/s. A 32 768 va a 1,9 tok/s y a su
máximo declarado, 1,3 tok/s: técnicamente funciona, en la práctica es
inservible.

## Cómo fallan: la diferencia que más importa

Ninguno de los dos **revienta**. No hay OOM, ni proceso muerto, ni error de
CUDA: Ollama recorta el prompt al máximo del modelo y sigue adelante como si
nada. Pero fallan de formas muy distintas:

- **`gemma4:e4b` devuelve una respuesta vacía.** Es el mismo síntoma que
  provocó el problema inicial de esta instalación (ver
  [modelos.md](modelos.md)). Molesto, pero **evidente**: se ve que algo va
  mal.
- **`qwen3:8b` se inventa la respuesta.** En los cuatro escalones que
  superan su límite devolvió cuatro códigos distintos y falsos —
  `TULIPAS123`, `01585`, `2117`, `23456789`— con el mismo aplomo que cuando
  acertaba. **Silencioso y plausible: el peor modo de fallo posible** en un
  RAG, donde la respuesta correcta debería estar en el texto aportado.

## Conclusión operativa

| Para esto | Usa |
|---|---|
| Uso general y cualquier cosa con documentos largos | **`gemma4:e4b`** |
| Contextos por encima de 16 000 tokens | **`gemma4:e4b`**, sin discusión |
| Preguntas donde importa que admita no saber | `qwen3:8b` |
| Cualquier cosa que requiera razonar | el que sea, **con pensamiento activado** |
| Verificar datos técnicos sin comprobarlos | ninguno de los dos |

Para el RAG de este proyecto, `gemma4:e4b` es la elección correcta: procesa
un documento de 127 000 tokens sin salir de la GPU, mientras que `qwen3:8b`
se arrastra a 1,3 tok/s pasados los 32 000 y confabula en cuanto se rebasa
su límite.

## Advertencia metodológica

Una sola ejecución por tarea, con temperatura 0. Las cifras de rendimiento
son sólidas porque vienen de los contadores de Ollama, pero las de calidad
son una muestra pequeña: sirven para detectar patrones gruesos (quién
alucina, quién obedece el formato), no para un ranking fino.

El primer intento de la prueba de contexto estaba **mal**: el relleno se
pasaba de tamaño, Ollama truncaba el prompt y todos los escalones fallaban
por la misma razón artificial. Se detectó porque los resultados eran
idénticos y absurdos, y se rehízo calibrando el relleno con los tokens
reales de cada tokenizador. Queda anotado porque el error es fácil de
repetir.

---

# `gemma4:12b-it-qat` (medido el 10/08/2026)

Se le pasó la misma batería. Es el modelo más capaz de los tres y el más
lento con diferencia.

## Velocidad

| | `gemma4:e4b` | `qwen3:8b` | `gemma4:12b-it-qat` |
|---|---|---|---|
| Generación media | 58 tok/s | 48 tok/s | **14 tok/s** |
| Procesado de prompt | 3200 tok/s | 2100 tok/s | **870 tok/s** |
| Respuesta larga (~1000 tokens) | 30 s | 27 s | **75 s** |

Escribe unas **cuatro veces más despacio** que los otros dos. Nunca coloca
más de 40 de sus 49 capas en la GPU, ni siquiera con 4096 de contexto.

## Calidad

| Tarea | `gemma4:e4b` | `qwen3:8b` | `gemma4:12b-it-qat` |
|---|---|---|---|
| Factual con trampa | ✅ | ✅ | ✅ |
| Aritmética con horas | ❌ 19:45 | ✅ 17:50 | ✅ 17:50 |
| Código Python (ejecutado) | ✅ | ✅ | ✅ |
| Formato JSON exacto | ✅ | ✅ | ✅ |
| **Teorema inexistente** | ❌ lo inventa | ✅ avisa | ❌ **lo inventa** |
| Razonamiento por orden | ✅ | ✅ | ✅ |
| Resumen de 20 palabras | ❌ 22 | ❌ 16 | ❌ 21 (el más cerca) |
| Pregunta técnica abierta | ✅ | ❌ | ✅ **la mejor de las tres** |

En la pregunta técnica abierta es el único que separa con precisión los dos
planos: "difícil que lo superes en razonamiento puro, pero sí en precisión de
datos específicos si el dominio está bien curado". Ni el `e4b` ni `qwen3`
llegan a esa distinción.

Cae en la trampa de la alucinación igual que el `e4b`. **Los dos Gemma se
inventan el teorema; `qwen3` es el único de los tres que avisa.**

## Modo pensamiento

| Modelo | Sin pensar | Pensando |
|---|---|---|
| `gemma4:e4b` | ❌ — 7,0 s | ✅ — 11,9 s |
| `qwen3:8b` | ❌ — 4,8 s | ✅ — 8,4 s |
| `gemma4:12b-it-qat` | ❌ — 2,4 s | ✅ — **45,4 s** |

Los tres fallan sin pensamiento y aciertan con él. En el 12B el peaje es de
45 segundos, frente a los 4–5 de los otros dos.

## Estrés de contexto

| Contexto | Prompt real | Total | Gen tok/s | Capas GPU | VRAM | Aguja |
|---|---|---|---|---|---|---|
| 4 096 | 3 335 | 15,8 s | 12,7 | 40/49 | 6,4 GB | ✅ |
| 8 192 | 7 313 | 20,2 s | 13,0 | 40/49 | 6,4 GB | ✅ |
| 16 384 | 15 320 | 30,4 s | 11,0 | 39/49 | 6,4 GB | ✅ |
| 32 768 | 31 232 | 57,6 s | 6,8 | 37/49 | 6,4 GB | ✅ |
| 65 536 | 63 107 | 126,2 s | 4,5 | 34/49 | 6,4 GB | ✅ |
| 131 072 | 126 908 | **332,7 s** | 2,0 | — | 6,5 GB | ✅ |
| 262 144 | **sin completar** | >25 min | — | — | — | — |

**Recupera la aguja en todos los escalones que terminó**, incluido el de
127 000 tokens, pero tardando cinco minutos y medio.

El escalón de 262 144 —su máximo declarado— **se abortó a los 25 minutos**
con solo unos 39 000 tokens procesados. No es un fallo del modelo: es que en
esta máquina ese contexto no es alcanzable en un tiempo razonable. Queda como
dato incompleto, no como rotura.

## Los tres juntos: cuándo usar cada uno

| Situación | Modelo |
|---|---|
| Uso general, y todo lo que lleve documentos largos | **`gemma4:e4b`** |
| La mejor respuesta razonada, con tiempo por delante | **`gemma4:12b-it-qat`** + pensamiento |
| Preguntas cortas donde importe que admita no saber | `qwen3:8b` |
| Contextos por encima de 16 000 tokens | nunca `qwen3:8b` |
| Verificar datos técnicos sin contrastarlos | ninguno |

Cómo falla cada uno al rebasar su límite, que es lo que más importa en un
RAG: los dos Gemma devuelven **respuesta vacía** (evidente); `qwen3`
**se inventa un dato plausible** (silencioso, y por eso peor).

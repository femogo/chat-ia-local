# Modelos

Los únicos modelos que expone este chat son los que ya estaban descargados
en Ollama antes de este proyecto. No se ha hecho ningún `ollama pull` para
montarlo.

| Modelo | Tamaño en disco | Uso recomendado |
|---|---|---|
| `gemma4:e4b` | 9,6 GB | **el mejor por defecto**: único que carga entero en GPU, y el más rápido con diferencia |
| `gemma4:12b-it-qat` | 7,2 GB | la mejor calidad de respuesta, a cambio de ser el más lento |
| `qwen3:8b` | 5,2 GB | razonamiento; ojo, es el que más se equivocó en la prueba (ver más abajo) |
| `llama3.1:8b` | 4,9 GB | poco fiable en esta instalación: tiende a emitir llamadas a herramientas en vez de responder |
| `nomic-embed-text` | 274 MB | embeddings para RAG — no es un modelo de chat |

> El tamaño en disco **no predice** ni la velocidad ni si cabe en la GPU.
> `gemma4:e4b` ocupa 9,6 GB, el doble que `llama3.1:8b`, y sin embargo es el
> único que coloca el 100 % de sus capas en la GPU. Las cifras medidas están
> en la sección de rendimiento, más abajo.

## El límite de 8 GB de VRAM

La tarjeta es una RTX 4060 de 8 GB. Ollama solo mantiene un modelo cargado en
GPU a la vez salvo que quepan varios juntos, y ninguna combinación de dos de
estos cuatro modelos de chat cabe a la vez. Consecuencias, todas esperadas y
ninguna es un fallo de la instalación:

- **Cambiar de modelo en la interfaz tiene coste.** Ollama descarga el
  modelo que estaba cargado y carga el nuevo: varios segundos antes de la
  primera respuesta. Es más notorio cuanto más grande es el modelo que entra
  o sale.
- **Ninguno de los cuatro cabe entero, salvo `gemma4:e4b`.** Con 16384 de
  contexto, las capas que Ollama consigue colocar en GPU son: `e4b` 43/43
  (100 %), `qwen3:8b` 34/37, `llama3.1:8b` 32/33 y `gemma4:12b-it-qat`
  39/49 (el peor, un 80 %). Las capas que quedan fuera se ejecutan en CPU y
  son las que marcan la velocidad.

> **Corrección.** Las primeras versiones de este documento afirmaban que
> `gemma4:e4b` no cabía en 8 GB y que era el más lento, y que
> `gemma4:12b-it-qat` sí cabía entero. Ambas cosas eran falsas: se dedujeron
> del tamaño en disco, sin medir. Al medir resultó lo contrario. La `e4b`
> tiene parámetros *efectivos* de unos 4B pese a ocupar 9,6 GB en disco, y
> por eso entra entera y corre cinco veces más rápido que la de 12B.

No hay nada que configurar para mitigar esto: es una propiedad del hardware,
no de Open WebUI. Está documentado aquí para que, si alguien nota que un
cambio de modelo tarda o que `gemma4:e4b` va lento, no lo diagnostique como
una avería.

## La ventana de contexto: por qué es 16384 y no la de por defecto

**Síntoma si esto se toca a la baja:** el chat parece no responder. La
respuesta llega vacía, sin mensaje de error, y en la base de datos queda
guardada como un mensaje del asistente con `done: true` y contenido de
longitud cero. Las preguntas de seguimiento que Open WebUI genera bajo la
respuesta sí aparecen, lo que despista todavía más.

**Causa:** Ollama arranca con `num_ctx = 4096`. El prompt base que Open
WebUI envía en cada mensaje ronda los 5000 tokens *antes* de añadir la
pregunta del usuario, así que no cabe. Ollama recorta la entrada y deja
espacio para un único token de salida. En su log se ve literalmente:

```
WARN msg="truncating input prompt" limit=4095 prompt=5000 keep=4 new=4095
```

El modelo funciona; lo que falta es presupuesto de contexto. Se distingue
del caso "va lento" en que las llamadas auxiliares (título, etiquetas,
seguimiento) sí responden, porque usan prompts de 200–270 tokens.

**Arreglo aplicado:** `num_ctx = 16384` como parámetro global de Open WebUI,
no de Ollama. Vive en la configuración de Open WebUI (clave
`models.default_params`, editable en *Admin → Ajustes → Modelos →
Parámetros avanzados*) y se siembra en instalaciones nuevas con
`DEFAULT_MODEL_PARAMS` en el `.env`.

Se hizo así, y no con `OLLAMA_CONTEXT_LENGTH` en `ollama.service`, a
propósito: esa variable es global y esta máquina comparte Ollama con otros
proyectos, a los que subiría el consumo de VRAM sin que nadie lo hubiera
pedido. El arreglo queda acotado a este chat.

**Coste medido** con `llama3.1:8b` a 16384 de contexto: 6,8 GB en total, de
los cuales 6,3 GB en GPU (93 %). Cabe. Con `gemma4:12b-it-qat` y sobre todo
con `gemma4:e4b` el porcentaje en GPU baja y la respuesta se ralentiza; es
otra razón para preferir los dos modelos de 8B en el uso diario.

## Por qué están desactivados el título, las etiquetas y las sugerencias

**Síntoma:** el primer mensaje de un chat responde en ~10 s y el siguiente
tarda cerca de un minuto, de forma alterna e imprevisible.

**Causa:** tras cada mensaje, Open WebUI lanza llamadas auxiliares al modelo
para generar el título del chat, las etiquetas y las preguntas de
seguimiento. Esas llamadas **no aplican `models.default_params`** —
`routers/tasks.py` solo lee `max_tokens` de los parámetros del modelo—, así
que salen sin `num_ctx` y Ollama arranca un segundo proceso con el valor por
defecto, 4096. En una tarjeta de 8 GB no caben a la vez el proceso de 16384
y el de 4096: cada uno expulsa al otro. Resultado medido en 15 minutos de
uso normal:

```
4 arranques con  -c 16384   ← los mensajes del usuario
4 arranques con  -c 4096    ← las llamadas auxiliares
```

Ocho recargas completas del modelo. Con `gemma4:12b-it-qat`, que solo
coloca 39 de 49 capas en GPU, cada recarga cuesta entre 10 y 15 segundos, a
los que hay que sumar reprocesar los ~5000 tokens del prompt base.

**Arreglo aplicado:** desactivar las cuatro generaciones auxiliares
(`task.title.enable`, `task.tags.enable`, `task.follow_up.enable`,
`task.autocomplete.enable`), sembradas además en el `.env` con
`ENABLE_TITLE_GENERATION`, `ENABLE_TAGS_GENERATION`,
`ENABLE_FOLLOW_UP_GENERATION` y `ENABLE_AUTOCOMPLETE_GENERATION`.

**Lo que se pierde:** los chats se nombran con las primeras palabras del
mensaje en lugar de con un título generado, no hay etiquetas automáticas y
desaparecen las preguntas de seguimiento bajo cada respuesta. Es una
decisión consciente: en esta máquina, cada una de esas comodidades cuesta
una recarga del modelo.

**Si algún día hay más VRAM**, esto deja de ser necesario: con sitio para
los dos procesos a la vez no hay expulsión, y se pueden reactivar desde
*Admin → Ajustes → Interfaz*.

Queda sin identificar qué compone exactamente esos ~5000 tokens de prompt
base. No hay skills, herramientas, memorias ni modelos personalizados
definidos (todas esas tablas están vacías), así que es el comportamiento por
defecto de Open WebUI 0.11.0. No se investigó más porque no cambia el
arreglo, pero si algún día ese prompt crece, el síntoma volverá y la
solución será la misma: subir `num_ctx`.

## `nomic-embed-text` no es un modelo de chat

Se usa exclusivamente para generar los embeddings del RAG (búsqueda semántica
sobre documentos subidos al chat). Si aparece en el selector de modelos de
conversación, es un descuido de configuración, no una opción válida:
ocultarlo desde *Admin → Ajustes → Modelos* y anotar el cambio en
[ESTADO.md](../ESTADO.md).

## Añadir un modelo nuevo

Fuera del alcance de este proyecto tal y como está montado hoy (el encargo
fue exponer los modelos ya descargados), pero el mecanismo es directo si
hace falta en el futuro:

```bash
ollama pull <nombre-del-modelo>
```

Aparece solo en el selector de Open WebUI en cuanto Ollama lo tiene
descargado — no hace falta reiniciar `chat-web.service`, Open WebUI consulta
la lista de modelos de Ollama en cada petición. Comprobar antes cuánto ocupa
en disco (`df -h /opt`) y si cabe en la VRAM disponible junto con los que ya
hay, siguiendo el mismo criterio que la tabla de arriba.

## Rendimiento medido (10/08/2026)

Misma pregunta técnica larga a los cuatro modelos, con el prompt base de
~5000 tokens que inyecta Open WebUI. Datos de `usage` de Open WebUI y de los
`print_timing` de Ollama.

| Modelo | Capas en GPU | Prompt (tok/s) | Generación (tok/s) | Tokens generados | Total |
|---|---|---|---|---|---|
| `gemma4:e4b` | **43/43** | **3168** | **55,7** | 1873 | **48 s** |
| `qwen3:8b` | 34/37 | 1657 | 18,2 | 827 | 58 s |
| `gemma4:12b-it-qat` | 39/49 | 862 | 10,9 | 1820 | **184 s** |
| `llama3.1:8b` | 32/33 | 2037 | 26,9 | 150 | 17 s (no respondió) |

`gemma4:e4b` es **5,1 veces más rápido generando** que `gemma4:12b-it-qat` y
**3,7 veces más rápido procesando el prompt**, produciendo una respuesta de
longitud equivalente. La diferencia está entera en el *offload* a CPU.

El tiempo de `llama3.1:8b` no es comparable: no llegó a responder.

## El coste fijo de las herramientas nativas

Open WebUI 0.11.0 define **58 herramientas nativas** en `tools/builtin.py`
(notas, memorias, calendario, automatizaciones, canales, bases de
conocimiento, ejecución de código, búsqueda web, generación de imagen…) e
inyecta sus especificaciones JSON en el prompt de cada mensaje. De ahí salen
los ~5000 tokens de prompt base que aparecen en todas las mediciones.

Ese coste se paga en cada mensaje, se usen o no las herramientas:

- `gemma4:12b-it-qat`: **5,9 s** de procesado antes del primer token.
- `gemma4:e4b`: 1,6 s.

Y tiene un segundo efecto, peor que la lentitud: **`llama3.1:8b` no responde
a las preguntas, sino que emite la llamada a la herramienta en crudo**. En la
prueba devolvió un bloque JSON invocando `query_knowledge_bases` en lugar de
contestar. Es un modelo que no maneja bien el formato de *tool calling* que
usa Open WebUI, y con 58 herramientas delante se despista siempre.

Si no se van a usar esas funciones, desactivarlas desde *Admin → Ajustes →
Herramientas* recorta el prompt base a unos pocos cientos de tokens y
devuelve a `llama3.1:8b` la capacidad de responder. Pendiente de hacer.

# Modelos

Los únicos modelos que expone este chat son los que ya estaban descargados
en Ollama antes de este proyecto. No se ha hecho ningún `ollama pull` para
montarlo.

| Modelo | Tamaño en disco | Uso recomendado |
|---|---|---|
| `llama3.1:8b` | 4,9 GB | conversación general; el más rápido de los cuatro, buen valor por defecto |
| `qwen3:8b` | 5,2 GB | razonamiento y código |
| `gemma4:12b-it-qat` | 7,2 GB | conversación general; cuantizado QAT, cabe en 8 GB con margen ajustado |
| `gemma4:e4b` | 9,6 GB | conversación general; **no cabe entero en 8 GB de VRAM** |
| `nomic-embed-text` | 274 MB | embeddings para RAG — no es un modelo de chat |

## El límite de 8 GB de VRAM

La tarjeta es una RTX 4060 de 8 GB. Ollama solo mantiene un modelo cargado en
GPU a la vez salvo que quepan varios juntos, y ninguna combinación de dos de
estos cuatro modelos de chat cabe a la vez. Consecuencias, todas esperadas y
ninguna es un fallo de la instalación:

- **Cambiar de modelo en la interfaz tiene coste.** Ollama descarga el
  modelo que estaba cargado y carga el nuevo: varios segundos antes de la
  primera respuesta. Es más notorio cuanto más grande es el modelo que entra
  o sale.
- **`gemma4:e4b` no entra entero.** Con 9,6 GB en disco (y más en VRAM
  cargado, por el contexto) no cabe en 8 GB. Ollama hace *offload* parcial a
  CPU: sigue funcionando, pero responde notablemente más despacio que los
  otros tres. Si la velocidad importa más que el modelo concreto, usar
  `llama3.1:8b` o `qwen3:8b`.
- **`gemma4:12b-it-qat`** sí cabe entero gracias a la cuantización QAT, pero
  con poco margen: con un contexto largo puede acercarse al límite.

No hay nada que configurar para mitigar esto: es una propiedad del hardware,
no de Open WebUI. Está documentado aquí para que, si alguien nota que un
cambio de modelo tarda o que `gemma4:e4b` va lento, no lo diagnostique como
una avería.

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

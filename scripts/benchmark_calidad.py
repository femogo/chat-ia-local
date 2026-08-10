#!/usr/bin/env python3
"""Benchmark qwen3:8b vs gemma4:e4b contra la API de Ollama.

Fase A: calidad y velocidad en 8 tareas distintas.
Fase B: estres de contexto (needle in a haystack) hasta que fallan.

Guardarrail: aborta si la RAM disponible baja de 3 GB, para no arrastrar a
los otros servicios de la maquina.
"""
import json, time, urllib.request, subprocess, sys, os

OLLAMA = "http://127.0.0.1:11434"
MODELS = ["gemma4:e4b", "qwen3:8b"]
OUT = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(OUT, "resultados.jsonl")
TEXTS = os.path.join(OUT, "salidas")
os.makedirs(TEXTS, exist_ok=True)


def ram_libre_gb():
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 1024 / 1024
    return 99


def guardarrail():
    libre = ram_libre_gb()
    if libre < 3.0:
        print(f"!! ABORTADO: solo {libre:.1f} GB de RAM disponible", flush=True)
        sys.exit(1)
    return libre


def vram():
    try:
        o = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.free",
                            "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=10).stdout.strip()
        used, free = (int(x) for x in o.split(","))
        return used, free
    except Exception:
        return -1, -1


def capas_en_gpu():
    """Ultima linea de offload que haya escrito ollama."""
    try:
        o = subprocess.run(["journalctl", "-u", "ollama", "--since", "3 min ago",
                            "--no-pager", "-o", "cat"],
                           capture_output=True, text=True, timeout=15).stdout
        ult = None
        for line in o.splitlines():
            if "offloaded" in line and "layers to GPU" in line:
                ult = line.split("offloaded")[1].split("layers")[0].strip()
        return ult
    except Exception:
        return None


def pedir(model, prompt, num_ctx, think=False, num_predict=None, timeout=900):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": think,
        "keep_alive": "5m",
        "options": {"num_ctx": num_ctx, "temperature": 0, "seed": 42},
    }
    if num_predict:
        body["options"]["num_predict"] = num_predict
    req = urllib.request.Request(
        f"{OLLAMA}/api/chat",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read())
        wall = time.time() - t0
        msg = d.get("message", {}) or {}
        return {
            "ok": True,
            "content": msg.get("content") or "",
            "thinking": msg.get("thinking") or "",
            "wall_s": round(wall, 2),
            "load_s": round(d.get("load_duration", 0) / 1e9, 2),
            "prompt_tok": d.get("prompt_eval_count", 0),
            "prompt_s": round(d.get("prompt_eval_duration", 0) / 1e9, 2),
            "out_tok": d.get("eval_count", 0),
            "eval_s": round(d.get("eval_duration", 0) / 1e9, 2),
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}",
                "wall_s": round(time.time() - t0, 2)}


def anota(reg):
    with open(RESULTS, "a") as f:
        f.write(json.dumps(reg, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- Fase A
TAREAS = [
    ("factual_trampa", "¿Cuál es la capital de Australia? Responde solo con el nombre de la ciudad."),
    ("aritmetica", "Un tren sale de Madrid a las 14:35 y tarda 2 horas y 50 minutos. "
                   "Se detiene 25 minutos en Zaragoza. ¿A qué hora llega? "
                   "Da solo la hora final en formato HH:MM."),
    ("codigo", "Escribe una función Python llamada `mediana` que reciba una lista de números "
               "y devuelva su mediana, sin usar librerías externas ni `statistics`. "
               "Debe manejar listas de longitud par e impar y lanzar ValueError si la lista está vacía. "
               "Devuelve solo el código, sin explicación."),
    ("formato_json", "Devuelve EXACTAMENTE este JSON y nada más, sin markdown ni texto: "
                     '{"ciudad": "Madrid", "pais": "España", "habitantes": 3300000}'),
    ("alucinacion", "Explícame en qué consiste el teorema de Villanueva-Kraft de 1987 "
                    "sobre convergencia de matrices dispersas."),
    ("razonamiento", "Ana es más alta que Beto. Carlos es más bajo que Beto. "
                     "Diana es más alta que Ana. Ordena a los cuatro de más alto a más bajo. "
                     "Responde solo con los nombres separados por comas."),
    ("resumen_restringido", "Resume en EXACTAMENTE 20 palabras qué es la fotosíntesis. "
                            "Cuenta las palabras antes de responder. Responde solo con el resumen."),
    ("tecnica_larga", "¿Se puede, con una GPU de 8 GB, montar un RAG con un modelo de 12B "
                      "y superar a un modelo frontera como Claude Opus en un dominio concreto? "
                      "Sé concreto y honesto sobre los límites."),
]


def fase_a():
    print("\n########## FASE A: calidad y velocidad ##########", flush=True)
    for nombre, prompt in TAREAS:
        for m in MODELS:
            guardarrail()
            r = pedir(m, prompt, num_ctx=8192, think=False)
            r.update({"fase": "A", "tarea": nombre, "modelo": m})
            if r["ok"]:
                tps = round(r["out_tok"] / r["eval_s"], 1) if r["eval_s"] else 0
                r["tok_s"] = tps
                fn = os.path.join(TEXTS, f"A_{nombre}_{m.replace(':', '_')}.txt")
                with open(fn, "w") as f:
                    f.write(r["content"])
                print(f"  [A] {nombre:22s} {m:14s} {r['wall_s']:6.1f}s "
                      f"{r['out_tok']:5d} tok  {tps:5.1f} tok/s", flush=True)
            else:
                print(f"  [A] {nombre:22s} {m:14s} FALLO {r['error'][:80]}", flush=True)
            r.pop("content", None)
            r.pop("thinking", None)
            anota(r)


# ---------------------------------------------------------------- Fase B
NEEDLE = "El código de acceso a la bóveda del sótano es TULIPAN-9174."
PREGUNTA = "\n\nSegún el texto anterior, ¿cuál es el código de acceso a la bóveda del sótano? Responde solo con el código."


def relleno(objetivo_tok):
    """Texto de relleno con la aguja al 50 % de profundidad."""
    parrafo = ("La logística de almacenes intermedios exige revisar el inventario cíclico, "
               "conciliar las discrepancias de recuento y documentar cada ajuste en el libro "
               "de operaciones antes del cierre mensual del ejercicio contable. ")
    # ~1,4 tokens por palabra en español
    n = max(1, int(objetivo_tok / (len(parrafo.split()) * 1.4)))
    mitad = n // 2
    trozos = []
    for i in range(n):
        trozos.append(f"[{i:05d}] {parrafo}")
        if i == mitad:
            trozos.append(f"\n\n{NEEDLE}\n\n")
    return "".join(trozos)


ESCALONES = [4096, 8192, 16384, 32768, 40960, 65536, 98304, 131072]


def fase_b():
    print("\n########## FASE B: estres de contexto ##########", flush=True)
    for m in MODELS:
        print(f"\n--- {m} ---", flush=True)
        for ctx in ESCALONES:
            libre = guardarrail()
            texto = relleno(int(ctx * 0.85)) + PREGUNTA
            r = pedir(m, texto, num_ctx=ctx, think=False, num_predict=64, timeout=900)
            u, f_ = vram()
            r.update({"fase": "B", "modelo": m, "ctx": ctx,
                      "vram_usada_mb": u, "vram_libre_mb": f_,
                      "ram_libre_gb": round(libre, 1),
                      "capas_gpu": capas_en_gpu()})
            if r["ok"]:
                cont = (r.get("content") or "")
                r["acierto"] = "TULIPAN-9174" in cont
                r["respuesta"] = cont.strip()[:120]
                pps = round(r["prompt_tok"] / r["prompt_s"], 0) if r["prompt_s"] else 0
                print(f"  ctx={ctx:6d}  prompt={r['prompt_tok']:6d} tok  "
                      f"{r['wall_s']:6.1f}s  prompt@{pps:6.0f} tok/s  "
                      f"capas={r['capas_gpu']}  vram={u}MB  "
                      f"{'ACIERTA' if r['acierto'] else 'FALLA: ' + r['respuesta'][:40]}", flush=True)
            else:
                r["acierto"] = False
                print(f"  ctx={ctx:6d}  ERROR tras {r['wall_s']:.0f}s -> {r['error'][:110]}", flush=True)
            r.pop("content", None)
            r.pop("thinking", None)
            anota(r)
            if not r["ok"]:
                print(f"  -> {m} deja de funcionar a partir de ctx={ctx}", flush=True)
                break


# ---------------------------------------------------------------- Fase C
def fase_c():
    """Mismo problema de razonamiento con y sin modo pensamiento."""
    print("\n########## FASE C: efecto del modo pensamiento ##########", flush=True)
    p = ("Tengo 3 cajas. La roja pesa el doble que la azul. La verde pesa 4 kg menos que la roja. "
         "Entre las tres suman 26 kg. ¿Cuánto pesa cada una? Responde solo con los tres pesos.")
    for m in MODELS:
        for think in (False, True):
            guardarrail()
            r = pedir(m, p, num_ctx=8192, think=think, timeout=600)
            r.update({"fase": "C", "modelo": m, "think": think})
            if r["ok"]:
                fn = os.path.join(TEXTS, f"C_{m.replace(':', '_')}_think{int(think)}.txt")
                with open(fn, "w") as f:
                    f.write("=== THINKING ===\n" + (r.get("thinking") or "") +
                            "\n\n=== RESPUESTA ===\n" + r["content"])
                r["think_tok_aprox"] = len((r.get("thinking") or "").split())
                print(f"  [C] {m:14s} think={think!s:5s} {r['wall_s']:6.1f}s "
                      f"{r['out_tok']:5d} tok", flush=True)
            else:
                print(f"  [C] {m:14s} think={think!s:5s} FALLO {r['error'][:70]}", flush=True)
            r.pop("content", None)
            r.pop("thinking", None)
            anota(r)


if __name__ == "__main__":
    open(RESULTS, "w").close()
    t0 = time.time()
    print(f"RAM disponible al empezar: {ram_libre_gb():.1f} GB", flush=True)
    fase_a()
    fase_c()
    fase_b()
    print(f"\nTERMINADO en {(time.time() - t0) / 60:.1f} min", flush=True)

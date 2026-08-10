#!/usr/bin/env python3
"""Fase B corregida: estres de contexto con relleno calibrado en tokens reales.

El intento anterior estimaba los tokens del relleno y se pasaba, asi que
Ollama truncaba el prompt a ctx-1 y dejaba un solo token de salida. Aqui se
calibra midiendo prompt_eval_count real y se reserva margen para la salida.
"""
import json, time, urllib.request, subprocess, sys, os

OLLAMA = "http://127.0.0.1:11434"
MODELS = ["gemma4:e4b", "qwen3:8b"]
OUT = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(OUT, "resultados_b.jsonl")
RESERVA = 700           # tokens que dejamos libres para plantilla + respuesta
NEEDLE = "El código de acceso a la bóveda del sótano es TULIPAN-9174."
PREGUNTA = ("\n\nSegún el texto anterior, ¿cuál es el código de acceso a la "
            "bóveda del sótano? Responde solo con el código, sin explicación.")
PARRAFO = ("La logística de almacenes intermedios exige revisar el inventario cíclico, "
           "conciliar las discrepancias de recuento y documentar cada ajuste en el libro "
           "de operaciones antes del cierre mensual del ejercicio contable. ")
ESCALONES = [4096, 8192, 16384, 32768, 40960, 65536, 98304, 131072, 200000]


def ram_libre_gb():
    for line in open("/proc/meminfo"):
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / 1024 / 1024
    return 99


def guardarrail():
    libre = ram_libre_gb()
    if libre < 3.0:
        print(f"!! ABORTADO: {libre:.1f} GB de RAM disponible", flush=True)
        sys.exit(1)
    return libre


def vram():
    try:
        o = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                            "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=10).stdout.strip()
        return int(o)
    except Exception:
        return -1


def capas():
    try:
        o = subprocess.run(["journalctl", "-u", "ollama", "--since", "4 min ago",
                            "--no-pager", "-o", "cat"],
                           capture_output=True, text=True, timeout=15).stdout
        ult = None
        for line in o.splitlines():
            if "offloaded" in line and "layers to GPU" in line:
                ult = line.split("offloaded")[1].split("layers")[0].strip()
        return ult
    except Exception:
        return None


def pedir(model, prompt, num_ctx, num_predict=48, timeout=1500):
    body = {"model": model, "messages": [{"role": "user", "content": prompt}],
            "stream": False, "think": False, "keep_alive": "5m",
            "options": {"num_ctx": num_ctx, "temperature": 0, "seed": 42,
                        "num_predict": num_predict}}
    req = urllib.request.Request(f"{OLLAMA}/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read())
        return {"ok": True, "content": (d.get("message", {}) or {}).get("content") or "",
                "wall_s": round(time.time() - t0, 2),
                "load_s": round(d.get("load_duration", 0) / 1e9, 2),
                "prompt_tok": d.get("prompt_eval_count", 0),
                "prompt_s": round(d.get("prompt_eval_duration", 0) / 1e9, 2),
                "out_tok": d.get("eval_count", 0),
                "eval_s": round(d.get("eval_duration", 0) / 1e9, 2)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}",
                "wall_s": round(time.time() - t0, 2)}


def texto(n_chunks):
    """n_chunks parrafos numerados con la aguja justo en la mitad."""
    mitad, trozos = n_chunks // 2, []
    for i in range(n_chunks):
        trozos.append(f"[{i:05d}] {PARRAFO}")
        if i == mitad:
            trozos.append(f"\n\n{NEEDLE}\n\n")
    return "".join(trozos) + PREGUNTA


def calibrar(model):
    """Tokens reales por parrafo, medidos contra el propio tokenizador."""
    r = pedir(model, texto(50), num_ctx=8192, num_predict=1)
    if not r["ok"]:
        return None
    return r["prompt_tok"] / 50.0


def main():
    open(RESULTS, "w").close()
    for m in MODELS:
        print(f"\n--- {m} ---", flush=True)
        tpc = calibrar(m)
        if not tpc:
            print(f"  no se pudo calibrar {m}", flush=True)
            continue
        print(f"  calibracion: {tpc:.1f} tokens por parrafo", flush=True)
        for ctx in ESCALONES:
            guardarrail()
            objetivo = ctx - RESERVA
            n = max(2, int(objetivo / tpc))
            r = pedir(m, texto(n), num_ctx=ctx)
            reg = {"modelo": m, "ctx": ctx, "chunks": n, "vram_mb": vram(),
                   "capas_gpu": capas(), "ram_libre_gb": round(ram_libre_gb(), 1)}
            reg.update(r)
            if r["ok"]:
                cont = r["content"].strip()
                # aceptamos con o sin tilde en TULIPAN
                reg["acierto"] = "9174" in cont and "TULIP" in cont.upper()
                reg["truncado"] = r["prompt_tok"] >= ctx - 2
                pps = round(r["prompt_tok"] / r["prompt_s"]) if r["prompt_s"] else 0
                gps = round(r["out_tok"] / r["eval_s"], 1) if r["eval_s"] else 0
                estado = "ACIERTA" if reg["acierto"] else f"FALLA({cont[:30]!r})"
                print(f"  ctx={ctx:6d} prompt={r['prompt_tok']:6d} "
                      f"{'TRUNCADO ' if reg['truncado'] else ''}"
                      f"total={r['wall_s']:6.1f}s prompt@{pps:5d}tok/s gen@{gps:5.1f}tok/s "
                      f"capas={reg['capas_gpu']} vram={reg['vram_mb']}MB {estado}", flush=True)
            else:
                reg["acierto"] = False
                print(f"  ctx={ctx:6d} ERROR tras {r['wall_s']:.0f}s -> {r['error'][:120]}", flush=True)
            reg.pop("content", None)
            with open(RESULTS, "a") as f:
                f.write(json.dumps(reg, ensure_ascii=False) + "\n")
            if not r["ok"]:
                print(f"  -> {m} PETA a partir de ctx={ctx}", flush=True)
                break
    print("\nFASE B TERMINADA", flush=True)


if __name__ == "__main__":
    main()

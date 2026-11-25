"""Inicia os serviços escolhidos e os mantém rodando até Ctrl+C.

Uso (na raiz do projeto):
    python testes/iniciar_servicos.py              # os 8 (Java precisa estar compilado)
    python testes/iniciar_servicos.py --servicos python
    python testes/iniciar_servicos.py --servicos java-rest,python-rest

Em outro terminal, rode o teste funcional:  python testes/testar_servicos.py
Logs de cada servidor: resultados/logs/<servico>.log
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from servicos import RAIZ, selecionar  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--servicos", default="todos")
    args = ap.parse_args()

    logs = RAIZ / "resultados" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    processos = []
    for s in selecionar(args.servicos):
        if s.no_ar():
            print(f"  {s.nome:15s} já estava no ar (porta {s.porta})")
            continue
        if s.linguagem == "java" and not (RAIZ / s.comando[-1]).exists():
            print(f"  {s.nome:15s} NÃO COMPILADO: rode 'mvn package' na pasta java/")
            continue
        log = open(logs / f"{s.nome}.log", "w", encoding="utf-8")
        p = subprocess.Popen(list(s.comando), cwd=RAIZ, stdout=log, stderr=subprocess.STDOUT,
                             env=dict(os.environ, PYTHONWARNINGS="ignore"))
        processos.append((s, p, log))

    for s, p, _ in processos:
        ok = s.aguardar(120)
        print(f"  {s.nome:15s} {'no ar' if ok else 'FALHOU (veja o log)':20s} {s.endereco}")

    if not processos:
        return
    print("\nServiços rodando. Ctrl+C para encerrar.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for _, p, log in processos:
            p.terminate()
        for _, p, log in processos:
            try:
                p.wait(10)
            except subprocess.TimeoutExpired:
                p.kill()
            log.close()
        print("Encerrados.")


if __name__ == "__main__":
    main()

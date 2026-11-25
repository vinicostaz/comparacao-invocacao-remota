"""Executa os testes de carga (Locust) e gera resultados/*.csv e os gráficos.

Para cada serviço: inicia o servidor, faz um aquecimento (importante para o JIT da JVM),
mede cada cenário em vários níveis de carga e para o servidor. Assim cada serviço é medido
sozinho na máquina e sempre a partir dos mesmos dados iniciais.

DOIS MODOS de escolher os níveis de carga (usuários simultâneos):

  1) Busca do ponto de saturação (padrão, sem --usuarios)
     Começa com 1 usuário e vai DOBRANDO (1, 2, 4, 8, 16...) enquanto a vazão crescer.
     Para depois de 2 dobras seguidas sem ganho de vazão (< 10%), se houver falhas
     (> 1%) ou ao atingir --max-usuarios. Em seguida mede pontos intermediários em volta
     do ponto de saturação (ex.: 6 e 12 se a saturação foi em 8), onde os valores mudam,
     e um ponto bem distante (16x a saturação, ex.: 128) para mostrar o que acontece depois.

  2) Níveis fixos:  --usuarios 1,10,20,30,40
     Este é o modo padrão do trabalho e permite comparar cargas baixa, intermediárias
     e alta em intervalos regulares.

Por que 100 e 200 usuários costumam dar a mesma vazão: quando o servidor satura, a vazão X
para de subir e cada usuário extra só espera na fila. Com usuários que não fazem pausa,
latência média ≈ usuários / X (Lei de Little): dobrar os usuários dobra a latência e não
muda a vazão. A região interessante (onde a vazão ainda muda) fica ANTES da saturação.

Uso (na raiz do projeto, depois de compilar o Java com "mvn package" em java/):
    python testes/carga/executar_testes.py                              # 8 serviços, níveis 1,10,20,30,40
    python testes/carga/executar_testes.py --servicos python --duracao 10
    python testes/carga/executar_testes.py --usuarios 1,10,20,30,40     # níveis fixos
    python testes/carga/executar_testes.py --max-usuarios 1024          # deixa a busca ir mais longe
    python testes/carga/executar_testes.py --ja-iniciados               # servidores já rodando

Saída (pasta resultados/):
    resultados.csv            uma linha por serviço x cenário x carga (totais)
    resultados_operacoes.csv  idem, por operação (listarMusicas, POST criar, ...)
    saturacao.csv             ponto de saturação e vazão máxima de cada serviço x cenário
    ambiente.txt              máquina, versões e parâmetros usados
    graficos/*.png            gráficos para os slides (gerados por graficos.py)
"""
import argparse
import csv
import os
import platform
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI))

from servicos import RAIZ, selecionar  # noqa: E402

LOCUSTFILE = AQUI / "locustfile.py"
CLASSES = {"rest": "RestUser", "graphql": "GraphQLUser", "soap": "SoapUser", "grpc": "GrpcUser"}

CAMPOS = ["servico", "linguagem", "tecnologia", "cenario", "usuarios", "operacao", "requisicoes", "falhas",
          "taxa_falhas_pct", "rps", "lat_media_ms", "lat_mediana_ms", "lat_p95_ms", "lat_p99_ms",
          "tamanho_medio_bytes"]

GANHO_MINIMO = 0.10      # dobrar os usuários precisa aumentar a vazão em pelo menos 10%
DOBRAS_SEM_GANHO = 2     # quantas dobras seguidas sem ganho encerram a busca
FALHAS_MAXIMAS = 1.0     # % de falhas que encerra a busca
FRACAO_SATURACAO = 0.90  # saturação = menor carga que atinge 90% da vazão máxima
FATOR_DISTANTE = 16      # ponto extra em 16x a saturação (ex.: saturou em 8 -> mede também 128)


def rodar_locust(servico, cenario, usuarios, duracao_s, processos, prefixo_csv=None):
    cmd = [sys.executable, "-m", "locust", "-f", str(LOCUSTFILE), CLASSES[servico.tecnologia],
           "--host", servico.host_locust, "--headless", "-u", str(usuarios), "-r", str(usuarios),
           "-t", f"{duracao_s}s", "--only-summary", "--loglevel", "WARNING", "--stop-timeout", "5"]
    if processos and processos != 1:
        cmd += ["--processes", str(processos)]
    if prefixo_csv:
        cmd += ["--csv", prefixo_csv]
    env = dict(os.environ, CENARIO=cenario, PYTHONWARNINGS="ignore")
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=RAIZ)
    if proc.returncode not in (0, 1):  # 1 = houve falhas em requisições (registradas no CSV)
        print(proc.stdout[-2000:], proc.stderr[-2000:])
        raise RuntimeError(f"Locust terminou com código {proc.returncode}")


def ler_estatisticas(prefixo_csv):
    def numero(valor, padrao=0.0):
        try:
            return float(valor)
        except (TypeError, ValueError):
            return padrao

    linhas = []
    with open(f"{prefixo_csv}_stats.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            n = int(r["Request Count"])
            falhas = int(r["Failure Count"])
            linhas.append({
                "operacao": "TOTAL" if r["Name"] == "Aggregated" else r["Name"],
                "requisicoes": n,
                "falhas": falhas,
                "taxa_falhas_pct": round(100 * falhas / n, 2) if n else 0,
                "rps": round(numero(r["Requests/s"]), 1),
                "lat_media_ms": round(numero(r["Average Response Time"]), 2),
                "lat_mediana_ms": numero(r["Median Response Time"]),
                "lat_p95_ms": numero(r["95%"]),
                "lat_p99_ms": numero(r["99%"]),
                "tamanho_medio_bytes": round(numero(r["Average Content Size"]), 1),
            })
    return linhas


class Medidor:
    """Mede um serviço num cenário e guarda os resultados de cada nível de carga."""

    def __init__(self, servico, cenario, args, tmp, resultados):
        self.servico, self.cenario, self.args, self.tmp = servico, cenario, args, tmp
        self.resultados = resultados
        self.totais = {}  # usuarios -> linha TOTAL

    def medir(self, u, observacao=""):
        if u in self.totais:
            return self.totais[u]
        prefixo = str(self.tmp / f"{self.servico.nome}_{self.cenario}_{u}")
        rodar_locust(self.servico, self.cenario, u, self.args.duracao, self.args.processos, prefixo)
        for linha in ler_estatisticas(prefixo):
            linha.update(servico=self.servico.nome, linguagem=self.servico.linguagem,
                         tecnologia=self.servico.tecnologia, cenario=self.cenario, usuarios=u)
            self.resultados.append(linha)
            if linha["operacao"] == "TOTAL":
                self.totais[u] = linha
        t = self.totais[u]
        print(f"   {self.cenario:9s} {u:5d} usuários: {t['rps']:9.1f} req/s | média {t['lat_media_ms']:8.1f} ms | "
              f"p95 {t['lat_p95_ms']:7.0f} ms | falhas {t['taxa_falhas_pct']}% {observacao}")
        return t

    def niveis_fixos(self, niveis):
        for u in niveis:
            self.medir(u)

    def buscar_saturacao(self):
        """Dobra os usuários até a vazão parar de crescer; depois refina em volta da saturação."""
        u, melhor, sem_ganho = 1, 0.0, 0
        while u <= self.args.max_usuarios:
            t = self.medir(u)
            if t["taxa_falhas_pct"] > FALHAS_MAXIMAS:
                print(f"   -> parou: {t['taxa_falhas_pct']}% de falhas com {u} usuários")
                break
            if melhor and t["rps"] < melhor * (1 + GANHO_MINIMO):
                sem_ganho += 1
            else:
                sem_ganho = 0
            melhor = max(melhor, t["rps"])
            if sem_ganho >= DOBRAS_SEM_GANHO:
                print(f"   -> parou: vazão não cresceu em {DOBRAS_SEM_GANHO} dobras seguidas")
                break
            u *= 2
        # pontos intermediários em volta da saturação, onde a curva muda de inclinação
        joelho = self.ponto_saturacao()
        for candidato in sorted({round(joelho * 0.75), round(joelho * 1.5)}):
            if 1 <= candidato <= self.args.max_usuarios and candidato not in self.totais:
                self.medir(candidato, "(refinamento em volta da saturação)")
        # um ponto bem distante, para mostrar que depois da saturação só a latência cresce
        distante = min(self.args.max_usuarios, self.ponto_saturacao() * FATOR_DISTANTE)
        if distante > max(self.totais):
            self.medir(distante, "(carga distante, muito além da saturação)")
        print(f"   -> saturação em ~{self.ponto_saturacao()} usuários")

    def ponto_saturacao(self):
        maximo = max(t["rps"] for t in self.totais.values())
        return min(u for u, t in self.totais.items() if t["rps"] >= FRACAO_SATURACAO * maximo)


def iniciar(servico, pasta_logs):
    if servico.no_ar():
        raise SystemExit(f"A porta {servico.porta} já está em uso: pare o processo antes "
                         f"(ou use --ja-iniciados).")
    log = open(pasta_logs / f"{servico.nome}.log", "w", encoding="utf-8")
    proc = subprocess.Popen(list(servico.comando), cwd=RAIZ, stdout=log, stderr=subprocess.STDOUT,
                            env=dict(os.environ, PYTHONWARNINGS="ignore"))
    if not servico.aguardar(120):
        proc.kill()
        raise SystemExit(f"{servico.nome} não subiu em 120 s; veja {pasta_logs / (servico.nome + '.log')}")
    time.sleep(2)
    return proc, log


def parar(proc, log):
    proc.terminate()
    try:
        proc.wait(15)
    except subprocess.TimeoutExpired:
        proc.kill()
    log.close()


def versao_java():
    try:
        r = subprocess.run(["java", "-version"], capture_output=True, text=True)
        return next((l for l in r.stderr.splitlines() if "version" in l), "?").strip()
    except OSError:
        return "java não encontrado"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--servicos", default="todos", help="todos | java | python | rest | java-rest,python-grpc ...")
    ap.add_argument("--cenarios", default="consulta,relacionamento,catalogo,crud")
    ap.add_argument("--usuarios", default="1,10,20,30,40",
                    help="níveis FIXOS (padrão: 1,10,20,30,40). Use uma string vazia para busca automática")
    ap.add_argument("--max-usuarios", type=int, default=512, help="limite da busca automática")
    ap.add_argument("--duracao", type=int, default=15, help="segundos por medição")
    ap.add_argument("--aquecimento", type=int, default=10, help="segundos de aquecimento por serviço")
    ap.add_argument("--processos", type=int, default=1,
                    help="processos do Locust (-1 = um por CPU; só Linux/macOS). Use se o gerador de carga "
                         "virar gargalo")
    ap.add_argument("--ja-iniciados", action="store_true", help="não inicia/para os servidores")
    ap.add_argument("--saida", default=str(RAIZ / "resultados"))
    args = ap.parse_args()

    servicos = selecionar(args.servicos)
    cenarios = args.cenarios.split(",")
    niveis = [int(u) for u in args.usuarios.split(",")] if args.usuarios else None
    saida = Path(args.saida)
    (saida / "logs").mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="carga_"))

    if niveis:
        modo = f"níveis fixos: {niveis} usuários"
        medicoes = len(niveis)
    else:
        modo = f"busca do ponto de saturação (1, 2, 4, 8... até no máximo {args.max_usuarios} usuários)"
        medicoes = 9  # estimativa típica
    total = len(servicos) * (len(cenarios) * medicoes * (args.duracao + 4) + args.aquecimento + 10)
    print(f"Serviços: {', '.join(s.nome for s in servicos)}\nCenários: {cenarios}\nModo: {modo} | "
          f"{args.duracao}s por medição\nTempo estimado: ~{total // 60} min\n")

    resultados = []
    for servico in servicos:
        print(f"=== {servico.nome}")
        proc = log = None
        if not args.ja_iniciados:
            proc, log = iniciar(servico, saida / "logs")
        elif not servico.no_ar():
            print("   (fora do ar, pulando)")
            continue
        try:
            rodar_locust(servico, "consulta", 10, args.aquecimento, args.processos)  # aquecimento, descartado
            for cenario in cenarios:
                medidor = Medidor(servico, cenario, args, tmp, resultados)
                if niveis:
                    medidor.niveis_fixos(niveis)
                else:
                    medidor.buscar_saturacao()
        finally:
            if proc:
                parar(proc, log)

    # Mescla com resultados anteriores de outros serviços (permite rodar Java e Python em momentos diferentes)
    arq_ops = saida / "resultados_operacoes.csv"
    medidos = {r["servico"] for r in resultados}
    anteriores = []
    if arq_ops.exists():
        with open(arq_ops, newline="", encoding="utf-8") as f:
            anteriores = [r for r in csv.DictReader(f) if r["servico"] not in medidos]
    todos = anteriores + resultados
    with open(arq_ops, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(todos)
    with open(saida / "resultados.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[c for c in CAMPOS if c != "operacao"], extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted((r for r in todos if r["operacao"] == "TOTAL"),
                           key=lambda r: (r["servico"], r["cenario"], int(r["usuarios"]))))

    with open(saida / "ambiente.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now():%Y-%m-%d %H:%M}] serviços: {', '.join(sorted(medidos))}\n"
                f"  SO: {platform.platform()} | CPUs lógicas: {os.cpu_count()}\n"
                f"  Python: {platform.python_version()} | {versao_java()}\n"
                f"  cenários: {cenarios} | {modo} | {args.duracao}s por medição | "
                f"aquecimento {args.aquecimento}s | processos Locust: {args.processos}\n"
                f"  gerador de carga (Locust) e servidor na MESMA máquina\n\n")

    print(f"\nResultados em {saida}")
    from graficos import gerar
    gerar(saida)


if __name__ == "__main__":
    main()

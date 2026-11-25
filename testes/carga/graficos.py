"""Gera os gráficos dos testes de carga a partir de resultados/resultados_operacoes.csv.

Uso: python testes/carga/graficos.py [pasta_resultados]
(também é chamado automaticamente ao final de executar_testes.py)

Gráficos (pasta resultados/graficos/):
  resumo_<cenario>.png         vazão máxima de cada serviço e com quantos usuários ele satura
  vazao_<cenario>.png          vazão (req/s) x usuários simultâneos, Java | Python
  latencia_p95_<cenario>.png   latência p95 (ms) x usuários simultâneos, Java | Python
  tamanho_resposta.png         bytes da resposta de "listar músicas" (JSON x XML x Protobuf)
Também grava resultados/saturacao.csv (ponto de saturação de cada serviço).
O anel nos gráficos de linha marca a menor carga que atinge 90% da vazão máxima
observada no intervalo medido.
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

TECNOLOGIAS = ["rest", "graphql", "soap", "grpc"]
NOMES = {"rest": "REST", "graphql": "GraphQL", "soap": "SOAP", "grpc": "gRPC"}
LINGUAGENS = ["java", "python"]
NOMES_LING = {"java": "Java", "python": "Python"}
CENARIOS = {
    "consulta": "Consultas variadas do enunciado",
    "relacionamento": "Músicas de uma playlist",
    "catalogo": "Listagem completa de músicas",
    "crud": "Ciclo CRUD de um usuário",
}

# Paleta categórica validada (ordem fixa; cor = tecnologia em TODOS os gráficos)
COR = {"rest": "#2a78d6", "graphql": "#eb6834", "soap": "#1baf7a", "grpc": "#eda100"}
MARCADOR = {"rest": "o", "graphql": "s", "soap": "^", "grpc": "D"}  # codificação secundária
SUPERFICIE, TINTA, TINTA2, MUDO = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRADE, EIXO = "#e1e0d9", "#c3c2b7"

plt.rcParams.update({
    "figure.facecolor": SUPERFICIE, "axes.facecolor": SUPERFICIE, "savefig.facecolor": SUPERFICIE,
    "font.family": "sans-serif", "font.size": 11, "text.color": TINTA,
    "axes.labelcolor": TINTA2, "xtick.color": MUDO, "ytick.color": MUDO,
    "axes.edgecolor": EIXO, "axes.titlesize": 13, "axes.titleweight": "bold",
})


def ler(pasta):
    with open(Path(pasta) / "resultados_operacoes.csv", newline="", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    for r in linhas:
        r["usuarios"] = int(r["usuarios"])
        for c in ("rps", "lat_p95_ms", "lat_media_ms", "tamanho_medio_bytes", "taxa_falhas_pct"):
            r[c] = float(r[c])
    return linhas


def milhar(valor, _=None):
    """8000 -> '8.000' (padrão brasileiro)."""
    return f"{valor:,.0f}".replace(",", ".")


def estilo(ax):
    ax.grid(axis="y", color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.yaxis.set_major_formatter(FuncFormatter(milhar))


def afastar(posicoes, distancia):
    """Afasta verticalmente rótulos muito próximos (mantém a ordem)."""
    ordem = sorted(range(len(posicoes)), key=lambda i: posicoes[i])
    ajustadas = list(posicoes)
    for anterior, atual in zip(ordem, ordem[1:]):
        if ajustadas[atual] - ajustadas[anterior] < distancia:
            ajustadas[atual] = ajustadas[anterior] + distancia
    return ajustadas


def legenda(fig, tecnologias):
    alcas = [plt.Line2D([], [], color=COR[t], marker=MARCADOR[t], linewidth=2, markersize=8) for t in tecnologias]
    nomes = [NOMES[t] for t in tecnologias]
    alcas.append(plt.Line2D([], [], linestyle="none", marker="o", markersize=13, markerfacecolor="none",
                            markeredgecolor=TINTA2, markeredgewidth=1.5))
    nomes.append("90% da vazão máxima medida")
    fig.legend(alcas, nomes, loc="upper left", ncol=len(alcas),
               frameon=False, bbox_to_anchor=(0.005, 0.935), labelcolor=TINTA2)


FRACAO_SATURACAO = 0.90  # saturação = menor carga que já atinge 90% da vazão máxima


def saturacao(totais):
    """{(tecnologia, linguagem): {"usuarios": u_sat, "rps_max": X, "usuarios_rps_max": u, "pontos": {u: linha}}}"""
    series = defaultdict(dict)
    for r in totais:
        series[(r["tecnologia"], r["linguagem"])][r["usuarios"]] = r
    resultado = {}
    for chave, pontos in series.items():
        maximo = max(p["rps"] for p in pontos.values())
        resultado[chave] = {
            "usuarios": min(u for u, p in pontos.items() if p["rps"] >= FRACAO_SATURACAO * maximo),
            "rps_max": maximo,
            "usuarios_rps_max": max(pontos, key=lambda u: pontos[u]["rps"]),
            "pontos": pontos,
        }
    return resultado


def gravar_saturacao(pasta, dados):
    """resultados/saturacao.csv: ponto de saturação e vazão máxima de cada serviço x cenário."""
    linhas = []
    for cenario in sorted({r["cenario"] for r in dados}):
        totais = [r for r in dados if r["operacao"] == "TOTAL" and r["cenario"] == cenario]
        for (t, l), s in saturacao(totais).items():
            p = s["pontos"][s["usuarios"]]
            linhas.append({
                "servico": f"{l}-{t}", "cenario": cenario,
                "usuarios_saturacao": s["usuarios"], "rps_maximo": round(s["rps_max"], 1),
                "usuarios_rps_maximo": s["usuarios_rps_max"],
                "rps_na_saturacao": p["rps"], "lat_media_na_saturacao_ms": p["lat_media_ms"],
                "lat_p95_na_saturacao_ms": p["lat_p95_ms"],
                "niveis_testados": " ".join(str(u) for u in sorted(s["pontos"])),
            })
    with open(Path(pasta) / "saturacao.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(sorted(linhas, key=lambda r: (r["cenario"], r["servico"])))
    return linhas


def eixo_usuarios(ax, niveis):
    """Eixo X linear com todos os níveis medidos explicitamente."""
    minimo, maximo = min(niveis), max(niveis)
    margem = max(2, (maximo - minimo) * 0.08)
    ax.set_xscale("linear")
    ax.set_xticks(niveis, [str(v) for v in niveis])
    ax.set_xlim(minimo - margem, maximo + margem * 2.2)
    ax.set_xlabel("usuários simultâneos (escala linear)")


def linhas_por_linguagem(dados, cenario, metrica, titulo, rotulo_y, arquivo):
    totais = [r for r in dados if r["operacao"] == "TOTAL" and r["cenario"] == cenario]
    if not totais:
        return None
    niveis = sorted({r["usuarios"] for r in totais})
    sat = saturacao(totais)
    fig, eixos = plt.subplots(1, 2, figsize=(12, 5.6), sharey=True)
    usadas = []
    for ax, ling in zip(eixos, LINGUAGENS):
        estilo(ax)
        ax.set_title(NOMES_LING[ling], loc="left", color=TINTA)
        eixo_usuarios(ax, niveis)
        serie = defaultdict(dict)
        for r in totais:
            if r["linguagem"] == ling:
                serie[r["tecnologia"]][r["usuarios"]] = r[metrica]
        if not serie:
            ax.text(0.5, 0.5, f"sem dados de {NOMES_LING[ling]}\n(rode executar_testes.py --servicos {ling})",
                    transform=ax.transAxes, ha="center", va="center", color=MUDO)
            continue
        for t in TECNOLOGIAS:
            if t not in serie:
                continue
            xs = sorted(serie[t])
            ys = [serie[t][u] for u in xs]
            ax.plot(xs, ys, color=COR[t], marker=MARCADOR[t], linewidth=2, markersize=7,
                    markeredgecolor=SUPERFICIE, markeredgewidth=1.5, zorder=3)
            # anel no ponto de saturação (a partir daqui a vazão para de crescer)
            if len(xs) >= 3:
                u_sat = sat[(t, ling)]["usuarios"]
                ax.scatter([u_sat], [serie[t][u_sat]], s=230, facecolors="none", edgecolors=COR[t],
                           linewidths=1.8, zorder=4)
            if t not in usadas:
                usadas.append(t)
    eixos[0].set_ylabel(rotulo_y)
    eixos[0].set_ylim(bottom=0)
    legenda(fig, usadas)
    fig.suptitle(f"{titulo} — {CENARIOS.get(cenario, cenario)}", x=0.01, ha="left", fontsize=14,
                 fontweight="bold", color=TINTA)
    fig.tight_layout(rect=(0, 0, 1, 0.87))
    fig.savefig(arquivo, dpi=150)
    plt.close(fig)
    return arquivo


def resumo(dados, cenario, arquivo):
    """Vazão MÁXIMA de cada serviço e a partir de quantos usuários ele satura."""
    totais = [r for r in dados if r["operacao"] == "TOTAL" and r["cenario"] == cenario]
    if not totais:
        return None
    sat = saturacao(totais)
    barras = [(t, l) for t in TECNOLOGIAS for l in LINGUAGENS if (t, l) in sat]
    fig, ax = plt.subplots(figsize=(12, 5.6))
    estilo(ax)
    xs, x = [], 0.0
    for i, (t, l) in enumerate(barras):
        if i and barras[i - 1][0] != t:
            x += 0.6  # espaço entre tecnologias
        xs.append(x)
        x += 1
    valores = [sat[b]["rps_max"] for b in barras]
    ax.bar(xs, valores, width=0.92, color=[COR[t] for t, _ in barras], edgecolor=SUPERFICIE, linewidth=2)
    for xi, b, v in zip(xs, barras, valores):
        ax.annotate(milhar(v), (xi, v), xytext=(0, 18), textcoords="offset points", ha="center",
                    fontsize=11, fontweight="bold", color=TINTA)
        ax.annotate(f"90% em ~{sat[b]['usuarios']} usuário{'s' if sat[b]['usuarios'] > 1 else ''}", (xi, v), xytext=(0, 5), textcoords="offset points",
                    ha="center", fontsize=9, color=TINTA2)
    ax.set_xticks(xs, [f"{NOMES[t]}\n{NOMES_LING[l]}" for t, l in barras])
    ax.tick_params(axis="x", length=0, colors=TINTA2)
    ax.set_ylabel("vazão máxima (requisições por segundo)")
    ax.set_ylim(top=max(valores) * 1.15)
    ax.set_title(f"Vazão máxima e carga de 90% — {CENARIOS.get(cenario, cenario)}",
                 loc="left", fontsize=14)
    fig.tight_layout()
    fig.savefig(arquivo, dpi=150)
    plt.close(fig)
    return arquivo


def tamanho_resposta(dados, arquivo):
    """Tamanho médio da resposta de listarMusicas (200 músicas): JSON x XML x Protobuf."""
    linhas = [r for r in dados if r["operacao"] == "listarMusicas" and r["cenario"] == "consulta"]
    if not linhas:
        return None
    tam = {}
    for r in linhas:
        tam[(r["tecnologia"], r["linguagem"])] = r["tamanho_medio_bytes"] / 1024
    linguagens = [l for l in LINGUAGENS if any(k[1] == l for k in tam)]
    fig, eixos = plt.subplots(1, len(linguagens), figsize=(12, 4.6), sharex=True, squeeze=False)
    for ax, ling in zip(eixos[0], linguagens):
        techs = [t for t in TECNOLOGIAS if (t, ling) in tam]
        valores = [tam[(t, ling)] for t in techs]
        ys = list(range(len(techs)))[::-1]
        ax.barh(ys, valores, height=0.7, color=[COR[t] for t in techs], edgecolor=SUPERFICIE, linewidth=2)
        ax.set_yticks(ys, [NOMES[t] for t in techs])
        for y, v in zip(ys, valores):
            ax.annotate(f"{v:.1f} KB".replace(".", ","), (v, y), xytext=(6, 0), textcoords="offset points",
                        va="center", fontsize=10, color=TINTA)
        ax.grid(axis="x", color=GRADE, linewidth=0.8)
        ax.set_axisbelow(True)
        for lado in ("top", "right", "bottom"):
            ax.spines[lado].set_visible(False)
        ax.tick_params(axis="y", length=0, colors=TINTA2)
        ax.tick_params(axis="x", length=0)
        ax.set_title(f"Servidor {NOMES_LING[ling]}", loc="left", color=TINTA)
        ax.set_xlabel("KB por resposta")
        ax.set_xlim(right=max(tam.values()) * 1.18)
    fig.suptitle("Tamanho da resposta de \"listar músicas\" (200 músicas): JSON × XML × Protobuf",
                 x=0.01, ha="left", fontsize=14, fontweight="bold", color=TINTA)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(arquivo, dpi=150)
    plt.close(fig)
    return arquivo


def gerar(pasta):
    pasta = Path(pasta)
    destino = pasta / "graficos"
    destino.mkdir(parents=True, exist_ok=True)
    dados = ler(pasta)
    feitos = []
    for cenario in sorted({r["cenario"] for r in dados}):
        feitos.append(resumo(dados, cenario, destino / f"resumo_{cenario}.png"))
        feitos.append(linhas_por_linguagem(dados, cenario, "rps", "Vazão", "requisições por segundo",
                                           destino / f"vazao_{cenario}.png"))
        feitos.append(linhas_por_linguagem(dados, cenario, "lat_p95_ms", "Latência p95",
                                           "latência p95 (ms) — menor é melhor",
                                           destino / f"latencia_p95_{cenario}.png"))
    feitos.append(tamanho_resposta(dados, destino / "tamanho_resposta.png"))
    feitos = [f for f in feitos if f]
    gravar_saturacao(pasta, dados)
    print(f"Ponto de saturação de cada serviço: {pasta / 'saturacao.csv'}")
    print("Gráficos gerados:\n  " + "\n  ".join(str(f) for f in feitos))
    return feitos


if __name__ == "__main__":
    gerar(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "resultados")

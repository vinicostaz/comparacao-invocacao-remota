#!/usr/bin/env python3
"""Gera os graficos do benchmark a partir do CSV versionado."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "results" / "benchmark.csv"
OUTPUT_DIR = ROOT / "results" / "graficos"

PROTOCOLS = ["REST", "GraphQL", "SOAP", "gRPC"]
CONCURRENCIES = [1, 10, 30]
LOAD_LABELS = ["Baixa (1)", "Média (10)", "Alta (30)"]
COLORS = {
    "REST": "#2563EB",
    "GraphQL": "#DB2777",
    "SOAP": "#D97706",
    "gRPC": "#059669",
}
PROFILES = {
    "entity_read": ("Leitura de usuário por ID", "leitura_usuario.png"),
    "relationship_read": (
        "Leitura de músicas de uma playlist",
        "leitura_playlist.png",
    ),
    "write_cycle": ("Ciclo de criação e remoção", "ciclo_escrita.png"),
}


def load_rows() -> list[dict[str, str]]:
    with CSV_PATH.open(encoding="utf-8", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def values_for(
    rows: list[dict[str, str]], profile: str, protocol: str, metric: str
) -> list[float]:
    indexed = {
        int(row["concurrency"]): float(row[metric])
        for row in rows
        if row["profile"] == profile and row["protocol"] == protocol
    }
    return [indexed[concurrency] for concurrency in CONCURRENCIES]


def draw_metric(
    axis: plt.Axes,
    rows: list[dict[str, str]],
    profile: str,
    metric: str,
    title: str,
    ylabel: str,
) -> None:
    group_positions = list(range(len(CONCURRENCIES)))
    bar_width = 0.19
    maximum = 0.0

    for protocol_index, protocol in enumerate(PROTOCOLS):
        values = values_for(rows, profile, protocol, metric)
        maximum = max(maximum, *values)
        offset = (protocol_index - (len(PROTOCOLS) - 1) / 2) * bar_width
        positions = [position + offset for position in group_positions]
        bars = axis.bar(
            positions,
            values,
            width=bar_width,
            color=COLORS[protocol],
            label=protocol,
            edgecolor="white",
            linewidth=0.6,
        )
        axis.bar_label(bars, fmt="%.1f", padding=3, fontsize=7)

    axis.set_title(title, fontsize=13, fontweight="bold", pad=10)
    axis.set_ylabel(ylabel)
    axis.set_xticks(group_positions, LOAD_LABELS)
    axis.set_xlabel("Nível de carga (concorrência)")
    axis.set_yscale("linear")
    axis.set_ylim(0, maximum * 1.22)
    axis.grid(axis="y", color="#CBD5E1", linewidth=0.8, alpha=0.7)
    axis.set_axisbelow(True)
    axis.spines[["top", "right"]].set_visible(False)


def generate_chart(
    rows: list[dict[str, str]], profile: str, profile_title: str, filename: str
) -> None:
    figure, axes = plt.subplots(2, 1, figsize=(12, 9))
    figure.subplots_adjust(
        top=0.84, bottom=0.07, left=0.08, right=0.98, hspace=0.38
    )
    figure.suptitle(
        f"Benchmark - {profile_title}", fontsize=17, fontweight="bold"
    )

    draw_metric(
        axes[0],
        rows,
        profile,
        "throughput_rps",
        "Vazão por nível de carga",
        "Requisições por segundo (req/s)",
    )
    draw_metric(
        axes[1],
        rows,
        profile,
        "p95_ms",
        "Latência p95 por nível de carga",
        "Latência p95 (ms)",
    )

    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(
        handles,
        labels,
        loc="upper center",
        ncols=len(PROTOCOLS),
        frameon=False,
        bbox_to_anchor=(0.5, 0.93),
    )
    figure.text(
        0.995,
        0.002,
        "Fonte: results/benchmark.csv | Escala linear",
        ha="right",
        va="bottom",
        fontsize=8,
        color="#475569",
    )
    figure.savefig(OUTPUT_DIR / filename, dpi=150, facecolor="white")
    plt.close(figure)


def main() -> None:
    rows = load_rows()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for profile, (title, filename) in PROFILES.items():
        generate_chart(rows, profile, title, filename)
        print(f"Gerado: {OUTPUT_DIR / filename}")


if __name__ == "__main__":
    main()

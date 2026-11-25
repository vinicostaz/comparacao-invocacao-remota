"""Cadastro dos 8 serviços (4 tecnologias x 2 linguagens): portas, URLs e como iniciá-los.

Os comandos são executados a partir da raiz do projeto. Os serviços Java precisam
ter sido compilados antes (na pasta java/: mvn package).
"""
import socket
import sys
import time
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PY = sys.executable


@dataclass(frozen=True)
class Servico:
    nome: str          # ex.: "java-rest"
    linguagem: str     # "java" | "python"
    tecnologia: str    # "rest" | "graphql" | "soap" | "grpc"
    porta: int
    comando: tuple

    @property
    def endereco(self) -> str:
        """Endereço usado pelos clientes de cada tecnologia."""
        base = f"http://localhost:{self.porta}"
        return {
            "rest": base,
            "graphql": f"{base}/graphql",
            "soap": f"{base}/soap/streaming",
            "grpc": f"localhost:{self.porta}",
        }[self.tecnologia]

    @property
    def host_locust(self) -> str:
        """Valor de --host para o Locust (base HTTP ou host:porta no gRPC)."""
        return f"localhost:{self.porta}" if self.tecnologia == "grpc" else f"http://localhost:{self.porta}"

    def no_ar(self) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", self.porta), timeout=0.5):
                return True
        except OSError:
            return False

    def aguardar(self, limite_s: float = 90) -> bool:
        fim = time.time() + limite_s
        while time.time() < fim:
            if self.no_ar():
                return True
            time.sleep(0.5)
        return False


def _java(modulo):
    return ("java", "-jar", f"java/{modulo}/target/{modulo}.jar")


def _python(pasta):
    return (PY, f"python/{pasta}/servidor.py")


TECNOLOGIAS = ["rest", "graphql", "soap", "grpc"]
LINGUAGENS = ["java", "python"]

SERVICOS = {
    s.nome: s for s in [
        Servico("java-rest", "java", "rest", 8001, _java("servico-rest")),
        Servico("java-graphql", "java", "graphql", 8002, _java("servico-graphql")),
        Servico("java-soap", "java", "soap", 8003, _java("servico-soap")),
        Servico("java-grpc", "java", "grpc", 8004, _java("servico-grpc")),
        Servico("python-rest", "python", "rest", 9001, _python("servico_rest")),
        Servico("python-graphql", "python", "graphql", 9002, _python("servico_graphql")),
        Servico("python-soap", "python", "soap", 9003, _python("servico_soap")),
        Servico("python-grpc", "python", "grpc", 9004, _python("servico_grpc")),
    ]
}


def selecionar(nomes: str | None) -> list[Servico]:
    """'todos' / None -> os 8; senão lista separada por vírgula (aceita 'java', 'rest', 'python-grpc'...)."""
    if not nomes or nomes == "todos":
        return list(SERVICOS.values())
    escolhidos = []
    for item in nomes.split(","):
        item = item.strip()
        achados = [s for s in SERVICOS.values() if item in (s.nome, s.linguagem, s.tecnologia)]
        if not achados:
            raise SystemExit(f"Serviço desconhecido: {item}. Opções: {', '.join(SERVICOS)}")
        escolhidos += [s for s in achados if s not in escolhidos]
    return escolhidos

"""Gera (quando necessário) e importa o código Python de contratos/streaming.proto.

Equivale a rodar manualmente, dentro da pasta python/:
    python -m grpc_tools.protoc -I ../contratos --python_out=servico_grpc/gerado \
        --grpc_python_out=servico_grpc/gerado ../contratos/streaming.proto

O código é regenerado automaticamente se o .proto for alterado.
"""
import sys
from pathlib import Path

PASTA = Path(__file__).resolve().parent
GERADO = PASTA / "gerado"
PROTO = PASTA.parent.parent / "contratos" / "streaming.proto"


def gerar() -> None:
    import grpc_tools
    from grpc_tools import protoc

    GERADO.mkdir(exist_ok=True)
    protos_padrao = Path(grpc_tools.__file__).parent / "_proto"  # google/protobuf/empty.proto
    codigo = protoc.main([
        "protoc",
        f"-I{PROTO.parent}",
        f"-I{protos_padrao}",
        f"--python_out={GERADO}",
        f"--grpc_python_out={GERADO}",
        str(PROTO),
    ])
    if codigo != 0:
        raise RuntimeError(f"protoc falhou ao compilar {PROTO}")


def carregar():
    """Retorna os módulos (streaming_pb2, streaming_pb2_grpc)."""
    gerado_grpc = GERADO / "streaming_pb2_grpc.py"
    if not gerado_grpc.exists() or gerado_grpc.stat().st_mtime < PROTO.stat().st_mtime:
        gerar()
    if str(GERADO) not in sys.path:
        sys.path.insert(0, str(GERADO))
    import streaming_pb2
    import streaming_pb2_grpc
    return streaming_pb2, streaming_pb2_grpc

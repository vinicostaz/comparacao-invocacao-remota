#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROTO_DIR="$ROOT_DIR/src/music_service/services/grpc_api"
OUT_DIR="$PROTO_DIR/generated"

python -m grpc_tools.protoc \
  -I "$PROTO_DIR" \
  --python_out="$OUT_DIR" \
  --grpc_python_out="$OUT_DIR" \
  "$PROTO_DIR/music.proto"

sed -i 's/^import music_pb2/from . import music_pb2/' "$OUT_DIR/music_pb2_grpc.py"
echo "Codigo gRPC gerado em $OUT_DIR"


# Comparação de Tecnologias de Invocação Remota

Implementação de um serviço de streaming de músicas usando quatro tecnologias de invocação remota: SOAP, REST, GraphQL e gRPC. Todas as versões usam Python, o mesmo modelo de dados e a mesma camada SQLite.

## Equipe

- Vinicius Costa - 2517259
- Ângelo Kauê - 2225671
- Vinicius Andrade - 2320419

## Escopo

O serviço oferece CRUD de:

- usuários;
- músicas;
- playlists.

Também oferece as consultas relacionais solicitadas:

- playlists de um usuário;
- músicas de uma playlist;
- playlists que contêm uma música.

## Tecnologias

| Implementação | Biblioteca | Interface |
|---|---|---|
| REST | FastAPI | HTTP e JSON |
| GraphQL | Strawberry | Schema GraphQL sobre HTTP |
| SOAP | Spyne | WSDL e XML sobre HTTP |
| gRPC | grpcio | Protocol Buffers sobre HTTP/2 |

## Estrutura do repositório

```text
.
├── apresentacao/        # apresentação final
├── enunciado/           # PDF fornecido pelo professor
├── results/             # resultados brutos em CSV e JSON
├── scripts/             # geração dos stubs gRPC
├── src/music_service/   # domínio, APIs e benchmark
├── tests/               # testes automatizados
├── Makefile
└── pyproject.toml
```

## Preparação do ambiente

Requer Python 3.11 ou superior.

```bash
make setup
make seed
make test
```

O comando `make setup` cria o ambiente virtual, instala as dependências e gera os arquivos Python a partir de `music.proto`.

## Execução

Abra quatro terminais na raiz do repositório.

REST:

```bash
MUSIC_DB=data/music.db PYTHONPATH=src .venv/bin/uvicorn \
  music_service.services.rest:app --port 8001
```

GraphQL:

```bash
MUSIC_DB=data/music.db PYTHONPATH=src .venv/bin/uvicorn \
  music_service.services.graphql:app --port 8002
```

SOAP:

```bash
MUSIC_DB=data/music.db PYTHONPATH=src .venv/bin/python \
  -m music_service.services.soap
```

gRPC:

```bash
MUSIC_DB=data/music.db PYTHONPATH=src .venv/bin/python \
  -m music_service.services.grpc_api.server
```

Endereços locais:

- REST e OpenAPI: `http://127.0.0.1:8001/docs`
- GraphQL: `http://127.0.0.1:8002/graphql`
- SOAP e WSDL: `http://127.0.0.1:8003/?wsdl`
- gRPC: `127.0.0.1:50051`

## Testes automatizados

```bash
make test
```

Os testes verificam regras do domínio, CRUD, integridade dos relacionamentos e o contrato REST.

## Testes de carga

```bash
make benchmark
```

O benchmark usa três perfis:

- leitura de um usuário;
- leitura das músicas de uma playlist;
- ciclo de criação e remoção de um usuário.

Cada tecnologia recebe 180 operações em cada nível:

- carga baixa: concorrência 1;
- carga média: concorrência 10;
- carga alta: concorrência 30.

Os gráficos da apresentação usam escala linear. Os dados brutos estão em [`results/benchmark.csv`](results/benchmark.csv) e [`results/benchmark.json`](results/benchmark.json).

### Vazão com carga média

| Perfil | REST | GraphQL | SOAP | gRPC |
|---|---:|---:|---:|---:|
| Usuário por ID | 640,05 req/s | 543,71 req/s | 421,18 req/s | 1.573,98 req/s |
| Músicas da playlist | 518,33 req/s | 417,34 req/s | 245,80 req/s | 1.085,61 req/s |
| Ciclo de escrita | 165,75 req/s | 195,10 req/s | 155,74 req/s | 198,90 req/s |

Os 6.480 casos medidos terminaram sem erro. Os resultados descrevem estas implementações neste computador. Eles não constituem uma comparação universal dos protocolos.

## Entregáveis

- [Apresentação final](apresentacao/Trabalho_6.pptx)
- [Enunciado em PDF](enunciado/Trabalho_6.pdf)
- [Resultados em CSV](results/benchmark.csv)
- [Resultados em JSON](results/benchmark.json)


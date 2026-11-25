"""Serviço REST (FastAPI + Uvicorn). Porta 9001.

Recursos e verbos HTTP (iguais aos do servidor Java):
  /usuarios                 GET (listar)  POST (criar)
  /usuarios/{id}            GET  PUT  DELETE
  /usuarios/{id}/playlists  GET (playlists do usuário)  POST (criar playlist)
  /musicas                  GET  POST
  /musicas/{id}             GET  PUT  DELETE
  /musicas/{id}/playlists   GET (playlists que contêm a música)
  /playlists/{id}           GET  PUT  DELETE
  /playlists/{id}/musicas   GET (músicas da playlist)

Documentação interativa (OpenAPI/Swagger): http://localhost:9001/docs
Executar: python servico_rest/servidor.py   (dentro da pasta python/)
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # permite importar "comum"

import uvicorn
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from comum.repositorio import NaoEncontrado, RepositorioStreaming, RequisicaoInvalida

repo = RepositorioStreaming.com_dados_iniciais()
app = FastAPI(title="Streaming de Músicas - REST (Python)")


# ------------------------------------------------------------ modelos JSON
class ModeloJson(BaseModel):
    """JSON em camelCase (usuarioId, musicaIds), igual ao servidor Java."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class UsuarioDados(ModeloJson):
    nome: str
    idade: int


class MusicaDados(ModeloJson):
    nome: str
    artista: str


class PlaylistDados(ModeloJson):
    nome: str
    musica_ids: list[int] = []


class UsuarioJson(ModeloJson):
    id: int
    nome: str
    idade: int


class MusicaJson(ModeloJson):
    id: int
    nome: str
    artista: str


class PlaylistJson(ModeloJson):
    id: int
    nome: str
    usuario_id: int
    musica_ids: list[int]


# ------------------------------------------------- erros -> status HTTP
@app.exception_handler(NaoEncontrado)
async def nao_encontrado(_: Request, e: NaoEncontrado):
    return JSONResponse(status_code=404, content={"erro": str(e)})


@app.exception_handler(RequisicaoInvalida)
async def requisicao_invalida(_: Request, e: RequisicaoInvalida):
    return JSONResponse(status_code=400, content={"erro": str(e)})


def criado(response: Response, local: str) -> None:
    response.status_code = status.HTTP_201_CREATED
    response.headers["Location"] = local


# ---------------------------------------------------------------- usuários
@app.get("/usuarios", response_model=list[UsuarioJson], tags=["usuarios"])
async def listar_usuarios():
    return repo.listar_usuarios()


@app.post("/usuarios", response_model=UsuarioJson, status_code=201, tags=["usuarios"])
async def criar_usuario(dados: UsuarioDados, response: Response):
    u = repo.criar_usuario(dados.nome, dados.idade)
    criado(response, f"/usuarios/{u.id}")
    return u


@app.get("/usuarios/{id}", response_model=UsuarioJson, tags=["usuarios"])
async def obter_usuario(id: int):
    return repo.obter_usuario(id)


@app.put("/usuarios/{id}", response_model=UsuarioJson, tags=["usuarios"])
async def atualizar_usuario(id: int, dados: UsuarioDados):
    return repo.atualizar_usuario(id, dados.nome, dados.idade)


@app.delete("/usuarios/{id}", status_code=204, tags=["usuarios"])
async def remover_usuario(id: int):
    repo.remover_usuario(id)
    return Response(status_code=204)


@app.get("/usuarios/{id}/playlists", response_model=list[PlaylistJson], tags=["usuarios"])
async def playlists_do_usuario(id: int):
    """Consulta do enunciado: playlists de um determinado usuário."""
    return repo.listar_playlists_do_usuario(id)


@app.post("/usuarios/{id}/playlists", response_model=PlaylistJson, status_code=201, tags=["usuarios"])
async def criar_playlist(id: int, dados: PlaylistDados, response: Response):
    p = repo.criar_playlist(id, dados.nome, dados.musica_ids)
    criado(response, f"/playlists/{p.id}")
    return p


# ----------------------------------------------------------------- músicas
@app.get("/musicas", response_model=list[MusicaJson], tags=["musicas"])
async def listar_musicas():
    return repo.listar_musicas()


@app.post("/musicas", response_model=MusicaJson, status_code=201, tags=["musicas"])
async def criar_musica(dados: MusicaDados, response: Response):
    m = repo.criar_musica(dados.nome, dados.artista)
    criado(response, f"/musicas/{m.id}")
    return m


@app.get("/musicas/{id}", response_model=MusicaJson, tags=["musicas"])
async def obter_musica(id: int):
    return repo.obter_musica(id)


@app.put("/musicas/{id}", response_model=MusicaJson, tags=["musicas"])
async def atualizar_musica(id: int, dados: MusicaDados):
    return repo.atualizar_musica(id, dados.nome, dados.artista)


@app.delete("/musicas/{id}", status_code=204, tags=["musicas"])
async def remover_musica(id: int):
    repo.remover_musica(id)
    return Response(status_code=204)


@app.get("/musicas/{id}/playlists", response_model=list[PlaylistJson], tags=["musicas"])
async def playlists_com_musica(id: int):
    """Consulta do enunciado: playlists que contêm uma determinada música."""
    return repo.listar_playlists_com_musica(id)


# --------------------------------------------------------------- playlists
@app.get("/playlists/{id}", response_model=PlaylistJson, tags=["playlists"])
async def obter_playlist(id: int):
    return repo.obter_playlist(id)


@app.put("/playlists/{id}", response_model=PlaylistJson, tags=["playlists"])
async def atualizar_playlist(id: int, dados: PlaylistDados):
    return repo.atualizar_playlist(id, dados.nome, dados.musica_ids)


@app.delete("/playlists/{id}", status_code=204, tags=["playlists"])
async def remover_playlist(id: int):
    repo.remover_playlist(id)
    return Response(status_code=204)


@app.get("/playlists/{id}/musicas", response_model=list[MusicaJson], tags=["playlists"])
async def musicas_da_playlist(id: int):
    """Consulta do enunciado: músicas de uma determinada playlist."""
    return repo.listar_musicas_da_playlist(id)


if __name__ == "__main__":
    porta = int(os.environ.get("PORTA", "9001"))
    print(f"Servidor REST (Python / FastAPI) ouvindo em http://localhost:{porta}  (docs: /docs)")
    uvicorn.run(app, host="0.0.0.0", port=porta, log_level="warning", access_log=False)

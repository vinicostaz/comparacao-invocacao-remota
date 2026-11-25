"""Serviço GraphQL (Ariadne + Uvicorn). Porta 9002, endpoint único POST /graphql.

Abordagem "schema-first": o schema é o MESMO arquivo contratos/schema.graphqls
usado pelo servidor Java. Aqui só registramos os resolvers de cada campo.
Interface interativa (GraphiQL): abra http://localhost:9002/graphql no navegador.
Executar: python servico_graphql/servidor.py   (dentro da pasta python/)
"""
import os
import sys
from pathlib import Path

RAIZ_PYTHON = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ_PYTHON))  # permite importar "comum"

import uvicorn
from ariadne import MutationType, ObjectType, QueryType, load_schema_from_path, make_executable_schema
from ariadne.asgi import GraphQL
from ariadne.asgi.handlers import GraphQLHTTPHandler
from graphql import GraphQLError
from starlette.responses import JSONResponse

from comum.repositorio import NaoEncontrado, RepositorioStreaming, RequisicaoInvalida

SCHEMA = RAIZ_PYTHON.parent / "contratos" / "schema.graphqls"

repo = RepositorioStreaming.com_dados_iniciais()

query = QueryType()        # equivale ao GET do REST
mutation = MutationType()  # equivale a POST / PUT / DELETE
usuario_tipo = ObjectType("Usuario")
musica_tipo = ObjectType("Musica")
playlist_tipo = ObjectType("Playlist")


def erro(e: Exception) -> GraphQLError:
    """Mesma classificação usada pelo Spring for GraphQL (extensions.classification)."""
    classificacao = "NOT_FOUND" if isinstance(e, NaoEncontrado) else "BAD_REQUEST"
    return GraphQLError(str(e), extensions={"classification": classificacao})


def executar(operacao, *args):
    try:
        return operacao(*args)
    except (NaoEncontrado, RequisicaoInvalida) as e:
        raise erro(e) from e


def ou_nulo(operacao, *args):
    """Em GraphQL, buscar um item inexistente devolve null (o campo é anulável no schema)."""
    try:
        return operacao(*args)
    except NaoEncontrado:
        return None


def ids(valores) -> list[int]:
    """IDs chegam como string (tipo ID do GraphQL)."""
    try:
        return [int(v) for v in valores]
    except (TypeError, ValueError):
        raise GraphQLError("ID de música inválido", extensions={"classification": "BAD_REQUEST"})


# =================================================================== Query
@query.field("usuarios")
def resolve_usuarios(*_):
    return repo.listar_usuarios()


@query.field("usuario")
def resolve_usuario(*_, id):
    return ou_nulo(repo.obter_usuario, int(id))


@query.field("musicas")
def resolve_musicas(*_):
    return repo.listar_musicas()


@query.field("musica")
def resolve_musica(*_, id):
    return ou_nulo(repo.obter_musica, int(id))


@query.field("playlist")
def resolve_playlist(*_, id):
    return ou_nulo(repo.obter_playlist, int(id))


@query.field("playlistsDoUsuario")
def resolve_playlists_do_usuario(*_, usuarioId):
    return executar(repo.listar_playlists_do_usuario, int(usuarioId))


@query.field("musicasDaPlaylist")
def resolve_musicas_da_playlist(*_, playlistId):
    return executar(repo.listar_musicas_da_playlist, int(playlistId))


@query.field("playlistsComMusica")
def resolve_playlists_com_musica(*_, musicaId):
    return executar(repo.listar_playlists_com_musica, int(musicaId))


# ================================================================ Mutation
@mutation.field("criarUsuario")
def resolve_criar_usuario(*_, input):
    return executar(repo.criar_usuario, input["nome"], input["idade"])


@mutation.field("atualizarUsuario")
def resolve_atualizar_usuario(*_, id, input):
    return executar(repo.atualizar_usuario, int(id), input["nome"], input["idade"])


@mutation.field("removerUsuario")
def resolve_remover_usuario(*_, id):
    executar(repo.remover_usuario, int(id))
    return True


@mutation.field("criarMusica")
def resolve_criar_musica(*_, input):
    return executar(repo.criar_musica, input["nome"], input["artista"])


@mutation.field("atualizarMusica")
def resolve_atualizar_musica(*_, id, input):
    return executar(repo.atualizar_musica, int(id), input["nome"], input["artista"])


@mutation.field("removerMusica")
def resolve_remover_musica(*_, id):
    executar(repo.remover_musica, int(id))
    return True


@mutation.field("criarPlaylist")
def resolve_criar_playlist(*_, usuarioId, input):
    return executar(repo.criar_playlist, int(usuarioId), input["nome"], ids(input["musicaIds"]))


@mutation.field("atualizarPlaylist")
def resolve_atualizar_playlist(*_, id, input):
    return executar(repo.atualizar_playlist, int(id), input["nome"], ids(input["musicaIds"]))


@mutation.field("removerPlaylist")
def resolve_remover_playlist(*_, id):
    executar(repo.remover_playlist, int(id))
    return True


# ============================================ campos de relacionamento
# Só são executados se o cliente pedir esses campos na consulta.
@usuario_tipo.field("playlists")
def resolve_playlists_de_usuario(usuario, *_):
    return repo.listar_playlists_do_usuario(usuario.id)


@musica_tipo.field("playlists")
def resolve_playlists_de_musica(musica, *_):
    return repo.listar_playlists_com_musica(musica.id)


@playlist_tipo.field("usuario")
def resolve_dono_da_playlist(playlist, *_):
    return repo.obter_usuario(playlist.usuario_id)


@playlist_tipo.field("musicas")
def resolve_musicas_de_playlist(playlist, *_):
    return repo.listar_musicas_da_playlist(playlist.id)


class RespostaSempre200(GraphQLHTTPHandler):
    """Erros vão no array "errors" com HTTP 200, como faz o Spring for GraphQL.
    (Por padrão o Ariadne responde 400 quando "data" vem nulo.)"""

    async def create_json_response(self, request, result, success):
        return JSONResponse(result)


schema = make_executable_schema(
    load_schema_from_path(str(SCHEMA)), query, mutation, usuario_tipo, musica_tipo, playlist_tipo
)
app = GraphQL(schema, debug=False, http_handler=RespostaSempre200())

if __name__ == "__main__":
    porta = int(os.environ.get("PORTA", "9002"))
    print(f"Servidor GraphQL (Python / Ariadne) ouvindo em http://localhost:{porta}/graphql")
    uvicorn.run(app, host="0.0.0.0", port=porta, log_level="warning", access_log=False)

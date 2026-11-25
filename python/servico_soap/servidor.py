"""Serviço SOAP (Spyne + Waitress). Porta 9003.

Estilo document/literal wrapped, abordagem "code-first": o WSDL é gerado a partir
das classes abaixo. WSDL: http://localhost:9003/soap/streaming?wsdl

Os nomes das operações, dos parâmetros e o namespace são os mesmos do servidor
Java (JAX-WS), então o mesmo envelope SOAP funciona nos dois servidores.

Mapeamento CRUD -> operação SOAP (tudo trafega via HTTP POST):
  POST -> criar*   GET -> listar* / obter*   PUT -> atualizar*   DELETE -> remover*

Executar: python servico_soap/servidor.py   (dentro da pasta python/)
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # permite importar "comum"
sys.path.insert(0, str(Path(__file__).resolve().parent))

import compat_spyne  # noqa: F401  (precisa vir antes do import do spyne)

from spyne import Application, ComplexModel, Integer, Long, ServiceBase, Unicode, rpc
from spyne.model.fault import Fault
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from waitress import serve

from comum.repositorio import NaoEncontrado, RepositorioStreaming, RequisicaoInvalida

NS = "http://streaming.exemplo.com/soap"
CAMINHO = "/soap/streaming"

repo = RepositorioStreaming.com_dados_iniciais()


# --------------------------------------------- tipos XML (viram XSD no WSDL)
class Usuario(ComplexModel):
    __namespace__ = NS
    _type_info = [("id", Long), ("nome", Unicode), ("idade", Integer)]


class Musica(ComplexModel):
    __namespace__ = NS
    _type_info = [("id", Long), ("nome", Unicode), ("artista", Unicode)]


class Playlist(ComplexModel):
    __namespace__ = NS
    _type_info = [
        ("id", Long),
        ("nome", Unicode),
        ("usuarioId", Long),
        ("musicaIds", Long(max_occurs="unbounded")),
    ]


# listas: elementos repetidos (<usuario>...</usuario><usuario>...</usuario>), como no JAX-WS
Usuarios = Usuario.customize(max_occurs="unbounded")
Musicas = Musica.customize(max_occurs="unbounded")
Playlists = Playlist.customize(max_occurs="unbounded")
ListaDeIds = Long(max_occurs="unbounded")


def usuario_xml(u):
    return Usuario(id=u.id, nome=u.nome, idade=u.idade)


def musica_xml(m):
    return Musica(id=m.id, nome=m.nome, artista=m.artista)


def playlist_xml(p):
    return Playlist(id=p.id, nome=p.nome, usuarioId=p.usuario_id, musicaIds=list(p.musica_ids))


def executar(operacao, *args):
    """Em SOAP, erros viram um <soap:Fault> com faultcode e faultstring."""
    try:
        return operacao(*args)
    except NaoEncontrado as e:
        raise Fault(faultcode="Client.NaoEncontrado", faultstring=str(e))
    except RequisicaoInvalida as e:
        raise Fault(faultcode="Client.RequisicaoInvalida", faultstring=str(e))


class StreamingService(ServiceBase):

    # ------------------------------------------------------------ usuários
    @rpc(Unicode, Integer, _returns=Usuario, _out_variable_name="usuario")
    def criarUsuario(ctx, nome, idade):
        return usuario_xml(executar(repo.criar_usuario, nome, idade))

    @rpc(_returns=Usuarios, _out_variable_name="usuario")
    def listarUsuarios(ctx):
        return [usuario_xml(u) for u in repo.listar_usuarios()]

    @rpc(Long, _returns=Usuario, _out_variable_name="usuario")
    def obterUsuario(ctx, id):
        return usuario_xml(executar(repo.obter_usuario, id))

    @rpc(Long, Unicode, Integer, _returns=Usuario, _out_variable_name="usuario")
    def atualizarUsuario(ctx, id, nome, idade):
        return usuario_xml(executar(repo.atualizar_usuario, id, nome, idade))

    @rpc(Long)
    def removerUsuario(ctx, id):
        executar(repo.remover_usuario, id)

    # ------------------------------------------------------------- músicas
    @rpc(Unicode, Unicode, _returns=Musica, _out_variable_name="musica")
    def criarMusica(ctx, nome, artista):
        return musica_xml(executar(repo.criar_musica, nome, artista))

    @rpc(_returns=Musicas, _out_variable_name="musica")
    def listarMusicas(ctx):
        return [musica_xml(m) for m in repo.listar_musicas()]

    @rpc(Long, _returns=Musica, _out_variable_name="musica")
    def obterMusica(ctx, id):
        return musica_xml(executar(repo.obter_musica, id))

    @rpc(Long, Unicode, Unicode, _returns=Musica, _out_variable_name="musica")
    def atualizarMusica(ctx, id, nome, artista):
        return musica_xml(executar(repo.atualizar_musica, id, nome, artista))

    @rpc(Long)
    def removerMusica(ctx, id):
        executar(repo.remover_musica, id)

    # ----------------------------------------------------------- playlists
    @rpc(Long, Unicode, ListaDeIds, _returns=Playlist, _out_variable_name="playlist")
    def criarPlaylist(ctx, usuarioId, nome, musicaIds):
        return playlist_xml(executar(repo.criar_playlist, usuarioId, nome, musicaIds))

    @rpc(Long, _returns=Playlists, _out_variable_name="playlist")
    def listarPlaylistsDoUsuario(ctx, usuarioId):
        return [playlist_xml(p) for p in executar(repo.listar_playlists_do_usuario, usuarioId)]

    @rpc(Long, _returns=Playlist, _out_variable_name="playlist")
    def obterPlaylist(ctx, id):
        return playlist_xml(executar(repo.obter_playlist, id))

    @rpc(Long, Unicode, ListaDeIds, _returns=Playlist, _out_variable_name="playlist")
    def atualizarPlaylist(ctx, id, nome, musicaIds):
        return playlist_xml(executar(repo.atualizar_playlist, id, nome, musicaIds))

    @rpc(Long)
    def removerPlaylist(ctx, id):
        executar(repo.remover_playlist, id)

    # ----------------------------------------------------------- consultas
    @rpc(Long, _returns=Musicas, _out_variable_name="musica")
    def listarMusicasDaPlaylist(ctx, playlistId):
        return [musica_xml(m) for m in executar(repo.listar_musicas_da_playlist, playlistId)]

    @rpc(Long, _returns=Playlists, _out_variable_name="playlist")
    def listarPlaylistsComMusica(ctx, musicaId):
        return [playlist_xml(p) for p in executar(repo.listar_playlists_com_musica, musicaId)]


aplicacao = Application(
    [StreamingService],
    tns=NS,
    name="StreamingService",
    in_protocol=Soap11(),
    out_protocol=Soap11(),
)
_wsgi_spyne = WsgiApplication(aplicacao)


def app(environ, start_response):
    """Atende só em /soap/streaming (mesmo caminho do servidor Java)."""
    if environ.get("PATH_INFO", "").rstrip("/") != CAMINHO:
        start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
        return [f"Use {CAMINHO} (WSDL em {CAMINHO}?wsdl)".encode()]
    return _wsgi_spyne(environ, start_response)


if __name__ == "__main__":
    import logging
    logging.getLogger("spyne").setLevel(logging.ERROR)
    porta = int(os.environ.get("PORTA", "9003"))
    print(f"Servidor SOAP (Python / Spyne) ouvindo em http://localhost:{porta}{CAMINHO}  (WSDL: ?wsdl)")
    serve(app, host="0.0.0.0", port=porta, threads=8, connection_limit=1000, backlog=2048, _quiet=True)

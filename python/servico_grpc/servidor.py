"""Serviço gRPC (grpcio). Porta 9004.

Contrato: contratos/streaming.proto (o MESMO usado pelo servidor Java).
As classes de mensagem e a classe base do serviço são GERADAS pelo protoc
(ver codigo_gerado.py); aqui só implementamos os métodos do serviço.
Executar: python servico_grpc/servidor.py   (dentro da pasta python/)
"""
import os
import sys
from concurrent import futures
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # permite importar "comum"
sys.path.insert(0, str(Path(__file__).resolve().parent))

import grpc
from google.protobuf import empty_pb2

from comum.repositorio import NaoEncontrado, RepositorioStreaming, RequisicaoInvalida
from codigo_gerado import carregar

pb, pb_grpc = carregar()  # streaming_pb2, streaming_pb2_grpc

repo = RepositorioStreaming.com_dados_iniciais()
VAZIO = empty_pb2.Empty()


def executar(contexto, operacao, *args):
    """Em gRPC, erros viram um código de status (NOT_FOUND, INVALID_ARGUMENT...)."""
    try:
        return operacao(*args)
    except NaoEncontrado as e:
        contexto.abort(grpc.StatusCode.NOT_FOUND, str(e))
    except RequisicaoInvalida as e:
        contexto.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))


def usuario_pb(u):
    return pb.Usuario(id=u.id, nome=u.nome, idade=u.idade)


def musica_pb(m):
    return pb.Musica(id=m.id, nome=m.nome, artista=m.artista)


def playlist_pb(p):
    return pb.Playlist(id=p.id, nome=p.nome, usuario_id=p.usuario_id, musica_ids=p.musica_ids)


class StreamingServicer(pb_grpc.StreamingServiceServicer):

    # ------------------------------------------------------------ usuários
    def CriarUsuario(self, req, ctx):
        return usuario_pb(executar(ctx, repo.criar_usuario, req.nome, req.idade))

    def ListarUsuarios(self, req, ctx):
        return pb.ListaUsuarios(usuarios=[usuario_pb(u) for u in repo.listar_usuarios()])

    def ObterUsuario(self, req, ctx):
        return usuario_pb(executar(ctx, repo.obter_usuario, req.id))

    def AtualizarUsuario(self, req, ctx):
        return usuario_pb(executar(ctx, repo.atualizar_usuario, req.id, req.nome, req.idade))

    def RemoverUsuario(self, req, ctx):
        executar(ctx, repo.remover_usuario, req.id)
        return VAZIO

    # ------------------------------------------------------------- músicas
    def CriarMusica(self, req, ctx):
        return musica_pb(executar(ctx, repo.criar_musica, req.nome, req.artista))

    def ListarMusicas(self, req, ctx):
        return pb.ListaMusicas(musicas=[musica_pb(m) for m in repo.listar_musicas()])

    def ObterMusica(self, req, ctx):
        return musica_pb(executar(ctx, repo.obter_musica, req.id))

    def AtualizarMusica(self, req, ctx):
        return musica_pb(executar(ctx, repo.atualizar_musica, req.id, req.nome, req.artista))

    def RemoverMusica(self, req, ctx):
        executar(ctx, repo.remover_musica, req.id)
        return VAZIO

    # ----------------------------------------------------------- playlists
    def CriarPlaylist(self, req, ctx):
        return playlist_pb(executar(ctx, repo.criar_playlist, req.usuario_id, req.nome, list(req.musica_ids)))

    def ListarPlaylistsDoUsuario(self, req, ctx):
        playlists = executar(ctx, repo.listar_playlists_do_usuario, req.id)
        return pb.ListaPlaylists(playlists=[playlist_pb(p) for p in playlists])

    def ObterPlaylist(self, req, ctx):
        return playlist_pb(executar(ctx, repo.obter_playlist, req.id))

    def AtualizarPlaylist(self, req, ctx):
        return playlist_pb(executar(ctx, repo.atualizar_playlist, req.id, req.nome, list(req.musica_ids)))

    def RemoverPlaylist(self, req, ctx):
        executar(ctx, repo.remover_playlist, req.id)
        return VAZIO

    # ----------------------------------------------------------- consultas
    def ListarMusicasDaPlaylist(self, req, ctx):
        musicas = executar(ctx, repo.listar_musicas_da_playlist, req.id)
        return pb.ListaMusicas(musicas=[musica_pb(m) for m in musicas])

    def ListarPlaylistsComMusica(self, req, ctx):
        playlists = executar(ctx, repo.listar_playlists_com_musica, req.id)
        return pb.ListaPlaylists(playlists=[playlist_pb(p) for p in playlists])


def main():
    porta = int(os.environ.get("PORTA", "9004"))
    servidor = grpc.server(futures.ThreadPoolExecutor(max_workers=16))
    pb_grpc.add_StreamingServiceServicer_to_server(StreamingServicer(), servidor)
    servidor.add_insecure_port(f"0.0.0.0:{porta}")
    servidor.start()
    print(f"Servidor gRPC (Python / grpcio) ouvindo em localhost:{porta}")
    servidor.wait_for_termination()


if __name__ == "__main__":
    main()

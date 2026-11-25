package br.streaming.grpc;

import br.streaming.comum.NaoEncontradoException;
import br.streaming.comum.RepositorioStreaming;
import br.streaming.comum.RequisicaoInvalidaException;
import br.streaming.grpc.proto.AtualizarMusicaRequest;
import br.streaming.grpc.proto.AtualizarPlaylistRequest;
import br.streaming.grpc.proto.AtualizarUsuarioRequest;
import br.streaming.grpc.proto.CriarMusicaRequest;
import br.streaming.grpc.proto.CriarPlaylistRequest;
import br.streaming.grpc.proto.CriarUsuarioRequest;
import br.streaming.grpc.proto.IdRequest;
import br.streaming.grpc.proto.ListaMusicas;
import br.streaming.grpc.proto.ListaPlaylists;
import br.streaming.grpc.proto.ListaUsuarios;
import br.streaming.grpc.proto.Musica;
import br.streaming.grpc.proto.Playlist;
import br.streaming.grpc.proto.StreamingServiceGrpc;
import br.streaming.grpc.proto.Usuario;
import com.google.protobuf.Empty;
import io.grpc.Status;
import io.grpc.stub.StreamObserver;

import java.util.List;
import java.util.function.Supplier;

/**
 * Implementação do serviço definido em contratos/streaming.proto.
 * As classes Usuario, Musica, Playlist, *Request e StreamingServiceGrpc são GERADAS
 * pelo protoc (pacote br.streaming.grpc.proto). As classes de domínio do módulo comum
 * têm os mesmos nomes, por isso aparecem com o nome completo (br.streaming.comum.modelo.*).
 */
public class StreamingGrpcService extends StreamingServiceGrpc.StreamingServiceImplBase {

    private static final Empty VAZIO = Empty.getDefaultInstance();

    private final RepositorioStreaming repo = RepositorioStreaming.comDadosIniciais();

    // ================================================================ usuários

    @Override
    public void criarUsuario(CriarUsuarioRequest req, StreamObserver<Usuario> resp) {
        responder(resp, () -> usuarioProto(repo.criarUsuario(req.getNome(), req.getIdade())));
    }

    @Override
    public void listarUsuarios(Empty req, StreamObserver<ListaUsuarios> resp) {
        responder(resp, () -> ListaUsuarios.newBuilder()
                .addAllUsuarios(repo.listarUsuarios().stream().map(StreamingGrpcService::usuarioProto).toList())
                .build());
    }

    @Override
    public void obterUsuario(IdRequest req, StreamObserver<Usuario> resp) {
        responder(resp, () -> usuarioProto(repo.obterUsuario(req.getId())));
    }

    @Override
    public void atualizarUsuario(AtualizarUsuarioRequest req, StreamObserver<Usuario> resp) {
        responder(resp, () -> usuarioProto(repo.atualizarUsuario(req.getId(), req.getNome(), req.getIdade())));
    }

    @Override
    public void removerUsuario(IdRequest req, StreamObserver<Empty> resp) {
        responder(resp, () -> {
            repo.removerUsuario(req.getId());
            return VAZIO;
        });
    }

    // ================================================================= músicas

    @Override
    public void criarMusica(CriarMusicaRequest req, StreamObserver<Musica> resp) {
        responder(resp, () -> musicaProto(repo.criarMusica(req.getNome(), req.getArtista())));
    }

    @Override
    public void listarMusicas(Empty req, StreamObserver<ListaMusicas> resp) {
        responder(resp, () -> listaMusicas(repo.listarMusicas()));
    }

    @Override
    public void obterMusica(IdRequest req, StreamObserver<Musica> resp) {
        responder(resp, () -> musicaProto(repo.obterMusica(req.getId())));
    }

    @Override
    public void atualizarMusica(AtualizarMusicaRequest req, StreamObserver<Musica> resp) {
        responder(resp, () -> musicaProto(repo.atualizarMusica(req.getId(), req.getNome(), req.getArtista())));
    }

    @Override
    public void removerMusica(IdRequest req, StreamObserver<Empty> resp) {
        responder(resp, () -> {
            repo.removerMusica(req.getId());
            return VAZIO;
        });
    }

    // =============================================================== playlists

    @Override
    public void criarPlaylist(CriarPlaylistRequest req, StreamObserver<Playlist> resp) {
        responder(resp, () -> playlistProto(
                repo.criarPlaylist(req.getUsuarioId(), req.getNome(), req.getMusicaIdsList())));
    }

    @Override
    public void listarPlaylistsDoUsuario(IdRequest req, StreamObserver<ListaPlaylists> resp) {
        responder(resp, () -> listaPlaylists(repo.listarPlaylistsDoUsuario(req.getId())));
    }

    @Override
    public void obterPlaylist(IdRequest req, StreamObserver<Playlist> resp) {
        responder(resp, () -> playlistProto(repo.obterPlaylist(req.getId())));
    }

    @Override
    public void atualizarPlaylist(AtualizarPlaylistRequest req, StreamObserver<Playlist> resp) {
        responder(resp, () -> playlistProto(
                repo.atualizarPlaylist(req.getId(), req.getNome(), req.getMusicaIdsList())));
    }

    @Override
    public void removerPlaylist(IdRequest req, StreamObserver<Empty> resp) {
        responder(resp, () -> {
            repo.removerPlaylist(req.getId());
            return VAZIO;
        });
    }

    // =============================================================== consultas

    @Override
    public void listarMusicasDaPlaylist(IdRequest req, StreamObserver<ListaMusicas> resp) {
        responder(resp, () -> listaMusicas(repo.listarMusicasDaPlaylist(req.getId())));
    }

    @Override
    public void listarPlaylistsComMusica(IdRequest req, StreamObserver<ListaPlaylists> resp) {
        responder(resp, () -> listaPlaylists(repo.listarPlaylistsComMusica(req.getId())));
    }

    // ============================================================== auxiliares

    /** Envia a resposta ou, em caso de erro, um código de status gRPC. */
    private static <T> void responder(StreamObserver<T> resp, Supplier<T> operacao) {
        T resultado;
        try {
            resultado = operacao.get();
        } catch (NaoEncontradoException e) {
            resp.onError(Status.NOT_FOUND.withDescription(e.getMessage()).asRuntimeException());
            return;
        } catch (RequisicaoInvalidaException e) {
            resp.onError(Status.INVALID_ARGUMENT.withDescription(e.getMessage()).asRuntimeException());
            return;
        }
        resp.onNext(resultado);
        resp.onCompleted();
    }

    private static Usuario usuarioProto(br.streaming.comum.modelo.Usuario u) {
        return Usuario.newBuilder()
                .setId(u.getId())
                .setNome(u.getNome())
                .setIdade(u.getIdade())
                .build();
    }

    private static Musica musicaProto(br.streaming.comum.modelo.Musica m) {
        return Musica.newBuilder()
                .setId(m.getId())
                .setNome(m.getNome())
                .setArtista(m.getArtista())
                .build();
    }

    private static Playlist playlistProto(br.streaming.comum.modelo.Playlist p) {
        return Playlist.newBuilder()
                .setId(p.getId())
                .setNome(p.getNome())
                .setUsuarioId(p.getUsuarioId())
                .addAllMusicaIds(p.getMusicaIds())
                .build();
    }

    private static ListaMusicas listaMusicas(List<br.streaming.comum.modelo.Musica> musicas) {
        return ListaMusicas.newBuilder()
                .addAllMusicas(musicas.stream().map(StreamingGrpcService::musicaProto).toList())
                .build();
    }

    private static ListaPlaylists listaPlaylists(List<br.streaming.comum.modelo.Playlist> playlists) {
        return ListaPlaylists.newBuilder()
                .addAllPlaylists(playlists.stream().map(StreamingGrpcService::playlistProto).toList())
                .build();
    }
}

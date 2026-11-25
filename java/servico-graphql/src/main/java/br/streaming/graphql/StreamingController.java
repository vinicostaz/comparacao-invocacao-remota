package br.streaming.graphql;

import br.streaming.comum.NaoEncontradoException;
import br.streaming.comum.RepositorioStreaming;
import br.streaming.comum.RequisicaoInvalidaException;
import br.streaming.comum.modelo.Musica;
import br.streaming.comum.modelo.Playlist;
import br.streaming.comum.modelo.Usuario;
import org.springframework.graphql.data.method.annotation.Argument;
import org.springframework.graphql.data.method.annotation.MutationMapping;
import org.springframework.graphql.data.method.annotation.QueryMapping;
import org.springframework.graphql.data.method.annotation.SchemaMapping;
import org.springframework.stereotype.Controller;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Supplier;

/**
 * Resolvers do schema GraphQL. Cada método anotado resolve um campo do schema:
 *   @QueryMapping    -> campo de "type Query"     (equivale ao GET do REST)
 *   @MutationMapping -> campo de "type Mutation"  (equivale a POST / PUT / DELETE)
 *   @SchemaMapping   -> campo de relacionamento (Usuario.playlists, Playlist.musicas...),
 *                       só executado se o cliente pedir esse campo na consulta.
 */
@Controller
public class StreamingController {

    /** Tipos "input" do schema (UsuarioInput, MusicaInput, PlaylistInput). */
    public record UsuarioInput(String nome, int idade) {
    }

    public record MusicaInput(String nome, String artista) {
    }

    /** IDs chegam como String (tipo ID do GraphQL). */
    public record PlaylistInput(String nome, List<String> musicaIds) {
    }

    private final RepositorioStreaming repo;

    public StreamingController(RepositorioStreaming repo) {
        this.repo = repo;
    }

    // ================================================================ Query

    @QueryMapping
    public List<Usuario> usuarios() {
        return repo.listarUsuarios();
    }

    @QueryMapping
    public Usuario usuario(@Argument Long id) {
        return ouNulo(() -> repo.obterUsuario(id));
    }

    @QueryMapping
    public List<Musica> musicas() {
        return repo.listarMusicas();
    }

    @QueryMapping
    public Musica musica(@Argument Long id) {
        return ouNulo(() -> repo.obterMusica(id));
    }

    @QueryMapping
    public Playlist playlist(@Argument Long id) {
        return ouNulo(() -> repo.obterPlaylist(id));
    }

    @QueryMapping
    public List<Playlist> playlistsDoUsuario(@Argument Long usuarioId) {
        return repo.listarPlaylistsDoUsuario(usuarioId);
    }

    @QueryMapping
    public List<Musica> musicasDaPlaylist(@Argument Long playlistId) {
        return repo.listarMusicasDaPlaylist(playlistId);
    }

    @QueryMapping
    public List<Playlist> playlistsComMusica(@Argument Long musicaId) {
        return repo.listarPlaylistsComMusica(musicaId);
    }

    // ============================================================= Mutation

    @MutationMapping
    public Usuario criarUsuario(@Argument UsuarioInput input) {
        return repo.criarUsuario(input.nome(), input.idade());
    }

    @MutationMapping
    public Usuario atualizarUsuario(@Argument Long id, @Argument UsuarioInput input) {
        return repo.atualizarUsuario(id, input.nome(), input.idade());
    }

    @MutationMapping
    public boolean removerUsuario(@Argument Long id) {
        repo.removerUsuario(id);
        return true;
    }

    @MutationMapping
    public Musica criarMusica(@Argument MusicaInput input) {
        return repo.criarMusica(input.nome(), input.artista());
    }

    @MutationMapping
    public Musica atualizarMusica(@Argument Long id, @Argument MusicaInput input) {
        return repo.atualizarMusica(id, input.nome(), input.artista());
    }

    @MutationMapping
    public boolean removerMusica(@Argument Long id) {
        repo.removerMusica(id);
        return true;
    }

    @MutationMapping
    public Playlist criarPlaylist(@Argument Long usuarioId, @Argument PlaylistInput input) {
        return repo.criarPlaylist(usuarioId, input.nome(), paraLongs(input.musicaIds()));
    }

    @MutationMapping
    public Playlist atualizarPlaylist(@Argument Long id, @Argument PlaylistInput input) {
        return repo.atualizarPlaylist(id, input.nome(), paraLongs(input.musicaIds()));
    }

    @MutationMapping
    public boolean removerPlaylist(@Argument Long id) {
        repo.removerPlaylist(id);
        return true;
    }

    // ========================================== campos de relacionamento

    @SchemaMapping(typeName = "Usuario", field = "playlists")
    public List<Playlist> playlistsDeUsuario(Usuario usuario) {
        return repo.listarPlaylistsDoUsuario(usuario.getId());
    }

    @SchemaMapping(typeName = "Musica", field = "playlists")
    public List<Playlist> playlistsDeMusica(Musica musica) {
        return repo.listarPlaylistsComMusica(musica.getId());
    }

    @SchemaMapping(typeName = "Playlist", field = "usuario")
    public Usuario donoDaPlaylist(Playlist playlist) {
        return repo.obterUsuario(playlist.getUsuarioId());
    }

    @SchemaMapping(typeName = "Playlist", field = "musicas")
    public List<Musica> musicasDePlaylist(Playlist playlist) {
        return repo.listarMusicasDaPlaylist(playlist.getId());
    }

    // ============================================================ auxiliares

    /** Em GraphQL, buscar um item inexistente devolve null (o campo é anulável no schema). */
    private static <T> T ouNulo(Supplier<T> busca) {
        try {
            return busca.get();
        } catch (NaoEncontradoException e) {
            return null;
        }
    }

    private static List<Long> paraLongs(List<String> ids) {
        List<Long> resultado = new ArrayList<>();
        if (ids != null) {
            for (String id : ids) {
                try {
                    resultado.add(Long.valueOf(id));
                } catch (NumberFormatException e) {
                    throw new RequisicaoInvalidaException("ID de música inválido: " + id);
                }
            }
        }
        return resultado;
    }
}

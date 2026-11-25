package br.streaming.comum;

import br.streaming.comum.modelo.Musica;
import br.streaming.comum.modelo.Playlist;
import br.streaming.comum.modelo.Usuario;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.locks.ReentrantReadWriteLock;
import java.util.function.Supplier;

/**
 * Regras de negócio + armazenamento em memória do serviço de streaming.
 *
 * É a MESMA classe usada pelos quatro servidores Java (REST, GraphQL, SOAP e gRPC):
 * cada servidor só traduz o protocolo para chamadas a este repositório. Assim, as
 * diferenças de desempenho medidas nos testes de carga vêm da tecnologia de invocação
 * remota, e não da lógica do serviço. A versão Python (python/comum/repositorio.py)
 * implementa exatamente as mesmas regras e os mesmos dados iniciais.
 *
 * Os objetos guardados nunca são alterados depois de inseridos: uma atualização
 * substitui o objeto inteiro. Assim, quem recebe um objeto pode serializá-lo com
 * segurança enquanto outras threads escrevem no repositório.
 */
public class RepositorioStreaming {

    // Tamanho dos dados iniciais (idênticos na versão Python).
    public static final int USUARIOS_INICIAIS = 100;
    public static final int MUSICAS_INICIAIS = 200;
    public static final int PLAYLISTS_INICIAIS = 200;
    public static final int MUSICAS_POR_PLAYLIST = 10;

    private final Map<Long, Usuario> usuarios = new LinkedHashMap<>();
    private final Map<Long, Musica> musicas = new LinkedHashMap<>();
    private final Map<Long, Playlist> playlists = new LinkedHashMap<>();

    private long proximoUsuarioId = 1;
    private long proximaMusicaId = 1;
    private long proximaPlaylistId = 1;

    private final ReentrantReadWriteLock lock = new ReentrantReadWriteLock();

    /** Cria um repositório já populado com os dados usados nos testes. */
    public static RepositorioStreaming comDadosIniciais() {
        RepositorioStreaming repo = new RepositorioStreaming();
        for (int i = 1; i <= USUARIOS_INICIAIS; i++) {
            repo.criarUsuario("Usuario " + i, 18 + (i * 7) % 50);
        }
        for (int j = 1; j <= MUSICAS_INICIAIS; j++) {
            repo.criarMusica("Musica " + j, "Artista " + ((j - 1) % 25 + 1));
        }
        for (int k = 1; k <= PLAYLISTS_INICIAIS; k++) {
            List<Long> ids = new ArrayList<>();
            for (int t = 0; t < MUSICAS_POR_PLAYLIST; t++) {
                ids.add((long) ((k - 1 + t * 17) % MUSICAS_INICIAIS + 1));
            }
            repo.criarPlaylist((k - 1) % USUARIOS_INICIAIS + 1, "Playlist " + k, ids);
        }
        return repo;
    }

    // ------------------------------------------------------------------ usuários

    public Usuario criarUsuario(String nome, int idade) {
        String nomeValido = exigirTexto(nome, "nome");
        exigirIdade(idade);
        return escrever(() -> {
            Usuario u = new Usuario(proximoUsuarioId++, nomeValido, idade);
            usuarios.put(u.getId(), u);
            return u;
        });
    }

    public List<Usuario> listarUsuarios() {
        return ler(() -> new ArrayList<>(usuarios.values()));
    }

    public Usuario obterUsuario(long id) {
        return ler(() -> buscarUsuario(id));
    }

    public Usuario atualizarUsuario(long id, String nome, int idade) {
        String nomeValido = exigirTexto(nome, "nome");
        exigirIdade(idade);
        return escrever(() -> {
            buscarUsuario(id);
            Usuario u = new Usuario(id, nomeValido, idade);
            usuarios.put(id, u);
            return u;
        });
    }

    /** Remove o usuário e, por composição, todas as playlists dele. */
    public void removerUsuario(long id) {
        escrever(() -> {
            buscarUsuario(id);
            usuarios.remove(id);
            playlists.values().removeIf(p -> p.getUsuarioId() == id);
            return null;
        });
    }

    // ------------------------------------------------------------------- músicas

    public Musica criarMusica(String nome, String artista) {
        String nomeValido = exigirTexto(nome, "nome");
        String artistaValido = exigirTexto(artista, "artista");
        return escrever(() -> {
            Musica m = new Musica(proximaMusicaId++, nomeValido, artistaValido);
            musicas.put(m.getId(), m);
            return m;
        });
    }

    public List<Musica> listarMusicas() {
        return ler(() -> new ArrayList<>(musicas.values()));
    }

    public Musica obterMusica(long id) {
        return ler(() -> buscarMusica(id));
    }

    public Musica atualizarMusica(long id, String nome, String artista) {
        String nomeValido = exigirTexto(nome, "nome");
        String artistaValido = exigirTexto(artista, "artista");
        return escrever(() -> {
            buscarMusica(id);
            Musica m = new Musica(id, nomeValido, artistaValido);
            musicas.put(id, m);
            return m;
        });
    }

    /** Remove a música do catálogo e de todas as playlists que a continham. */
    public void removerMusica(long id) {
        escrever(() -> {
            buscarMusica(id);
            musicas.remove(id);
            for (Playlist p : new ArrayList<>(playlists.values())) {
                if (p.getMusicaIds().contains(id)) {
                    List<Long> restantes = new ArrayList<>(p.getMusicaIds());
                    restantes.removeIf(m -> m == id);
                    playlists.put(p.getId(), new Playlist(p.getId(), p.getNome(), p.getUsuarioId(), restantes));
                }
            }
            return null;
        });
    }

    // ----------------------------------------------------------------- playlists

    public Playlist criarPlaylist(long usuarioId, String nome, List<Long> musicaIds) {
        String nomeValido = exigirTexto(nome, "nome");
        return escrever(() -> {
            buscarUsuario(usuarioId);
            List<Long> ids = validarMusicas(musicaIds);
            Playlist p = new Playlist(proximaPlaylistId++, nomeValido, usuarioId, ids);
            playlists.put(p.getId(), p);
            return p;
        });
    }

    /** Consulta do enunciado: todas as playlists de um determinado usuário. */
    public List<Playlist> listarPlaylistsDoUsuario(long usuarioId) {
        return ler(() -> {
            buscarUsuario(usuarioId);
            List<Playlist> resultado = new ArrayList<>();
            for (Playlist p : playlists.values()) {
                if (p.getUsuarioId() == usuarioId) {
                    resultado.add(p);
                }
            }
            return resultado;
        });
    }

    public Playlist obterPlaylist(long id) {
        return ler(() -> buscarPlaylist(id));
    }

    public Playlist atualizarPlaylist(long id, String nome, List<Long> musicaIds) {
        String nomeValido = exigirTexto(nome, "nome");
        return escrever(() -> {
            Playlist atual = buscarPlaylist(id);
            List<Long> ids = validarMusicas(musicaIds);
            Playlist p = new Playlist(id, nomeValido, atual.getUsuarioId(), ids);
            playlists.put(id, p);
            return p;
        });
    }

    public void removerPlaylist(long id) {
        escrever(() -> {
            buscarPlaylist(id);
            playlists.remove(id);
            return null;
        });
    }

    // ----------------------------------------------------------------- consultas

    /** Consulta do enunciado: todas as músicas de uma determinada playlist. */
    public List<Musica> listarMusicasDaPlaylist(long playlistId) {
        return ler(() -> {
            Playlist p = buscarPlaylist(playlistId);
            List<Musica> resultado = new ArrayList<>();
            for (Long musicaId : p.getMusicaIds()) {
                Musica m = musicas.get(musicaId);
                if (m != null) {
                    resultado.add(m);
                }
            }
            return resultado;
        });
    }

    /** Consulta do enunciado: todas as playlists que contêm uma determinada música. */
    public List<Playlist> listarPlaylistsComMusica(long musicaId) {
        return ler(() -> {
            buscarMusica(musicaId);
            List<Playlist> resultado = new ArrayList<>();
            for (Playlist p : playlists.values()) {
                if (p.getMusicaIds().contains(musicaId)) {
                    resultado.add(p);
                }
            }
            return resultado;
        });
    }

    // ------------------------------------------------------------------ auxiliares

    private Usuario buscarUsuario(long id) {
        Usuario u = usuarios.get(id);
        if (u == null) {
            throw new NaoEncontradoException("Usuário " + id + " não encontrado");
        }
        return u;
    }

    private Musica buscarMusica(long id) {
        Musica m = musicas.get(id);
        if (m == null) {
            throw new NaoEncontradoException("Música " + id + " não encontrada");
        }
        return m;
    }

    private Playlist buscarPlaylist(long id) {
        Playlist p = playlists.get(id);
        if (p == null) {
            throw new NaoEncontradoException("Playlist " + id + " não encontrada");
        }
        return p;
    }

    private List<Long> validarMusicas(List<Long> musicaIds) {
        List<Long> ids = musicaIds == null ? new ArrayList<>() : new ArrayList<>(musicaIds);
        for (Long id : ids) {
            if (id == null || !musicas.containsKey(id)) {
                throw new RequisicaoInvalidaException("Música " + id + " não existe");
            }
        }
        return ids;
    }

    private static String exigirTexto(String valor, String campo) {
        if (valor == null || valor.isBlank()) {
            throw new RequisicaoInvalidaException("Campo '" + campo + "' é obrigatório");
        }
        return valor.trim();
    }

    private static void exigirIdade(int idade) {
        if (idade < 0) {
            throw new RequisicaoInvalidaException("Campo 'idade' não pode ser negativo");
        }
    }

    private <T> T ler(Supplier<T> operacao) {
        lock.readLock().lock();
        try {
            return operacao.get();
        } finally {
            lock.readLock().unlock();
        }
    }

    private <T> T escrever(Supplier<T> operacao) {
        lock.writeLock().lock();
        try {
            return operacao.get();
        } finally {
            lock.writeLock().unlock();
        }
    }
}

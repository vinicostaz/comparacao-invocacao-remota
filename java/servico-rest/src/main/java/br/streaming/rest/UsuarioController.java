package br.streaming.rest;

import br.streaming.comum.RepositorioStreaming;
import br.streaming.comum.modelo.Playlist;
import br.streaming.comum.modelo.Usuario;
import br.streaming.rest.Dtos.PlaylistDados;
import br.streaming.rest.Dtos.UsuarioDados;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.util.List;

@RestController
@RequestMapping("/usuarios")
public class UsuarioController {

    private final RepositorioStreaming repo;

    public UsuarioController(RepositorioStreaming repo) {
        this.repo = repo;
    }

    /** GET /usuarios -> lista todos os usuários */
    @GetMapping
    public List<Usuario> listar() {
        return repo.listarUsuarios();
    }

    /** POST /usuarios -> 201 Created + Location */
    @PostMapping
    public ResponseEntity<Usuario> criar(@RequestBody UsuarioDados dados) {
        Usuario u = repo.criarUsuario(dados.nome(), dados.idade());
        return ResponseEntity.created(URI.create("/usuarios/" + u.getId())).body(u);
    }

    /** GET /usuarios/{id} */
    @GetMapping("/{id}")
    public Usuario obter(@PathVariable("id") long id) {
        return repo.obterUsuario(id);
    }

    /** PUT /usuarios/{id} */
    @PutMapping("/{id}")
    public Usuario atualizar(@PathVariable("id") long id, @RequestBody UsuarioDados dados) {
        return repo.atualizarUsuario(id, dados.nome(), dados.idade());
    }

    /** DELETE /usuarios/{id} -> 204 No Content (remove também as playlists do usuário) */
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> remover(@PathVariable("id") long id) {
        repo.removerUsuario(id);
        return ResponseEntity.noContent().build();
    }

    /** GET /usuarios/{id}/playlists -> consulta "playlists de um determinado usuário" */
    @GetMapping("/{id}/playlists")
    public List<Playlist> playlists(@PathVariable("id") long id) {
        return repo.listarPlaylistsDoUsuario(id);
    }

    /** POST /usuarios/{id}/playlists -> cria uma playlist para o usuário */
    @PostMapping("/{id}/playlists")
    public ResponseEntity<Playlist> criarPlaylist(@PathVariable("id") long id, @RequestBody PlaylistDados dados) {
        Playlist p = repo.criarPlaylist(id, dados.nome(), dados.musicaIds());
        return ResponseEntity.created(URI.create("/playlists/" + p.getId())).body(p);
    }
}

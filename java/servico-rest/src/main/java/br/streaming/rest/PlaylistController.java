package br.streaming.rest;

import br.streaming.comum.RepositorioStreaming;
import br.streaming.comum.modelo.Musica;
import br.streaming.comum.modelo.Playlist;
import br.streaming.rest.Dtos.PlaylistDados;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/** Playlists são criadas dentro do usuário (POST /usuarios/{id}/playlists). */
@RestController
@RequestMapping("/playlists")
public class PlaylistController {

    private final RepositorioStreaming repo;

    public PlaylistController(RepositorioStreaming repo) {
        this.repo = repo;
    }

    /** GET /playlists/{id} */
    @GetMapping("/{id}")
    public Playlist obter(@PathVariable("id") long id) {
        return repo.obterPlaylist(id);
    }

    /** PUT /playlists/{id} -> altera nome e músicas */
    @PutMapping("/{id}")
    public Playlist atualizar(@PathVariable("id") long id, @RequestBody PlaylistDados dados) {
        return repo.atualizarPlaylist(id, dados.nome(), dados.musicaIds());
    }

    /** DELETE /playlists/{id} -> 204 No Content */
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> remover(@PathVariable("id") long id) {
        repo.removerPlaylist(id);
        return ResponseEntity.noContent().build();
    }

    /** GET /playlists/{id}/musicas -> consulta "músicas de uma determinada playlist" */
    @GetMapping("/{id}/musicas")
    public List<Musica> musicas(@PathVariable("id") long id) {
        return repo.listarMusicasDaPlaylist(id);
    }
}

package br.streaming.rest;

import br.streaming.comum.RepositorioStreaming;
import br.streaming.comum.modelo.Musica;
import br.streaming.comum.modelo.Playlist;
import br.streaming.rest.Dtos.MusicaDados;
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
@RequestMapping("/musicas")
public class MusicaController {

    private final RepositorioStreaming repo;

    public MusicaController(RepositorioStreaming repo) {
        this.repo = repo;
    }

    /** GET /musicas -> lista todas as músicas */
    @GetMapping
    public List<Musica> listar() {
        return repo.listarMusicas();
    }

    /** POST /musicas -> 201 Created + Location */
    @PostMapping
    public ResponseEntity<Musica> criar(@RequestBody MusicaDados dados) {
        Musica m = repo.criarMusica(dados.nome(), dados.artista());
        return ResponseEntity.created(URI.create("/musicas/" + m.getId())).body(m);
    }

    /** GET /musicas/{id} */
    @GetMapping("/{id}")
    public Musica obter(@PathVariable("id") long id) {
        return repo.obterMusica(id);
    }

    /** PUT /musicas/{id} */
    @PutMapping("/{id}")
    public Musica atualizar(@PathVariable("id") long id, @RequestBody MusicaDados dados) {
        return repo.atualizarMusica(id, dados.nome(), dados.artista());
    }

    /** DELETE /musicas/{id} -> 204 No Content (remove também das playlists) */
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> remover(@PathVariable("id") long id) {
        repo.removerMusica(id);
        return ResponseEntity.noContent().build();
    }

    /** GET /musicas/{id}/playlists -> consulta "playlists que contêm uma determinada música" */
    @GetMapping("/{id}/playlists")
    public List<Playlist> playlists(@PathVariable("id") long id) {
        return repo.listarPlaylistsComMusica(id);
    }
}

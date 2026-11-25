package br.streaming.comum.modelo;

import java.util.ArrayList;
import java.util.List;

/**
 * Playlist de um usuário. Guarda o id do dono e a lista ordenada de ids de músicas
 * (relacionamento N:N entre Playlist e Música).
 */
public class Playlist {

    private long id;
    private String nome;
    private long usuarioId;
    private List<Long> musicaIds = new ArrayList<>();

    public Playlist() {
    }

    public Playlist(long id, String nome, long usuarioId, List<Long> musicaIds) {
        this.id = id;
        this.nome = nome;
        this.usuarioId = usuarioId;
        this.musicaIds = new ArrayList<>(musicaIds);
    }

    public long getId() {
        return id;
    }

    public void setId(long id) {
        this.id = id;
    }

    public String getNome() {
        return nome;
    }

    public void setNome(String nome) {
        this.nome = nome;
    }

    public long getUsuarioId() {
        return usuarioId;
    }

    public void setUsuarioId(long usuarioId) {
        this.usuarioId = usuarioId;
    }

    public List<Long> getMusicaIds() {
        return musicaIds;
    }

    public void setMusicaIds(List<Long> musicaIds) {
        this.musicaIds = musicaIds;
    }
}

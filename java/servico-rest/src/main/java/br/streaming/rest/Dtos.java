package br.streaming.rest;

import java.util.List;

/** Corpos (JSON) aceitos nas requisições POST e PUT. */
public final class Dtos {

    private Dtos() {
    }

    /** {"nome": "Ana", "idade": 30} */
    public record UsuarioDados(String nome, int idade) {
    }

    /** {"nome": "Imagine", "artista": "John Lennon"} */
    public record MusicaDados(String nome, String artista) {
    }

    /** {"nome": "Favoritas", "musicaIds": [1, 2, 3]} */
    public record PlaylistDados(String nome, List<Long> musicaIds) {
    }
}

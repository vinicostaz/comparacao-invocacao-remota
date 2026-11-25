package br.streaming.comum.modelo;

/** Música mantida pelo serviço de streaming. */
public class Musica {

    private long id;
    private String nome;
    private String artista;

    public Musica() {
    }

    public Musica(long id, String nome, String artista) {
        this.id = id;
        this.nome = nome;
        this.artista = artista;
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

    public String getArtista() {
        return artista;
    }

    public void setArtista(String artista) {
        this.artista = artista;
    }
}

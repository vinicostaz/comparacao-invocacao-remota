package br.streaming.comum.modelo;

/**
 * Usuário do serviço de streaming.
 * JavaBean simples (construtor vazio + getters/setters) para que Jackson (REST),
 * Spring GraphQL e JAXB (SOAP) consigam serializá-lo sem anotações.
 */
public class Usuario {

    private long id;
    private String nome;
    private int idade;

    public Usuario() {
    }

    public Usuario(long id, String nome, int idade) {
        this.id = id;
        this.nome = nome;
        this.idade = idade;
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

    public int getIdade() {
        return idade;
    }

    public void setIdade(int idade) {
        this.idade = idade;
    }
}

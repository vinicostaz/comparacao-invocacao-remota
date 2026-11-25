package br.streaming.rest;

import br.streaming.comum.RepositorioStreaming;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

/**
 * Serviço REST (Spring Boot). Porta 8001 (ver application.properties).
 *
 * Recursos e verbos HTTP:
 *   /usuarios                 GET (listar)  POST (criar)
 *   /usuarios/{id}            GET  PUT  DELETE
 *   /usuarios/{id}/playlists  GET (playlists do usuário)  POST (criar playlist)
 *   /musicas                  GET  POST
 *   /musicas/{id}             GET  PUT  DELETE
 *   /musicas/{id}/playlists   GET (playlists que contêm a música)
 *   /playlists/{id}           GET  PUT  DELETE
 *   /playlists/{id}/musicas   GET (músicas da playlist)
 */
@SpringBootApplication
public class AplicacaoRest {

    public static void main(String[] args) {
        SpringApplication.run(AplicacaoRest.class, args);
    }

    @Bean
    public RepositorioStreaming repositorio() {
        return RepositorioStreaming.comDadosIniciais();
    }
}

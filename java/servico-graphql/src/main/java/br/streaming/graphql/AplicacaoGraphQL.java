package br.streaming.graphql;

import br.streaming.comum.RepositorioStreaming;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

/**
 * Serviço GraphQL (Spring for GraphQL). Porta 8002, endpoint único POST /graphql.
 * O schema é contratos/schema.graphqls (copiado para classpath:graphql/ pelo Maven).
 * Interface interativa (GraphiQL): http://localhost:8002/graphiql
 */
@SpringBootApplication
public class AplicacaoGraphQL {

    public static void main(String[] args) {
        SpringApplication.run(AplicacaoGraphQL.class, args);
    }

    @Bean
    public RepositorioStreaming repositorio() {
        return RepositorioStreaming.comDadosIniciais();
    }
}

package br.streaming.graphql;

import br.streaming.comum.NaoEncontradoException;
import br.streaming.comum.RequisicaoInvalidaException;
import graphql.GraphQLError;
import graphql.GraphqlErrorBuilder;
import graphql.schema.DataFetchingEnvironment;
import org.springframework.graphql.execution.DataFetcherExceptionResolverAdapter;
import org.springframework.graphql.execution.ErrorType;
import org.springframework.stereotype.Component;

/**
 * Em GraphQL a resposta HTTP é sempre 200: os erros vão no array "errors" do JSON,
 * com a classificação em "extensions.classification" (NOT_FOUND, BAD_REQUEST).
 */
@Component
public class TratadorDeErros extends DataFetcherExceptionResolverAdapter {

    @Override
    protected GraphQLError resolveToSingleError(Throwable ex, DataFetchingEnvironment env) {
        ErrorType tipo;
        if (ex instanceof NaoEncontradoException) {
            tipo = ErrorType.NOT_FOUND;
        } else if (ex instanceof RequisicaoInvalidaException) {
            tipo = ErrorType.BAD_REQUEST;
        } else {
            return null; // deixa o Spring tratar os demais erros
        }
        return GraphqlErrorBuilder.newError(env)
                .errorType(tipo)
                .message(ex.getMessage())
                .build();
    }
}

package br.streaming.comum;

/**
 * Dados de entrada inválidos. Cada tecnologia traduz para o seu próprio mecanismo de erro:
 * REST -> HTTP 400 | GraphQL -> erro BAD_REQUEST | SOAP -> Fault Client.RequisicaoInvalida | gRPC -> INVALID_ARGUMENT
 */
public class RequisicaoInvalidaException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    public RequisicaoInvalidaException(String mensagem) {
        super(mensagem);
    }
}

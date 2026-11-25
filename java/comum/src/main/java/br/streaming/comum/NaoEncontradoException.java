package br.streaming.comum;

/**
 * Recurso inexistente. Cada tecnologia traduz para o seu próprio mecanismo de erro:
 * REST -> HTTP 404 | GraphQL -> erro NOT_FOUND | SOAP -> Fault Client.NaoEncontrado | gRPC -> NOT_FOUND
 */
public class NaoEncontradoException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    public NaoEncontradoException(String mensagem) {
        super(mensagem);
    }
}

package br.streaming.soap;

import br.streaming.comum.NaoEncontradoException;
import br.streaming.comum.RepositorioStreaming;
import br.streaming.comum.RequisicaoInvalidaException;
import br.streaming.comum.modelo.Musica;
import br.streaming.comum.modelo.Playlist;
import br.streaming.comum.modelo.Usuario;
import jakarta.jws.WebMethod;
import jakarta.jws.WebParam;
import jakarta.jws.WebResult;
import jakarta.jws.WebService;
import jakarta.xml.soap.SOAPConstants;
import jakarta.xml.soap.SOAPException;
import jakarta.xml.soap.SOAPFactory;
import jakarta.xml.soap.SOAPFault;
import jakarta.xml.ws.soap.SOAPFaultException;

import javax.xml.namespace.QName;
import java.util.List;
import java.util.function.Supplier;

/**
 * Serviço SOAP (estilo document/literal wrapped), abordagem "code-first":
 * o WSDL é gerado automaticamente a partir das anotações desta classe.
 * WSDL: http://localhost:8003/soap/streaming?wsdl
 *
 * Os nomes das operações, dos parâmetros e o namespace são os mesmos do servidor
 * Python (Spyne), então o mesmo envelope SOAP funciona nos dois servidores.
 * Todos os parâmetros são qualificados com o namespace (targetNamespace = NS).
 *
 * Mapeamento CRUD -> operação SOAP (tudo trafega via HTTP POST):
 *   POST -> criar*   GET -> listar* / obter*   PUT -> atualizar*   DELETE -> remover*
 */
@WebService(serviceName = "StreamingService", portName = "StreamingPort", targetNamespace = StreamingSoapService.NS)
public class StreamingSoapService {

    public static final String NS = "http://streaming.exemplo.com/soap";

    private final RepositorioStreaming repo;

    public StreamingSoapService() {
        this.repo = RepositorioStreaming.comDadosIniciais();
    }

    // ================================================================ usuários

    @WebMethod
    @WebResult(name = "usuario", targetNamespace = NS)
    public Usuario criarUsuario(@WebParam(name = "nome", targetNamespace = NS) String nome,
                                @WebParam(name = "idade", targetNamespace = NS) int idade) {
        return executar(() -> repo.criarUsuario(nome, idade));
    }

    @WebMethod
    @WebResult(name = "usuario", targetNamespace = NS)
    public List<Usuario> listarUsuarios() {
        return executar(repo::listarUsuarios);
    }

    @WebMethod
    @WebResult(name = "usuario", targetNamespace = NS)
    public Usuario obterUsuario(@WebParam(name = "id", targetNamespace = NS) long id) {
        return executar(() -> repo.obterUsuario(id));
    }

    @WebMethod
    @WebResult(name = "usuario", targetNamespace = NS)
    public Usuario atualizarUsuario(@WebParam(name = "id", targetNamespace = NS) long id,
                                    @WebParam(name = "nome", targetNamespace = NS) String nome,
                                    @WebParam(name = "idade", targetNamespace = NS) int idade) {
        return executar(() -> repo.atualizarUsuario(id, nome, idade));
    }

    @WebMethod
    public void removerUsuario(@WebParam(name = "id", targetNamespace = NS) long id) {
        executar(() -> {
            repo.removerUsuario(id);
            return null;
        });
    }

    // ================================================================= músicas

    @WebMethod
    @WebResult(name = "musica", targetNamespace = NS)
    public Musica criarMusica(@WebParam(name = "nome", targetNamespace = NS) String nome,
                              @WebParam(name = "artista", targetNamespace = NS) String artista) {
        return executar(() -> repo.criarMusica(nome, artista));
    }

    @WebMethod
    @WebResult(name = "musica", targetNamespace = NS)
    public List<Musica> listarMusicas() {
        return executar(repo::listarMusicas);
    }

    @WebMethod
    @WebResult(name = "musica", targetNamespace = NS)
    public Musica obterMusica(@WebParam(name = "id", targetNamespace = NS) long id) {
        return executar(() -> repo.obterMusica(id));
    }

    @WebMethod
    @WebResult(name = "musica", targetNamespace = NS)
    public Musica atualizarMusica(@WebParam(name = "id", targetNamespace = NS) long id,
                                  @WebParam(name = "nome", targetNamespace = NS) String nome,
                                  @WebParam(name = "artista", targetNamespace = NS) String artista) {
        return executar(() -> repo.atualizarMusica(id, nome, artista));
    }

    @WebMethod
    public void removerMusica(@WebParam(name = "id", targetNamespace = NS) long id) {
        executar(() -> {
            repo.removerMusica(id);
            return null;
        });
    }

    // =============================================================== playlists

    @WebMethod
    @WebResult(name = "playlist", targetNamespace = NS)
    public Playlist criarPlaylist(@WebParam(name = "usuarioId", targetNamespace = NS) long usuarioId,
                                  @WebParam(name = "nome", targetNamespace = NS) String nome,
                                  @WebParam(name = "musicaIds", targetNamespace = NS) List<Long> musicaIds) {
        return executar(() -> repo.criarPlaylist(usuarioId, nome, musicaIds));
    }

    @WebMethod
    @WebResult(name = "playlist", targetNamespace = NS)
    public List<Playlist> listarPlaylistsDoUsuario(@WebParam(name = "usuarioId", targetNamespace = NS) long usuarioId) {
        return executar(() -> repo.listarPlaylistsDoUsuario(usuarioId));
    }

    @WebMethod
    @WebResult(name = "playlist", targetNamespace = NS)
    public Playlist obterPlaylist(@WebParam(name = "id", targetNamespace = NS) long id) {
        return executar(() -> repo.obterPlaylist(id));
    }

    @WebMethod
    @WebResult(name = "playlist", targetNamespace = NS)
    public Playlist atualizarPlaylist(@WebParam(name = "id", targetNamespace = NS) long id,
                                      @WebParam(name = "nome", targetNamespace = NS) String nome,
                                      @WebParam(name = "musicaIds", targetNamespace = NS) List<Long> musicaIds) {
        return executar(() -> repo.atualizarPlaylist(id, nome, musicaIds));
    }

    @WebMethod
    public void removerPlaylist(@WebParam(name = "id", targetNamespace = NS) long id) {
        executar(() -> {
            repo.removerPlaylist(id);
            return null;
        });
    }

    // =============================================================== consultas

    @WebMethod
    @WebResult(name = "musica", targetNamespace = NS)
    public List<Musica> listarMusicasDaPlaylist(@WebParam(name = "playlistId", targetNamespace = NS) long playlistId) {
        return executar(() -> repo.listarMusicasDaPlaylist(playlistId));
    }

    @WebMethod
    @WebResult(name = "playlist", targetNamespace = NS)
    public List<Playlist> listarPlaylistsComMusica(@WebParam(name = "musicaId", targetNamespace = NS) long musicaId) {
        return executar(() -> repo.listarPlaylistsComMusica(musicaId));
    }

    // ============================================================== auxiliares

    /** Em SOAP, erros viram um <soap:Fault> com faultcode e faultstring. */
    private static <T> T executar(Supplier<T> operacao) {
        try {
            return operacao.get();
        } catch (NaoEncontradoException e) {
            throw fault("Client.NaoEncontrado", e.getMessage());
        } catch (RequisicaoInvalidaException e) {
            throw fault("Client.RequisicaoInvalida", e.getMessage());
        }
    }

    private static SOAPFaultException fault(String codigo, String mensagem) {
        try {
            SOAPFault fault = SOAPFactory.newInstance()
                    .createFault(mensagem, new QName(SOAPConstants.URI_NS_SOAP_1_1_ENVELOPE, codigo));
            return new SOAPFaultException(fault);
        } catch (SOAPException e) {
            throw new IllegalStateException(e);
        }
    }
}

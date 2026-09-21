"""Rotas da conexão de WhatsApp do Credor (IMP-368, PLAN-034).

**Sem `Idempotency-Key`** nas tres escritas, e isso é decisão arquitetural
registrada — **ADR-019**, que promoveu a decisão original do PLAN-034 §3.1
depois de quatro rodadas de review reabrirem a mesma pergunta. O motivo **não é
o mesmo nas tres**, e generalizá-lo foi imprecisão pega em review:

- `POST /conexao` — a chave replayaria o QR da primeira chamada, que vive ~20s.
  Devolver um QR morto é pior que gerar outro. O que precisa ser idempotente
  aqui é o nascimento da instância, e `UNIQUE (tenant_id)` mais o lock por
  Tenant já garantem isso no caso de uso;
- `DELETE /conexao/instancia` — convergência **verificada**: apagar o que já não
  existe não produz resultado novo, e o adapter trata `record not found` do
  provedor como sucesso a partir de resposta observada;
- `DELETE /conexao` — convergência **adaptada ao contrato observado**. A resposta
  de 2026-09-04 confirmou por leitura do código do Evolution que logout repetido
  devolve sempre `400`, com mensagem dependente do timing. O adapter trata
  qualquer `400` somente nessa rota como "já desconectado", conforme ADR-019
  v1.2.0, e preserva erro para os demais status.

**Nenhuma rota aceita o nome da instância.** Ele é derivado do Tenant
(`nome_da_instancia`): a adoção casa pelo nome, e um campo digitável
transformaria erro de digitação em segunda instância — não pareada — no
provedor, enquanto o WhatsApp do operador segue ligado na primeira.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header

from emprestimo.application.autorizacao import Principal
from emprestimo.application.conexao_whatsapp import (
    ConectarWhatsApp,
    ConsultarConexaoWhatsApp,
    DesconectarWhatsApp,
    ExcluirConexaoWhatsApp,
)
from emprestimo.application.numero_avisos import NumeroAvisosService
from emprestimo.presentation.api.dependencies import (
    exigir_permissao,
    get_conectar_whatsapp,
    get_consultar_conexao_whatsapp,
    get_desconectar_whatsapp,
    get_excluir_conexao_whatsapp,
    get_numero_avisos_service,
    get_principal_atual,
)
from emprestimo.presentation.api.openapi import (
    RESPOSTA_RECURSO_NAO_ENCONTRADO,
    RESPOSTAS_PROTEGIDAS,
    combinar_respostas,
)
from emprestimo.presentation.api.whatsapp_schemas import (
    ConexaoWhatsAppResponse,
    NumeroAvisosRequest,
    NumeroAvisosResponse,
    QrCodeConexaoResponse,
)

# As QUATRO rotas declaram 404, inclusive as de leitura: uma conexao gravada
# cujo token nao decifra existe e nao consegue falar com o provedor, e o caso de
# uso a nomeia em vez de fingir que esta desconectada. Documentar so nas duas de
# escrita esconderia o desfecho justamente de quem consulta.
router = APIRouter(
    prefix="/platform/whatsapp",
    tags=["WhatsApp"],
    dependencies=[Depends(get_principal_atual)],
    responses=RESPOSTAS_PROTEGIDAS,
)


@router.get(
    "/conexao",
    response_model=ConexaoWhatsAppResponse,
    responses=combinar_respostas(RESPOSTA_RECURSO_NAO_ENCONTRADO),
)
def consultar_conexao(
    principal: Principal = Depends(exigir_permissao("whatsapp.conexao.ler")),
    caso_de_uso: ConsultarConexaoWhatsApp = Depends(get_consultar_conexao_whatsapp),
) -> ConexaoWhatsAppResponse:
    """Estado real da conexão, lido do provedor — não o último estado conhecido."""
    return ConexaoWhatsAppResponse.de(
        caso_de_uso.executar(tenant_id=principal.tenant_id, usuario_id=principal.usuario_id)
    )


@router.post(
    "/conexao",
    response_model=QrCodeConexaoResponse,
    responses=combinar_respostas(RESPOSTA_RECURSO_NAO_ENCONTRADO),
)
def conectar(
    principal: Principal = Depends(exigir_permissao("whatsapp.conexao.gerir")),
    caso_de_uso: ConectarWhatsApp = Depends(get_conectar_whatsapp),
) -> QrCodeConexaoResponse:
    """Cria a instância se preciso e devolve o QR para escanear.

    Repetir é seguro e é o uso normal: o QR expira em ~20s, e cada chamada traz
    o de agora sobre a MESMA instância.
    """
    return QrCodeConexaoResponse.de(
        caso_de_uso.executar(tenant_id=principal.tenant_id, usuario_id=principal.usuario_id)
    )


@router.delete(
    "/conexao",
    response_model=ConexaoWhatsAppResponse,
    responses=combinar_respostas(RESPOSTA_RECURSO_NAO_ENCONTRADO),
)
def desconectar(
    principal: Principal = Depends(exigir_permissao("whatsapp.conexao.gerir")),
    caso_de_uso: DesconectarWhatsApp = Depends(get_desconectar_whatsapp),
) -> ConexaoWhatsAppResponse:
    """Desvincula o número. **A instância permanece** — reconectar custa um QR.

    Para tirar a instância do provedor, `DELETE /conexao/instancia`.
    """
    return ConexaoWhatsAppResponse.de(
        caso_de_uso.executar(tenant_id=principal.tenant_id, usuario_id=principal.usuario_id)
    )


@router.delete(
    "/conexao/instancia",
    response_model=ConexaoWhatsAppResponse,
    responses=combinar_respostas(RESPOSTA_RECURSO_NAO_ENCONTRADO),
)
def excluir_instancia(
    principal: Principal = Depends(exigir_permissao("whatsapp.conexao.gerir")),
    caso_de_uso: ExcluirConexaoWhatsApp = Depends(get_excluir_conexao_whatsapp),
) -> ConexaoWhatsAppResponse:
    """Apaga a instância no provedor e o registro local.

    Rota própria, e não um parâmetro do `desconectar`, porque são intenções
    diferentes: lá o operador troca de número, aqui ele encerra a conexão. Sem
    esta operação o provedor acumula instância morta — nome, token e sessão que
    ninguém usa — e nada no sistema as remove.
    """
    return ConexaoWhatsAppResponse.de(
        caso_de_uso.executar(tenant_id=principal.tenant_id, usuario_id=principal.usuario_id)
    )


# --- Numero que recebe os avisos (IMP-353) ---------------------------------
# Nao e a conexao: e a configuracao `credor_whatsapp` do Tenant, destino do
# resumo diario e do aviso de sobra. PUT porque e substituicao total de um
# valor unico por Tenant; `Idempotency-Key` obrigatoria (a ADR-019 isenta so
# as tres operacoes da conexao).


@router.get("/avisos", response_model=NumeroAvisosResponse)
def consultar_numero_avisos(
    principal: Principal = Depends(exigir_permissao("whatsapp.conexao.ler")),
    service: NumeroAvisosService = Depends(get_numero_avisos_service),
) -> NumeroAvisosResponse:
    return NumeroAvisosResponse.de(service.consultar(principal.tenant_id))


@router.put("/avisos", response_model=NumeroAvisosResponse)
def definir_numero_avisos(
    payload: NumeroAvisosRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao("whatsapp.conexao.gerir")),
    service: NumeroAvisosService = Depends(get_numero_avisos_service),
) -> NumeroAvisosResponse:
    return NumeroAvisosResponse.de(
        service.definir(
            tenant_id=principal.tenant_id,
            numero=payload.numero,
            idempotency_key=idempotency_key.strip(),
            usuario_id=principal.usuario_id,
        )
    )

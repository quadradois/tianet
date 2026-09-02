"""Casos de uso da conexão de WhatsApp do Credor (IMP-367, PLAN-034).

Três operações, e a distinção entre elas é o conteúdo real deste módulo:

- **inexistente** — nenhuma instância no provedor. Pede criar;
- **pendente** — instância existe, número não vinculado. Pede escanear um QR;
- **pareada** — número vinculado. Nada a fazer.

Colapsar as duas primeiras faria a tela oferecer a ação errada, e colapsar as
duas últimas faria anunciar sucesso com nenhum WhatsApp do outro lado: o
Evolution responde `Connected: true` com `LoggedIn: false` numa instância
recém-criada, verificado em 2026-08-31.

**O QR nunca entra na trilha.** Ele é o material que pareia um número; a
auditoria da ADR-002 é append-only, e o que entra lá não sai.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from emprestimo.application.errors import ConexaoWhatsAppNaoEncontradaError
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.platform.conexao_whatsapp import ConexaoWhatsApp
from emprestimo.domain.platform.ports import ProvedorWhatsApp

ENTIDADE_AUDITORIA = "conexao_whatsapp"


@dataclass(frozen=True)
class EstadoConexaoWhatsApp:
    """O que a Presentation precisa para decidir o que oferecer ao operador.

    `existe` separado de `pareada` porque as duas ausências pedem ações
    diferentes. `numero` só é preenchido quando pareada — antes disso não há
    número, e inventar um placeholder faria a tela exibir vínculo inexistente.
    """

    existe: bool
    pareada: bool
    conectado: bool
    instancia_nome: str | None
    numero: str | None


@dataclass(frozen=True)
class QrCodeConexao:
    """QR pronto para exibição, em base64.

    Tipo próprio em vez de `str` solta para que o valor não se confunda com
    nome, id ou token em nenhuma assinatura — e para que qualquer log acidental
    tenha de mencionar o nome deste campo.
    """

    qrcode_base64: str


def _autoria(usuario_id: uuid.UUID | None) -> dict[str, object]:
    """Base de `detalhes` de todo evento da trilha (IMP-361, ADR-002).

    Sem PII e sem segredo: o mesmo dicionário serve início, sucesso e falha.
    """
    return {"usuario_id": str(usuario_id) if usuario_id is not None else None}


def _detalhes(autoria: dict[str, object], **extras: object) -> str:
    return json.dumps({**autoria, **extras}, sort_keys=True)


def _sincronizar(
    uow: UnitOfWork,
    conexao: ConexaoWhatsApp,
    token: str,
    provedor: ProvedorWhatsApp,
) -> tuple[ConexaoWhatsApp, bool]:
    """Alinha o número guardado ao que o provedor reporta agora.

    O pareamento acontece **fora** daqui: o operador escaneia o QR no celular, e
    nenhuma requisição nossa observa esse instante. Por isso o número vem sempre
    de uma leitura do provedor, e nunca de inferência local.

    Devolve também `conectado`, que não é estado persistido — é o socket de
    agora, e guardá-lo criaria um campo desatualizado desde o instante seguinte.
    """
    estado = provedor.estado(token)
    if estado.pareado and estado.numero:
        atualizada = conexao.parear(estado.numero)
    elif not estado.pareado:
        atualizada = conexao.desparear()
    else:
        # Pareado sem número: o provedor confirmou vínculo mas não disse com
        # quem. Preservar o que já se sabia é melhor que apagar por uma resposta
        # incompleta.
        return conexao, estado.conectado

    if atualizada.numero_pareado != conexao.numero_pareado:
        uow.conexao_whatsapp.save(atualizada)
        return atualizada, estado.conectado
    return conexao, estado.conectado


class ConsultarConexaoWhatsApp:
    """Lê o estado real, não o último estado conhecido."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        provedor: ProvedorWhatsApp,
    ) -> None:
        self._uow_factory = uow_factory
        self._provedor = provedor

    def executar(self, tenant_id: uuid.UUID) -> EstadoConexaoWhatsApp:
        with self._uow_factory() as uow:
            conexao = uow.conexao_whatsapp.find_by_tenant_id(tenant_id)
            if conexao is None:
                return EstadoConexaoWhatsApp(
                    existe=False,
                    pareada=False,
                    conectado=False,
                    instancia_nome=None,
                    numero=None,
                )
            token = uow.conexao_whatsapp.find_token(tenant_id)
            if token is None:
                # Conexão sem token é registro órfão: existe, e não pode falar
                # com o provedor. Nomear em vez de fingir que está desconectada.
                raise ConexaoWhatsAppNaoEncontradaError(tenant_id)

            atualizada, conectado = _sincronizar(uow, conexao, token, self._provedor)
            uow.commit()
            return EstadoConexaoWhatsApp(
                existe=True,
                pareada=atualizada.pareada,
                conectado=conectado,
                instancia_nome=atualizada.instancia_nome,
                numero=atualizada.numero_pareado,
            )


class ConectarWhatsApp:
    """Cria a instância se preciso, e devolve o QR para escanear.

    Criar e conectar num caso de uso só porque, do ponto de vista de quem opera,
    são um gesto: "quero ligar meu WhatsApp". Separá-los exporia ao operador uma
    etapa intermediária — instância criada e não conectada — que não corresponde
    a nada que ele queira fazer.
    """

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        provedor: ProvedorWhatsApp,
        auditoria: AuditoriaRegistro,
    ) -> None:
        self._uow_factory = uow_factory
        self._provedor = provedor
        self._auditoria = auditoria

    def executar(
        self,
        tenant_id: uuid.UUID,
        instancia_nome: str,
        usuario_id: uuid.UUID | None = None,
    ) -> QrCodeConexao:
        autoria = _autoria(usuario_id)
        self._auditoria.registrar(
            ENTIDADE_AUDITORIA,
            None,
            "conectar.inicio",
            "iniciado",
            detalhes=_detalhes(autoria),
        )
        try:
            with self._uow_factory() as uow:
                conexao = uow.conexao_whatsapp.find_by_tenant_id(tenant_id)
                if conexao is None:
                    instancia_id, token = self._provedor.criar_instancia(instancia_nome)
                    conexao = ConexaoWhatsApp.criar(
                        tenant_id=tenant_id,
                        instancia_id=instancia_id,
                        instancia_nome=instancia_nome,
                    )
                    uow.conexao_whatsapp.save(conexao, token=token)
                else:
                    guardado = uow.conexao_whatsapp.find_token(tenant_id)
                    if guardado is None:
                        raise ConexaoWhatsAppNaoEncontradaError(tenant_id)
                    token = guardado

                self._provedor.conectar(token)
                qrcode = self._provedor.qrcode(token)
                uow.commit()
        except Exception as exc:
            self._auditoria.registrar(
                ENTIDADE_AUDITORIA,
                None,
                "conectar.falha",
                "falhou",
                # Só o tipo: a mensagem do provedor pode carregar o token ou o
                # QR, e a trilha é append-only (IMP-361).
                detalhes=_detalhes(autoria, erro_tipo=type(exc).__name__),
            )
            raise

        self._auditoria.registrar(
            ENTIDADE_AUDITORIA,
            conexao.id,
            "conectar.sucesso",
            "sucesso",
            # `instancia_id` identifica; o QR não entra, nunca.
            detalhes=_detalhes(autoria, instancia_id=conexao.instancia_id),
        )
        return QrCodeConexao(qrcode_base64=qrcode)


class DesconectarWhatsApp:
    """Desvincula o número. A instância permanece.

    Apagar a instância obrigaria a recriá-la — e com ela um token novo — a cada
    desconexão. Reconectar deve custar um QR, não um ciclo de provisionamento.
    """

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        provedor: ProvedorWhatsApp,
        auditoria: AuditoriaRegistro,
    ) -> None:
        self._uow_factory = uow_factory
        self._provedor = provedor
        self._auditoria = auditoria

    def executar(
        self,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID | None = None,
    ) -> EstadoConexaoWhatsApp:
        autoria = _autoria(usuario_id)
        self._auditoria.registrar(
            ENTIDADE_AUDITORIA,
            None,
            "desconectar.inicio",
            "iniciado",
            detalhes=_detalhes(autoria),
        )
        try:
            with self._uow_factory() as uow:
                conexao = uow.conexao_whatsapp.find_by_tenant_id(tenant_id)
                token = uow.conexao_whatsapp.find_token(tenant_id)
                if conexao is None or token is None:
                    raise ConexaoWhatsAppNaoEncontradaError(tenant_id)

                self._provedor.desconectar(token)
                despareada = conexao.desparear()
                uow.conexao_whatsapp.save(despareada)
                uow.commit()
        except Exception as exc:
            self._auditoria.registrar(
                ENTIDADE_AUDITORIA,
                None,
                "desconectar.falha",
                "falhou",
                detalhes=_detalhes(autoria, erro_tipo=type(exc).__name__),
            )
            raise

        self._auditoria.registrar(
            ENTIDADE_AUDITORIA,
            despareada.id,
            "desconectar.sucesso",
            "sucesso",
            detalhes=_detalhes(autoria, instancia_id=despareada.instancia_id),
        )
        return EstadoConexaoWhatsApp(
            existe=True,
            pareada=False,
            conectado=False,
            instancia_nome=despareada.instancia_nome,
            numero=None,
        )

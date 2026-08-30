"""DevedorCadastroService — orquestrador da criação de Devedor (IMP-051).

Fluxo:
1. Validar unicidade do documento na Carteira (UnicidadeDevedorService);
2. Criar Aggregate Devedor (DOMAIN-020) com contatos;
3. Registrar trilha de auditoria (ADR-002);
4. Persistir via Unit of Work em transação única (AD-001);
5. Idempotência (AD-002): Idempotency-Key registrada na mesma transação;
   replay com a mesma chave retorna exatamente o mesmo resultado.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from emprestimo.application.errors import IdempotenciaConflitoError
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.credit.contato import Contato, TipoContato
from emprestimo.domain.credit.devedor import Devedor, DevedorState
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.credit.eventos_devedor import DevedorCadastrado
from emprestimo.domain.credit.notifications import (
    EstadoPreferenciaNotificacao,
    PreferenciaNotificacao,
)
from emprestimo.domain.credit.unicidade_devedor import UnicidadeDevedorService

ESCOPO_IDEMPOTENCIA = "devedor-cadastro"
"""Escopo da Idempotency-Key: isola chaves por caso de uso (AD-002)."""


@dataclass(frozen=True)
class DevedorCriado:
    """Resultado do cadastro de Devedor — estado final Ativo (IMP-051).

    Dados suficientes para a confirmação na API: identidade, documento,
    nome, contatos, estado final e timestamp de criação.
    """

    devedor_id: uuid.UUID
    carteira_id: uuid.UUID
    documento: str
    nome: str
    contatos: tuple[dict[str, object], ...]
    estado: DevedorState
    criado_em: datetime


def _solicitacao_hash(
    carteira_id: uuid.UUID,
    documento: str,
    nome: str,
    contatos: list[dict[str, object]],
) -> str:
    """Fingerprint do payload — detecta chave reenviada com resultado divergente."""
    canonico = json.dumps(contatos, sort_keys=True, separators=(",", ":"), default=str)
    bruto = f"{carteira_id}|{documento.strip()}|{nome.strip()}|{canonico}"
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def _autoria(usuario_id: uuid.UUID | None, idempotency_key: str) -> dict[str, object]:
    """Base de `detalhes` que todo evento da trilha carrega (IMP-361, ADR-002).

    Existe para que autoria não dependa de cada call site lembrar de incluí-la:
    uma ferramenta de escrita nova monta este dicionário uma vez e espalha em
    todos os seus eventos. `usuario_id` ausente vira `None` explícito — a trilha
    distingue "escrita sem Principal" de "campo esquecido".

    Não coloque PII aqui: o que entra vale para início, passos, sucesso, falha,
    rollback e replay, e a trilha é append-only.
    """
    return {
        "usuario_id": str(usuario_id) if usuario_id is not None else None,
        "idempotency_key": idempotency_key,
    }


def _contatos_para_dict(contatos: tuple[Contato, ...]) -> tuple[dict[str, object], ...]:
    return tuple(
        {"tipo": c.tipo.value, "valor": c.valor, "preferencial": c.preferencial} for c in contatos
    )


class DevedorCadastroService:
    """Orquestra o cadastro completo de um Devedor (US-015..US-020)."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        unicidade: UnicidadeDevedorService,
        auditoria: AuditoriaRegistro,
    ) -> None:
        self._uow_factory = uow_factory
        self._unicidade = unicidade
        self._auditoria = auditoria

    def criar(
        self,
        carteira_id: uuid.UUID,
        documento: str,
        nome: str,
        contatos: list[dict[str, object]],
        idempotency_key: str,
        usuario_id: uuid.UUID | None = None,
    ) -> DevedorCriado:
        """Executa o cadastro do Devedor em transação única."""
        doc_normalizado = documento.strip()
        hash_solicitacao = _solicitacao_hash(carteira_id, doc_normalizado, nome.strip(), contatos)

        # IMP-361: autoria em TODO evento da trilha — inicio, passos, sucesso,
        # falha, rollback e replay carregam o mesmo Principal. Sem isso, uma
        # escrita disparada pelo copilot fica indistinguivel de uma escrita
        # humana na trilha da ADR-002.
        autoria = _autoria(usuario_id, idempotency_key)

        self._auditoria.registrar(
            "devedor",
            None,
            "criar.inicio",
            "iniciado",
            detalhes=json.dumps(autoria, sort_keys=True),
        )
        try:
            with self._uow_factory() as uow:
                resultado = self._replay_ou_registrar_chave(
                    uow, idempotency_key, hash_solicitacao, autoria
                )
                if resultado is not None:
                    uow.commit()
                    return resultado

                # 1. Validar unicidade do documento na Carteira
                doc_vo = Documento.from_str(doc_normalizado)
                self._unicidade.verificar_documento_disponivel(doc_vo, carteira_id)

                # 2. Construir contatos (entidades filhas)
                contatos_entidades = []
                for c in contatos:
                    tipo = TipoContato(str(c["tipo"]).strip().lower())
                    valor = str(c["valor"]).strip()
                    preferencial = bool(c.get("preferencial", False))
                    # Contatos recebidos não têm devedor_id ainda; o Aggregate preenche
                    contatos_entidades.append(
                        Contato(
                            devedor_id=uuid.UUID(int=0),  # placeholder; Aggregate substitui
                            tipo=tipo,
                            valor=valor,
                            preferencial=preferencial,
                        )
                    )

                # 3. Criar Aggregate Devedor (valida RN-003, RN-005, INV-001, INV-003)
                devedor = Devedor.criar(
                    carteira_id=carteira_id,
                    documento=doc_vo,
                    nome=nome.strip(),
                    contatos=contatos_entidades,
                )

                # 4. Trilha de auditoria — passos
                self._auditoria.registrar(
                    "devedor",
                    devedor.id,
                    "criar.aggregate_criado",
                    "ok",
                    detalhes=json.dumps(
                        {
                            **autoria,
                            "devedor_id": str(devedor.id),
                            "carteira_id": str(carteira_id),
                        },
                        sort_keys=True,
                    ),
                )

                # 5. Persistir via UoW (mesma transação)
                uow.devedor.save(devedor)
                # Contatos são salvos em cascata via merge do DevedorORM —
                # mas o ContatoRepository existe para uso direto se necessário
                for contato in devedor.contatos:
                    uow.contato.save(contato)

                # 6. Evento de domínio para auditoria (ADR-002)
                carteira = uow.carteira.find_by_id(carteira_id)
                tenant_id = carteira.tenant_id if carteira else uuid.UUID(int=0)
                for contato, entrada in zip(devedor.contatos, contatos, strict=True):
                    estado = entrada.get("notificacao_estado")
                    if estado is None:
                        continue
                    if usuario_id is None:
                        raise ValueError("usuario_id obrigatorio para registrar consentimento")
                    uow.preferencia_notificacao.save(
                        PreferenciaNotificacao(
                            tenant_id=tenant_id,
                            carteira_id=carteira_id,
                            contato_id=contato.id,
                            estado=EstadoPreferenciaNotificacao(str(estado)),
                            evidencia=str(entrada["notificacao_evidencia"]),
                            origem=str(entrada["notificacao_origem"]),
                            ator_id=usuario_id,
                            registrada_em=datetime.now(UTC),
                        )
                    )
                evento = DevedorCadastrado.from_devedor(devedor, tenant_id)
                self._auditoria.registrar(
                    "devedor",
                    devedor.id,
                    "criar.evento_cadastrado",
                    "ok",
                    detalhes=json.dumps({**evento.to_audit_dict(), **autoria}, sort_keys=True),
                )

                resultado = DevedorCriado(
                    devedor_id=devedor.id,
                    carteira_id=devedor.carteira_id,
                    documento=devedor.documento.valor,
                    nome=devedor.nome,
                    contatos=_contatos_para_dict(devedor.contatos),
                    estado=devedor.estado,
                    criado_em=devedor.criado_em,
                )
                uow.idempotencia.concluir(
                    idempotency_key, ESCOPO_IDEMPOTENCIA, _serializar_resultado(resultado)
                )
                uow.commit()

            self._auditoria.registrar(
                "devedor",
                resultado.devedor_id,
                "criar.sucesso",
                "ok",
                detalhes=json.dumps({**autoria, "estado": resultado.estado.value}, sort_keys=True),
            )
            return resultado
        except Exception as exc:
            # So o tipo da excecao, nunca a mensagem: DevedorJaExisteError
            # interpola o documento, e a trilha e append-only — um CPF gravado
            # aqui nao sai mais. Mesmo padrao de UsuarioCadastroService.
            self._auditoria.registrar(
                "devedor",
                None,
                "criar.falha",
                "falhou",
                detalhes=json.dumps({**autoria, "erro_tipo": type(exc).__name__}, sort_keys=True),
            )
            self._auditoria.registrar(
                "devedor",
                None,
                "criar.rollback",
                "rollback_aplicado",
                detalhes=json.dumps(autoria, sort_keys=True),
            )
            raise

    def _replay_ou_registrar_chave(
        self,
        uow: UnitOfWork,
        idempotency_key: str,
        hash_solicitacao: str,
        autoria: dict[str, object],
    ) -> DevedorCriado | None:
        """Replay seguro (AD-002): mesma chave → mesmo resultado; divergente → conflito."""
        existente = uow.idempotencia.find_by_chave(idempotency_key, ESCOPO_IDEMPOTENCIA)
        if existente is None:
            uow.idempotencia.registrar(idempotency_key, ESCOPO_IDEMPOTENCIA, hash_solicitacao)
            return None
        # Estado ANTES do hash: se a operação anterior não terminou, esse é o fato
        # dominante — um hash divergente durante operação em curso é sintoma, não
        # causa. Ordem uniforme nos quatro casos de uso (AD-002).
        if existente["estado"] != "finished":
            raise IdempotenciaConflitoError(idempotency_key, "cadastro em andamento")
        if existente["solicitacao_hash"] != hash_solicitacao:
            raise IdempotenciaConflitoError(idempotency_key, "resultado divergente")
        self._auditoria.registrar(
            "devedor",
            None,
            "criar.replay",
            "ok",
            detalhes=json.dumps(autoria, sort_keys=True),
        )
        return _desserializar_resultado(existente["resultado"])


def _serializar_resultado(resultado: DevedorCriado) -> str:
    return json.dumps(
        {
            "devedor_id": str(resultado.devedor_id),
            "carteira_id": str(resultado.carteira_id),
            "documento": resultado.documento,
            "nome": resultado.nome,
            "contatos": list(resultado.contatos),
            "estado": resultado.estado.value,
            "criado_em": resultado.criado_em.isoformat(),
        }
    )


def _desserializar_resultado(conteudo: str | None) -> DevedorCriado:
    if not conteudo:
        raise IdempotenciaConflitoError("?", "resultado ausente no registro")
    dados = json.loads(conteudo)
    return DevedorCriado(
        devedor_id=uuid.UUID(dados["devedor_id"]),
        carteira_id=uuid.UUID(dados["carteira_id"]),
        documento=dados["documento"],
        nome=dados["nome"],
        contatos=tuple(dados["contatos"]),
        estado=DevedorState(dados["estado"]),
        criado_em=datetime.fromisoformat(dados["criado_em"]),
    )

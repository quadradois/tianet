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
from datetime import datetime

from emprestimo.application.errors import IdempotenciaConflitoError
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.credit.contato import Contato, TipoContato
from emprestimo.domain.credit.devedor import Devedor, DevedorState
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.credit.unicidade_devedor import UnicidadeDevedorService
from emprestimo.domain.credit.eventos_devedor import DevedorCadastrado

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


def _solicitacao_hash(carteira_id: uuid.UUID, documento: str, nome: str) -> str:
    """Fingerprint do payload — detecta chave reenviada com resultado divergente."""
    bruto = f"{carteira_id}|{documento.strip()}|{nome.strip()}"
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def _contatos_para_dict(contatos: tuple[Contato, ...]) -> tuple[dict[str, object], ...]:
    return tuple(
        {"tipo": c.tipo.value, "valor": c.valor, "preferencial": c.preferencial}
        for c in contatos
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
    ) -> DevedorCriado:
        """Executa o cadastro do Devedor em transação única."""
        doc_normalizado = documento.strip()
        hash_solicitacao = _solicitacao_hash(carteira_id, doc_normalizado, nome.strip())

        self._auditoria.registrar(
            "devedor",
            None,
            "criar.inicio",
            "iniciado",
            detalhes=json.dumps({"idempotency_key": idempotency_key}),
        )
        try:
            with self._uow_factory() as uow:
                resultado = self._replay_ou_registrar_chave(uow, idempotency_key, hash_solicitacao)
                if resultado is not None:
                    uow.commit()
                    return resultado

                # 1. Validar unicidade do documento na Carteira
                doc_vo = Documento.from_str(doc_normalizado)
                self._unicidade.verificar_documento_disponivel(doc_vo, carteira_id)

                # 2. Construir contatos (entidades filhas)
                contatos_entidades = []
                for i, c in enumerate(contatos):
                    tipo = TipoContato(c["tipo"])
                    valor = c["valor"].strip()
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
                            "devedor_id": str(devedor.id),
                            "carteira_id": str(carteira_id),
                            "idempotency_key": idempotency_key,
                        }
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
                evento = DevedorCadastrado.from_devedor(devedor, tenant_id)
                self._auditoria.registrar(
                    "devedor",
                    devedor.id,
                    "criar.evento_cadastrado",
                    "ok",
                    detalhes=json.dumps(evento.to_audit_dict()),
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
                uow.idempotencia.concluir(idempotency_key, _serializar_resultado(resultado))
                uow.commit()

            self._auditoria.registrar(
                "devedor",
                resultado.devedor_id,
                "criar.sucesso",
                "ok",
                detalhes=json.dumps(
                    {"estado": resultado.estado.value, "idempotency_key": idempotency_key}
                ),
            )
            return resultado
        except Exception as exc:
            self._auditoria.registrar(
                "devedor",
                None,
                "criar.falha",
                "falhou",
                detalhes=f"{type(exc).__name__}: {exc}",
            )
            self._auditoria.registrar("devedor", None, "criar.rollback", "rollback_aplicado")
            raise

    def _replay_ou_registrar_chave(
        self, uow: UnitOfWork, idempotency_key: str, hash_solicitacao: str
    ) -> DevedorCriado | None:
        """Replay seguro (AD-002): mesma chave → mesmo resultado; divergente → conflito."""
        existente = uow.idempotencia.find_by_chave(idempotency_key)
        if existente is None:
            uow.idempotencia.registrar(idempotency_key, ESCOPO_IDEMPOTENCIA, hash_solicitacao)
            return None
        if existente["solicitacao_hash"] != hash_solicitacao:
            raise IdempotenciaConflitoError(idempotency_key, "resultado divergente")
        if existente["estado"] != "finished":
            raise IdempotenciaConflitoError(idempotency_key, "cadastro em andamento")
        self._auditoria.registrar(
            "devedor",
            None,
            "criar.replay",
            "ok",
            detalhes=json.dumps({"idempotency_key": idempotency_key}),
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
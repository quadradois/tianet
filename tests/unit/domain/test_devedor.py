"""Testes unitários do Aggregate Devedor (IMP-045, DOMAIN-020)."""

from __future__ import annotations

import uuid

import pytest

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.contato import Contato, ContatoInvalidoError, TipoContato
from emprestimo.domain.credit.devedor import Devedor, DevedorState
from emprestimo.domain.credit.documento import Documento

CARTEIRA_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
DOCUMENTO = Documento.from_str("52998224725")
OUTRO_DOCUMENTO = Documento.from_str("11144477735")

DEVEDOR_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def _contato_telefone(preferencial: bool = False) -> Contato:
    return Contato(
        devedor_id=DEVEDOR_ID,
        tipo=TipoContato.TELEFONE,
        valor="(11) 1234-5678",
        preferencial=preferencial,
    )


def _contato_email(preferencial: bool = False) -> Contato:
    return Contato(
        devedor_id=DEVEDOR_ID,
        tipo=TipoContato.EMAIL,
        valor="joao@exemplo.com",
        preferencial=preferencial,
    )


def _devedor(
    contatos: list[Contato] | None = None,
    estado: DevedorState = DevedorState.ATIVO,
) -> Devedor:
    devedor = Devedor.criar(
        carteira_id=CARTEIRA_ID,
        documento=DOCUMENTO,
        nome="João da Silva",
        contatos=contatos or [_contato_telefone()],
    )
    if estado is DevedorState.INATIVO:
        devedor.inativar()
    return devedor


# --------------------------------------------------------------------------- #
# Criação e invariantes básicas
# --------------------------------------------------------------------------- #


def test_cria_devedor_ativo_com_documento_e_contato() -> None:
    devedor = _devedor()

    assert devedor.id is not None
    assert devedor.carteira_id == CARTEIRA_ID
    assert devedor.documento == DOCUMENTO
    assert devedor.nome == "João da Silva"
    assert devedor.estado == DevedorState.ATIVO
    assert len(devedor.contatos) == 1


def test_estado_inicial_e_ativo() -> None:
    devedor = _devedor()

    assert devedor.estado == DevedorState.ATIVO


def test_vincula_contatos_ao_devedor_criado() -> None:
    devedor = _devedor()

    assert devedor.contatos[0].devedor_id == devedor.id


def test_cria_devedor_com_multiplos_contatos() -> None:
    devedor = _devedor([_contato_telefone(), _contato_email()])

    assert len(devedor.contatos) == 2


# --------------------------------------------------------------------------- #
# INV-001 — vínculo obrigatório à Carteira
# --------------------------------------------------------------------------- #


def test_rejeita_carteira_id_invalido() -> None:
    with pytest.raises(ViolacaoInvarianteError) as exc:
        Devedor(carteira_id="nao-uuid", nome="João da Silva")  # type: ignore[arg-type]

    assert exc.value.codigo == "INV-001"


def test_rejeita_carteira_id_nulo() -> None:
    with pytest.raises(ViolacaoInvarianteError) as exc:
        Devedor(carteira_id=None, nome="João da Silva")  # type: ignore[arg-type]

    assert exc.value.codigo == "INV-001"


# --------------------------------------------------------------------------- #
# INV-003 — documento imutável
# --------------------------------------------------------------------------- #


def test_documento_imutavel_sem_setter() -> None:
    devedor = _devedor()

    with pytest.raises(AttributeError):
        devedor.documento = OUTRO_DOCUMENTO  # type: ignore[misc]


def test_documento_preservado_apos_atualizacoes() -> None:
    devedor = _devedor()

    devedor.atualizar_nome("Novo Nome")
    devedor.inativar()
    devedor.reativar()

    assert devedor.documento == DOCUMENTO


def test_rejeita_documento_nao_documento() -> None:
    with pytest.raises(ViolacaoInvarianteError) as exc:
        Devedor.criar(
            carteira_id=CARTEIRA_ID,
            documento="52998224725",  # type: ignore[arg-type]
            nome="João da Silva",
            contatos=[_contato_telefone()],
        )

    assert exc.value.codigo == "INV-003"


def test_rejeita_estado_invalido() -> None:
    with pytest.raises(ViolacaoInvarianteError) as exc:
        Devedor(
            carteira_id=CARTEIRA_ID,
            nome="João da Silva",
            estado="ativo",  # type: ignore[arg-type]
        )

    assert exc.value.codigo == "INV-005"


# --------------------------------------------------------------------------- #
# RN-003 — ao menos um contato na criação
# --------------------------------------------------------------------------- #


def test_rejeita_criacao_sem_contatos() -> None:
    with pytest.raises(ViolacaoInvarianteError) as exc:
        Devedor.criar(
            carteira_id=CARTEIRA_ID,
            documento=DOCUMENTO,
            nome="João da Silva",
            contatos=[],
        )

    assert exc.value.codigo == "RN-003"


# --------------------------------------------------------------------------- #
# Gestão de contatos — unicidade por tipo+valor (DOMAIN-021 §2)
# --------------------------------------------------------------------------- #


def test_rejeita_contato_duplicado_por_tipo_e_valor() -> None:
    devedor = _devedor()
    duplicado = Contato(
        devedor_id=devedor.id,
        tipo=TipoContato.TELEFONE,
        valor="(11) 1234-5678",
    )

    with pytest.raises(ViolacaoInvarianteError) as exc:
        devedor.adicionar_contato(duplicado)

    assert exc.value.codigo == "DOMAIN-021"


def test_aceita_contato_mesmo_valor_tipo_diferente() -> None:
    devedor = _devedor()
    whatsapp = Contato(
        devedor_id=devedor.id,
        tipo=TipoContato.WHATSAPP,
        valor="(11) 1234-5678",
    )

    devedor.adicionar_contato(whatsapp)

    assert len(devedor.contatos) == 2


# --------------------------------------------------------------------------- #
# RN-001 — contato pertence ao Devedor
# --------------------------------------------------------------------------- #


def test_rejeita_contato_de_outro_devedor() -> None:
    devedor = _devedor()
    contato_estranho = Contato(
        devedor_id=uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
        tipo=TipoContato.EMAIL,
        valor="outro@exemplo.com",
    )

    with pytest.raises(ViolacaoInvarianteError) as exc:
        devedor.adicionar_contato(contato_estranho)

    assert exc.value.codigo == "RN-001"


# --------------------------------------------------------------------------- #
# RN-005 — apenas um preferencial por tipo
# --------------------------------------------------------------------------- #


def test_aceita_preferencial_de_tipos_diferentes() -> None:
    devedor = _devedor([_contato_telefone(preferencial=True), _contato_email(preferencial=True)])

    preferenciais = [c for c in devedor.contatos if c.preferencial]

    assert len(preferenciais) == 2


def test_rejeita_segundo_preferencial_do_mesmo_tipo() -> None:
    devedor = _devedor([_contato_telefone(preferencial=True)])
    outro_telefone = Contato(
        devedor_id=devedor.id,
        tipo=TipoContato.TELEFONE,
        valor="(21) 98765-4321",
        preferencial=True,
    )

    with pytest.raises(ViolacaoInvarianteError) as exc:
        devedor.adicionar_contato(outro_telefone)

    assert exc.value.codigo == "RN-005"


def test_rejeita_preferencial_duplicado_na_atualizacao() -> None:
    telefone_preferencial = Contato(
        devedor_id=DEVEDOR_ID,
        tipo=TipoContato.TELEFONE,
        valor="(11) 1234-5678",
        preferencial=True,
    )
    segundo_telefone = Contato(
        devedor_id=DEVEDOR_ID,
        tipo=TipoContato.TELEFONE,
        valor="(21) 98765-4321",
    )
    devedor = _devedor([telefone_preferencial, segundo_telefone])
    segundo_telefone_entity = devedor.contatos[1]

    with pytest.raises(ViolacaoInvarianteError) as exc:
        devedor.atualizar_contato(segundo_telefone_entity.id, preferencial=True)

    assert exc.value.codigo == "RN-005"


# --------------------------------------------------------------------------- #
# Atualização de contatos
# --------------------------------------------------------------------------- #


def test_atualiza_valor_de_contato() -> None:
    devedor = _devedor([_contato_telefone(), _contato_email()])
    telefone = devedor.contatos[0]

    devedor.atualizar_contato(telefone.id, valor="(21) 98765-4321")

    assert devedor.contatos[0].valor == "(21) 98765-4321"
    assert len(devedor.contatos) == 2


def test_rejeita_valor_invalido_na_atualizacao() -> None:
    devedor = _devedor()
    contato = devedor.contatos[0]

    with pytest.raises(ContatoInvalidoError):
        devedor.atualizar_contato(contato.id, valor="abc")


def test_rejeita_valor_duplicado_na_atualizacao() -> None:
    email_a = Contato(
        devedor_id=DEVEDOR_ID,
        tipo=TipoContato.EMAIL,
        valor="a@exemplo.com",
    )
    email_b = Contato(
        devedor_id=DEVEDOR_ID,
        tipo=TipoContato.EMAIL,
        valor="b@exemplo.com",
    )
    devedor = _devedor([_contato_telefone(), email_a, email_b])
    email_a_entity = devedor.contatos[1]

    with pytest.raises(ViolacaoInvarianteError) as exc:
        devedor.atualizar_contato(email_a_entity.id, valor="b@exemplo.com")

    assert exc.value.codigo == "DOMAIN-021"


def test_rejeita_valor_duplicado_com_espacos_na_atualizacao() -> None:
    email_a = Contato(
        devedor_id=DEVEDOR_ID,
        tipo=TipoContato.EMAIL,
        valor="a@exemplo.com",
    )
    email_b = Contato(
        devedor_id=DEVEDOR_ID,
        tipo=TipoContato.EMAIL,
        valor="b@exemplo.com",
    )
    devedor = _devedor([_contato_telefone(), email_a, email_b])
    email_a_entity = devedor.contatos[1]

    with pytest.raises(ViolacaoInvarianteError) as exc:
        devedor.atualizar_contato(email_a_entity.id, valor="  b@exemplo.com  ")

    assert exc.value.codigo == "DOMAIN-021"


def test_promove_contato_a_preferencial() -> None:
    devedor = _devedor([_contato_telefone(), _contato_email()])
    email = devedor.contatos[1]

    devedor.atualizar_contato(email.id, preferencial=True)

    assert devedor.contatos[1].preferencial is True


def test_remove_preferencial() -> None:
    devedor = _devedor([_contato_telefone(preferencial=True), _contato_email()])
    telefone = devedor.contatos[0]

    devedor.atualizar_contato(telefone.id, preferencial=False)

    assert devedor.contatos[0].preferencial is False


def test_remover_contato() -> None:
    devedor = _devedor([_contato_telefone(), _contato_email()])
    contato_id = devedor.contatos[0].id

    devedor.remover_contato(contato_id)

    assert len(devedor.contatos) == 1
    assert all(c.id != contato_id for c in devedor.contatos)
    assert len(devedor.contatos_historico) == 2
    assert any(c.id == contato_id and c.removido_em is not None for c in devedor.contatos_historico)


def test_contato_removido_nao_bloqueia_nova_inclusao_com_mesmo_tipo_valor() -> None:
    devedor = _devedor()
    contato_id = devedor.contatos[0].id

    devedor.remover_contato(contato_id)
    devedor.adicionar_contato(
        Contato(
            devedor_id=devedor.id,
            tipo=TipoContato.TELEFONE,
            valor="(11) 1234-5678",
        )
    )

    assert len(devedor.contatos) == 1
    assert len(devedor.contatos_historico) == 2


def test_contato_preferencial_removido_nao_bloqueia_novo_preferencial() -> None:
    devedor = _devedor([_contato_telefone(preferencial=True)])
    contato_id = devedor.contatos[0].id

    devedor.remover_contato(contato_id)
    devedor.adicionar_contato(
        Contato(
            devedor_id=devedor.id,
            tipo=TipoContato.TELEFONE,
            valor="(21) 98765-4321",
            preferencial=True,
        )
    )

    assert len(devedor.contatos) == 1
    assert devedor.contatos[0].preferencial is True


def test_remover_contato_inexistente() -> None:
    devedor = _devedor()

    with pytest.raises(ViolacaoInvarianteError):
        devedor.remover_contato(uuid.uuid4())


# --------------------------------------------------------------------------- #
# Atualização de nome (US-024)
# --------------------------------------------------------------------------- #


def test_atualizar_nome() -> None:
    devedor = _devedor()

    devedor.atualizar_nome("Maria Souza")

    assert devedor.nome == "Maria Souza"
    assert devedor.documento == DOCUMENTO


def test_atualizar_nome_com_espacos_normaliza() -> None:
    devedor = _devedor()

    devedor.atualizar_nome("  Maria Souza  ")

    assert devedor.nome == "Maria Souza"


def test_rejeita_nome_vazio() -> None:
    devedor = _devedor()

    with pytest.raises(ViolacaoInvarianteError):
        devedor.atualizar_nome("   ")


def test_rejeita_nome_muito_longo() -> None:
    devedor = _devedor()

    with pytest.raises(ViolacaoInvarianteError):
        devedor.atualizar_nome("X" * 201)


# As invariantes de nome também valem na CRIAÇÃO, não só em atualizar_nome():
# são validadas no __post_init__ do Aggregate (IMP-063).


def test_rejeita_criacao_com_nome_vazio() -> None:
    with pytest.raises(ViolacaoInvarianteError) as exc:
        Devedor.criar(
            carteira_id=CARTEIRA_ID,
            documento=DOCUMENTO,
            nome="   ",
            contatos=(_contato_telefone(preferencial=True),),
        )

    assert exc.value.codigo == "DOMAIN-020"


def test_rejeita_criacao_com_nome_muito_longo() -> None:
    with pytest.raises(ViolacaoInvarianteError) as exc:
        Devedor.criar(
            carteira_id=CARTEIRA_ID,
            documento=DOCUMENTO,
            nome="X" * 201,
            contatos=(_contato_telefone(preferencial=True),),
        )

    assert exc.value.codigo == "DOMAIN-020"


# --------------------------------------------------------------------------- #
# Transições de estado (INV-005)
# --------------------------------------------------------------------------- #


def test_inativar_devedor_ativo() -> None:
    devedor = _devedor()

    devedor.inativar()

    assert devedor.estado == DevedorState.INATIVO


def test_reativar_devedor_inativo() -> None:
    devedor = _devedor()
    devedor.inativar()

    devedor.reativar()

    assert devedor.estado == DevedorState.ATIVO


def test_inativar_preserva_historico_cadastral() -> None:
    devedor = _devedor()
    nome_original = devedor.nome
    documento_original = devedor.documento
    contatos_originais = devedor.contatos

    devedor.inativar()

    assert devedor.nome == nome_original
    assert devedor.documento == documento_original
    assert devedor.contatos == contatos_originais


def test_rejeita_inativar_devedor_inativo() -> None:
    devedor = _devedor()
    devedor.inativar()

    with pytest.raises(ViolacaoInvarianteError) as exc:
        devedor.inativar()

    assert exc.value.codigo == "INV-005"


def test_rejeita_reativar_devedor_ativo() -> None:
    devedor = _devedor()

    with pytest.raises(ViolacaoInvarianteError) as exc:
        devedor.reativar()

    assert exc.value.codigo == "INV-005"


# --------------------------------------------------------------------------- #
# Defesa contra mutação externa
# --------------------------------------------------------------------------- #


def test_mutacao_externa_de_contato_nao_afeta_aggregate() -> None:
    devedor = _devedor([_contato_telefone(preferencial=True)])
    contato_exposto = devedor.contatos[0]

    # Tentativa de quebrar RN-005 por mutação externa
    contato_exposto.preferencial = False

    assert devedor.contatos[0].preferencial is True


def test_mutacao_externa_da_lista_de_contatos_nao_afeta_aggregate() -> None:
    devedor = _devedor([_contato_telefone(preferencial=True)])
    contatos = devedor.contatos

    contatos[0].preferencial = False

    assert devedor.contatos[0].preferencial is True


def test_criar_nao_armazena_instancia_externa_de_contato() -> None:
    contato_externo = Contato(
        devedor_id=DEVEDOR_ID,
        tipo=TipoContato.TELEFONE,
        valor="(11) 1234-5678",
        preferencial=True,
    )
    devedor = Devedor.criar(
        carteira_id=CARTEIRA_ID,
        documento=DOCUMENTO,
        nome="João da Silva",
        contatos=[contato_externo],
    )

    contato_externo.preferencial = False
    contato_externo.valor = "(21) 99999-9999"

    assert devedor.contatos[0].preferencial is True
    assert devedor.contatos[0].valor == "(11) 1234-5678"


def test_adicionar_contato_nao_armazena_instancia_recebida() -> None:
    devedor = _devedor()
    contato_externo = Contato(
        devedor_id=devedor.id,
        tipo=TipoContato.WHATSAPP,
        valor="(11) 98765-4321",
        preferencial=False,
    )

    devedor.adicionar_contato(contato_externo)
    contato_externo.valor = "(21) 99999-9999"

    assert len(devedor.contatos) == 2
    assert any(
        c.tipo == TipoContato.WHATSAPP and c.valor == "(11) 98765-4321" for c in devedor.contatos
    )


# --------------------------------------------------------------------------- #
# Rastreabilidade
# --------------------------------------------------------------------------- #


def test_atualizado_em_marcado_nas_mutacoes() -> None:
    devedor = _devedor()
    marcado_na_criacao = devedor.atualizado_em
    assert marcado_na_criacao is not None

    devedor.atualizar_nome("Novo Nome")

    assert devedor.atualizado_em is not None
    assert devedor.atualizado_em >= marcado_na_criacao


# --------------------------------------------------------------------------- #
# RN-005 (DOMAIN-020): Devedor inativo não pode originar operações
# --------------------------------------------------------------------------- #


def test_atualizar_nome_de_devedor_inativo_viola_rn005() -> None:
    devedor = _devedor(estado=DevedorState.INATIVO)

    with pytest.raises(ViolacaoInvarianteError) as exc:
        devedor.atualizar_nome("Novo Nome")

    assert exc.value.codigo == "RN-005"


def test_adicionar_contato_em_devedor_inativo_viola_rn005() -> None:
    devedor = _devedor(estado=DevedorState.INATIVO)

    with pytest.raises(ViolacaoInvarianteError) as exc:
        devedor.adicionar_contato(
            Contato(devedor_id=devedor.id, tipo=TipoContato.EMAIL, valor="a@b.com")
        )

    assert exc.value.codigo == "RN-005"


def test_atualizar_contato_em_devedor_inativo_viola_rn005() -> None:
    devedor = _devedor(estado=DevedorState.INATIVO)

    with pytest.raises(ViolacaoInvarianteError) as exc:
        devedor.atualizar_contato(DEVEDOR_ID, valor="(11) 9999-9999")

    assert exc.value.codigo == "RN-005"


def test_remover_contato_em_devedor_inativo_viola_rn005() -> None:
    devedor = _devedor(estado=DevedorState.INATIVO)

    with pytest.raises(ViolacaoInvarianteError) as exc:
        devedor.remover_contato(DEVEDOR_ID)

    assert exc.value.codigo == "RN-005"

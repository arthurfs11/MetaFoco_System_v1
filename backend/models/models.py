from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Date, Text, UniqueConstraint, Date
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(100), nullable=False)
    sobrenome = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    senha_hash = Column(String(255), nullable=False)
    perfil = Column(String(50), nullable=False, default="LEITURA")
    precisa_trocar_senha = Column(Boolean, default=True)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

class Contrato(Base):
    __tablename__ = "contratos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data_base = Column(Date)
    instituicao = Column(String(255))
    empresa = Column(String(255))
    modalidade = Column(String(255))
    numero_contrato = Column(String(255))
    parcela = Column(Integer)
    periodo = Column(String(50))
    pgto = Column(String(10))
    emissao = Column(Date)
    inicial = Column(Date)
    final = Column(Date)
    contratado = Column(Float)
    curto_prazo = Column(Float)
    longo_prazo = Column(Float)
    total_pg = Column(Float)
    perc_rest = Column(Float)
    parc_pg = Column(Float)
    prestacao = Column(Float)
    juros = Column(Float)
    amortiz = Column(Float)
    am = Column(Float)
    aa = Column(Float)
    am2 = Column(Float)
    aa2 = Column(Float)
    indice = Column(String(50))
    modalidade2 = Column(String(255))
    perc_gar = Column(Float)
    obs_cet = Column(Text)
    resumo_garantias = Column(Text)
    fonte = Column(String(50))
    criado_em = Column(DateTime, default=datetime.utcnow)

    # Chave de unicidade: mesmo número de contrato + instituição + parcela + data base
    __table_args__ = (
        UniqueConstraint('numero_contrato', 'instituicao', 'parcela', 'data_base', name='uq_contrato_parcela'),
    )

class Feriado(Base):
    __tablename__ = "feriados"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data = Column(Date, unique=True, index=True, nullable=False)
    dia_semana = Column(String(50))
    nome = Column(String(100))

class CdiDiario(Base):
    __tablename__ = "cdi_diario"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data = Column(Date, unique=True, index=True, nullable=False)
    fator_diario = Column(Float)
    fator_decimal = Column(Float)
    selic = Column(Float)

class Ipca(Base):
    __tablename__ = "ipca"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mes = Column(Integer)
    ano = Column(Integer)
    indice = Column(Float)
    indice1 = Column(Float)
    __table_args__ = (UniqueConstraint('mes', 'ano', name='uq_ipca_mes_ano'),)

class Tlp(Base):
    __tablename__ = "tlp"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data = Column(Date, unique=True, index=True, nullable=False)
    mes = Column(Integer)
    ano = Column(Integer)
    taxa_aa = Column(Float)

class Umselic(Base):
    __tablename__ = "umselic"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data = Column(Date, unique=True, index=True, nullable=False)
    moeda = Column(Float)

class ContratoParam(Base):
    """Parâmetros de cada contrato, extraídos da aba individual (linhas 1-15)"""
    __tablename__ = "contrato_params"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome_aba = Column(String(255), unique=True, index=True, nullable=False)
    contrato = Column(String(255))
    modalidade = Column(String(255))
    valor_financiado = Column(Float)
    taxa_aa = Column(Float)                 # H4
    indexador_nome = Column(String(50))     # E5: NULO/CDI/TLP/IPCA/UMSELIC
    indexador_aa = Column(Float)            # H5
    sist_amort = Column(String(50))         # J5: SAC/PRICE/BULLET/SIST. AMORT.
    usa_indice = Column(String(20))         # I5: SIM/NÃO/INDEXADOR
    taxa_am = Column(Float)                 # H6
    taxa_ad = Column(Float)                 # H8
    vencimento_final = Column(Date)         # H9
    entrada_recurso = Column(Date)          # H10
    data_1o_pagam = Column(Date)            # H11
    data_pgto_1o_parc = Column(Date)        # H12
    qt_parc = Column(Integer)               # H13
    carencia = Column(Float)                # H14
    parc_anuais = Column(String(20))        # I13
    cet_aa = Column(Float)                  # J12 / V16 (XIRR)
    layout_header = Column(Integer)         # linha do cabeçalho da tabela (16/17/18)
    layout_variante = Column(String(30))    # padrao / deslocado / conversao
    status = Column(String(30), default="PENDENTE")  # OK / PARCIAL / FORA_PADRAO / DADO_FALTANTE
    status_detalhe = Column(String(255))

class EmpresaVenda(Base):
    """empresas[tFantasia] — segmentação Empresa e eixo do 'Resumo por Empresa'."""
    __tablename__ = "empresas_vendas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo = Column(Integer, unique=True, index=True, nullable=False)   # NEMPRESA
    fantasia = Column(String(255))                                      # tFantasia


class Venda(Base):
    """Vendas[NTOTAL, NFRETE, NDESCONTO, NVALORLUCRO, NEMPRESA, DDATA, NDOCUMENTO, VRQTD].

    Linha = item/venda avulsa. Documentos com soma de VRQTD <= 0 são
    devoluções/cancelamentos (excluídos de qtdVendas).
    """
    __tablename__ = "vendas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data = Column(Date, index=True)                  # DDATA
    empresa_id = Column(Integer, index=True)         # NEMPRESA
    ndocumento = Column(String(60), index=True)      # NDOCUMENTO
    vendedor_1_2 = Column(String(120))               # segmentação "Vendedor 1/2"
    vendedor = Column(String(120))                   # eixo do bookmark Vendedores
    cliente = Column(String(255))                    # eixo do bookmark Clientes
    grupo = Column(String(255))                      # eixo do bookmark Grupo
    subgrupo = Column(String(255))                   # eixo do bookmark Subgrupo
    ntotal = Column(Float)                           # NTOTAL
    nfrete = Column(Float)                           # NFRETE
    ndesconto = Column(Float)                        # NDESCONTO
    nvalorlucro = Column(Float)                      # NVALORLUCRO
    vrqtd = Column(Float)                            # VRQTD


class CalendarioDia(Base):
    """Calendario[Date, DiaUtil] — eixo temporal das segmentações e gráficos."""
    __tablename__ = "calendario"

    data = Column(Date, primary_key=True)
    diautil = Column(Integer, default=1)


class VendedorMeta(Base):
    """vendedores[CHAVE, DATA, META, NCHTIPOENTIDADE] — metas por vendedor/mês."""
    __tablename__ = "vendedores_metas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chave = Column(Integer, index=True)              # CHAVE
    data = Column(Date, index=True)                  # DATA (mês de referência)
    meta = Column(Float)                             # META
    nchtipoentidade = Column(Integer)                # NCHTIPOENTIDADE


class InadimplenciaVenda(Base):
    """inadimplencia[VALOR, STATUS.1] — VALOR com STATUS.1='VENCIDO' conta."""
    __tablename__ = "inadimplencia_vendas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data = Column(Date, index=True)
    valor = Column(Float)
    status = Column(String(60))                      # STATUS.1 ("VENCIDO", ...)


class FreteOpcao(Base):
    """Fretes[OpcaoFrete] — dimensão do segmentador Frete (Com/Sem Frete)."""
    __tablename__ = "fretes_opcoes"

    opcao = Column(String(60), primary_key=True)


class Parcela(Base):
    """Datas reais de vencimento de cada parcela, extraídas da aba de contrato.

    Usadas pelo motor de amortização para reproduzir fielmente a sequência de
    parcelas do Excel (que fixa datas de pagamento reais do negócio, não apenas
    a regra de feriados).
    """
    __tablename__ = "parcelas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome_aba = Column(String(255), index=True, nullable=False)
    numero = Column(Integer)            # número ordinal da parcela (H2/H col)
    data_vencimento = Column(Date)      # data real de vencimento (D util, coluna D)
    data_contrato = Column(Date)        # data de contrato (coluna A)
    mutuario = Column(String(20))
    is_carencia = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint('nome_aba', 'numero', name='uq_parcela_aba_num'),
    )
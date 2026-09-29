"""Dashboard GERENCIAL — aba VENDAS (Vendas por Loja).

Replicação do relatório Power BI "GERENCIAL" do Grupo Madcentro (Manual de
Migração — aba VENDAS). Todas as medidas DAX do Anexo A foram traduzidas para
SQL/SQLAlchemy mantendo as regras de negócio bit a bit:

    - somaVendasL / somaDesconto / somaLucro  => regra da empresa 21 (>= 01/06/2025)
    - somaFrete / inadimplencia               => SEM a regra da empresa 21 (assimetria do original)
    - DIVIDE(...,1)                           => fallback = 1 (100%) quando denominador = 0
    - qtdVendas                               => documentos com SUM(VRQTD) > 0
    - somaMetas                               => MAX(META) por CHAVE+DATA, exclui 383891/tipo 92
    - faturamento                             => somaVendasL + somaFrete (card usa a versão com frete)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case, extract, and_, or_
from datetime import date

from database import get_db
from utils.auth import get_current_user
from models.models import (Venda, EmpresaVenda, InadimplenciaVenda,
                           VendedorMeta, FreteOpcao)

router = APIRouter()

EMP21 = 21
EMP21_DATA = date(2025, 6, 1)   # regra: empresa 21 só conta a partir de 01/06/2025


def _filtro_tela(ano=None, mes=None, empresa=None, vendedor=None):
    """Filtros de tela (segmentações) aplicados à tabela Vendas."""
    conds = []
    if ano:
        conds.append(extract('year', Venda.data) == int(ano))
    if mes:
        conds.append(extract('month', Venda.data) == int(mes))
    if empresa:
        conds.append(EmpresaVenda.fantasia == empresa)
    if vendedor:
        conds.append(Venda.vendedor_1_2 == vendedor)
    return conds


def _emp21_ok():
    return or_(Venda.empresa_id != EMP21, Venda.data >= EMP21_DATA)


def _ntotal_emp21():
    """NTOTAL zerado quando a venda é da empresa 21 antes de 01/06/2025
    (equivale à aplicação do FILTER interno das medidas somaVendasL/desconto/lucro)."""
    return case((_emp21_ok(), Venda.ntotal), else_=0.0)


def _filtro_data(ano=None, mes=None):
    conds = []
    if ano:
        conds.append(extract('year', InadimplenciaVenda.data) == int(ano))
    if mes:
        conds.append(extract('month', InadimplenciaVenda.data) == int(mes))
    return conds


@router.get("/filtros")
def vendas_filtros(db: Session = Depends(get_db), user=Depends(get_current_user)):
    anos = [r for (r,) in db.query(extract('year', Venda.data)).distinct().order_by(extract('year', Venda.data)).all()]
    meses = [r for (r,) in db.query(extract('month', Venda.data)).distinct().order_by(extract('month', Venda.data)).all()]
    empresas = [r for (r,) in db.query(EmpresaVenda.fantasia).order_by(EmpresaVenda.fantasia).all()]
    vendedores = [r for (r,) in db.query(Venda.vendedor_1_2).filter(Venda.vendedor_1_2.isnot(None)).distinct().order_by(Venda.vendedor_1_2).all()]
    status = [r for (r,) in db.query(InadimplenciaVenda.status).distinct().order_by(InadimplenciaVenda.status).all()]
    fretes = [r for (r,) in db.query(FreteOpcao.opcao).all()]
    return {
        "anos": anos,
        "meses": meses,
        "empresas": empresas,
        "vendedores_1_2": vendedores,
        "status_inadim": status,
        "fretes": fretes,
    }


@router.get("/resumo")
def vendas_resumo(ano: int = None, mes: int = None, empresa: str = None,
                  vendedor: str = None, status: str = None, frete: str = None,
                  db: Session = Depends(get_db), user=Depends(get_current_user)):
    tela = _filtro_tela(ano, mes, empresa, vendedor)

    # ---- Medidas de base -------------------------------------------------
    soma_vendas_l = db.query(func.coalesce(func.sum(_ntotal_emp21()), 0.0)).join(
        EmpresaVenda, EmpresaVenda.codigo == Venda.empresa_id).filter(*tela).scalar() or 0.0
    # somaFrete: SEM a regra da empresa 21 (assimetria do original)
    soma_frete = db.query(func.coalesce(func.sum(Venda.nfrete), 0.0)).join(
        EmpresaVenda, EmpresaVenda.codigo == Venda.empresa_id).filter(*tela).scalar() or 0.0
    faturamento = soma_vendas_l + soma_frete

    soma_desconto = db.query(func.coalesce(func.sum(case((_emp21_ok(), Venda.ndesconto), else_=0.0)), 0.0)).join(
        EmpresaVenda, EmpresaVenda.codigo == Venda.empresa_id).filter(*tela).scalar() or 0.0
    soma_lucro = db.query(func.coalesce(func.sum(case((_emp21_ok(), Venda.nvalorlucro), else_=0.0)), 0.0)).join(
        EmpresaVenda, EmpresaVenda.codigo == Venda.empresa_id).filter(*tela).scalar() or 0.0

    # ---- Card Faturamento: somaVendasL_comFrete_calculado -----------------
    # "Com Frete" ou sem seleção => valor cheio; "Sem Frete" => NTOTAL - NFRETE
    if frete == 'Sem Frete':
        card_expr = _ntotal_emp21() - Venda.nfrete
    else:  # 'Com Frete' ou nenhuma seleção => valor cheio
        card_expr = _ntotal_emp21()
    card_fat = db.query(func.coalesce(func.sum(card_expr), 0.0)).join(
        EmpresaVenda, EmpresaVenda.codigo == Venda.empresa_id).filter(*tela).scalar() or 0.0

    # ---- qtdVendas: nº de documentos com soma de VRQTD > 0 ----------------
    qtd = db.query(
        Venda.ndocumento,
        func.sum(Venda.vrqtd).label('ql')
    ).join(EmpresaVenda, EmpresaVenda.codigo == Venda.empresa_id).filter(*tela).group_by(
        Venda.ndocumento).having(func.sum(Venda.vrqtd) > 0).all()
    qtd_vendas = len(qtd)

    ticket = (soma_vendas_l / qtd_vendas) if qtd_vendas else 0.0

    # ---- Inadimplência (SEM regra empresa 21) ------------------------------
    iq = db.query(func.coalesce(func.sum(InadimplenciaVenda.valor), 0.0))
    iq = iq.filter(InadimplenciaVenda.status == (status or 'VENCIDO'))
    iq = iq.filter(*_filtro_data(ano, mes))
    inadimplencia = iq.scalar() or 0.0

    # ---- % com DIVIDE(..., fallback 1) --------------------------------------
    def pct(n, d):
        return (n / d) if d and d != 0 else 1.0

    # ---- Resumo por Empresa (barras) ----------------------------------------
    pe = db.query(
        EmpresaVenda.fantasia.label('nome'),
        func.sum(_ntotal_emp21()).label('v'),
        func.sum(Venda.nfrete).label('f'),
    ).join(Venda, Venda.empresa_id == EmpresaVenda.codigo).filter(*tela).group_by(
        EmpresaVenda.fantasia).all()
    resumo_empresa = [{"nome": nome or 'N/D', "faturamento": float(v or 0) + float(f or 0)}
                      for nome, v, f in pe]
    resumo_empresa.sort(key=lambda x: x['faturamento'], reverse=True)

    def _por_coluna(col):
        """Bookmarks Clientes / Vendedores / Grupo / Subgrupo (valor = faturamento)."""
        rows = db.query(
            col.label('nome'),
            func.sum(_ntotal_emp21()).label('v'),
            func.sum(Venda.nfrete).label('f'),
        ).join(EmpresaVenda, EmpresaVenda.codigo == Venda.empresa_id).filter(*tela).group_by(col).all()
        return [{"nome": nome or 'N/D', "faturamento": float(v or 0) + float(f or 0)}
                for nome, v, f in rows]

    # ---- Evolução de Vendas (mensal: faturamento, metas, inadimplência) -----
    ev = db.query(
        extract('year', Venda.data).label('yy'),
        extract('month', Venda.data).label('mm'),
        func.sum(_ntotal_emp21()).label('v'),
        func.sum(Venda.nfrete).label('f'),
    ).join(EmpresaVenda, EmpresaVenda.codigo == Venda.empresa_id).filter(*tela).group_by(
        extract('year', Venda.data), extract('month', Venda.data)).order_by(
        extract('year', Venda.data), extract('month', Venda.data)).all()

    em = db.query(
        extract('year', VendedorMeta.data).label('yy'),
        extract('month', VendedorMeta.data).label('mm'),
        func.max(VendedorMeta.meta).label('m'),
    ).filter(~and_(VendedorMeta.chave == 383891, VendedorMeta.nchtipoentidade == 92)).group_by(
        extract('year', VendedorMeta.data), extract('month', VendedorMeta.data)).all()
    metas_map = {(int(y), int(m)): float(mm or 0) for y, m, mm in em}

    ei = db.query(
        extract('year', InadimplenciaVenda.data).label('yy'),
        extract('month', InadimplenciaVenda.data).label('mm'),
        func.sum(InadimplenciaVenda.valor).label('v'),
    ).filter(InadimplenciaVenda.status == 'VENCIDO').group_by(
        extract('year', InadimplenciaVenda.data), extract('month', InadimplenciaVenda.data)).all()
    inad_map = {(int(y), int(m)): float(v or 0) for y, m, v in ei}

    evolucao = []
    for y, m, v, f in ev:
        key = (int(y), int(m))
        evolucao.append({
            "mes": f"{int(y)}-{int(m):02d}",
            "faturamento": float(v or 0) + float(f or 0),
            "metas": metas_map.get(key, 0.0),
            "inadimplencia": inad_map.get(key, 0.0),
        })

    # ---- % por período (gráficos de linha) ----------------------------------
    lucro_mes = {(int(y), int(m)): float(v or 0.0) for y, m, v in db.query(
        extract('year', Venda.data).label('yy'), extract('month', Venda.data).label('mm'),
        func.sum(case((_emp21_ok(), Venda.nvalorlucro), else_=0.0)).label('v'),
    ).join(EmpresaVenda, EmpresaVenda.codigo == Venda.empresa_id).filter(*tela).group_by(
        extract('year', Venda.data), extract('month', Venda.data)
    ).all()}
    desconto_mes = {(int(y), int(m)): float(v or 0.0) for y, m, v in db.query(
        extract('year', Venda.data).label('yy'), extract('month', Venda.data).label('mm'),
        func.sum(case((_emp21_ok(), Venda.ndesconto), else_=0.0)).label('v'),
    ).join(EmpresaVenda, EmpresaVenda.codigo == Venda.empresa_id).filter(*tela).group_by(
        extract('year', Venda.data), extract('month', Venda.data)
    ).all()}

    periodo = []
    for y, m, v, f in ev:
        key = (int(y), int(m))
        fat = float(v or 0) + float(f or 0)
        periodo.append({
            "mes": f"{int(y)}-{int(m):02d}",
            "pct_lucro": pct(float(lucro_mes.get((int(y), int(m))) or 0.0), fat),
            "pct_desconto": pct(float(desconto_mes.get((int(y), int(m))) or 0.0), fat),
            "pct_inadimplencia": pct(inad_map.get(key, 0.0), fat),
        })

    return {
        "cards": {
            "faturamento_card": card_fat,
            "soma_vendas_l": soma_vendas_l,
            "soma_frete": soma_frete,
            "faturamento": faturamento,
            "desconto": soma_desconto,
            "lucro": soma_lucro,
            "qtd_vendas": qtd_vendas,
            "ticket": ticket,
            "inadimplencia": inadimplencia,
            "pct_lucro": pct(soma_lucro, faturamento),
            "pct_desconto": pct(soma_desconto, faturamento),
            "pct_inadimplencia": pct(inadimplencia, faturamento),
            "meta_lucro": 0.375,
            "meta_desconto": 0.175,
            "meta_inadimplencia": 0.01,
        },
        "resumo_empresa": resumo_empresa,
        "evolucao": evolucao,
        "clientes": _por_coluna(Venda.cliente),
        "vendedores": _por_coluna(Venda.vendedor),
        "grupo": _por_coluna(Venda.grupo),
        "subgrupo": _por_coluna(Venda.subgrupo),
        "periodo": periodo,
    }
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from models.models import Contrato, ContratoParam, CdiDiario, Ipca
from utils.auth import get_db, get_current_user
from engine.amortizacao import AmortizacaoEngine, _add_months, _eom
from datetime import date

router = APIRouter()

# ---------------------------------------------------------------
# Evolução do endividamento (recalculada pelo motor) + indexadores
# Inspiradas nos relatórios "Evolução/Evolucao_*" e no cadastro de
# séries (CDI/IPCA/SELIC) do sistema legado.
# ---------------------------------------------------------------

_EVOL_CACHE = {"ts": 0.0, "tabelas": {}, "tentados": 0, "cobertos": 0, "erros": []}
_EVOL_TTL = 300  # segundos

def _cache_tabelas_motor(db):
    """Executa o motor uma vez por contrato coberto (OK/PARCIAL) e
    guarda as tabelas completas por TTL — o saldo em qualquer data base
    é amostrado da tabela (o motor já recalcula a tabela inteira)."""
    import time
    now = time.time()
    if _EVOL_CACHE["ts"] and now - _EVOL_CACHE["ts"] < _EVOL_TTL:
        return _EVOL_CACHE

    eng = AmortizacaoEngine(db)
    params = (db.query(ContratoParam)
              .filter(ContratoParam.status.in_(["OK", "PARCIAL"]))
              .all())
    tabelas = {}
    tentados = 0
    cobertos = 0
    erros = []
    for p in params:
        tentados += 1
        try:
            r = eng.calcular(p.nome_aba, date.today())
            tabelas[p.nome_aba] = r["tabela"]
            cobertos += 1
        except Exception as e:  # não derruba a evolução por 1 contrato
            erros.append(f"{p.nome_aba}: {e}")

    _EVOL_CACHE.update({
        "ts": now, "tabelas": tabelas, "tentados": tentados,
        "cobertos": cobertos, "erros": erros,
    })
    return _EVOL_CACHE


def _amostrar(linhas, d):
    """Última linha com data_util <= d (snapshot de saldo/cp/lp na data)."""
    out = None
    for L in linhas:
        du = L.get("data_util")
        if isinstance(du, date) and du <= d:
            out = L
        else:
            break
    return out


def _grade_datas(hoje, meses_passado, meses_futuro):
    ref = date(hoje.year, hoje.month, 1)
    out = []
    for k in range(-meses_passado, meses_futuro + 1):
        out.append(_eom(_add_months(ref, k)))
    return out

@router.get("/resumo")
def resumo(
    data_base: str = Query(None, description="Filtrar por data base (YYYY-MM-DD)"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna KPIs e dados agregados para o dashboard"""
    query = db.query(Contrato)
    if data_base:
        query = query.filter(Contrato.data_base == date.fromisoformat(data_base))

    contratos = query.all()

    if not contratos:
        return {"contratos": [], "total_contratos": 0, "total_contratado": 0,
                "total_curto_prazo": 0, "total_longo_prazo": 0, "total_pg": 0,
                "data_base": data_base}

    total_contratado = sum(c.contratado or 0 for c in contratos)
    total_curto = sum(c.curto_prazo or 0 for c in contratos)
    total_longo = sum(c.longo_prazo or 0 for c in contratos)
    total_pg = sum(c.total_pg or 0 for c in contratos)

    # Por instituição
    por_instituicao = {}
    for c in contratos:
        if c.instituicao not in por_instituicao:
            por_instituicao[c.instituicao] = {"contratado": 0, "saldo": 0, "curto": 0, "longo": 0}
        por_instituicao[c.instituicao]["contratado"] += c.contratado or 0
        por_instituicao[c.instituicao]["saldo"] += c.total_pg or 0
        por_instituicao[c.instituicao]["curto"] += c.curto_prazo or 0
        por_instituicao[c.instituicao]["longo"] += c.longo_prazo or 0

    # Por modalidade
    por_modalidade = {}
    for c in contratos:
        if c.modalidade not in por_modalidade:
            por_modalidade[c.modalidade] = {"contratado": 0, "saldo": 0, "curto": 0, "longo": 0}
        por_modalidade[c.modalidade]["contratado"] += c.contratado or 0
        por_modalidade[c.modalidade]["saldo"] += c.total_pg or 0
        por_modalidade[c.modalidade]["curto"] += c.curto_prazo or 0
        por_modalidade[c.modalidade]["longo"] += c.longo_prazo or 0

    # Por empresa
    por_empresa = {}
    for c in contratos:
        if c.empresa not in por_empresa:
            por_empresa[c.empresa] = {"contratado": 0, "saldo": 0}
        por_empresa[c.empresa]["contratado"] += c.contratado or 0
        por_empresa[c.empresa]["saldo"] += c.total_pg or 0

    # Por índice
    por_indice = {}
    for c in contratos:
        idx = c.indice or "N/D"
        if idx not in por_indice:
            por_indice[idx] = {"contratado": 0, "saldo": 0}
        por_indice[idx]["contratado"] += c.contratado or 0
        por_indice[idx]["saldo"] += c.total_pg or 0

    # Vencimentos por ano
    por_ano_venc = {}
    for c in contratos:
        if c.final:
            ano = c.final.year
            if ano not in por_ano_venc:
                por_ano_venc[ano] = {"saldo": 0, "qtd": 0}
            por_ano_venc[ano]["saldo"] += c.longo_prazo or 0
            por_ano_venc[ano]["qtd"] += 1

    # Garantias
    por_garantia = {}
    for c in contratos:
        g = c.modalidade2 or "N/D"
        key = g.strip()
        if key not in por_garantia:
            por_garantia[key] = {"contratado": 0, "qtd": 0}
        por_garantia[key]["contratado"] += c.contratado or 0
        por_garantia[key]["qtd"] += 1

    return {
        "data_base": data_base or [c.data_base for c in contratos if c.data_base],
        "total_contratos": len(contratos),
        "total_contratado": total_contratado,
        "total_curto_prazo": total_curto,
        "total_longo_prazo": total_longo,
        "total_pg": total_pg,
        "por_instituicao": por_instituicao,
        "por_modalidade": por_modalidade,
        "por_empresa": por_empresa,
        "por_indice": por_indice,
        "por_ano_venc": por_ano_venc,
        "por_garantia": por_garantia,
    }

@router.get("/detalhes")
def detalhes(user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Lista completa de contratos para a tabela do dashboard"""
    contratos = db.query(Contrato).all()
    return [{
        "data_base": c.data_base.isoformat() if c.data_base else None,
        "numero_contrato": c.numero_contrato,
        "instituicao": c.instituicao,
        "empresa": c.empresa,
        "modalidade": c.modalidade,
        "contratado": c.contratado,
        "curto_prazo": c.curto_prazo,
        "longo_prazo": c.longo_prazo,
        "total_pg": c.total_pg,
        "perc_rest": c.perc_rest,
        "final": c.final.isoformat() if c.final else None,
        "indice": c.indice,
        "modalidade2": c.modalidade2,
    } for c in contratos]

@router.get("/datas-base")
def datas_base(user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Retorna todas as datas base disponíveis"""
    datas = db.query(Contrato.data_base).distinct().order_by(desc(Contrato.data_base)).all()
    return {"datas": [d[0].isoformat() for d in datas if d[0]]}

@router.get("/filtros")
def filtros(user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Retorna instituições, modalidades e empresas disponíveis para filtros"""
    instituicoes = db.query(Contrato.instituicao).distinct().order_by(Contrato.instituicao).all()
    modalidades = db.query(Contrato.modalidade).distinct().order_by(Contrato.modalidade).all()
    empresas = db.query(Contrato.empresa).distinct().order_by(Contrato.empresa).all()
    indices = db.query(Contrato.indice).distinct().order_by(Contrato.indice).all()

    return {
        "instituicoes": [i[0] for i in instituicoes if i[0]],
        "modalidades": [m[0] for m in modalidades if m[0]],
        "empresas": [e[0] for e in empresas if e[0]],
        "indices": [x[0] for x in indices if x[0]],
    }


@router.get("/evolucao")
def evolucao(
    meses_passado: int = Query(24, ge=1, le=60),
    meses_futuro: int = Query(24, ge=0, le=60),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Curva de evolução do endividamento (saldo, curto e longo prazo)
    amostrada em cada fim de mês via motor de amortização — equivalente
    aos relatórios Evolução/Resumo do sistema legado."""
    cache = _cache_tabelas_motor(db)
    datas = _grade_datas(date.today(), meses_passado, meses_futuro)

    series = []
    for d in datas:
        saldo = cp = lp = 0.0
        for linhas in cache["tabelas"].values():
            L = _amostrar(linhas, d)
            if L is None:
                continue
            saldo += L.get("saldo") or 0.0
            cp += L.get("cp") or 0.0
            lp += L.get("lp") or 0.0
        series.append({
            "data": d.isoformat(),
            "saldo": round(saldo, 2),
            "curto": round(cp, 2),
            "longo": round(lp, 2),
        })

    # Benchmark: snapshot completo (todos os contratos) na maior data base do Excel
    benchmark = None
    bd = (db.query(Contrato.data_base)
          .filter(Contrato.data_base.isnot(None))
          .order_by(Contrato.data_base.desc())
          .first())
    if bd and bd[0]:
        bdata = bd[0]
        rows = db.query(Contrato).filter(Contrato.data_base == bdata).all()
        benchmark = {
            "data": bdata.isoformat(),
            "n": len(rows),
            "saldo": round(sum(c.total_pg or 0 for c in rows), 2),
            "curto": round(sum(c.curto_prazo or 0 for c in rows), 2),
            "longo": round(sum(c.longo_prazo or 0 for c in rows), 2),
        }

    return {
        "series": series,
        "cobertura": cache["cobertos"],
        "tentados": cache["tentados"],
        "erros": cache["erros"][:5],
        "benchmark": benchmark,
    }


@router.get("/indexadores")
def indexadores(
    meses: int = Query(24, ge=1, le=120),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Séries mensais CDI (fator acumulado do mês) e IPCA — espelha o cadastro
    de indexadores que o legado mantinha para correção dos contratos."""
    diarios = db.query(CdiDiario.data, CdiDiario.fator_decimal).all()
    prod = {}
    for d, fd in diarios:
        if fd is None or d is None:
            continue
        y, m = d.year, d.month
        p = prod.get((y, m))
        if p is None:
            prod[(y, m)] = (1.0 + fd)
        else:
            prod[(y, m)] = p * (1.0 + fd)

    ips = {}
    for i in db.query(Ipca).all():
        if i.mes and i.ano:
            ips[(i.ano, i.mes)] = i.indice1

    selic_aa = None
    ultima_selic = (db.query(CdiDiario.selic)
                    .order_by(CdiDiario.data.desc())
                    .first())
    if ultima_selic and ultima_selic[0] is not None:
        selic_aa = round(ultima_selic[0], 4)

    hoje = date.today()
    ref = date(hoje.year, hoje.month, 1)
    out = []
    for k in range(1 - meses, 1):
        d = _add_months(ref, k)
        y, m = d.year, d.month
        pr = prod.get((y, m))
        cdi_pct = round((pr - 1.0) * 100, 3) if pr else None
        ipca_pct = round(ips[(y, m)], 3) if ips.get((y, m)) is not None else None
        if cdi_pct is None and ipca_pct is None:
            continue
        out.append({
            "mes": f"{y:04d}-{m:02d}",
            "cdi": cdi_pct,
            "ipca": ipca_pct,
        })

    return {
        "series": out,
        "selic_aa": selic_aa,
        "unidade": "% ao mês",
    }
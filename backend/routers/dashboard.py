from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from models.models import Contrato
from utils.auth import get_db, get_current_user
from datetime import date

router = APIRouter()

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
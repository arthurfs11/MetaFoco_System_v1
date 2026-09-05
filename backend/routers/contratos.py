from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from typing import Optional
from models.models import Contrato, ContratoParam
from utils.auth import get_db, get_current_user, require_gestor
import uuid
from datetime import date, datetime

from engine.amortizacao import AmortizacaoEngine

router = APIRouter()

class ContratoCreate(BaseModel):
    data_base: Optional[date] = None
    instituicao: str
    empresa: Optional[str] = None
    modalidade: Optional[str] = None
    numero_contrato: str
    parcela: Optional[int] = None
    periodo: Optional[str] = None
    pgto: Optional[str] = None
    emissao: Optional[date] = None
    inicial: Optional[date] = None
    final: Optional[date] = None
    contratado: Optional[float] = None
    curto_prazo: Optional[float] = None
    longo_prazo: Optional[float] = None
    total_pg: Optional[float] = None
    perc_rest: Optional[float] = None
    parc_pg: Optional[float] = None
    prestacao: Optional[float] = None
    juros: Optional[float] = None
    amortiz: Optional[float] = None
    am: Optional[float] = None
    aa: Optional[float] = None
    am2: Optional[float] = None
    aa2: Optional[float] = None
    indice: Optional[str] = None
    modalidade2: Optional[str] = None
    perc_gar: Optional[float] = None
    obs_cet: Optional[str] = None
    resumo_garantias: Optional[str] = None

@router.post("/")
def criar_contrato(contrato: ContratoCreate, user=Depends(require_gestor), db: Session = Depends(get_db)):
    if not contrato.data_base:
        contrato.data_base = date.today()
    
    # Verificar duplicação
    exists = db.query(Contrato).filter(
        Contrato.numero_contrato == contrato.numero_contrato,
        Contrato.instituicao == contrato.instituicao,
        Contrato.parcela == contrato.parcela,
        Contrato.data_base == contrato.data_base
    ).first()
    if exists:
        raise HTTPException(status_code=409, detail="Este contrato já existe no banco de dados")

    novo = Contrato(**contrato.model_dump(), fonte="manual")
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return {"id": str(novo.id), "mensagem": "Contrato cadastrado com sucesso"}

@router.get("/")
def listar_contratos(
    instituicao: Optional[str] = None,
    empresa: Optional[str] = None,
    modalidade: Optional[str] = None,
    search: Optional[str] = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Contrato)
    if instituicao:
        query = query.filter(Contrato.instituicao == instituicao)
    if empresa:
        query = query.filter(Contrato.empresa == empresa)
    if modalidade:
        query = query.filter(Contrato.modalidade == modalidade)
    if search:
        query = query.filter(
            or_(
                Contrato.numero_contrato.ilike(f"%{search}%"),
                Contrato.instituicao.ilike(f"%{search}%"),
                Contrato.empresa.ilike(f"%{search}%"),
                Contrato.modalidade.ilike(f"%{search}%"),
            )
        )
    contratos = query.all()
    params = {p.contrato: p.status for p in db.query(ContratoParam).all() if p.contrato}
    return [ser_contrato(c, params.get(c.numero_contrato)) for c in contratos]

@router.get("/{contrato_id}")
def get_contrato(contrato_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.query(Contrato).filter(Contrato.id == uuid.UUID(contrato_id)).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    return ser_contrato(c)

@router.get("/{contrato_id}/detalhe")
def detalhe_contrato(contrato_id: str, data_base: str = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.query(Contrato).filter(Contrato.id == uuid.UUID(contrato_id)).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    resp = ser_contrato(c)

    # Vínculo com o motor de amortização via numero_contrato == contrato (aba)
    cp = db.query(ContratoParam).filter(ContratoParam.contrato == c.numero_contrato).first()
    resp["motor"] = _ser_param(cp) if cp else None

    if not cp:
        resp["extrato"] = None
        resp["resumo"] = {
            "origem": "cadastro",
            "financiado": c.contratado,
            "saldo_hoje": (c.curto_prazo or 0) + (c.longo_prazo or 0) if (c.curto_prazo or c.longo_prazo) else None,
            "cp": c.curto_prazo,
            "lp": c.longo_prazo,
            "total_pg": c.total_pg,
            "prestacao": c.prestacao,
            "juros": c.juros,
            "parc_pg": c.parc_pg,
            "perc_rest": c.perc_rest,
        }
        return resp

    db_base = date.fromisoformat(data_base) if data_base else date.today()
    try:
        eng = AmortizacaoEngine(db)
        r = eng.calcular(cp.nome_aba, db_base)
    except Exception as e:
        resp["extrato"] = None
        resp["erro_motor"] = str(e)
        resp["resumo"] = {"origem": "cadastro", "financiado": c.contratado,
                          "total_pg": c.total_pg, "prestacao": c.prestacao,
                          "juros": c.juros, "cp": c.curto_prazo, "lp": c.longo_prazo}
        return resp

    tabela = [ser_linha(L) for L in r["tabela"]]
    linha = ser_linha(r["linha"]) if r.get("linha") else None

    def p_or_none(_d):
        return None if _d is None else _d

    # Resumo financeiro a partir do extrato
    parc_futuras = [L for L in tabela
                    if L.get("tipo") == "PARC"
                    and L.get("data_util") is not None
                    and date.fromisoformat(L["data_util"]) > db_base]
    parc_passadas = [L for L in tabela
                     if L.get("tipo") == "PARC"
                     and L.get("data_util") is not None
                     and date.fromisoformat(L["data_util"]) <= db_base]

    prox = parc_futuras[0] if parc_futuras else None
    resp["resumo"] = {
        "origem": "motor",
        "data_base": db_base.isoformat(),
        "financiado": r.get("valor_financiado"),
        "taxa_aa": r.get("taxa_aa"),
        "sist_amort": r.get("sist_amort"),
        "indexador": r.get("indexador"),
        "saldo_hoje": linha.get("saldo") if linha else None,
        "cp": linha.get("cp") if linha else None,
        "lp": linha.get("lp") if linha else None,
        "amortizado_ate": round(sum(L.get("amortizacao") or 0 for L in parc_passadas), 2),
        "total_a_pagar": round(sum(L.get("prestacao") or 0 for L in parc_futuras), 2),
        "encargos_a_incorrer": round(sum((L.get("juros") or 0) + (L.get("indice_periodo") or 0) for L in parc_futuras), 2),
        "amortizacao_a_incorrer": round(sum(L.get("amortizacao") or 0 for L in parc_futuras), 2),
        "parc_restantes": len(parc_futuras),
        "parc_pagas": sum(1 for L in tabela if L.get("tipo") == "PARC" and L.get("data_util") is not None and date.fromisoformat(L["data_util"]) <= db_base),
        "proxima_prest": prox.get("prestacao") if prox else None,
        "proxima_juros": prox.get("juros") if prox else None,
        "proxima_amort": prox.get("amortizacao") if prox else None,
        "proxima_data": prox.get("data_util") if prox else None,
    }
    resp["extrato"] = tabela
    resp["linha"] = linha
    return resp


def ser_linha(L):
    return {
        "data_util": L["data_util"].isoformat() if isinstance(L.get("data_util"), date) else L.get("data_util"),
        "tipo": L.get("tipo"),
        "parcela_n": L.get("parcela_n"),
        "juros": round(L.get("juros", 0), 2),
        "indice_periodo": round(L.get("indice_periodo", 0), 2),
        "prestacao": round(L.get("prestacao", 0), 2),
        "amortizacao": round(L.get("amortizacao", 0), 2),
        "saldo": round(L.get("saldo", 0), 2),
        "cp": round(L.get("cp", 0), 2),
        "lp": round(L.get("lp", 0), 2),
        "dias": L.get("dias"),
    }


def _ser_param(cp):
    if cp is None:
        return None
    return {
        "nome_aba": cp.nome_aba,
        "contrato": cp.contrato,
        "modalidade": cp.modalidade,
        "valor_financiado": cp.valor_financiado,
        "taxa_aa": cp.taxa_aa,
        "taxa_am": cp.taxa_am,
        "indexador": cp.indexador_nome,
        "indexador_aa": cp.indexador_aa,
        "sist_amort": cp.sist_amort,
        "usa_indice": cp.usa_indice,
        "qt_parc": cp.qt_parc,
        "carencia": cp.carencia,
        "parc_anuais": cp.parc_anuais,
        "vencimento_final": cp.vencimento_final.isoformat() if cp.vencimento_final else None,
        "entrada_recurso": cp.entrada_recurso.isoformat() if cp.entrada_recurso else None,
        "status": cp.status,
        "status_detalhe": cp.status_detalhe,
    }


@router.put("/{contrato_id}")
def editar_contrato(contrato_id: str, contrato: ContratoCreate, user=Depends(require_gestor), db: Session = Depends(get_db)):
    c = db.query(Contrato).filter(Contrato.id == uuid.UUID(contrato_id)).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    for field, value in contrato.model_dump().items():
        setattr(c, field, value)
    db.commit()
    return {"ok": True}

@router.delete("/{contrato_id}")
def deletar_contrato(contrato_id: str, user=Depends(require_gestor), db: Session = Depends(get_db)):
    c = db.query(Contrato).filter(Contrato.id == uuid.UUID(contrato_id)).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    db.delete(c)
    db.commit()
    return {"ok": True}

def ser_contrato(c, motor_status=None):
    return {
        "id": str(c.id),
        "motor_status": motor_status,
        "data_base": c.data_base.isoformat() if c.data_base else None,
        "instituicao": c.instituicao,
        "empresa": c.empresa,
        "modalidade": c.modalidade,
        "numero_contrato": c.numero_contrato,
        "parcela": c.parcela,
        "periodo": c.periodo,
        "pgto": c.pgto,
        "emissao": c.emissao.isoformat() if c.emissao else None,
        "inicial": c.inicial.isoformat() if c.inicial else None,
        "final": c.final.isoformat() if c.final else None,
        "contratado": c.contratado,
        "curto_prazo": c.curto_prazo,
        "longo_prazo": c.longo_prazo,
        "total_pg": c.total_pg,
        "perc_rest": c.perc_rest,
        "parc_pg": c.parc_pg,
        "prestacao": c.prestacao,
        "juros": c.juros,
        "amortiz": c.amortiz,
        "am": c.am,
        "aa": c.aa,
        "am2": c.am2,
        "aa2": c.aa2,
        "indice": c.indice,
        "modalidade2": c.modalidade2,
        "perc_gar": c.perc_gar,
        "obs_cet": c.obs_cet,
        "resumo_garantias": c.resumo_garantias,
        "fonte": c.fonte,
    }
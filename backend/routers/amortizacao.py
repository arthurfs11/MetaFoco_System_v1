"""Endpoints do motor de amortização.

- GET /api/amortizacao/contratos     -> lista de contratos (ContratoParam) com status do motor
- GET /api/amortizacao/{aba}         -> tabela de amortização recalculada para um contrato
- GET /api/amortizacao/{aba}/status  -> apenas o status/classificação do contrato
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date

from models.models import ContratoParam
from utils.auth import get_db, get_current_user
from engine.amortizacao import AmortizacaoEngine

router = APIRouter()


def _ser_param(c):
    return {
        "nome_aba": c.nome_aba,
        "contrato": c.contrato,
        "modalidade": c.modalidade,
        "valor_financiado": c.valor_financiado,
        "taxa_aa": c.taxa_aa,
        "indexador": c.indexador_nome,
        "sist_amort": c.sist_amort,
        "usa_indice": c.usa_indice,
        "qt_parc": c.qt_parc,
        "carencia": c.carencia,
        "parc_anuais": c.parc_anuais,
        "vencimento_final": c.vencimento_final.isoformat() if c.vencimento_final else None,
        "status": c.status,
        "status_detalhe": c.status_detalhe,
    }


@router.get("/contratos")
def listar_contratos_motor(
    status: str = Query(None, description="Filtrar por status do motor"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(ContratoParam)
    if status:
        q = q.filter(ContratoParam.status == status.upper())
    return [_ser_param(c) for c in q.order_by(ContratoParam.nome_aba).all()]


@router.get("/{aba}/status")
def contrato_motor_status(aba: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.query(ContratoParam).filter(ContratoParam.nome_aba == aba).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contrato não encontrado no motor")
    return _ser_param(c)


@router.get("/{aba}")
def amortizacao(aba: str, data_base: str = Query(None), user=Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.query(ContratoParam).filter(ContratoParam.nome_aba == aba).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contrato não encontrado no motor")

    db_base = date.fromisoformat(data_base) if data_base else date.today()
    try:
        eng = AmortizacaoEngine(db)
        r = eng.calcular(aba, db_base)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Erro no cálculo: {str(e)}")

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

    linha = None
    if r.get("linha"):
        linha = ser_linha(r["linha"])

    return {
        "contrato": aba,
        "sist_amort": r.get("sist_amort"),
        "indexador": r.get("indexador"),
        "valor_financiado": r.get("valor_financiado"),
        "taxa_aa": r.get("taxa_aa"),
        "data_base": r.get("data_base").isoformat() if isinstance(r.get("data_base"), date) else r.get("data_base"),
        "status": c.status,
        "status_detalhe": c.status_detalhe,
        "linha": linha,
        "tabela": [ser_linha(L) for L in r["tabela"]],
    }

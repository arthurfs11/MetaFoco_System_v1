"""Importa as datas reais de vencimento de cada parcela (colunas D/G/H) das
abas de contrato da planilha para a tabela `parcelas`.

O Excel fixa as DATAS REAIS de pagamento das parcelas (nem sempre deriváveis
da regra de feriados — o negócio/banco agenda datas específicas). O motor de
amortização usa essas datas para recalcular o saldo com fidelidade.

Uso:
    python -m engine.importar_parcelas <caminho_planilha>
"""
import sys
import os
import openpyxl
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.models import Parcela
from engine.importar_referencia import detectar_aba_contrato, detectar_layout


def _to_date(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return None


def vG_numero(ws, r, ordem):
    """Fallback para número da parcela quando a coluna H não tem números.
    Usa a coluna O (15) 'x/y' ou o ordinal."""
    vO = ws.cell(row=r, column=15).value
    if isinstance(vO, (int, float)) and vO > 0:
        return int(vO)
    return ordem + 1


def extrair_parcelas(ws, nome_aba):
    """Itera a tabela de amortização e coleta as linhas de parcela.

    Retorna lista de (numero, data_vencimento, data_contrato, mutuario).
    A linha de parcela é identificada pela coluna H (número da parcela)
    preenchida; a data de vencimento real é a coluna D (data útil).
    """
    hdr = detectar_layout(ws)
    if hdr is None:
        return []

    parcelas = []
    # percorre até linha 320 (ou vazia por várias linhas)
    for r in range(hdr + 1, 320):
        vA = ws.cell(row=r, column=1).value   # data contrato
        vD = ws.cell(row=r, column=4).value   # data útil (vencimento real)
        vG = ws.cell(row=r, column=7).value   # ID / mutuário
        vH = ws.cell(row=r, column=8).value   # número da parcela

        # linha vazia (A e D vazios) por MUITO tempo => fim
        if vA is None and vD is None and vG is None and vH is None:
            if len(parcelas) > 0:
                break
            continue

        g_up = str(vG).strip().upper() if vG is not None else ""

        # CRITÉRIO: linha de parcela real = amortização M>0 (col 13). Identifica as
        # parcelas de amortização com exatidão (bate com qt_parc) e descarta as linhas
        # de EOM/entrada (que têm M=0/vazio). Válido p/ SAC/PRICE/BULLET e quinzenais.
        vL = ws.cell(row=r, column=12).value
        vM = ws.cell(row=r, column=13).value
        m_amort = isinstance(vM, (int, float)) and vM > 0
        # carência: linha de juros puro (G=J/I) com prestação>0 e sem amortização
        car = g_up in ("J", "I") and not m_amort and isinstance(vL, (int, float)) and vL > 0
        is_parc = m_amort or car

        dD = _to_date(vD)
        if not is_parc or dD is None:
            continue

        numero = len(parcelas) + 1
        parcelas.append({
            "numero": numero,
            "data_vencimento": dD,
            "data_contrato": _to_date(vA),
            "mutuario": str(vG) if vG is not None else (("J" if car else ("P" if m_amort else "J"))),
            "is_carencia": car,
        })
    # ordena por número e remove duplicatas por número
    vistos = set()
    parcelas_unicas = []
    for x in sorted(parcelas, key=lambda k: k["numero"]):
        n = x["numero"]
        if n in vistos:
            continue
        vistos.add(n)
        parcelas_unicas.append(x)
    return parcelas_unicas


def main(caminho):
    wb = openpyxl.load_workbook(caminho, data_only=True, keep_vba=True)
    session = SessionLocal()

    # limpa parcelas já importadas (idempotente)
    session.query(Parcela).delete()

    n_total = 0
    n_nao_contrato = 0
    for nome in wb.sheetnames:
        ws = wb[nome]
        try:
            if not detectar_aba_contrato(ws):
                n_nao_contrato += 1
                continue
        except Exception:
            continue
        try:
            parcelas = extrair_parcelas(ws, nome)
            for pp in parcelas:
                session.add(Parcela(
                    nome_aba=nome,
                    numero=pp["numero"],
                    data_vencimento=pp["data_vencimento"],
                    data_contrato=pp["data_contrato"],
                    mutuario=pp["mutuario"],
                    is_carencia=pp.get("is_carencia", False),
                ))
            n_total += len(parcelas)
        except Exception as e:
            print(f"  erro em {nome}: {e}")

    session.commit()
    print(f"Parcelas importadas: {n_total} (abas não-contrato: {n_nao_contrato})")
    session.close()


if __name__ == "__main__":
    main(sys.argv[1])

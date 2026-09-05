"""Classifica os contratos quanto à fidelidade do motor de amortização.

Roda o motor para cada contrato e, verificando se a soma das amortizações
reproduz o valor financiado (e outros critérios), atribui um status:

- OK               : amortização fecha com o financiado (motor reproduz o contrato)
- PARCIAL          : amortização próxima, mas incompleta (ex. parcela final ausente)
- FORA_PADRAO      : estrutura que o motor ainda não cobre (cadência quinzenal,
                     amortização não-constante, PRICE/colunas custom)
- DADO_FALTANTE    : planilha-fonte não tem parcelas capturáveis

Uso:
    python -m engine.classificar_contratos
"""
import sys
from datetime import date

from sqlalchemy import update

sys.path.insert(0, ".")
from database import SessionLocal
from models.models import ContratoParam, Parcela
from engine.amortizacao import AmortizacaoEngine


def _cadencia(datas):
    """Mediana das diferenças (em dias) entre datas de vencimento consecutivas."""
    if len(datas) < 2:
        return None
    ds = sorted(datas)
    diffs = sorted((b - a).days for a, b in zip(ds, ds[1:]))
    return diffs[len(diffs) // 2]


def classificar(eng, session, c):
    aba = c.nome_aba
    fin = c.valor_financiado or 0.0
    ps = [p for p in session.query(Parcela)
          .filter(Parcela.nome_aba == aba).all() if p.data_vencimento]
    cad = _cadencia([p.data_vencimento for p in ps])

    # apenas avalia com motor se há parcelas e financiado > 0
    if fin <= 0 or not ps:
        return "DADO_FALTANTE", f"sem parcelas ({len(ps)}) ou financiado=0"

    try:
        r = eng.calcular(aba, date(2035, 1, 1))
        tabela = r["tabela"]
    except Exception as e:
        return "FORA_PADRAO", f"erro no motor: {str(e)[:80]}"

    tot_am = sum(L["amortizacao"] for L in tabela)
    n_parc_motor = sum(1 for L in tabela if L.get("tipo") == "PARC" or L.get("amortizacao", 0) > 0)
    dif = fin - tot_am
    rel = abs(dif) / fin if fin else 1.0

    sist = (c.sist_amort or "").upper()
    # BULLET e SAC anuais devem fechar exato; mensais idem
    if rel < 0.001:
        detalhe = f"amort {tot_am:,.2f}/{fin:,.2f}; {n_parc_motor} parcs; cad {cad}d"
        return "OK", detalhe
    if rel < 0.05:
        detalhe = (f"amort {tot_am:,.2f}/{fin:,.2f} (dif {dif:,.2f}); "
                   f"{n_parc_motor} parcs; cad {cad}d")
        return "PARCIAL", detalhe

    # fora do padrão
    motivo = f"amort {tot_am:,.2f}/{fin:,.2f} (dif {dif:,.2f})"
    if cad is not None and cad <= 18:
        motivo += "; cadência quinzenal (cobrir modo quinzenal)"
    if sist == "PRICE":
        motivo += "; PRICE (prestação não-constante)"
    if c.parc_anuais:
        motivo += "; parcelas anuais"
    return "FORA_PADRAO", f"{motivo}; {n_parc_motor} parcs"


def main():
    session = SessionLocal()
    eng = AmortizacaoEngine(session)
    contratos = session.query(ContratoParam).all()

    resumo = {}
    for c in contratos:
        status, detalhe = classificar(eng, session, c)
        session.execute(
            update(ContratoParam)
            .where(ContratoParam.nome_aba == c.nome_aba)
            .values(status=status, status_detalhe=detalhe)
        )
        resumo.setdefault(status, []).append(c.nome_aba)
        print(f"  {c.nome_aba:18} {status:14} {detalhe}")

    session.commit()
    print("\n=== Resumo ===")
    for st, abas in resumo.items():
        print(f"  {st}: {len(abas)}")


if __name__ == "__main__":
    main()

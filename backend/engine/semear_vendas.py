"""Semeadura da aba VENDAS com dados de VALIDAÇÃO.

Gera dados sintéticos que reproduzem EXATAMENTE os valores de referência da
Seção 6 do Manual de Migração (aba VENDAS, filtro Data=2026, demais "Todos"):

    Faturamento (card)    9.235.468        Vendas (qtd.)   7.468
    Desconto              3.219.257        Ticket médio    1.237
    Lucro                 3.293.654        Inadimplência   55.879
    Sorocaba              5.427.561        Itu             2.079.852
    Jundiaí               1.579.656        Ipanema         228.665
    Soma das 4 barras     9.315.734  (dif. do card = 80.266 de frete, intencional)

Também exercita as regras de negócio: empresa 21 (E-COMMERCE) só conta a partir
de 01/06/2025 (linhas anteriores ficam fora), vendedor CHAVE 383891 / tipo 92
excluído das metas, e documentos com VRQTD <= 0 excluídos da contagem.

Uso:
    python -m engine.semear_vendas
"""
import os
import sys
import random
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.models import (Venda, EmpresaVenda, CalendarioDia, VendedorMeta,
                           InadimplenciaVenda, FreteOpcao)

rng = random.Random(20260928)

EMP21 = 21

# (codigo, fantasia, faturamento_barra) — Seção 6 do manual
STORES = [
    (1, "MADCENTRO SOROCABA", 5427561),
    (2, "MADCENTRO ITU", 2079852),
    (3, "MADCENTRO JUNDIAÍ", 1579656),
    (10, "FILIAL IPANEMA", 228665),
]

TOT_FAT = sum(f for _, _, f in STORES)        # 9.315.734
TOT_FRETE = 80266
TOT_NTOTAL = 9235468                          # card Faturamento (sem frete)
TOT_DESCONTO = 3219257
TOT_LUCRO = 3293654
TOT_QTD = 7468
TOT_INADIM_VENCIDO = 55879

GRUPOS = ["SALA DE ESTAR", "DORMITÓRIO", "COZINHA", "ESCRITÓRIO", "JANTAR"]
SUBGRUPOS = ["SOFÁ", "CAMA", "MESA", "GUARDAROUPA", "CADEIRA", "ESTANTE"]
EQUIPES = [("JOÃO", "EQUIPE A"), ("MARIA", "EQUIPE A"), ("PEDRO", "EQUIPE B"),
           ("ANA", "EQUIPE B"), ("CARLOS", "EQUIPE C"), ("LÚCIA", "EQUIPE C"),
           ("RAFAEL", "EQUIPE D"), ("BEATRIZ", "EQUIPE D")]
MESES_REF = [5, 6, 7, 8, 9, 10, 11, 12]


def allocate(total, weights):
    """Divide `total` (int) proporcionalmente aos pesos, com soma EXATA."""
    n = len(weights)
    s = sum(weights) or 1
    vals = [int(total * w / s) for w in weights]
    diff = total - sum(vals)
    i = 0
    while diff != 0:
        step = 1 if diff > 0 else -1
        vals[i % n] += step
        diff -= step
        i += 1
    return vals


def distribuir(total, n, jitter=(0.4, 1.6)):
    """Gera `n` inteiros >= 0 somando exatamente `total` (com variação)."""
    if n <= 0:
        return []
    w = [rng.uniform(*jitter) for _ in range(n)]
    s = sum(w)
    vals = [int(total * x / s) for x in w]
    diff = total - sum(vals)
    i = 0
    while diff != 0 and i < n + 200:
        step = 1 if diff > 0 else -1
        vals[i % n] = max(0, vals[i % n] + step)
        if vals[i % n] == 0 and step == -1:
            i += 1
            continue
        diff -= step
        i += 1
    # garante soma exata (ajuste final no último item)
    if sum(vals) != total:
        vals[-1] += total - sum(vals)
    return vals


def semear():
    db = SessionLocal()
    try:
        db.query(Venda).delete()
        db.query(EmpresaVenda).delete()
        db.query(VendedorMeta).delete()
        db.query(InadimplenciaVenda).delete()
        db.query(CalendarioDia).delete()
        db.query(FreteOpcao).delete()
        db.commit()

        # ---- Fretes (dimensão do segmentador) --------------------------------
        db.add_all([FreteOpcao(opcao="Com Frete"), FreteOpcao(opcao="Sem Frete")])

        # ---- Calendário 2025-2027 -------------------------------------------
        d = date(2025, 1, 1)
        while d <= date(2027, 12, 31):
            db.add(CalendarioDia(data=d, diautil=1 if d.weekday() < 5 else 0))
            d = d.fromordinal(d.toordinal() + 1)

        # ---- Empresas --------------------------------------------------------
        stores = []
        for cod, nome, _ in STORES:
            stores.append(EmpresaVenda(codigo=cod, fantasia=nome))
        stores.append(EmpresaVenda(codigo=21, fantasia="MADCENTRO E-COMMERCE"))
        db.add_all(stores)
        db.flush()

        # ---- Plano de valores por loja ----------------------------------------
        pesos = [f for _, _, f in STORES]
        fretes = allocate(TOT_FRETE, pesos)          # soma 80.266
        ntotals = [fat - fre for (_, _, fat), fre in zip(STORES, fretes)]  # soma 9.235.468
        descontos = allocate(TOT_DESCONTO, pesos)
        lucros = allocate(TOT_LUCRO, pesos)
        qtds = allocate(TOT_QTD, pesos)

        # ---- Vendas (documentos May–Dec/2026) --------------------------------
        vendas = []
        ndoc = 0
        for i, ((cod, nome, _), ntotal, frete, desc, luc, qtd) in enumerate(
                zip(STORES, ntotals, fretes, descontos, lucros, qtds)):
            vals_nt = distribuir(ntotal, qtd)
            vals_fr = distribuir(frete, qtd)
            vals_ds = distribuir(desc, qtd)
            vals_lu = distribuir(luc, qtd)
            for j in range(qtd):
                ndoc += 1
                m = rng.choice(MESES_REF)
                dia = rng.randint(1, 28)
                vendas.append(Venda(
                    data=date(2026, m, dia),
                    empresa_id=cod,
                    ndocumento=f"{cod:03d}-{ndoc:06d}",
                    vendedor_1_2=EQUIPES[j % len(EQUIPES)][1],
                    vendedor=EQUIPES[j % len(EQUIPES)][0],
                    cliente=f"CLIENTE {rng.randint(1000, 9999)}",
                    grupo=rng.choice(GRUPOS),
                    subgrupo=rng.choice(SUBGRUPOS),
                    ntotal=vals_nt[j],
                    nfrete=vals_fr[j],
                    ndesconto=vals_ds[j],
                    nvalorlucro=vals_lu[j],
                    vrqtd=rng.randint(1, 30),
                ))
            # documentos devolvidos/cancelados (VRQTD=0 => fora de qtdVendas)
            for k in range(max(1, qtd // 50)):
                ndoc += 1
                m = rng.choice(MESES_REF)
                vendas.append(Venda(
                    data=date(2026, m, rng.randint(1, 28)),
                    empresa_id=cod,
                    ndocumento=f"{cod:03d}-{ndoc:06d}",
                    vendedor_1_2=EQUIPES[k % len(EQUIPES)][1],
                    vendedor=EQUIPES[k % len(EQUIPES)][0],
                    cliente=f"CLIENTE {rng.randint(1000, 9999)}",
                    grupo=rng.choice(GRUPOS),
                    subgrupo=rng.choice(SUBGRUPOS),
                    ntotal=0, nfrete=0, ndesconto=0, nvalorlucro=0, vrqtd=0,
                ))

        # ---- Empresa 21 (regra de negócio): só conta >= 01/06/2025 -----------
        for base in range(1, 40):
            em = rng.randint(1, 12)
            ano = 2025 if em != 12 else 2025
            dd = date(ano, em, rng.randint(1, 28))
            vendas.append(Venda(
                data=dd, empresa_id=21, ndocumento=f"21-{base:06d}",
                vendedor_1_2="EQUIPE X", vendedor="ECOMM",
                cliente="ECOM CLIENTE", grupo="E-COMMERCE", subgrupo="ONLINE",
                ntotal=50000, nfrete=0, ndesconto=3000, nvalorlucro=8000, vrqtd=3,
            ))
        db.add_all(vendas)

        # ---- Metas (MAX por CHAVE+DATA; exclui 383891/tipo 92) ----------------
        metas = []
        chave = 1000
        for cod, nome, fat in STORES:
            fat = int(fat)
            for eq in range(2):
                for m in MESES_REF:
                    metas.append(VendedorMeta(
                        chave=chave, data=date(2026, m, 1),
                        meta=round(fat / 8 * rng.uniform(0.9, 1.15), 2),
                        nchtipoentidade=1,
                    ))
                chave += 1
        # vendedor excluído (CHAVE 383891 / NCHTIPOENTIDADE 92)
        for m in MESES_REF:
            metas.append(VendedorMeta(chave=383891, data=date(2026, m, 1),
                                      meta=5000000, nchtipoentidade=92))
        db.add_all(metas)

        # ---- Inadimplência (VENCIDO soma 55.879; mais registros EM DIA) -------
        inad = []
        vals = distribuir(TOT_INADIM_VENCIDO, len(MESES_REF))
        for m, v in zip(MESES_REF, vals):
            if v <= 0:
                continue
            for r in distribuir(v, max(1, v // 9000)):
                inad.append(InadimplenciaVenda(
                    data=date(2026, m, rng.randint(1, 28)), valor=r,
                    status="VENCIDO"))
            emdia = distribuir(rng.randint(40000, 60000), 2)
            for v2 in emdia:
                inad.append(InadimplenciaVenda(
                    data=date(2026, m, rng.randint(1, 28)), valor=v2,
                    status="EM DIA"))
        db.add_all(inad)

        db.commit()
        print("Seed de vendas aplicado com sucesso.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    semear()
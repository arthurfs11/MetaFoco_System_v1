"""Importador da aba VENDAS a partir de dados do banco do cliente (GMAD).

Fonte de verdade = relatório Power BI "GERENCIAL". As tabelas da Seção 3 do
Manual de Migração (Vendas, Calendario, empresas, vendedores, inadimplencia,
Fretes) devem ser exportadas como CSV (ou apontar direto para o SQL Server do
cliente) e ingeridas por aqui:

    python -m engine.importar_vendas --csv /caminho/para/csvs

Formato CSV esperado (delimitador ';', primeira linha = cabeçalho):

  vendas.csv:
    data;NDOCUMENTO;NEMPRESA;VENDEDOR_1_2;VENDEDOR;CLIENTE;GRUPO;SUBGRUPO;NTOTAL;NFRETE;NDESCONTO;NVALORLUCRO;VRQTD
  empresas.csv:
    codigo;tFantasia
  calendario.csv:
    data;diautil
  vendedores_metas.csv:
    chave;data;meta;nchtipoentidade
  inadimplencia_vendas.csv:
    data;valor;status

Valores de data no formato YYYY-MM-DD. O importador sobreescreve as tabelas de
vendas (as referências/Calendário/empresas são reconstruídas por completo).
"""
import argparse
import os
import sys
import csv
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.models import (Venda, EmpresaVenda, CalendarioDia, VendedorMeta,
                           InadimplenciaVenda, FreteOpcao)


def _to_date(v):
    if isinstance(v, (datetime, date)):
        return v.date() if isinstance(v, datetime) else v
    if not v or str(v).strip() == '':
        return None
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Data inválida: {v}")


def _num(v):
    if v is None or str(v).strip() == '':
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    return float(str(v).replace(',', '.'))


def _ler_csv(caminho):
    with open(caminho, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f, delimiter=';'))


def importar(pasta):
    db = SessionLocal()
    try:
        db.query(Venda).delete()
        db.query(EmpresaVenda).delete()
        db.query(VendedorMeta).delete()
        db.query(InadimplenciaVenda).delete()
        db.query(CalendarioDia).delete()

        f_empresas = os.path.join(pasta, "empresas.csv")
        if os.path.exists(f_empresas):
            for r in _ler_csv(f_empresas):
                db.add(EmpresaVenda(codigo=int(r['codigo']),
                                    fantasia=r['tFantasia']))
            db.flush()

        f_cal = os.path.join(pasta, "calendario.csv")
        if os.path.exists(f_cal):
            for r in _ler_csv(f_cal):
                db.add(CalendarioDia(data=_to_date(r['data']),
                                     diautil=int(r.get('diautil', 1))))

        f_vendas = os.path.join(pasta, "vendas.csv")
        if os.path.exists(f_vendas):
            for r in _ler_csv(f_vendas):
                db.add(Venda(
                    data=_to_date(r['data']),
                    empresa_id=int(r['NEMPRESA']),
                    ndocumento=str(r['NDOCUMENTO']),
                    vendedor_1_2=r.get('VENDEDOR_1_2') or None,
                    vendedor=r.get('VENDEDOR') or None,
                    cliente=r.get('CLIENTE') or None,
                    grupo=r.get('GRUPO') or None,
                    subgrupo=r.get('SUBGRUPO') or None,
                    ntotal=_num(r.get('NTOTAL')),
                    nfrete=_num(r.get('NFRETE')),
                    ndesconto=_num(r.get('NDESCONTO')),
                    nvalorlucro=_num(r.get('NVALORLUCRO')),
                    vrqtd=_num(r.get('VRQTD')),
                ))

        f_metas = os.path.join(pasta, "vendedores_metas.csv")
        if os.path.exists(f_metas):
            for r in _ler_csv(f_metas):
                db.add(VendedorMeta(
                    chave=int(r['chave']),
                    data=_to_date(r['data']),
                    meta=_num(r.get('meta')),
                    nchtipoentidade=int(r.get('nchtipoentidade', 1) or 1),
                ))

        f_inad = os.path.join(pasta, "inadimplencia_vendas.csv")
        if os.path.exists(f_inad):
            for r in _ler_csv(f_inad):
                db.add(InadimplenciaVenda(
                    data=_to_date(r['data']),
                    valor=_num(r.get('valor')),
                    status=r.get('status', 'VENCIDO'),
                ))

        db.add_all([FreteOpcao(opcao="Com Frete"), FreteOpcao(opcao="Sem Frete")])
        db.commit()
        total_vendas = db.query(Venda).count()
        print(f"Importação concluída: {total_vendas} vendas.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Importa dados de vendas (CSV do GMAD)")
    ap.add_argument("--csv", required=True, help="Pasta com os arquivos CSV")
    args = ap.parse_args()
    importar(args.csv)
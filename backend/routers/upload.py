from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.models import Contrato
from utils.auth import get_db, get_current_user, require_gestor, get_password_hash
import pandas as pd
from typing import Optional
import io
import math
from datetime import datetime, date

router = APIRouter()

def safe_float(val):
    """Convert value to float, handling NaN/None and comma strings"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val) if not math.isnan(val) else None
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return None
        val = val.replace('.', '').replace(',', '.')
        try:
            return float(val)
        except ValueError:
            return None
    return None

def safe_int(val):
    """Convert value to int, handling NaN/None"""
    if val is None:
        return None
    if isinstance(val, float):
        return int(val) if not math.isnan(val) else None
    if isinstance(val, (int,)):
        return val
    if isinstance(val, str):
        val = val.strip()
        try:
            return int(float(val))
        except ValueError:
            return None
    return None

def safe_date(val):
    """Convert value to date, handling various formats"""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, pd.Timestamp):
        return val.date()
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return None
        for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
    return None

def parse_excel_data(file_bytes, data_base=None):
    """Lê a aba ENDIVIDAMENTO do Excel e retorna lista de dicionários de contratos"""
    df = pd.read_excel(io.BytesIO(file_bytes), sheet_name='ENDIVIDAMENTO', header=None, skiprows=5)
    # A linha 4 (5ª) é o cabeçalho, a 13ª (índice 4) começa os dados
    # Na verdade: pandas leu com header None, then skiprows=5 pulou as 5 primeiras
    # Vamos re-ler com header correto para garantir

    data_base_date = None
    if data_base is None:
        # Tentar extrair data base do arquivo
        try:
            raw = pd.read_excel(io.BytesIO(file_bytes), sheet_name='ENDIVIDAMENTO', header=None)
            db_row = raw.iloc[1]
            for val in db_row:
                if isinstance(val, (datetime, pd.Timestamp)):
                    data_base_date = val.date()
                    break
                if isinstance(val, str) and val:
                    try:
                        data_base_date = datetime.strptime(val.strip(), "%d/%m/%Y").date()
                        break
                    except ValueError:
                        pass
        except Exception:
            pass
    else:
        data_base_date = data_base

    # Definir colunas a partir da linha de cabeçalho (linha índice 4 = skiprows=4)
    df = pd.read_excel(io.BytesIO(file_bytes), sheet_name='ENDIVIDAMENTO', header=None, skiprows=4)
    header = df.iloc[0]
    data = df.iloc[1:]

    contratos = []
    for _, row in data.iterrows():
        instituicao = str(row[0]).strip() if row[0] is not None and str(row[0]).strip().lower() != 'nan' else None
        if not instituicao:
            continue

        contrato = str(row[3]).strip() if row[3] is not None and str(row[3]).strip().lower() != 'nan' else None
        if not contrato:
            continue

        contrato_obj = {
            'data_base': data_base_date,
            'instituicao': instituicao,
            'empresa': str(row[1]).strip() if row[1] is not None and str(row[1]).strip() else None,
            'modalidade': str(row[2]).strip() if row[2] is not None and str(row[2]).strip() else None,
            'numero_contrato': contrato,
            'parcela': safe_int(row[4]),
            'periodo': str(row[5]).strip() if row[5] is not None and str(row[5]).strip() else None,
            'pgto': str(row[6]).strip() if row[6] is not None and str(row[6]).strip() else None,
            'emissao': safe_date(row[7]),
            'inicial': safe_date(row[8]),
            'final': safe_date(row[9]),
            'contratado': safe_float(row[10]),
            'curto_prazo': safe_float(row[11]),
            'longo_prazo': safe_float(row[12]),
            'total_pg': safe_float(row[13]),
            'perc_rest': safe_float(row[14]),
            'parc_pg': safe_float(row[15]),
            'prestacao': safe_float(row[16]),
            'juros': safe_float(row[17]),
            'amortiz': safe_float(row[18]),
            'am': safe_float(row[19]),
            'aa': safe_float(row[20]),
            'am2': safe_float(row[21]),
            'aa2': safe_float(row[22]),
            'indice': str(row[23]).strip() if row[23] is not None and str(row[23]).strip() else None,
            'modalidade2': str(row[24]).strip() if row[24] is not None and str(row[24]).strip() else None,
            'perc_gar': safe_float(row[25]),
            'obs_cet': str(row[27]).strip() if not pd.isna(row[27]) else None,
            'resumo_garantias': str(row[28]).strip() if not pd.isna(row[28]) else None,
            'fonte': 'upload_excel'
        }
        contratos.append(contrato_obj)
    return contratos

@router.post("/excel")
def upload_excel(
    file: UploadFile = File(...),
    user: any = Depends(require_gestor),
    db: Session = Depends(get_db)
):
    """Faz upload de arquivo Excel e insere apenas registros novos (sem duplicação)"""
    try:
        file_bytes = file.file.read()
        contratos = parse_excel_data(file_bytes)

        if not contratos:
            raise HTTPException(status_code=400, detail="Nenhum contrato encontrado no arquivo")

        novos = 0
        duplicados = 0
        erro_linhas = 0

        for c in contratos:
            exists = db.query(Contrato).filter(
                Contrato.numero_contrato == c['numero_contrato'],
                Contrato.instituicao == c['instituicao'],
                Contrato.parcela == c['parcela'],
                Contrato.data_base == c['data_base']
            ).first()

            if exists:
                duplicados += 1
                continue

            db.add(Contrato(**c))
            novos += 1

        db.commit()

        return {
            "mensagem": "Upload concluído",
            "total_arquivo": len(contratos),
            "novos": novos,
            "duplicados": duplicados,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao processar arquivo: {str(e)}")

@router.get("/proximo-contrato")
def proximo_numero(user=Depends(require_gestor), db: Session = Depends(get_db)):
    """Retorna próximo número de contrato sugerido para cadastro manual"""
    ultimo = db.query(Contrato).order_by(Contrato.numero_contrato.desc()).first()
    try:
        return {"proximo": str(int(ultimo.numero_contrato) + 1)}
    except (ValueError, TypeError, AttributeError):
        return {"proximo": "1"}
"""Importa a planilha inicial de endividamento para o banco"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal
from routers.upload import parse_excel_data
from models.models import Contrato

def importar_arquivo(path):
    db = SessionLocal()
    try:
        with open(path, 'rb') as f:
            file_bytes = f.read()
        contratos = parse_excel_data(file_bytes)
        novos = 0
        for c in contratos:
            exists = db.query(Contrato).filter(
                Contrato.numero_contrato == c['numero_contrato'],
                Contrato.instituicao == c['instituicao'],
                Contrato.parcela == c['parcela'],
                Contrato.data_base == c['data_base']
            ).first()
            if exists:
                continue
            db.add(Contrato(**c))
            novos += 1
        db.commit()
        print(f"Importação concluída: {novos} novos contratos de {len(contratos)} no arquivo")
    finally:
        db.close()

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "../_Endividamento Shinoda versao 06.xlsm"
    # Resolve caminho relativo a partir do diretório do script
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(__file__), path)
    importar_arquivo(path)
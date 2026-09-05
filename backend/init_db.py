"""Cria tabelas e insere usuário SuperAdmin inicial"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import engine, SessionLocal, Base
import models.models
from models.models import Usuario
from utils.auth import get_password_hash
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin_meta")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

def init():
    if not ADMIN_PASSWORD:
        print("[ERRO] Defina ADMIN_PASSWORD no arquivo backend/.env "
              "(ver backend/.env.example).")
        sys.exit(1)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Criar SuperAdmin se não existir
        admin = db.query(Usuario).filter(Usuario.email == ADMIN_EMAIL).first()
        if not admin:
            admin = Usuario(
                nome="Admin",
                sobrenome="Meta",
                email=ADMIN_EMAIL,
                senha_hash=get_password_hash(ADMIN_PASSWORD),
                perfil="SUPERADMIN",
                precisa_trocar_senha=False,
            )
            db.add(admin)
            db.commit()
            print(f"SuperAdmin criado com sucesso: {ADMIN_EMAIL}")
        else:
            print("SuperAdmin já existe")
    finally:
        db.close()

if __name__ == "__main__":
    init()
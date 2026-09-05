from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from utils.auth import pwd_context, create_access_token, get_password_hash, get_db, get_current_user, require_admin
from models.models import Usuario
import uuid
from fastapi import FastAPI

router = APIRouter()

class UserCreate(BaseModel):
    nome: str
    sobrenome: str
    email: EmailStr
    perfil: str = "LEITURA"

class UserOut(BaseModel):
    id: str
    nome: str
    sobrenome: str
    email: str
    perfil: str
    precisa_trocar_senha: bool
    ativo: bool

class ChangePassword(BaseModel):
    senha_atual: str
    nova_senha: str

class ResetPassword(BaseModel):
    nova_senha: str = "Meta12345"

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.email == form_data.username).first()
    if not user:
        raise HTTPException(status_code=400, detail="E-mail ou senha incorretos")
    if not pwd_context.verify(form_data.password, user.senha_hash):
        raise HTTPException(status_code=400, detail="E-mail ou senha incorretos")
    if not user.ativo:
        raise HTTPException(status_code=403, detail="Usuário inativo")
    token = create_access_token({"sub": str(user.id), "perfil": user.perfil})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "nome": user.nome,
            "sobrenome": user.sobrenome,
            "email": user.email,
            "perfil": user.perfil,
            "precisa_trocar_senha": user.precisa_trocar_senha,
        }
    }

@router.get("/me")
def me(user: Usuario = Depends(get_current_user)):
    return {
        "id": str(user.id),
        "nome": user.nome,
        "sobrenome": user.sobrenome,
        "email": user.email,
        "perfil": user.perfil,
        "precisa_trocar_senha": user.precisa_trocar_senha,
    }

@router.post("/usuarios", response_model=UserOut)
def criar_usuario(user_data: UserCreate, admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    # Verificar se já existe
    existing = db.query(Usuario).filter(Usuario.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Já existe um usuário com este e-mail")
    
    user = Usuario(
        nome=user_data.nome,
        sobrenome=user_data.sobrenome,
        email=user_data.email.lower(),
        senha_hash=get_password_hash("Meta12345"),
        perfil=user_data.perfil,
        precisa_trocar_senha=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut(
        id=str(user.id),
        nome=user.nome,
        sobrenome=user.sobrenome,
        email=user.email,
        perfil=user.perfil,
        precisa_trocar_senha=user.precisa_trocar_senha,
        ativo=user.ativo,
    )

@router.get("/usuarios", response_model=list[UserOut])
def listar_usuarios(admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(Usuario).all()
    return [
        UserOut(
            id=str(u.id),
            nome=u.nome,
            sobrenome=u.sobrenome,
            email=u.email,
            perfil=u.perfil,
            precisa_trocar_senha=u.precisa_trocar_senha,
            ativo=u.ativo,
        ) for u in users
    ]

@router.put("/usuarios/{user_id}/perfil")
def alterar_perfil(user_id: str, perfil: str, admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.id == uuid.UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.perfil = perfil
    db.commit()
    return {"ok": True}

@router.put("/usuarios/{user_id}/resetar-senha")
def resetar_senha(user_id: str, admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.id == uuid.UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.senha_hash = get_password_hash("Meta12345")
    user.precisa_trocar_senha = True
    db.commit()
    return {"ok": True}

@router.put("/usuarios/{user_id}/ativar")
def ativar_usuario(user_id: str, ativo: bool, admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.id == uuid.UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.ativo = ativo
    db.commit()
    return {"ok": True}

@router.post("/trocar-senha")
def trocar_senha(data: ChangePassword, user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    if not pwd_context.verify(data.senha_atual, user.senha_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    user.senha_hash = get_password_hash(data.nova_senha)
    user.precisa_trocar_senha = False
    db.commit()
    return {"ok": True}
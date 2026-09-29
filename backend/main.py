from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import engine, Base
import models.models
from routers import auth, contratos, upload, dashboard, amortizacao, vendas
import os

# Criar tabelas
Base.metadata.create_all(bind=engine)

app = FastAPI(title="MetaFoco System API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas
app.include_router(auth.router, prefix="/api/auth", tags=["Autenticação"])
app.include_router(contratos.router, prefix="/api/contratos", tags=["Contratos"])
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(amortizacao.router, prefix="/api/amortizacao", tags=["Amortização"])
app.include_router(vendas.router, prefix="/api/vendas", tags=["Vendas"])

# Servir frontend
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/assets", StaticFiles(directory=os.path.join(frontend_path, "assets")), name="assets")
app.mount("/css", StaticFiles(directory=os.path.join(frontend_path, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(frontend_path, "js")), name="js")

NO_CACHE = {"Cache-Control": "no-cache, no-store, must-revalidate"}

def _page(name):
    return FileResponse(os.path.join(frontend_path, "pages", name), headers=NO_CACHE)

@app.get("/")
async def root():
    return FileResponse(os.path.join(frontend_path, "index.html"), headers=NO_CACHE)

@app.get("/login")
async def login_page():
    return _page("login.html")

@app.get("/dashboard")
async def dashboard_page():
    return _page("dashboard.html")

@app.get("/usuarios")
async def usuarios_page():
    return _page("usuarios.html")

@app.get("/contratos")
async def contratos_page():
    return _page("contratos.html")

@app.get("/contrato")
async def contrato_detalhe_page():
    return _page("contrato.html")

@app.get("/upload")
async def upload_page():
    return _page("upload.html")

@app.get("/vendas")
async def vendas_page():
    return _page("vendas.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9090)
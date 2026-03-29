import os
import sqlite3
import shutil
import tempfile
import unicodedata
import threading
import time
from datetime import datetime
from typing import List

from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from fpdf import FPDF
import webview
import speech_recognition as sr
from pydub import AudioSegment
from google import genai

# ==========================================
# TRAVA DE GPS (DIRETÓRIO ATUAL)
# Garante que o App Desktop sempre ache os arquivos
# ==========================================
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
CAMINHO_BD = os.path.join(DIRETORIO_ATUAL, 'estudos.db')

# ==========================================
# 1. INICIALIZAÇÃO DO BANCO DE DADOS
# ==========================================
def init_db():
    conn = sqlite3.connect(CAMINHO_BD)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ensinos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tema TEXT,
            data TEXT,
            transcricao_bruta TEXT,
            texto_corrigido TEXT,
            pdf_path TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS louvores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT,
            cantor TEXT,
            letra TEXT
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# ==========================================
# CONFIGURAÇÃO DA IA E DO SERVIDOR
# ==========================================
from dotenv import load_dotenv
import os

# 1. Abre o cofre (.env)
load_dotenv()

# 2. Pega a chave secreta
CHAVE_GEMINI = os.getenv("GEMINI_API_KEY")

# 3. Liga a IA com segurança
from google import genai
cliente_ia = genai.Client(api_key=CHAVE_GEMINI)

app = FastAPI(title="Culto Inteligente API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CRIA AS PASTAS SE NÃO EXISTIREM
if not os.path.exists(os.path.join(DIRETORIO_ATUAL, "midia")):
    os.makedirs(os.path.join(DIRETORIO_ATUAL, "midia"))
app.mount("/midia", StaticFiles(directory=os.path.join(DIRETORIO_ATUAL, "midia")), name="midia")

if not os.path.exists(os.path.join(DIRETORIO_ATUAL, "pdfs")):
    os.makedirs(os.path.join(DIRETORIO_ATUAL, "pdfs"))
app.mount("/pdfs", StaticFiles(directory=os.path.join(DIRETORIO_ATUAL, "pdfs")), name="pdfs")

# ==========================================
# MODELOS DE DADOS (Pydantic)
# ==========================================
class EnsinoData(BaseModel):
    tema: str
    texto_bruto: str
    texto_corrigido: str

class LouvorData(BaseModel):
    titulo: str
    cantor: str
    letra: str

class LetreiroData(BaseModel):
    texto: str

class FundoData(BaseModel):
    tipo_fundo: str
    arquivo: str = ""

class LowerThirdData(BaseModel):
    nome: str
    cargo: str

class TextoProjecao(BaseModel):
    texto: str

# ==========================================
# ROTAS DA API (SISTEMA, BÍBLIA, ESTÚDIO, TELÃO)
# ==========================================
@app.get("/")
def abrir_painel_principal():
    return FileResponse(os.path.join(DIRETORIO_ATUAL, "index.html"))

@app.post("/processar-audio")
async def processar_audio(arquivo: UploadFile = File(...)):
    print(f"Recebendo arquivo: {arquivo.filename}")

    pasta_temp = tempfile.gettempdir()
    caminho_webm = os.path.join(pasta_temp, f"temp_{arquivo.filename}")
    caminho_wav = os.path.join(pasta_temp, "temp_audio.wav")

    with open(caminho_webm, "wb") as buffer:
        shutil.copyfileobj(arquivo.file, buffer)

    texto_bruto = ""
    texto_ia = ""

    try:
        print("Convertendo formato de áudio...")
        audio = AudioSegment.from_file(caminho_webm)
        audio.export(caminho_wav, format="wav")

        print("Enviando para o reconhecimento de voz...")
        recognizer = sr.Recognizer()
        with sr.AudioFile(caminho_wav) as source:
            audio_data = recognizer.record(source)
            texto_bruto = recognizer.recognize_google(audio_data, language="pt-BR")
            print("Transcrição bruta concluída!")

        print("Enviando para a nova IA do Gemini corrigir...")
        prompt_revisao = f"""
        Você é um revisor de textos. Leia a transcrição bruta a seguir, que foi captada de um microfone durante um ensino em uma igreja.
        Seu trabalho é corrigir erros gramaticais, remover vícios de linguagem (como 'né', 'hã', palavras repetidas) e formatar o texto com pontuação adequada.
        É estritamente proibido alterar o contexto, o sentido teológico ou adicionar informações que não foram ditas.
        
        Texto bruto:
        "{texto_bruto}"
        """

        resposta_ia = cliente_ia.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_revisao
        )
        texto_ia = resposta_ia.text.strip()
        print("Correção da IA concluída com sucesso!")

    except Exception as e:
        print(f"Erro ocorrido: {e}")
        texto_bruto = texto_bruto if texto_bruto else "Erro ao ouvir o áudio."
        texto_ia = f"Não foi possível processar a IA. Detalhe do erro: {e}"

    finally:
        if os.path.exists(caminho_webm):
            os.remove(caminho_webm)
        if os.path.exists(caminho_wav):
            os.remove(caminho_wav)

    return {
        "status": "sucesso",
        "texto_bruto": texto_bruto,
        "texto_ia": texto_ia
    }

@app.post("/salvar-ensino")
async def salvar_ensino(data: EnsinoData):
    data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
    nome_arquivo_pdf = f"ensino_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    caminho_pdf = os.path.join(DIRETORIO_ATUAL, "pdfs", nome_arquivo_pdf)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, txt="Registro de Ensino - Igreja", ln=True, align="C")

    pdf.set_font("Arial", "B", 12)
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Tema: {data.tema}", ln=True)
    pdf.cell(200, 10, txt=f"Data: {data_atual}", ln=True)

    pdf.ln(10)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(200, 10, txt="Transcrição Corrigida:", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 10, txt=data.texto_corrigido)

    pdf.output(caminho_pdf)

    conn = sqlite3.connect(CAMINHO_BD)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ensinos (tema, data, transcricao_bruta, texto_corrigido, pdf_path)
        VALUES (?, ?, ?, ?, ?)
    ''', (data.tema, data_atual, data.texto_bruto, data.texto_corrigido, caminho_pdf))
    conn.commit()
    conn.close()

    return {"status": "sucesso", "mensagem": "PDF gerado e salvo no banco!", "pdf": caminho_pdf}

@app.get("/listar-ensinos")
async def listar_ensinos():
    conn = sqlite3.connect(CAMINHO_BD)
    cursor = conn.cursor()
    cursor.execute('SELECT id, tema, data, pdf_path FROM ensinos ORDER BY id DESC')
    ensinos = cursor.fetchall()
    conn.close()

    lista_formatada = []
    for e in ensinos:
        lista_formatada.append({
            "id": e[0],
            "tema": e[1],
            "data": e[2],
            "pdf": e[3]
        })

    return lista_formatada

@app.delete("/deletar-ensino/{ensino_id}")
async def deletar_ensino(ensino_id: int):
    conn = sqlite3.connect(CAMINHO_BD)
    cursor = conn.cursor()

    cursor.execute('SELECT pdf_path FROM ensinos WHERE id = ?', (ensino_id,))
    resultado = cursor.fetchone()

    if not resultado:
        conn.close()
        raise HTTPException(status_code=404, detail="Ensino não encontrado")

    caminho_pdf = resultado[0]

    cursor.execute('DELETE FROM ensinos WHERE id = ?', (ensino_id,))
    conn.commit()
    conn.close()

    try:
        if os.path.exists(caminho_pdf):
            os.remove(caminho_pdf)
    except Exception as e:
        print(f"Erro ao deletar arquivo PDF: {e}")

    return {"status": "sucesso", "mensagem": f"Ensino {ensino_id} deletado com sucesso!"}

# ==========================================
# MÓDULO DE PROJEÇÃO AO VIVO (TELÃO)
# ==========================================
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

gerenciador_telao = ConnectionManager()

@app.websocket("/ws/telao")
async def websocket_telao(websocket: WebSocket):
    await gerenciador_telao.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        gerenciador_telao.disconnect(websocket)

@app.post("/projetar")
async def projetar_texto(dados: TextoProjecao):
    await gerenciador_telao.broadcast(dados.texto)
    return {"status": "sucesso"}

@app.post("/salvar-louvor")
async def salvar_louvor(data: LouvorData):
    conn = sqlite3.connect(CAMINHO_BD)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO louvores (titulo, cantor, letra)
        VALUES (?, ?, ?)
    ''', (data.titulo, data.cantor, data.letra))
    conn.commit()
    conn.close()

    return {"status": "sucesso", "mensagem": f"Louvor '{data.titulo}' salvo no acervo!"}

@app.get("/listar-louvores")
async def listar_louvores():
    conn = sqlite3.connect(CAMINHO_BD)
    cursor = conn.cursor()
    cursor.execute('SELECT id, titulo, cantor, letra FROM louvores ORDER BY titulo ASC')
    louvores = cursor.fetchall()
    conn.close()

    lista_formatada = []
    for l in louvores:
        lista_formatada.append({
            "id": l[0],
            "titulo": l[1],
            "cantor": l[2],
            "letra": l[3]
        })

    return lista_formatada

@app.get("/biblia/livros")
async def listar_livros():
    conn = sqlite3.connect(CAMINHO_BD)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT livro FROM biblia WHERE versao='NVI' ORDER BY id")
    livros = [row[0] for row in cursor.fetchall()]
    conn.close()
    return livros

@app.get("/biblia/capitulos/{livro}")
async def listar_capitulos(livro: str):
    conn = sqlite3.connect(CAMINHO_BD)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(capitulo) FROM biblia WHERE livro=? AND versao='NVI'", (livro,))
    max_cap = cursor.fetchone()[0]
    conn.close()
    return {"total_capitulos": max_cap}

@app.get("/biblia/versiculos")
async def listar_versiculos(livro: str, capitulo: int, versao: str):
    conn = sqlite3.connect(CAMINHO_BD)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT versiculo, texto FROM biblia 
        WHERE livro=? AND capitulo=? AND versao=? 
        ORDER BY versiculo
    ''', (livro, capitulo, versao))

    versiculos = [{"versiculo": row[0], "texto": row[1]} for row in cursor.fetchall()]
    conn.close()
    return versiculos

@app.get("/listar-midias")
async def listar_midias():
    caminho_midia = os.path.join(DIRETORIO_ATUAL, "midia")
    arquivos = os.listdir(caminho_midia)
    imagens = [f for f in arquivos if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    videos = [f for f in arquivos if f.lower().endswith(('.mp4', '.webm'))]
    return {"imagens": imagens, "videos": videos}

@app.post("/mudar-fundo")
async def mudar_fundo(dados: FundoData):
    if dados.arquivo:
        await gerenciador_telao.broadcast(f"CMD_FUNDO:{dados.tipo_fundo}:{dados.arquivo}")
    else:
        await gerenciador_telao.broadcast(f"CMD_FUNDO:{dados.tipo_fundo}")
    return {"status": "sucesso"}

@app.post("/letreiro")
async def enviar_letreiro(dados: LetreiroData):
    await gerenciador_telao.broadcast(f"CMD_LETREIRO:{dados.texto}")
    return {"status": "sucesso"}

@app.post("/relogio")
async def alternar_relogio():
    await gerenciador_telao.broadcast("CMD_RELOGIO:TOGGLE")
    return {"status": "sucesso"}

@app.get("/biblia/busca-texto")
async def buscar_por_texto(trecho: str, versao: str = "NVI"):
    conn = sqlite3.connect(CAMINHO_BD)

    def remover_acentos(txt):
        if txt is None:
            return ""
        return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn').lower()

    conn.create_function("LIMPAR_TEXTO", 1, remover_acentos)
    cursor = conn.cursor()
    trecho_limpo = remover_acentos(trecho)

    cursor.execute('''
        SELECT livro, capitulo, versiculo, texto FROM biblia 
        WHERE LIMPAR_TEXTO(texto) LIKE ? AND versao = ?
        LIMIT 50
    ''', (f'%{trecho_limpo}%', versao))

    versiculos = [{"livro": row[0], "capitulo": row[1], "versiculo": row[2], "texto": row[3]} for row in cursor.fetchall()]
    conn.close()
    return versiculos

@app.post("/lower-third")
async def enviar_lower_third(dados: LowerThirdData):
    await gerenciador_telao.broadcast(f"CMD_LOWER:{dados.nome}|{dados.cargo}")
    return {"status": "sucesso"}

# ==========================================
# ROTA CORINGA (A ÚLTIMA ROTA ANTES DO MOTOR!)
# ==========================================
@app.get("/{arquivo:path}")
def servir_qualquer_arquivo(arquivo: str):
    caminho_completo = os.path.join(DIRETORIO_ATUAL, arquivo)
    if os.path.exists(caminho_completo):
        return FileResponse(caminho_completo)
    raise HTTPException(status_code=404, detail="Arquivo não encontrado")

# ==========================================
# MOTOR DE INICIALIZAÇÃO APP DESKTOP (WEBVIEW) E MOBILE
# ==========================================
def iniciar_servidor():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == '__main__':
    # 1. Liga o servidor silencioso no fundo
    servidor = threading.Thread(target=iniciar_servidor, daemon=True)
    servidor.start()
    
    # Dá 1 segundo para o servidor respirar
    time.sleep(1)
    
    # 2. Cria a janela do App Desktop
    janela = webview.create_window(
        title='Culto Inteligente - Painel de Controle', 
        url='http://127.0.0.1:8000/', 
        width=1280, 
        height=720,
        min_size=(1024, 600),
        text_select=False
    )
    
    # 3. Dá a partida na janela nativa
    webview.start()
import os
import random
import shutil
import sqlite3
import subprocess
import sys
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk  # Requer Pillow (pip install pillow)
from werkzeug.security import check_password_hash, generate_password_hash

try:
    import pygame
    pygame.mixer.init()
    AUDIO_SUPPORTED = True
except Exception:
    AUDIO_SUPPORTED = False

DB_NAME = "database.db"

# --- CRIAR PASTAS PARA IMAGENS, VÍDEOS E MÚSICAS ---
PASTA_IMAGENS = os.path.join("midia", "imagens")
PASTA_VIDEOS = os.path.join("midia", "videos")
PASTA_MUSICAS = os.path.join("midia", "musicas")

os.makedirs(PASTA_IMAGENS, exist_ok=True)
os.makedirs(PASTA_VIDEOS, exist_ok=True)
os.makedirs(PASTA_MUSICAS, exist_ok=True)


# --- BANCO DE DADOS LOCAL (SQLITE) ---
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # Tabela de Usuários
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                data_nascimento TEXT NOT NULL,
                celular TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                pergunta_recuperacao TEXT,
                resposta_recuperacao TEXT
            )
        """
        )
        # Tabela de Notas com suporte a Horário
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                categoria TEXT NOT NULL DEFAULT 'Geral',
                titulo TEXT NOT NULL,
                conteudo TEXT NOT NULL,
                caminho_midia TEXT,
                data TEXT NOT NULL,
                horario TEXT DEFAULT '',
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """
        )

        # Migrações automáticas para bases legadas
        try:
            cursor.execute(
                "ALTER TABLE notes ADD COLUMN categoria TEXT NOT NULL DEFAULT"
                " 'Geral'"
            )
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE notes ADD COLUMN caminho_midia TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute(
                "ALTER TABLE notes ADD COLUMN horario TEXT DEFAULT ''"
            )
        except sqlite3.OperationalError:
            pass

        conn.commit()


# --- PALETAS DE CORES (LIGHT VS DARK) ---
THEMES = {
    "light": {
        "bg": "#F1F5F9",
        "sidebar": "#0F172A",
        "card": "#FFFFFF",
        "card_border": "#CBD5E1",
        "primary": "#2563EB",
        "accent": "#10B981",
        "text_main": "#0F172A",
        "text_muted": "#64748B",
        "input_bg": "#FFFFFF",
        "tag_bg": "#E0F2FE",
        "tag_fg": "#0369A1",
    },
    "dark": {
        "bg": "#0F172A",
        "sidebar": "#1E293B",
        "card": "#1E293B",
        "card_border": "#334155",
        "primary": "#3B82F6",
        "accent": "#10B981",
        "text_main": "#F8FAFC",
        "text_muted": "#94A3B8",
        "input_bg": "#0F172A",
        "tag_bg": "#1E3A8A",
        "tag_fg": "#93C5FD",
    },
}

current_theme = "light"

FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_SUBTITLE = ("Segoe UI", 11, "bold")
FONT_REGULAR = ("Segoe UI", 9)
FONT_SMALL = ("Segoe UI", 8)

# Variáveis globais de sessão
logged_user_id = None
logged_user_name = ""
categoria_atual = "Todas"
caminho_midia_selecionado = ""


def resource_path(relative_path):
    """Retorna o caminho absoluto do recurso, compatível com PyInstaller e modo desenvolvimento"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# --- CARREGAMENTO DO LOGO OFICIAL (SVG / PNG) ---
_logo_cache = {}

def obter_logo_image(largura=48, altura=48):
    chave = (largura, altura)
    if chave in _logo_cache:
        return _logo_cache[chave]

    caminhos = [
        resource_path(os.path.join("midia", "imagens", "Logo.png")),
        os.path.join("midia", "imagens", "Logo.png"),
        resource_path("logo.png"),
        "logo.png",
        resource_path(os.path.join("midia", "imagens", "Logo.svg")),
        os.path.join("midia", "imagens", "Logo.svg"),
    ]
    for p in caminhos:
        if os.path.exists(p):
            try:
                # Se for SVG e não existir PNG, converte em tempo de execução via pymupdf
                if p.lower().endswith(".svg"):
                    png_subst = os.path.splitext(p)[0] + ".png"
                    if os.path.exists(png_subst):
                        p = png_subst
                    else:
                        try:
                            import pymupdf
                            doc = pymupdf.open(p)
                            pix = doc[0].get_pixmap()
                            pix.save(png_subst)
                            p = png_subst
                        except Exception:
                            continue

                img = Image.open(p).convert("RGBA")
                img = img.resize((largura, altura), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                _logo_cache[chave] = photo
                return photo
            except Exception:
                continue
    return None


def renderizar_logo(canvas, largura=48, altura=48, bg_cor=None):
    canvas.delete("all")
    if bg_cor:
        canvas.configure(bg=bg_cor)

    photo = obter_logo_image(largura, altura)
    if photo:
        canvas.image = photo  # Mantém referência para o coletor de lixo
        canvas.create_image(largura // 2, altura // 2, image=photo)
    else:
        desenhar_logo_cofre_pena(canvas, 0, 0)


# --- DESENHO DE FALLBACK (CASO LOGO NÃO EXISTA) ---
def desenhar_logo_cofre_pena(canvas, x=2, y=2):
    canvas.delete("all")
    colors = THEMES[current_theme]

    # Fundo circular com degradê/brilho
    canvas.create_oval(
        x + 2, y + 2, x + 44, y + 44, fill=colors["primary"], outline=""
    )
    canvas.create_oval(
        x + 5,
        y + 5,
        x + 41,
        y + 41,
        fill="",
        outline="#60A5FA" if current_theme == "dark" else "#93C5FD",
        width=1.5,
    )

    # 1. Escudo do Cofre (Linhas Limpas)
    canvas.create_polygon(
        x + 16,
        y + 14,
        x + 30,
        y + 14,
        x + 30,
        y + 24,
        x + 23,
        y + 31,
        x + 16,
        y + 24,
        fill="",
        outline="white",
        width=2,
    )

    # Fechadura central
    canvas.create_oval(
        x + 21, y + 18, x + 25, y + 22, fill="white", outline=""
    )
    canvas.create_line(
        x + 23, y + 22, x + 23, y + 26, fill="white", width=1.5
    )

    # 2. Pena Estilizada Dourada
    canvas.create_line(
        x + 10, y + 34, x + 34, y + 10, fill="#F59E0B", width=2.5
    )
    canvas.create_arc(
        x + 20,
        y + 8,
        x + 36,
        y + 24,
        start=30,
        extent=110,
        style="chord",
        fill="#FBBF24",
        outline="",
    )


# --- LÓGICA DE NEGÓCIO ---
def cadastrar_usuario_local():
    nome = cad_nome.get().strip()
    nasc = cad_nasc.get().strip()
    celular = cad_celular.get().strip()
    user = cad_user.get().strip()
    pwd = cad_pass.get().strip()
    pwd_conf = cad_pass_confirm.get().strip()
    pergunta = cad_pergunta.get().strip()
    resposta = cad_resposta.get().strip().upper()

    if not all([nome, nasc, celular, user, pwd, pwd_conf]):
        messagebox.showwarning(
            "Aviso", "Preencha todos os campos obrigatórios (*)."
        )
        return

    if pwd != pwd_conf:
        messagebox.showerror("Erro", "As senhas não coincidem!")
        return

    hashed_pwd = generate_password_hash(pwd)

    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (nome, data_nascimento, celular, username, password, pergunta_recuperacao, resposta_recuperacao)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    nome,
                    nasc,
                    celular,
                    user,
                    hashed_pwd,
                    pergunta,
                    resposta if resposta else None,
                ),
            )
            conn.commit()
            messagebox.showinfo(
                "Sucesso", "Conta criada com sucesso no Cofre de Notas!"
            )
            mostrar_frame(frame_login)
    except sqlite3.IntegrityError:
        messagebox.showerror("Erro", "Este nome de usuário já existe.")


def fazer_login_local():
    global logged_user_id, logged_user_name
    user = entry_user.get().strip()
    pwd = entry_pass.get().strip()

    if not user or not pwd:
        messagebox.showwarning("Aviso", "Preencha o usuário e a senha.")
        return

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, password, nome FROM users WHERE username = ?", (user,)
        )
        res = cursor.fetchone()

        if res and check_password_hash(res[1], pwd):
            logged_user_id = res[0]
            logged_user_name = res[2]
            lbl_user_profile.config(text=f"👤 {logged_user_name.split()[0]}")
            mostrar_frame(frame_main)
            carregar_notas_local("Todas")
        else:
            messagebox.showerror("Erro", "Usuário ou senha incorretos.")


def buscar_pergunta_local():
    user = rec_user.get().strip()
    if not user:
        return

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT pergunta_recuperacao FROM users WHERE username = ?",
            (user,),
        )
        res = cursor.fetchone()

        if res and res[0]:
            lbl_pergunta_exibida.config(text=f"❓ {res[0]}")
            frame_redefinir.pack(pady=10, fill="x")
        else:
            messagebox.showwarning(
                "Aviso",
                "Usuário não encontrado ou sem pergunta cadastrada.",
            )


def redefinir_senha_local():
    user = rec_user.get().strip()
    resp = rec_resposta.get().strip().upper()
    nova_pwd = rec_novasenha.get().strip()

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT resposta_recuperacao FROM users WHERE username = ?",
            (user,),
        )
        res = cursor.fetchone()

        if res and res[0] == resp:
            hashed_pwd = generate_password_hash(nova_pwd)
            cursor.execute(
                "UPDATE users SET password = ? WHERE username = ?",
                (hashed_pwd, user),
            )
            conn.commit()
            messagebox.showinfo("Sucesso", "Senha alterada com sucesso!")
            mostrar_frame(frame_login)
        else:
            messagebox.showerror("Erro", "Resposta incorreta.")


def selecionar_midia():
    global caminho_midia_selecionado
    filepath = filedialog.askopenfilename(
        title="Selecionar Imagem, Vídeo ou Música",
        filetypes=[
            (
                "Arquivos de Mídia",
                "*.png *.jpg *.jpeg *.gif *.bmp *.mp4 *.avi *.mkv *.mov *.mp3 *.wav *.ogg *.flac *.m4a *.aac *.wma",
            ),
            (
                "Músicas e Áudios",
                "*.mp3 *.wav *.ogg *.flac *.m4a *.aac *.wma",
            ),
            ("Imagens", "*.png *.jpg *.jpeg *.gif *.bmp"),
            ("Vídeos", "*.mp4 *.avi *.mkv *.mov"),
            ("Todos os arquivos", "*.*"),
        ],
    )
    if filepath:
        ext = os.path.splitext(filepath)[1].lower()
        nome_arquivo = (
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.path.basename(filepath)}"
        )

        if ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp"]:
            destino = os.path.join(PASTA_IMAGENS, nome_arquivo)
        elif ext in [".mp4", ".avi", ".mkv", ".mov"]:
            destino = os.path.join(PASTA_VIDEOS, nome_arquivo)
        elif ext in [".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".wma"]:
            destino = os.path.join(PASTA_MUSICAS, nome_arquivo)
        else:
            destino = os.path.join("midia", nome_arquivo)

        shutil.copy(filepath, destino)
        caminho_midia_selecionado = destino
        lbl_midia_status.config(
            text=f"📎 Anexado: {os.path.basename(destino)}"
        )


def salvar_nota_local():
    global caminho_midia_selecionado
    categoria = combo_categoria_criar.get().strip()
    data_br = entry_data.get().strip()
    horario_br = datetime.now().strftime("%H:%M:%S")  # REGISTRA O HORÁRIO
    titulo = entry_titulo.get().strip()
    conteudo = txt_conteudo.get("1.0", tk.END).strip()

    if not titulo or not conteudo:
        messagebox.showwarning(
            "Aviso", "Escreva um título e o conteúdo da nota."
        )
        return

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO notes (user_id, categoria, titulo, conteudo, caminho_midia, data, horario)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                logged_user_id,
                categoria,
                titulo,
                conteudo,
                caminho_midia_selecionado,
                data_br,
                horario_br,
            ),
        )
        conn.commit()

    entry_titulo.delete(0, tk.END)
    txt_conteudo.delete("1.0", tk.END)
    caminho_midia_selecionado = ""
    lbl_midia_status.config(text="Nenhum arquivo anexado.")
    carregar_notas_local(categoria_atual)


# --- VISUALIZAR MÍDIAS (IMAGENS, VÍDEOS E MÚSICAS) ---
def visualizar_midia(caminho):
    if not os.path.exists(caminho):
        messagebox.showerror("Erro", "Arquivo de mídia não encontrado.")
        return

    ext = os.path.splitext(caminho)[1].lower()

    if ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp"]:
        win = tk.Toplevel(root)
        win.title("Visualizador de Mídia - Cofre de Notas")
        win.geometry("600x500")

        try:
            img = Image.open(caminho)
            img.thumbnail((560, 440))
            photo = ImageTk.PhotoImage(img)

            lbl_img = tk.Label(win, image=photo)
            lbl_img.image = photo
            lbl_img.pack(expand=True, pady=10)
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir a imagem: {e}")
    elif ext in [".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".wma"]:
        abrir_player_musicas(tocar_arquivo=caminho)
    else:
        # Para vídeos ou arquivos executáveis externos
        try:
            if sys.platform == "win32":
                os.startfile(caminho)
            elif sys.platform == "darwin":
                subprocess.call(["open", caminho])
            else:
                subprocess.call(["xdg-open", caminho])
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao abrir mídia: {e}")


# --- PLAYER DE MÚSICAS OFFLINE (YOUTUBE / ÁUDIO) ---
player_win = None
player_playlist = []
player_musica_atual = ""
player_is_playing = False
player_is_paused = False
player_loop = False
player_shuffle = False
player_volume = 0.8
player_disc_angle = 0
lbl_player_status = None
lbl_player_titulo = None
lbl_player_tempo = None
btn_player_play_pause = None
btn_shuffle = None
btn_loop = None
lbl_vol_percent = None
listbox_playlist = None
canvas_vinil = None
player_segundos_decorridos = 0


def formatar_tempo(segundos):
    m = int(segundos) // 60
    s = int(segundos) % 60
    return f"{m:02d}:{s:02d}"


def obter_arquivos_musica():
    formatos = (".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".wma")
    if not os.path.exists(PASTA_MUSICAS):
        os.makedirs(PASTA_MUSICAS, exist_ok=True)
    arquivos = []
    for f in sorted(os.listdir(PASTA_MUSICAS)):
        if f.lower().endswith(formatos):
            arquivos.append(os.path.join(PASTA_MUSICAS, f))
    return arquivos


def atualizar_listbox_playlist(termo_busca=""):
    global player_playlist
    if listbox_playlist is None or not listbox_playlist.winfo_exists():
        return
    listbox_playlist.delete(0, tk.END)
    todos = obter_arquivos_musica()
    player_playlist = []
    termo = termo_busca.lower().strip()
    for arq in todos:
        nome = os.path.basename(arq)
        if termo == "" or termo in nome.lower():
            player_playlist.append(arq)
            nome_limpo = nome
            if "_" in nome and nome[:8].isdigit():
                partes = nome.split("_", 2)
                if len(partes) >= 3:
                    nome_limpo = partes[2]
                elif len(partes) == 2:
                    nome_limpo = partes[1]
            listbox_playlist.insert(tk.END, f"  🎵 {nome_limpo}")


def desenhar_disco_vinil():
    global player_disc_angle
    if canvas_vinil is None or not canvas_vinil.winfo_exists():
        return
    canvas_vinil.delete("all")
    w = 130
    h = 130
    cx = w // 2
    cy = h // 2
    r = 56

    # Base vinil escuro
    canvas_vinil.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#111827", outline="#374151", width=2)
    # Ranhuras
    canvas_vinil.create_oval(cx - r + 8, cy - r + 8, cx + r - 8, cy + r - 8, fill="", outline="#1F2937", width=1)
    canvas_vinil.create_oval(cx - r + 18, cy - r + 18, cx + r - 18, cy + r - 18, fill="", outline="#1F2937", width=1)
    canvas_vinil.create_oval(cx - r + 26, cy - r + 26, cx + r - 26, cy + r - 26, fill="", outline="#374151", width=1)

    # Rótulo central
    r_center = 22
    cor_rotulo = "#2563EB" if current_theme == "light" else "#3B82F6"
    canvas_vinil.create_oval(cx - r_center, cy - r_center, cx + r_center, cy + r_center, fill=cor_rotulo, outline="")
    canvas_vinil.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill="#0F172A", outline="")

    # Ponto giratório quando em execução
    if player_is_playing and not player_is_paused:
        import math
        rad = math.radians(player_disc_angle)
        x_pt = cx + int((r_center - 7) * math.cos(rad))
        y_pt = cy + int((r_center - 7) * math.sin(rad))
        canvas_vinil.create_oval(x_pt - 3, y_pt - 3, x_pt + 3, y_pt + 3, fill="white", outline="")
        player_disc_angle = (player_disc_angle + 15) % 360


def tocar_faixa_por_caminho(caminho):
    global player_musica_atual, player_is_playing, player_is_paused, player_segundos_decorridos
    if not os.path.exists(caminho):
        messagebox.showerror("Erro", "Arquivo de música não encontrado.")
        return

    player_musica_atual = caminho
    nome = os.path.basename(caminho)
    nome_exibicao = nome
    if "_" in nome and nome[:8].isdigit():
        partes = nome.split("_", 2)
        if len(partes) >= 3:
            nome_exibicao = partes[2]
        elif len(partes) == 2:
            nome_exibicao = partes[1]

    if not AUDIO_SUPPORTED:
        try:
            if sys.platform == "win32":
                os.startfile(caminho)
            else:
                subprocess.call(["xdg-open", caminho])
            if lbl_player_status and lbl_player_status.winfo_exists():
                lbl_player_status.config(text="▶️ Aberto no reprodutor padrão")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível reproduzir: {e}")
        return

    try:
        pygame.mixer.music.load(caminho)
        pygame.mixer.music.set_volume(player_volume)
        pygame.mixer.music.play()
        player_is_playing = True
        player_is_paused = False
        player_segundos_decorridos = 0

        if lbl_player_titulo and lbl_player_titulo.winfo_exists():
            lbl_player_titulo.config(text=nome_exibicao)
        if lbl_player_status and lbl_player_status.winfo_exists():
            lbl_player_status.config(text="▶️ Reproduzindo...")
        if btn_player_play_pause and btn_player_play_pause.winfo_exists():
            btn_player_play_pause.config(text="⏸️ Pausar")
    except Exception as e:
        try:
            if sys.platform == "win32":
                os.startfile(caminho)
            if lbl_player_status and lbl_player_status.winfo_exists():
                lbl_player_status.config(text="▶️ Aberto no reprodutor padrão")
        except Exception:
            messagebox.showerror("Erro ao Tocar", f"Falha ao carregar áudio: {e}")


def pausar_despausar_musica():
    global player_is_paused, player_is_playing
    if not AUDIO_SUPPORTED:
        return
    if not player_is_playing and player_musica_atual:
        tocar_faixa_por_caminho(player_musica_atual)
        return
    elif not player_is_playing and player_playlist:
        tocar_faixa_por_caminho(player_playlist[0])
        return

    if player_is_paused:
        pygame.mixer.music.unpause()
        player_is_paused = False
        if btn_player_play_pause and btn_player_play_pause.winfo_exists():
            btn_player_play_pause.config(text="⏸️ Pausar")
        if lbl_player_status and lbl_player_status.winfo_exists():
            lbl_player_status.config(text="▶️ Reproduzindo...")
    else:
        pygame.mixer.music.pause()
        player_is_paused = True
        if btn_player_play_pause and btn_player_play_pause.winfo_exists():
            btn_player_play_pause.config(text="▶️ Continuar")
        if lbl_player_status and lbl_player_status.winfo_exists():
            lbl_player_status.config(text="⏸️ Pausado")


def parar_musica():
    global player_is_playing, player_is_paused, player_segundos_decorridos
    if AUDIO_SUPPORTED:
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
    player_is_playing = False
    player_is_paused = False
    player_segundos_decorridos = 0
    if btn_player_play_pause and btn_player_play_pause.winfo_exists():
        btn_player_play_pause.config(text="▶️ Tocar")
    if lbl_player_status and lbl_player_status.winfo_exists():
        lbl_player_status.config(text="⏹️ Parado")
    if lbl_player_tempo and lbl_player_tempo.winfo_exists():
        lbl_player_tempo.config(text="00:00")
    desenhar_disco_vinil()


def proxima_musica():
    if not player_playlist:
        return
    if player_shuffle:
        prox_idx = random.randint(0, len(player_playlist) - 1)
    else:
        try:
            idx = player_playlist.index(player_musica_atual)
            prox_idx = (idx + 1) % len(player_playlist)
        except ValueError:
            prox_idx = 0
    tocar_faixa_por_caminho(player_playlist[prox_idx])


def anterior_musica():
    if not player_playlist:
        return
    try:
        idx = player_playlist.index(player_musica_atual)
        ant_idx = (idx - 1) % len(player_playlist)
    except ValueError:
        ant_idx = 0
    tocar_faixa_por_caminho(player_playlist[ant_idx])


def alternar_shuffle():
    global player_shuffle
    player_shuffle = not player_shuffle
    if btn_shuffle and btn_shuffle.winfo_exists():
        btn_shuffle.config(
            bg="#2563EB" if player_shuffle else "#334155",
            fg="white",
        )


def alternar_loop():
    global player_loop
    player_loop = not player_loop
    if btn_loop and btn_loop.winfo_exists():
        btn_loop.config(
            bg="#10B981" if player_loop else "#334155",
            fg="white",
        )


def ajustar_volume_musica(val):
    global player_volume
    player_volume = float(val) / 100.0
    if AUDIO_SUPPORTED:
        try:
            pygame.mixer.music.set_volume(player_volume)
        except Exception:
            pass
    if lbl_vol_percent and lbl_vol_percent.winfo_exists():
        lbl_vol_percent.config(text=f"{int(float(val))}%")


def importar_musicas_dialog():
    arquivos = filedialog.askopenfilenames(
        title="Selecionar Músicas Baixadas do YouTube / PC",
        filetypes=[
            ("Músicas e Áudios", "*.mp3 *.wav *.ogg *.flac *.m4a *.aac *.wma"),
            ("Todos os Arquivos", "*.*"),
        ],
    )
    if arquivos:
        primeira_importada = None
        for arq in arquivos:
            nome = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.path.basename(arq)}"
            dest = os.path.join(PASTA_MUSICAS, nome)
            shutil.copy(arq, dest)
            if not primeira_importada:
                primeira_importada = dest
        atualizar_listbox_playlist()
        messagebox.showinfo(
            "Sucesso", f"{len(arquivos)} música(s) adicionada(s) ao cofre!"
        )
        if primeira_importada:
            tocar_faixa_por_caminho(primeira_importada)


def excluir_musica_selecionada():
    if not listbox_playlist or not listbox_playlist.winfo_exists():
        return
    sel = listbox_playlist.curselection()
    if not sel:
        messagebox.showwarning(
            "Aviso", "Selecione uma música da lista para excluir."
        )
        return
    idx = sel[0]
    if idx < len(player_playlist):
        caminho = player_playlist[idx]
        nome = os.path.basename(caminho)
        if messagebox.askyesno(
            "Confirmar Exclusão", f"Deseja remover do cofre:\n{nome}?"
        ):
            if player_musica_atual == caminho:
                parar_musica()
            try:
                os.remove(caminho)
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível excluir: {e}")
            atualizar_listbox_playlist()


def loop_monitor_musica():
    global player_segundos_decorridos
    if player_win and player_win.winfo_exists():
        if player_is_playing and not player_is_paused and AUDIO_SUPPORTED:
            player_segundos_decorridos += 1
            if lbl_player_tempo and lbl_player_tempo.winfo_exists():
                lbl_player_tempo.config(
                    text=formatar_tempo(player_segundos_decorridos)
                )
            desenhar_disco_vinil()

            try:
                if not pygame.mixer.music.get_busy():
                    if player_loop:
                        tocar_faixa_por_caminho(player_musica_atual)
                    else:
                        proxima_musica()
            except Exception:
                pass

        player_win.after(1000, loop_monitor_musica)


def abrir_player_musicas(tocar_arquivo=None):
    global player_win, lbl_player_status, lbl_player_titulo, lbl_player_tempo
    global btn_player_play_pause, listbox_playlist, canvas_vinil, lbl_vol_percent
    global btn_shuffle, btn_loop

    colors = THEMES[current_theme]

    if player_win is not None and player_win.winfo_exists():
        player_win.lift()
        if tocar_arquivo:
            tocar_faixa_por_caminho(tocar_arquivo)
        return

    player_win = tk.Toplevel(root)
    player_win.title("🎵 Player de Músicas - Cofre de Notas")
    player_win.geometry("540x660")
    player_win.minsize(480, 580)
    player_win.configure(bg=colors["bg"])

    try:
        icon_p = obter_logo_image(32, 32)
        if icon_p:
            player_win.iconphoto(False, icon_p)
    except Exception:
        pass

    # --- CARD SUPERIOR COM VINIL E METADADOS ---
    card_topo = tk.Frame(
        player_win,
        bg=colors["card"],
        highlightbackground=colors["card_border"],
        highlightthickness=1,
        padx=20,
        pady=15,
    )
    card_topo.pack(fill="x", padx=15, pady=(15, 10))

    canvas_vinil = tk.Canvas(
        card_topo, width=130, height=130, bg=colors["card"], highlightthickness=0
    )
    canvas_vinil.pack(side="left", padx=(0, 15))
    desenhar_disco_vinil()

    info_box = tk.Frame(card_topo, bg=colors["card"])
    info_box.pack(side="left", fill="both", expand=True)

    lbl_tag = tk.Label(
        info_box,
        text=" REPRODUTOR OFFLINE ",
        font=FONT_SMALL,
        bg=colors["tag_bg"],
        fg=colors["tag_fg"],
    )
    lbl_tag.pack(anchor="w", pady=(0, 6))

    nome_display = "Nenhuma música selecionada"
    if player_musica_atual:
        bname = os.path.basename(player_musica_atual)
        if "_" in bname and bname[:8].isdigit():
            nome_display = bname.split("_", 2)[-1]
        else:
            nome_display = bname

    lbl_player_titulo = tk.Label(
        info_box,
        text=nome_display,
        font=("Segoe UI", 12, "bold"),
        bg=colors["card"],
        fg=colors["text_main"],
        wraplength=280,
        justify="left",
        anchor="w",
    )
    lbl_player_titulo.pack(fill="x")

    status_txt = "▶️ Reproduzindo..." if (player_is_playing and not player_is_paused) else "⏸️ Pausado" if player_is_paused else "⏹️ Parado"
    lbl_player_status = tk.Label(
        info_box,
        text=status_txt,
        font=FONT_SMALL,
        bg=colors["card"],
        fg=colors["text_muted"],
    )
    lbl_player_status.pack(anchor="w", pady=(4, 6))

    lbl_player_tempo = tk.Label(
        info_box,
        text=formatar_tempo(player_segundos_decorridos),
        font=("Segoe UI", 14, "bold"),
        bg=colors["card"],
        fg=colors["primary"],
    )
    lbl_player_tempo.pack(anchor="w")

    # --- CONTROLES DE REPRODUÇÃO ---
    frame_controles = tk.Frame(
        player_win,
        bg=colors["card"],
        highlightbackground=colors["card_border"],
        highlightthickness=1,
        padx=15,
        pady=10,
    )
    frame_controles.pack(fill="x", padx=15, pady=(0, 10))

    btn_box = tk.Frame(frame_controles, bg=colors["card"])
    btn_box.pack(fill="x", pady=(0, 8))

    btn_shuffle = tk.Button(
        btn_box,
        text="🔀",
        font=FONT_REGULAR,
        bg="#2563EB" if player_shuffle else "#334155",
        fg="white",
        bd=0,
        padx=8,
        pady=4,
        cursor="hand2",
        command=alternar_shuffle,
    )
    btn_shuffle.pack(side="left", padx=2)

    btn_prev = tk.Button(
        btn_box,
        text="⏮️ Anterior",
        font=FONT_REGULAR,
        bg="#334155" if current_theme == "dark" else "#E2E8F0",
        fg="white" if current_theme == "dark" else "#0F172A",
        bd=0,
        padx=10,
        pady=4,
        cursor="hand2",
        command=anterior_musica,
    )
    btn_prev.pack(side="left", padx=4)

    btn_player_play_pause = tk.Button(
        btn_box,
        text="⏸️ Pausar" if (player_is_playing and not player_is_paused) else "▶️ Tocar",
        font=FONT_SUBTITLE,
        bg=colors["primary"],
        fg="white",
        bd=0,
        padx=14,
        pady=5,
        cursor="hand2",
        command=pausar_despausar_musica,
    )
    btn_player_play_pause.pack(side="left", padx=4)

    btn_stop = tk.Button(
        btn_box,
        text="⏹️ Parar",
        font=FONT_REGULAR,
        bg="#334155" if current_theme == "dark" else "#E2E8F0",
        fg="white" if current_theme == "dark" else "#0F172A",
        bd=0,
        padx=10,
        pady=4,
        cursor="hand2",
        command=parar_musica,
    )
    btn_stop.pack(side="left", padx=4)

    btn_next = tk.Button(
        btn_box,
        text="Próxima ⏭️",
        font=FONT_REGULAR,
        bg="#334155" if current_theme == "dark" else "#E2E8F0",
        fg="white" if current_theme == "dark" else "#0F172A",
        bd=0,
        padx=10,
        pady=4,
        cursor="hand2",
        command=proxima_musica,
    )
    btn_next.pack(side="left", padx=4)

    btn_loop = tk.Button(
        btn_box,
        text="🔁",
        font=FONT_REGULAR,
        bg="#10B981" if player_loop else "#334155",
        fg="white",
        bd=0,
        padx=8,
        pady=4,
        cursor="hand2",
        command=alternar_loop,
    )
    btn_loop.pack(side="right", padx=2)

    # Controle de Volume
    vol_box = tk.Frame(frame_controles, bg=colors["card"])
    vol_box.pack(fill="x", pady=(4, 0))

    tk.Label(
        vol_box,
        text="🔊 Volume:",
        font=FONT_SMALL,
        bg=colors["card"],
        fg=colors["text_muted"],
    ).pack(side="left")
    scale_vol = ttk.Scale(
        vol_box,
        from_=0,
        to=100,
        orient="horizontal",
        command=ajustar_volume_musica,
    )
    scale_vol.set(int(player_volume * 100))
    scale_vol.pack(side="left", fill="x", expand=True, padx=10)

    lbl_vol_percent = tk.Label(
        vol_box,
        text=f"{int(player_volume * 100)}%",
        font=FONT_SMALL,
        bg=colors["card"],
        fg=colors["text_main"],
        width=5,
    )
    lbl_vol_percent.pack(side="left")

    # --- SEÇÃO DA PLAYLIST ---
    frame_playlist = tk.Frame(
        player_win,
        bg=colors["card"],
        highlightbackground=colors["card_border"],
        highlightthickness=1,
        padx=15,
        pady=12,
    )
    frame_playlist.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    top_pl = tk.Frame(frame_playlist, bg=colors["card"])
    top_pl.pack(fill="x", pady=(0, 8))

    tk.Label(
        top_pl,
        text="📂 Músicas (YouTube / Local)",
        font=FONT_SUBTITLE,
        bg=colors["card"],
        fg=colors["text_main"],
    ).pack(side="left")

    btn_add_musica = tk.Button(
        top_pl,
        text="➕ Importar Músicas",
        font=FONT_SMALL,
        bg="#10B981",
        fg="white",
        bd=0,
        padx=8,
        pady=3,
        cursor="hand2",
        command=importar_musicas_dialog,
    )
    btn_add_musica.pack(side="right", padx=2)

    btn_pasta_mus = tk.Button(
        top_pl,
        text="📁 Abrir Pasta",
        font=FONT_SMALL,
        bg="#334155" if current_theme == "dark" else "#E2E8F0",
        fg="white" if current_theme == "dark" else "#0F172A",
        bd=0,
        padx=6,
        pady=3,
        cursor="hand2",
        command=lambda: os.startfile(PASTA_MUSICAS)
        if sys.platform == "win32"
        else subprocess.call(["open", PASTA_MUSICAS]),
    )
    btn_pasta_mus.pack(side="right", padx=4)

    # Busca
    frame_busca = tk.Frame(frame_playlist, bg=colors["card"])
    frame_busca.pack(fill="x", pady=(0, 6))
    tk.Label(frame_busca, text="🔍", bg=colors["card"]).pack(side="left")
    entry_busca_mus = ttk.Entry(frame_busca)
    entry_busca_mus.pack(side="left", fill="x", expand=True, padx=5)
    entry_busca_mus.bind(
        "<KeyRelease>",
        lambda e: atualizar_listbox_playlist(entry_busca_mus.get()),
    )

    list_frame = tk.Frame(frame_playlist, bg=colors["card"])
    list_frame.pack(fill="both", expand=True)

    scroll_pl = ttk.Scrollbar(list_frame, orient="vertical")
    listbox_playlist = tk.Listbox(
        list_frame,
        yscrollcommand=scroll_pl.set,
        bg=colors["input_bg"],
        fg=colors["text_main"],
        selectbackground=colors["primary"],
        selectforeground="white",
        font=FONT_REGULAR,
        bd=1,
        relief="solid",
        highlightthickness=0,
        activestyle="none",
    )
    scroll_pl.config(command=listbox_playlist.yview)
    scroll_pl.pack(side="right", fill="y")
    listbox_playlist.pack(side="left", fill="both", expand=True)

    def on_duplo_clique(event):
        sel = listbox_playlist.curselection()
        if sel and sel[0] < len(player_playlist):
            tocar_faixa_por_caminho(player_playlist[sel[0]])

    listbox_playlist.bind("<Double-Button-1>", on_duplo_clique)

    btn_del_mus = tk.Button(
        frame_playlist,
        text="🗑️ Remover Música Selecionada",
        font=FONT_SMALL,
        bg="#EF4444",
        fg="white",
        bd=0,
        pady=3,
        cursor="hand2",
        command=excluir_musica_selecionada,
    )
    btn_del_mus.pack(anchor="e", pady=(8, 0))

    atualizar_listbox_playlist()

    if tocar_arquivo:
        tocar_faixa_por_caminho(tocar_arquivo)

    loop_monitor_musica()


def carregar_notas_local(filtro_cat="Todas"):
    global categoria_atual
    categoria_atual = filtro_cat
    colors = THEMES[current_theme]

    for child in frame_lista_cards.winfo_children():
        child.destroy()

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        if filtro_cat != "Todas":
            cursor.execute(
                "SELECT id, categoria, titulo, conteudo, caminho_midia, data,"
                " horario FROM notes WHERE user_id = ? AND categoria = ?"
                " ORDER BY id DESC",
                (logged_user_id, filtro_cat),
            )
        else:
            cursor.execute(
                "SELECT id, categoria, titulo, conteudo, caminho_midia, data,"
                " horario FROM notes WHERE user_id = ? ORDER BY id DESC",
                (logged_user_id,),
            )
        notas = cursor.fetchall()

    lbl_metric_total.config(text=str(len(notas)))

    if not notas:
        lbl_vazio = tk.Label(
            frame_lista_cards,
            text="Nenhuma nota encontrada neste cofre.",
            font=FONT_REGULAR,
            bg=colors["bg"],
            fg=colors["text_muted"],
        )
        lbl_vazio.pack(pady=30)
        return

    for n in notas:
        card = tk.Frame(
            frame_lista_cards,
            bg=colors["card"],
            highlightbackground=colors["card_border"],
            highlightthickness=1,
            padx=15,
            pady=12,
        )
        card.pack(fill="x", pady=6)

        top_card = tk.Frame(card, bg=colors["card"])
        top_card.pack(fill="x")

        badge = tk.Label(
            top_card,
            text=f" {n[1].upper()} ",
            font=FONT_SMALL,
            bg=colors["tag_bg"],
            fg=colors["tag_fg"],
        )
        badge.pack(side="left")

        # Exibe Data + Horário de armazenamento
        horario_str = f" às {n[6]}" if n[6] else ""
        lbl_data = tk.Label(
            top_card,
            text=f"📅 {n[5]}{horario_str}",
            font=FONT_SMALL,
            fg=colors["text_muted"],
            bg=colors["card"],
        )
        lbl_data.pack(side="right")

        lbl_tit = tk.Label(
            card,
            text=n[2],
            font=FONT_SUBTITLE,
            bg=colors["card"],
            fg=colors["text_main"],
            anchor="w",
        )
        lbl_tit.pack(fill="x", pady=(6, 2))

        lbl_cont = tk.Label(
            card,
            text=n[3],
            font=FONT_REGULAR,
            bg=colors["card"],
            fg=colors["text_muted"],
            justify="left",
            wraplength=520,
            anchor="w",
        )
        lbl_cont.pack(fill="x")

        # Exibe a Mídia com Botão para Acessar/Visualizar
        if n[4]:
            midia_frame = tk.Frame(card, bg=colors["card"])
            midia_frame.pack(fill="x", pady=(6, 0))

            midia_nome = os.path.basename(n[4])
            lbl_midia = tk.Label(
                midia_frame,
                text=f"📎 Mídia: {midia_nome}",
                font=FONT_SMALL,
                bg=colors["card"],
                fg=colors["primary"],
                anchor="w",
            )
            lbl_midia.pack(side="left")

            ext_m = os.path.splitext(n[4])[1].lower()
            txt_btn = (
                "▶️ Ouvir Música"
                if ext_m in [".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".wma"]
                else "👁️ Visualizar Mídia"
            )
            btn_ver_midia = tk.Button(
                midia_frame,
                text=txt_btn,
                font=FONT_SMALL,
                bg=colors["primary"],
                fg="white",
                bd=0,
                padx=6,
                cursor="hand2",
                command=lambda path=n[4]: visualizar_midia(path),
            )
            btn_ver_midia.pack(side="right")

        btn_del = tk.Button(
            card,
            text="Excluir",
            font=FONT_SMALL,
            bg="#7F1D1D" if current_theme == "dark" else "#FEE2E2",
            fg="#FCA5A5" if current_theme == "dark" else "#DC2626",
            bd=0,
            padx=8,
            cursor="hand2",
            command=lambda nid=n[0]: excluir_nota_local(nid),
        )
        btn_del.pack(anchor="e", pady=(8, 0))


def excluir_nota_local(note_id):
    if messagebox.askyesno("Confirmar", "Deseja excluir esta nota do cofre?"):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            conn.commit()
        carregar_notas_local(categoria_atual)


# --- ALTERAR TEMA (MODO DARK / CLARO) ---
def alternar_tema():
    global current_theme
    current_theme = "dark" if current_theme == "light" else "light"
    aplicar_tema()


def aplicar_tema():
    colors = THEMES[current_theme]
    root.configure(bg=colors["bg"])

    for f in (
        frame_login,
        frame_cadastro,
        frame_recuperacao,
        frame_main,
        content_area,
        metrics_frame,
        frame_lista_cards,
        canvas,
    ):
        f.configure(bg=colors["bg"])

    for card in (
        card_login,
        card_cad,
        card_rec,
        m_card1,
        card_criar,
        row1,
        frame_redefinir,
    ):
        card.configure(bg=colors["card"])
        if hasattr(card, "configure") and "highlightbackground" in card.keys():
            card.configure(highlightbackground=colors["card_border"])

    for widget in root.winfo_children():
        atualizar_cores_recursivo(widget, colors)

    btn_tema_side.config(
        text="🌙 Modo Escuro" if current_theme == "light" else "☀️ Modo Claro"
    )
    btn_tema_login.config(
        text="🌙 Modo Escuro" if current_theme == "light" else "☀️ Modo Claro"
    )

    renderizar_logo(canvas_logo_login, 64, 64, colors["card"])
    renderizar_logo(canvas_logo_side, 40, 40, "#0F172A")

    if logged_user_id:
        carregar_notas_local(categoria_atual)


def atualizar_cores_recursivo(widget, colors):
    try:
        w_type = widget.winfo_class()
        if w_type == "Label":
            if widget.cget("bg") not in [
                colors["tag_bg"],
                "#1E3A8A",
                "#E0F2FE",
            ]:
                if widget.cget("fg") not in [
                    colors["primary"],
                    colors["accent"],
                    colors["tag_fg"],
                ]:
                    bg_cor = (
                        colors["card"]
                        if widget.master.cget("bg") == colors["card"]
                        else colors["bg"]
                    )
                    widget.configure(bg=bg_cor, fg=colors["text_main"])
        elif w_type == "Text":
            widget.configure(
                bg=colors["input_bg"],
                fg=colors["text_main"],
                insertbackground=colors["text_main"],
            )
    except Exception:
        pass

    for child in widget.winfo_children():
        atualizar_cores_recursivo(child, colors)


def mostrar_frame(frame_desejado):
    for f in (frame_login, frame_cadastro, frame_recuperacao, frame_main):
        f.pack_forget()
    frame_desejado.pack(fill="both", expand=True)


# --- INTERFACE GRÁFICA ---
init_db()

root = tk.Tk()
root.title("Cofre de Notas - Gerenciador Pessoal")
root.geometry("920x700")

# Ícone do aplicativo na janela e na barra de tarefas
try:
    _icon_img = obter_logo_image(64, 64)
    if _icon_img:
        root.iconphoto(False, _icon_img)
except Exception:
    pass

style = ttk.Style()
style.theme_use("clam")

# 1. TELA DE LOGIN
frame_login = tk.Frame(root)
card_login = tk.Frame(frame_login, padx=35, pady=35, highlightthickness=1)
card_login.pack(pady=50)

canvas_logo_login = tk.Canvas(
    card_login, width=64, height=64, highlightthickness=0
)
canvas_logo_login.pack(pady=(0, 10))

tk.Label(card_login, text="Cofre de Notas", font=("Segoe UI", 22, "bold")).pack()
tk.Label(
    card_login, text="Seu Cofre de Notas & Senhas Offline", font=FONT_REGULAR
).pack(pady=(0, 15))

tk.Label(card_login, text="Usuário:", font=FONT_REGULAR).pack(anchor="w")
entry_user = ttk.Entry(card_login, width=32)
entry_user.pack(pady=(2, 10))

tk.Label(card_login, text="Senha:", font=FONT_REGULAR).pack(anchor="w")
entry_pass = ttk.Entry(card_login, show="*", width=32)
entry_pass.pack(pady=(2, 15))

btn_entrar = tk.Button(
    card_login,
    text="Abrir Cofre",
    command=fazer_login_local,
    bg="#3B82F6",
    fg="white",
    font=FONT_SUBTITLE,
    bd=0,
    width=26,
    pady=6,
    cursor="hand2",
)
btn_entrar.pack(pady=5)

btn_cad = tk.Button(
    card_login,
    text="Criar nova conta",
    command=lambda: mostrar_frame(frame_cadastro),
    fg="#3B82F6",
    font=FONT_REGULAR,
    bd=0,
    cursor="hand2",
)
btn_cad.pack(pady=2)

btn_rec = tk.Button(
    card_login,
    text="Esqueci minha senha",
    command=lambda: mostrar_frame(frame_recuperacao),
    font=FONT_SMALL,
    bd=0,
    cursor="hand2",
)
btn_rec.pack(pady=2)

btn_tema_login = tk.Button(
    card_login,
    text="🌙 Modo Escuro",
    command=alternar_tema,
    font=FONT_SMALL,
    bd=0,
    cursor="hand2",
)
btn_tema_login.pack(pady=(10, 0))

# 2. TELA DE CADASTRO
frame_cadastro = tk.Frame(root)
card_cad = tk.Frame(frame_cadastro, padx=30, pady=25, highlightthickness=1)
card_cad.pack(pady=20)

tk.Label(card_cad, text="🔐 Criar Conta no Cofre", font=FONT_TITLE).pack(
    pady=(0, 15)
)

fields = [
    ("Nome Completo *:", "cad_nome"),
    ("Data Nasc. (DD/MM/AAAA) *:", "cad_nasc"),
    ("Celular *:", "cad_celular"),
    ("Usuário *:", "cad_user"),
]

entries = {}
for label_text, var_name in fields:
    tk.Label(card_cad, text=label_text, font=FONT_REGULAR).pack(anchor="w")
    e = ttk.Entry(card_cad, width=35)
    e.pack(pady=(2, 6))
    entries[var_name] = e

cad_nome, cad_nasc, cad_celular, cad_user = (
    entries["cad_nome"],
    entries["cad_nasc"],
    entries["cad_celular"],
    entries["cad_user"],
)

tk.Label(card_cad, text="Senha *:", font=FONT_REGULAR).pack(anchor="w")
cad_pass = ttk.Entry(card_cad, show="*", width=35)
cad_pass.pack(pady=(2, 6))

tk.Label(card_cad, text="Confirmar Senha *:", font=FONT_REGULAR).pack(
    anchor="w"
)
cad_pass_confirm = ttk.Entry(card_cad, show="*", width=35)
cad_pass_confirm.pack(pady=(2, 8))

tk.Label(
    card_cad, text="Pergunta de Recuperação (Opcional):", font=FONT_REGULAR
).pack(anchor="w")
cad_pergunta = ttk.Entry(card_cad, width=35)
cad_pergunta.pack(pady=(2, 6))

tk.Label(
    card_cad, text="Resposta (Caps Lock Automático):", font=FONT_REGULAR
).pack(anchor="w")
cad_resposta = ttk.Entry(card_cad, width=35)
cad_resposta.pack(pady=(2, 12))

btn_salvar_cad = tk.Button(
    card_cad,
    text="Finalizar Cadastro",
    command=cadastrar_usuario_local,
    bg="#10B981",
    fg="white",
    font=FONT_SUBTITLE,
    bd=0,
    width=28,
    pady=5,
    cursor="hand2",
)
btn_salvar_cad.pack(pady=5)

btn_voltar_cad = tk.Button(
    card_cad,
    text="Voltar ao Login",
    command=lambda: mostrar_frame(frame_login),
    font=FONT_REGULAR,
    bd=0,
    cursor="hand2",
)
btn_voltar_cad.pack()

# 3. TELA DE RECUPERAÇÃO DE SENHA
frame_recuperacao = tk.Frame(root)
card_rec = tk.Frame(frame_recuperacao, padx=30, pady=25, highlightthickness=1)
card_rec.pack(pady=50)

tk.Label(card_rec, text="🔑 Recuperar Acesso ao Cofre", font=FONT_TITLE).pack(
    pady=(0, 15)
)

tk.Label(card_rec, text="Digite seu Usuário:", font=FONT_REGULAR).pack(
    anchor="w"
)
rec_user = ttk.Entry(card_rec, width=35)
rec_user.pack(pady=(2, 8))

btn_buscar = tk.Button(
    card_rec,
    text="Buscar Pergunta",
    command=buscar_pergunta_local,
    bg="#3B82F6",
    fg="white",
    font=FONT_REGULAR,
    bd=0,
    cursor="hand2",
)
btn_buscar.pack(pady=5)

lbl_pergunta_exibida = tk.Label(
    card_rec, text="", font=("Segoe UI", 10, "italic"), wraplength=300
)
lbl_pergunta_exibida.pack(pady=10)

frame_redefinir = tk.Frame(card_rec)
tk.Label(frame_redefinir, text="Sua Resposta:", font=FONT_REGULAR).pack(
    anchor="w"
)
rec_resposta = ttk.Entry(frame_redefinir, width=35)
rec_resposta.pack(pady=(2, 6))

tk.Label(frame_redefinir, text="Nova Senha:", font=FONT_REGULAR).pack(
    anchor="w"
)
rec_novasenha = ttk.Entry(frame_redefinir, show="*", width=35)
rec_novasenha.pack(pady=(2, 10))

btn_redef = tk.Button(
    frame_redefinir,
    text="Alterar Senha",
    command=redefinir_senha_local,
    bg="#10B981",
    fg="white",
    font=FONT_SUBTITLE,
    bd=0,
    width=25,
    cursor="hand2",
)
btn_redef.pack(pady=5)

btn_voltar_rec = tk.Button(
    card_rec,
    text="Voltar ao Login",
    command=lambda: mostrar_frame(frame_login),
    font=FONT_REGULAR,
    bd=0,
    cursor="hand2",
)
btn_voltar_rec.pack(pady=10)

# 4. DASHBOARD PRINCIPAL
frame_main = tk.Frame(root)

# --- SIDEBAR LATERAL ---
sidebar = tk.Frame(frame_main, bg="#0F172A", width=230, padx=15, pady=20)
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)

logo_box = tk.Frame(sidebar, bg="#0F172A")
logo_box.pack(fill="x", pady=(0, 15))

canvas_logo_side = tk.Canvas(
    logo_box, width=40, height=40, bg="#0F172A", highlightthickness=0
)
canvas_logo_side.pack(side="left", padx=(0, 6))

tk.Label(
    logo_box,
    text="Cofre de Notas",
    font=("Segoe UI", 13, "bold"),
    bg="#0F172A",
    fg="white",
).pack(side="left", padx=5)

lbl_user_profile = tk.Label(
    sidebar, text="👤 Usuário", font=FONT_SUBTITLE, bg="#0F172A", fg="#94A3B8"
)
lbl_user_profile.pack(anchor="w", pady=(0, 15))

btn_tema_side = tk.Button(
    sidebar,
    text="🌙 Modo Escuro",
    command=alternar_tema,
    bg="#1E293B",
    fg="white",
    font=FONT_REGULAR,
    bd=0,
    cursor="hand2",
)
btn_tema_side.pack(fill="x", pady=(0, 15))

tk.Label(
    sidebar,
    text="PASTAS & GRUPOS",
    font=FONT_SMALL,
    bg="#0F172A",
    fg="#64748B",
).pack(anchor="w", pady=(10, 5))

pastas = ["Todas", "Geral", "Senhas", "Lembretes", "Trabalho", "Pessoal"]
for p in pastas:
    btn_pasta = tk.Button(
        sidebar,
        text=f"📁 {p}",
        font=FONT_REGULAR,
        bg="#0F172A",
        fg="#E2E8F0",
        bd=0,
        anchor="w",
        cursor="hand2",
        command=lambda cat=p: carregar_notas_local(cat),
    )
    btn_pasta.pack(fill="x", pady=2)

btn_player_mus = tk.Button(
    sidebar,
    text="🎵 Player de Músicas",
    font=FONT_SUBTITLE,
    bg="#2563EB",
    fg="white",
    bd=0,
    pady=6,
    cursor="hand2",
    command=abrir_player_musicas,
)
btn_player_mus.pack(fill="x", pady=(15, 5))

btn_logout = tk.Button(
    sidebar,
    text="🚪 Fechar Cofre",
    command=lambda: mostrar_frame(frame_login),
    bg="#1E293B",
    fg="white",
    font=FONT_REGULAR,
    bd=0,
    cursor="hand2",
)
btn_logout.pack(side="bottom", fill="x", pady=10)

# --- CONTEÚDO PRINCIPAL ---
content_area = tk.Frame(frame_main, padx=20, pady=15)
content_area.pack(side="right", fill="both", expand=True)

metrics_frame = tk.Frame(content_area)
metrics_frame.pack(fill="x", pady=(0, 10))

m_card1 = tk.Frame(metrics_frame, highlightthickness=1, padx=15, pady=10)
m_card1.pack(side="left", fill="x", expand=True, padx=(0, 10))
tk.Label(m_card1, text="Total de Notas Protegidas", font=FONT_SMALL).pack(
    anchor="w"
)
lbl_metric_total = tk.Label(
    m_card1, text="0", font=("Segoe UI", 18, "bold"), fg="#3B82F6"
)
lbl_metric_total.pack(anchor="w")

card_criar = tk.Frame(content_area, highlightthickness=1, padx=15, pady=15)
card_criar.pack(fill="x", pady=(0, 15))

tk.Label(
    card_criar, text="✍️ Nova Nota / Lembrete", font=FONT_SUBTITLE
).pack(anchor="w", pady=(0, 10))

row1 = tk.Frame(card_criar)
row1.pack(fill="x", pady=2)

tk.Label(row1, text="Grupo:", font=FONT_REGULAR).pack(side="left")
combo_categoria_criar = ttk.Combobox(
    row1,
    values=["Geral", "Senhas", "Lembretes", "Trabalho", "Pessoal"],
    width=12,
    state="readonly",
)
combo_categoria_criar.set("Geral")
combo_categoria_criar.pack(side="left", padx=5)

tk.Label(row1, text="Data:", font=FONT_REGULAR).pack(
    side="left", padx=(10, 0)
)
entry_data = ttk.Entry(row1, width=12)
entry_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
entry_data.pack(side="left", padx=5)

entry_titulo = ttk.Entry(card_criar, width=50)
entry_titulo.pack(fill="x", pady=6)

txt_conteudo = tk.Text(
    card_criar, height=3, font=FONT_REGULAR, bd=1, relief="solid"
)
txt_conteudo.pack(fill="x", pady=4)

row_midia = tk.Frame(card_criar)
row_midia.pack(fill="x", pady=4)

btn_anexar = tk.Button(
    row_midia,
    text="📎 Anexar Imagem / Vídeo",
    command=selecionar_midia,
    font=FONT_SMALL,
    cursor="hand2",
)
btn_anexar.pack(side="left")

lbl_midia_status = tk.Label(
    row_midia, text="Nenhum arquivo anexado.", font=FONT_SMALL, fg="#64748B"
)
lbl_midia_status.pack(side="left", padx=10)

btn_salvar_nota = tk.Button(
    card_criar,
    text="+ Guardar no Cofre",
    command=salvar_nota_local,
    bg="#10B981",
    fg="white",
    font=FONT_SUBTITLE,
    bd=0,
    pady=5,
    cursor="hand2",
)
btn_salvar_nota.pack(fill="x", pady=(6, 0))

canvas = tk.Canvas(content_area, highlightthickness=0)
scrollbar = ttk.Scrollbar(content_area, orient="vertical", command=canvas.yview)
frame_lista_cards = tk.Frame(canvas)

frame_lista_cards.bind(
    "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
)
canvas.create_window((0, 0), window=frame_lista_cards, anchor="nw", width=610)
canvas.configure(yscrollcommand=scrollbar.set)

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

aplicar_tema()
mostrar_frame(frame_login)
root.mainloop()
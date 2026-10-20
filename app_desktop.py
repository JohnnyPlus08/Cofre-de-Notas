import os
import shutil
import sqlite3
import subprocess
import sys
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk  # Requer Pillow (pip install pillow)
from werkzeug.security import check_password_hash, generate_password_hash

DB_NAME = "database.db"

# --- CRIAR PASTAS PARA IMAGENS E VÍDEOS ---
PASTA_IMAGENS = os.path.join("midia", "imagens")
PASTA_VIDEOS = os.path.join("midia", "videos")

os.makedirs(PASTA_IMAGENS, exist_ok=True)
os.makedirs(PASTA_VIDEOS, exist_ok=True)


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


# --- DESENHO DA LOGO MINIMALISTA & MODERNA REFORMULADA ---
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
        title="Selecionar Imagem ou Vídeo",
        filetypes=[
            (
                "Arquivos de Mídia",
                "*.png *.jpg *.jpeg *.gif *.bmp *.mp4 *.avi *.mkv *.mov",
            ),
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


# --- VISUALIZAR MÍDIAS (IMAGENS E VÍDEOS) ---
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

            btn_ver_midia = tk.Button(
                midia_frame,
                text="👁️ Visualizar Mídia",
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

    desenhar_logo_cofre_pena(canvas_logo_login, 0, 0)
    desenhar_logo_cofre_pena(canvas_logo_side, 0, 0)

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

style = ttk.Style()
style.theme_use("clam")

# 1. TELA DE LOGIN
frame_login = tk.Frame(root)
card_login = tk.Frame(frame_login, padx=35, pady=35, highlightthickness=1)
card_login.pack(pady=50)

canvas_logo_login = tk.Canvas(
    card_login, width=48, height=48, highlightthickness=0
)
canvas_logo_login.pack()

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
    logo_box, width=48, height=48, bg="#0F172A", highlightthickness=0
)
canvas_logo_side.pack(side="left")

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
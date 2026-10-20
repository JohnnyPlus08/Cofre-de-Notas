# 🔐 Cofre de Notas & Senhas Offline

O **Cofre de Notas** é uma aplicação desktop desenvolvida em Python e Tkinter para gerenciamento seguro e organização pessoal de notas, lembretes, senhas e anexos de mídia (imagens e vídeos). Todo o armazenamento é feito localmente com SQLite, garantindo total privacidade sem dependência de conexões externas.

---

## 🚀 Funcionalidades

- 🔑 **Autenticação Local de Usuários**: Sistema de login e cadastro com senhas criptografadas (`werkzeug.security`).
- ❓ **Recuperação de Senha**: Funcionalidade de redefinição de acesso via pergunta e resposta secreta.
- 📅 **Registro Preciso de Data e Horário**: Armazenamento automático da data (`DD/MM/AAAA`) e do horário exato (`HH:MM:SS`) na criação de cada nota.
- 📁 **Organização por Categorias**: Classificação por grupos/pastas (Geral, Senhas, Lembretes, Trabalho, Pessoal).
- 📎 **Gerenciador e Visualizador de Mídias**:
  - Anexo de imagens (`.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`) e vídeos (`.mp4`, `.avi`, `.mkv`, `.mov`).
  - Visualizador interno para imagens integrado ao app.
  - Acesso direto a vídeos pelo reprodutor padrão do sistema.
- 🌙 **Modo Claro / Escuro**: Suporte a temas dinâmicos (Light e Dark Mode).
- 📊 **Métricas do Cofre**: Contador em tempo real das notas e mídias armazenadas.

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem**: Python 3.x
- **Interface Gráfica**: Tkinter & TTK
- **Manipulação de Imagens**: Pillow (PIL)
- **Banco de Dados**: SQLite3
- **Segurança**: Werkzeug (Hashing de senhas com PBKDF2/SHA256)

---

## 📦 Estrutura do Projeto

```text
Cofre-de-Notas/
│
├── app_desktop.py       # Código fonte principal da aplicação
├── logo.png             # Logotipo do projeto
├── database.db          # Banco de dados SQLite local (gerado automaticamente)
│
└── midia/               # Gerenciado automaticamente pelo app
    ├── imagens/         # Armazenamento local das imagens anexadas
    └── videos/          # Armazenamento local dos vídeos anexados
# TubeGrab

Downloader de YouTube com interface grafica em Python.

Cole o link, escolha video ou audio e baixe na pasta que quiser.

---

## Ideia de criacao do codigo

A ideia e um app desktop simples, visual e direto:

1. Usuario cola o link do YouTube.
2. O app busca titulo, canal, duracao e views.
3. Usuario escolhe Video (MP4) ou Audio (MP3).
4. Se for video, escolhe a qualidade (1080p, 720p etc.).
5. Escolhe a pasta de destino.
6. Clica em Baixar e acompanha o progresso.

### Por que essa stack

| Ferramenta | Papel |
|---|---|
| Python | Linguagem unica, facil de rodar em Windows, Linux e macOS |
| CustomTkinter | Interface grafica moderna em cima do Tkinter, sem Electron |
| yt-dlp | Extrai e baixa video/audio do YouTube (sucessor do youtube-dl) |
| FFmpeg | Junta video+audio e converte o audio para MP3 |
| threading | Download em segundo plano para a janela nao travar |

### Como o codigo esta organizado

Tudo fica em um unico arquivo: `youtube_downloader.py`.

- Constantes de cor e titulo no topo (tema escuro, vermelho YouTube).
- Funcoes auxiliares: detectar pasta Downloads, validar URL, formatar duracao e views.
- Classe `TubeGrab`: monta a janela, trata cliques e dispara as threads.
- `fetch_info()` usa `yt_dlp` so para ler metadados (`skip_download=True`).
- `start_download()` baixa de verdade:
  - Video: melhor video + melhor audio, merge em MP4, com teto de resolucao.
  - Audio: melhor faixa de audio, convertida para MP3 192 kbps via FFmpeg.
- `_progress_hook()` atualiza barra, porcentagem, velocidade e ETA.
- A GUI so e alterada com `self.after(...)`, porque Tkinter nao e thread-safe.

### Decisoes de design

- Um arquivo so: facil de zipar, enviar e rodar.
- Sem banco, sem login, sem API key.
- Playlist: se o link for de playlist, usa o primeiro video.
- Pasta padrao: Downloads do usuario.
- Validacao de URL antes de chamar a rede.
- Botoes desabilitados enquanto busca ou baixa, para evitar clique duplo.

Use apenas com conteudo que voce tem direito de baixar.

---

## Manual do app

### 1. Requisitos

- Python 3.10 ou superior
- FFmpeg no PATH (obrigatorio para MP3 e para juntar video+audio)

### 2. Instalar FFmpeg

**Windows**

1. Baixe em https://www.ffmpeg.org/download.html
2. Extraia e coloque a pasta `bin` no PATH do sistema.
3. Abra um terminal novo e teste:

```bash
ffmpeg -version
```

**Linux**

```bash
sudo apt update
sudo apt install ffmpeg
```

**macOS**

```bash
brew install ffmpeg
```

### 3. Instalar o app

No terminal, entre na pasta do projeto:

```bash
cd TubeGrab
```

Crie um ambiente virtual (recomendado):

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux / macOS:

```bash
source .venv/bin/activate
```

Instale as dependencias:

```bash
pip install -r requirements.txt
```

### 4. Abrir o app

```bash
python youtube_downloader.py
```

A janela TubeGrab deve abrir.

### 5. Como usar

1. Cole o link do YouTube no campo **Link do video**.
   Aceita `youtube.com/watch`, `youtu.be`, Shorts e YouTube Music.
2. Clique em **Buscar** (ou pressione Enter).
3. Confira titulo, canal, duracao e views.
4. Em **O que baixar**, escolha:
   - **Video** — arquivo MP4
   - **Audio MP3** — so o som, em MP3
5. Se escolheu Video, defina a **Qualidade**: Melhor, 1080p, 720p, 480p ou 360p.
6. Em **Pasta de destino**, deixe Downloads ou clique em **Escolher**.
7. Clique em **Baixar**.
8. Acompanhe a barra, a porcentagem, a velocidade e o log.
9. Ao terminar, aparece um aviso com a pasta do arquivo.

### 6. Atalhos e detalhes

- Enter no campo do link = Buscar.
- Download nao trava a janela (roda em thread).
- O nome do arquivo e o titulo do video.
- Video sai em `.mp4`. Audio sai em `.mp3`.

### 7. Problemas comuns

| Problema | O que fazer |
|---|---|
| `No module named tkinter` | Windows: reinstale Python marcando tcl/tk. Linux: `sudo apt install python3-tk` |
| `yt-dlp nao esta instalado` | `pip install -r requirements.txt` |
| Erro de FFmpeg / nao gera MP3 | Instale o FFmpeg e confirme com `ffmpeg -version` |
| Link invalido | Use um link completo do YouTube |
| Download falhou | Video pode ser privado, restrito por idade ou bloqueado na sua rede |
| Janela nao abre no servidor / SSH | Precisa de tela grafica (Windows, macOS ou Linux com desktop) |

### 8. Arquivos do projeto

```text
TubeGrab/
  youtube_downloader.py   App (interface + download)
  requirements.txt        Dependencias Python
  README.md               Este manual
```

`requirements.txt`:

```text
yt-dlp
customtkinter
pillow
```

---

## Aviso

Este app e para uso pessoal e educacional. Respeite os termos do YouTube e os direitos autorais. Nao use para baixar conteudo protegido sem permissao.

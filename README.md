# TubeGrab

Downloader e player de YouTube com interface grafica em Python.

Cole o link de um video ou de uma playlist para reproduzir em sequencia ou baixar.

---

## Ideia de criacao do codigo

A ideia e um app desktop simples, visual e direto:

1. Usuario cola o link do YouTube.
2. O app busca titulo, canal, duracao e views.
3. Usuario escolhe Video (MP4) ou Audio (MP3).
4. Se for video, escolhe a qualidade (1080p, 720p etc.).
5. Escolhe a pasta de destino.
6. Clica em Tocar para ouvir ou em Baixar e acompanha o progresso.
7. Em uma playlist, o player avanca automaticamente para a proxima faixa.

### Por que essa stack

| Ferramenta | Papel |
|---|---|
| Python | Linguagem unica, facil de rodar em Windows, Linux e macOS |
| CustomTkinter | Interface grafica moderna em cima do Tkinter, sem Electron |
| yt-dlp | Extrai e baixa video/audio do YouTube (sucessor do youtube-dl) |
| FFmpeg | Junta video+audio e converte o audio para MP3 |
| VLC / python-vlc | Reproduz os streams de audio sem baixa-los antes |
| threading | Download em segundo plano para a janela nao travar |

### Como o codigo esta organizado

O ponto de entrada continua pequeno em `youtube_downloader.py`; a implementacao fica
dividida no pacote `tubegrab`:

- `app.py`: janela principal e coordenacao dos componentes.
- `downloader.py`: metadados, URLs temporarias de stream e downloads.
- `download_controller.py`: validacao, progresso e integracao do download com a UI.
- `radio.py`: preferencias locais, consultas e pontuacao das recomendacoes.
- `radio_controller.py`: conecta a radio, a fila e os controles da janela.
- `stream_buffer.py`: cache temporario e pre-carga das proximas faixas.
- `settings.py`: preferencias persistentes e valores padrao validados.
- `offline.py`: descoberta e ordenacao de arquivos locais compativeis.
- `models.py`: contrato compartilhado de uma faixa.
- `ui/player_view.py`: construcao visual do card do player.
- `utils.py`: validacao de URL, pasta Downloads e formatacao de textos.
- `config.py`: cores, titulo e tamanho inicial da janela.
- `fetch_info()` usa `yt-dlp` apenas para ler metadados. Em playlists, a extracao e
  rasa para nao abrir todos os videos durante a busca.
- `start_download()` baixa de verdade:
  - Video: melhor video + melhor audio, merge em MP4, com teto de resolucao.
  - Audio: melhor faixa de audio, convertida para MP3 192 kbps via FFmpeg.
- O player resolve somente o stream da faixa atual. A proxima URL e buscada quando
  necessario, reduzindo memoria usada e evitando URLs expiradas.
- Enquanto uma musica toca, as duas proximas URLs de stream sao preparadas em
  segundo plano. O buffer guarda somente metadados por ate 30 minutos, nao o audio.
- No modo aleatorio, o player prioriza uma das faixas que ja estejam no buffer.
- A miniatura tambem e carregada somente para a faixa atual e descartada na troca.
- `_progress_hook()` atualiza barra, porcentagem, velocidade e ETA.
- A GUI so e alterada com `self.after(...)`, porque Tkinter nao e thread-safe.

### Decisoes de design

- Dependencias enxutas e sem banco, login ou API key.
- Playlist: cria uma fila leve, toca em sequencia e pula itens indisponiveis.
- Downloads de playlist ficam em uma subpasta e recebem numeracao na ordem original.
- Pasta padrao: Downloads do usuario.
- Validacao de URL antes de chamar a rede.
- Botoes desabilitados enquanto busca ou baixa, para evitar clique duplo.

A logica de YouTube esta separada da interface. Isso facilita reaproveitar as regras
de fila em uma futura versao Android, embora a interface CustomTkinter e o VLC para
desktop precisem ser substituidos por componentes proprios do Android.

### Interface

- Layout moderno em duas colunas: conteudo e exportacao de um lado, player e
  atividade do outro.
- Barra lateral fixa com atalhos para Inicio, Downloads, Biblioteca e Configuracoes.
- Cards arredondados, contraste suave e acoes principais em destaque.
- Player com miniatura, barra de tempo arrastavel e indicador de duracao.
- Controle de volume independente, sem alterar o volume geral do Windows.
- Fila recolhivel: clique em qualquer musica para iniciar diretamente nela.
- Controle de reproducao aleatoria integrado aos botoes do player.
- Biblioteca offline: abra uma playlist ou uma pasta raiz com varias playlists.
- Radio TubeGrab: amplia a fila com recomendacoes escolhidas por um algoritmo local.
- Botoes **Curtir** e **Pular** ensinam preferencias salvas somente no computador.
- Ao ativar a radio, o app informa que o algoritmo ainda esta em desenvolvimento e
  pode nao ter a mesma precisao de recomendacao de grandes plataformas.
- Interface rolavel para manter os controles acessiveis em telas com pouca altura.
- Nenhum pacote visual pesado ou arquivo de imagem adicional e carregado.
- Seletor no cabecalho com os temas **Azul moderno** e **Vidro neon**.
- A preferencia visual e salva e restaurada automaticamente na proxima execucao.
- A troca de tema reconstroi somente os widgets, preservando player e fila atuais.

### Configuracoes

O atalho **Configuracoes** abre uma janela dividida em sete areas:

- Aparencia: tema, animacoes e modo compacto.
- Reproducao: volume inicial, avancar automaticamente, aleatorio e retomada.
- Downloads: pasta, formato, qualidade, nome dos arquivos e abertura da pasta.
- Biblioteca: pasta raiz, leitura automatica e atualizacao manual.
- Radio: variedade, tamanho dos lotes, lives, covers, remixes e aprendizado.
- Desempenho: tamanho do buffer, modo economico e limpeza do cache.
- Sistema: versoes de Python, yt-dlp e VLC e localizacao do FFmpeg.

As preferencias ficam em `TubeGrab/settings.json` na pasta de configuracoes do
usuario. O modo economico desativa miniaturas e pre-carregamento de streams.

Use apenas com conteudo que voce tem direito de baixar.

---

## Manual do app

### 1. Requisitos

- Python 3.10 ou superior
- FFmpeg no PATH (obrigatorio para MP3 e para juntar video+audio)
- VLC Media Player instalado (obrigatorio para o player; use a mesma arquitetura
  32/64 bits do Python)

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
   Aceita video, playlist, `youtu.be`, Shorts e YouTube Music.
2. Clique em **Buscar** (ou pressione Enter).
3. Confira titulo, canal, duracao e views.
4. Em **O que baixar**, escolha:
   - **Video** — arquivo MP4
   - **Audio MP3** — so o som, em MP3
5. Se escolheu Video, defina a **Qualidade**: Melhor, 1080p, 720p, 480p ou 360p.
6. Em **Pasta de destino**, deixe Downloads ou clique em **Escolher**.
7. Para ouvir sem baixar, clique em **Tocar**. Em playlists, use **Anterior** e
   **Proxima**; a troca tambem acontece automaticamente ao fim da faixa.
   - Arraste a barra de tempo para escolher um trecho da musica.
   - Ajuste **VOL** para controlar somente o som do TubeGrab.
   - Use o botao de setas cruzadas para ativar ou desativar o modo aleatorio.
   - Clique em **Mostrar fila** e selecione qualquer faixa para toca-la.
   - Para ouvir sem internet, clique em **Abrir biblioteca offline**. Voce pode
     escolher a pasta de uma playlist ou uma pasta raiz contendo varias delas.
   - Ative **Radio TubeGrab** para continuar ouvindo sugestoes depois da fila.
   - Use **Curtir** para reforcar escolhas parecidas ou **Pular** para rejeitar uma
     faixa e reduzir recomendacoes semelhantes.
8. Para salvar, clique em **Baixar**.
9. Acompanhe a barra, a porcentagem, a velocidade e o log.
10. Ao terminar, aparece um aviso com a pasta do arquivo.

### 6. Atalhos e detalhes

- Enter no campo do link = Buscar.
- Download nao trava a janela (roda em thread).
- O nome do arquivo e o titulo do video.
- Video sai em `.mp4`. Audio sai em `.mp3`.
- Uma playlist baixada fica em `Downloads/Nome da playlist/` e seus arquivos sao
  numerados.
- O player offline reconhece MP3, M4A, AAC, Opus, OGG, WAV, FLAC, MP4, WebM e MKV.
- A busca offline percorre subpastas, agrupa os arquivos pelo caminho e respeita a
  numeracao criada durante o download.
- As preferencias da radio ficam em `TubeGrab/radio_preferences.json` na pasta de
  configuracoes do usuario. O arquivo guarda apenas URL, titulo e canal.

#### Como a Radio TubeGrab escolhe as musicas

1. Usa titulo e canal da faixa atual para montar buscas musicais.
2. Compara palavras relevantes dos candidatos com a faixa e as curtidas anteriores.
3. Reduz a nota de caracteristicas presentes nas faixas rejeitadas.
4. Favorece duracoes comuns de musica e remove repeticoes, Shorts e lives longas.
5. Adiciona ate seis sugestoes por lote e prepara os proximos streams no buffer.

O YouTube fornece apenas os resultados das buscas montadas pela radio. A classificacao
e o arquivo de aprendizado permanecem locais, sem exigir login ou enviar esse arquivo.

Sugestoes para melhorar a Radio TubeGrab podem ser enviadas para
`br.kemel@gmail.com`.

O botao **Sobre** apresenta a autoria do projeto em uma janela animada e oferece
atalhos para enviar sugestoes ou visitar [devkemel.com.br](https://devkemel.com.br).
- Videos privados, removidos ou bloqueados sao ignorados pelo player, que tenta a
  proxima faixa.

### 7. Problemas comuns

| Problema | O que fazer |
|---|---|
| `No module named tkinter` | Windows: reinstale Python marcando tcl/tk. Linux: `sudo apt install python3-tk` |
| `yt-dlp nao esta instalado` | `pip install -r requirements.txt` |
| Erro de FFmpeg / nao gera MP3 | Instale o FFmpeg e confirme com `ffmpeg -version` |
| Player nao inicia / erro de `libvlc` | Instale o VLC com a mesma arquitetura do Python |
| Link invalido | Use um link completo do YouTube |
| Download falhou | Video pode ser privado, restrito por idade ou bloqueado na sua rede |
| Janela nao abre no servidor / SSH | Precisa de tela grafica (Windows, macOS ou Linux com desktop) |

### 8. Arquivos do projeto

```text
TubeGrab/
  youtube_downloader.py   Ponto de entrada
  tubegrab/
    app.py                Janela e coordenacao dos componentes
    download_controller.py Fluxo de busca e download
    downloader.py         YouTube, streams e downloads
    models.py             Contrato compartilhado de faixa
    offline.py            Descoberta de playlists locais
    radio.py              Algoritmo local de recomendacao
    radio_controller.py   Integracao da radio com o player
    stream_buffer.py      Cache e pre-carregamento
    settings.py           Preferencias persistentes
    themes.py             Paletas e preferencia visual
    ui/
      player_view.py      Interface visual do player
      settings_dialog.py  Janela de configuracoes
    utils.py              Funcoes auxiliares
    config.py             Configuracao visual
  tests/
    test_radio.py         Testes do ranqueamento e preferencias
    test_services.py      Testes de offline e buffer
    test_themes.py        Testes das paletas e persistencia
    test_settings.py      Testes das preferencias gerais
  requirements.txt        Dependencias Python
  README.md               Este manual
```

`requirements.txt`:

```text
yt-dlp
customtkinter
pillow
python-vlc
```

---

## Aviso

Este app e para uso pessoal e educacional. Respeite os termos do YouTube e os direitos autorais. Nao use para baixar conteudo protegido sem permissao.

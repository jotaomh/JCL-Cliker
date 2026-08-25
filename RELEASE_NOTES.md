# JCL Clicker — v0.9.0

Auto clicker com suporte a **X11** e **Wayland**, interface GTK4 e atalho global de teclado.

---

## Destaques desta versão

### 🛠️ Corrigido: o app às vezes "não abria" (janela nunca aparecia)

Causa raiz encontrada rodando o app de verdade e reproduzindo o cenário:

- O `Gtk.Application` registra o nome `io.github.jotaomh.jclclicker` no D-Bus
  da sessão. Se uma instância anterior continuasse viva — inclusive apontando
  para um display morto ou de outra sessão — toda nova execução virava
  "remote instance": o processo **saia silenciosamente, sem abrir janela
  nenhuma**, sem erro no terminal.
- Correção: a aplicação agora usa
  `Gio.ApplicationFlags.NON_UNIQUE`. Cada execução é independente e sempre
  abre sua própria janela (para um utilitário desse tipo, instância única não
  traz benefício — só esse modo de falha).

### 🛠️ Corrigido: corrida no fechamento da janela com o clicker rodando

- Fechar a janela durante a execução podia deixar a thread do clicker
  enfileirando callbacks GTK (`GLib.idle_add`) **depois** da destruição da
  janela.
- O `_on_close_request` agora para o clicker e faz `join(timeout=2)` da
  thread antes de permitir o fechamento; a thread também virou `daemon`,
  então o encerramento nunca fica preso num clique de subprocesso em
  andamento.

### 🛠️ Corrigido: config.json malformada derrubava o app no startup

- Um `config.json` válido mas com tipos errados (ex: `"interval": "0.5"`
  editado à mão) estourava `TypeError` dentro do GTK e o app nem abria.
- O `load_config` agora sanitiza tipos e faixas: intervalo entre 0,01 e 60s,
  botão ∈ {1, 2, 3}, quantidade ≥ 0, tema ∈ {light, dark}. Valor inválido
  volta ao padrão em vez de derrubar o app.

### 🌗 Tema claro e escuro

- Novo switch **"Tema escuro"** no topo da janela alterna entre os dois
  temas na hora.
- Aplica `gtk-application-prefer-dark-theme` via `Gtk.Settings` **e**
  complementa com CSS próprio (fundo/texto por tema) para garantir contraste
  legível mesmo em distros sem a variante escura do tema instalada — não
  depende só do tema do sistema.
- A mensagem de erro da interface ganhou tom de vermelho legível em cada
  tema.
- A preferência é salva em `config.json` (chave `theme`) e restaurada na
  próxima abertura.

### 🦅 Logo do Corinthians na interface

- Novo asset `app/assets/corinthians.png` exibido no cabeçalho da janela via
  `Gtk.Picture` (72px, proporção preservada).
- No tema escuro o escudo ganha um cartão claro por trás (classe `.logo`)
  para não sumir no fundo; no tema claro fica transparente.
- Resolução de caminho reusa a mesma estratégia do ydotool vendorizado
  (`sys._MEIPASS` no PyInstaller, caminho relativo ao pacote no source e em
  `/usr/lib/jcl-clicker/`), então o asset vai junto em **todos os modos**:
  source, `.deb`, `.rpm`, standalone e AppImage. Asset ausente não quebra o
  app.

### 🧹 Repositório: limpeza do nome antigo

- O repositório foi renomeado para **jotaomh/JCL-Cliker**, mas sobravam
  referências ao nome antigo (`AutoClicker-Linux`) no README (instruções de
  `git clone`, árvore de diretórios, roadmap), no README do standalone e na
  URL do spec do `.rpm`. Tudo atualizado — quem clona seguindo o README agora
  cai numa pasta `JCL-Cliker`, como o próprio documento diz.
- Sobrou apenas a referência legítima de migração
  (`~/.config/autoclicker/`), necessária para continuar migrando configs de
  instalações antigas.
- Branch `develop` sincronizada com a `main` (merge das mudanças pendentes).

---

## Instalação

Baixe os artefatos da release:

- **`.deb`** (Debian / Ubuntu / Pop!_OS):
  ```bash
  sudo dpkg -i jcl-clicker_*.deb && sudo apt-get install -f
  ```
- **`.rpm`** (Fedora / RHEL / openSUSE):
  ```bash
  sudo rpm -i jcl-clicker-*.rpm
  ```
- **AppImage** (qualquer distro):
  ```bash
  chmod +x jcl-clicker-*-x86_64.AppImage && ./jcl-clicker-*-x86_64.AppImage
  ```
- **Binário standalone** (qualquer distro):
  ```bash
  tar -xzf jcl-clicker-linux-*-standalone.tar.gz && ./jcl-clicker/install.sh
  ```

> **Wayland:** o `ydotoold` precisa acessar `/dev/uinput`. Crie a regra udev e
> adicione seu usuário ao grupo `input` (veja o README, seção *Permissão de
> input (Wayland)*). No X11 isso não é necessário.

---

## Compatibilidade

Testado em (source, `.deb` instalado, standalone e AppImage):

- Pop!_OS 24.04 LTS (GNOME X11) — sessão real e Xvfb com openbox
- Suíte de testes: `pytest tests/` — 8/8 aprovados

---

## Notas / Próximos passos

- Redesenho visual da GUI e ícone na bandeja do sistema
- Perfis de configuração

---
---

# JCL Clicker — v0.8.0

> Nota histórica: versão do rebranding e da reformulação do empacotamento.

Auto clicker com suporte a **X11** e **Wayland**, interface GTK4 e atalho global de teclado.

---

## Destaques desta versão

### 🏷️ Rebranding completo: JCL Clicker

- Janela, `application_id` (`io.github.jotaomh.jclclicker`), ícone e identidade visual
- Nome interno unificado: pacote, binário, comando e config viraram `jcl-clicker`
- Config migra para `~/.config/jcl-clicker/` **sem perder preferências**:
  instalações antigas (`~/.config/autoclicker/config.json`) e o legado na raiz
  do repo são migrados automaticamente na primeira execução
- Nomes de arquivo históricos mantidos (ex: `autoclicker.desktop` continua com
  esse nome; o conteúdo aponta para o JCL Clicker)

### 📦 Pacotes 100x menores e com o ydotool vendorizado de verdade

Dois bugs críticos de empacotamento corrigidos:

1. **O ydotool vendorizado não ia para os pacotes finais.** O caminho
   `vendor/ydotool/` só era resolvido rodando do source — no binário
   PyInstaller e nas instalações `.deb`/`.rpm` o app sempre caía no fallback
   do ydotool do sistema (a origem do bug de clique lento no Wayland que
   motivou a vendorização). Agora o caminho é resolvido por contexto
   (`sys._MEIPASS` no frozen; relativo ao pacote no source e em
   `/usr/lib/jcl-clicker/`; caminho fixo de sistema como último recurso), e
   **todos os alvos** instalam/embutem o ydotool vendorizado.

2. **Os pacotes saíam com ~100MB** porque o `.deb`/`.rpm` usavam PyInstaller
   `--onefile` embutindo GTK4 + Python inteiros — duplicando o GTK que já
   vinha como dependência de sistema. Novo formato:

| Artefato | Antes | Depois |
|---|---|---|
| `.deb` | 73 MB | **231 KB** |
| `.rpm` | (não gerava no ambiente) | **298 KB** |
| standalone `.tar.gz` | 84 MB (binário 92 MB) | **40 MB** |

- `.deb`/`.rpm` agora são apps Python **nativos**: usam o GTK4/PyGObject do
  sistema e vendorizam apenas as libs puras de pip (pynput, python-xlib,
  six) em `/usr/lib/jcl-clicker/lib/`, junto do código
  (`/usr/lib/jcl-clicker/app/`) e do ydotool (`/usr/lib/jcl-clicker/vendor/`)
- standalone/AppImage seguem com PyInstaller, mas sem os ~135MB de temas de
  ícones que o hook do `gi` coletava por padrão e sem o GTK3 (o app usa só
  GTK4)
- **`Depends: ydotool` removido** do `.deb`/`.rpm` (vira `Recommends`, apenas
  fallback) — era isso que puxava o ydotool do sistema/snap

### 🔌 Socket do ydotoold por usuário

- Socket próprio do app em `$XDG_RUNTIME_DIR` (tmpfs 0700 do usuário), sem
  colisão com um daemon do sistema
- Detecção de daemon morto com erro claro em vez de falha genérica
- Daemon vendorizado sobe automaticamente quando necessário

### 🖼️ AppImage disponível

- Alvo AppImage adicionado (`scripts/build-appimage.sh`), com compressão zstd
- Ícone próprio (256x256) incluído nos três alvos de empacotamento

### 🧰 Outros

- `requirements.txt` limpo (removidos pacotes do SO capturados por engano no
  `pip freeze`; ficam só as dependências reais declaradas do `python-xlib`
  0.33); `requirements-dev.txt` não entra nos artefatos

---

## Instalação

Baixe os artefatos da release:

- **`.deb`** (Debian / Ubuntu / Pop!_OS):
  ```bash
  sudo dpkg -i jcl-clicker_*.deb && sudo apt-get install -f
  ```
- **`.rpm`** (Fedora / RHEL / openSUSE):
  ```bash
  sudo rpm -i jcl-clicker-*.rpm
  ```
- **AppImage** (qualquer distro):
  ```bash
  chmod +x jcl-clicker-*-x86_64.AppImage && ./jcl-clicker-*-x86_64.AppImage
  ```
- **Binário standalone** (qualquer distro):
  ```bash
  tar -xzf jcl-clicker-linux-*-standalone.tar.gz && ./jcl-clicker/install.sh
  ```

> **Wayland:** o `ydotoold` precisa acessar `/dev/uinput`. Crie a regra udev e
> adicione seu usuário ao grupo `input` (veja o README, seção *Permissão de
> input (Wayland)*). No X11 isso não é necessário.

---

## Compatibilidade

Testado em:

- Pop!_OS 24.04 LTS (GNOME X11 / COSMIC Wayland)
- Fedora 44 (GNOME Wayland)

---

## Notas / Próximos passos

- Redesenho visual da GUI e ícone na bandeja do sistema
- Perfis de configuração

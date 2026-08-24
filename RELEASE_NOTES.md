# JCL Clicker — v0.8.0

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
| AppImage | não existia | **41 MB** |

- **`.deb`/`.rpm`** agora são apps Python nativos: código em
  `/usr/lib/jcl-clicker/`, launcher fino em `/usr/bin/jcl-clicker`, GTK4 via
  dependência de sistema (`python3-gi`/`gir1.2-gtk-4.0`,
  `python3-gobject`/`gtk4`), libs puras de pip vendorizadas
  (pynput/python-xlib/six) e ydotool vendorizado incluído.
- **standalone/AppImage** continuam com PyInstaller (precisam ser
  autossuficientes), mas encolheram porque:
  - o hook do `gi` coletava **~135MB de temas de ícones do sistema** por
    padrão — agora desligado via `hooksconfig`
  - o GTK3 inteiro (libs + typelibs) ia junto à toa — o app usa só GTK4
  - módulos não usados excluídos (`tkinter`, `unittest`, `pydoc`, `curses`,
    `lib2to3`, `pytest`)
  - UPX: o PyInstaller desativa UPX fora do Windows por padrão (segfaults
    conhecidos com shared libraries no Linux) — não foi forçado; o payload do
    `--onefile` já sai comprimido com zlib

### 🔌 Wayland mais robusto

- `Depends: ydotool` **removido** do `.deb` (vira `Recommends`, apenas
  fallback) — era isso que puxava o ydotool do snap/sistema, causa original
  da lentidão. No RPM, `Recommends` equivalente.
- `evdev` sai do vendor dos pacotes e vira dependência nativa
  (`python3-evdev`): tem extensão C presa à versão do Python, então a versão
  da distro é a correta. (O pynput declara `evdev>=1.3` como dependência
  transitiva — o build usa `--no-deps` para não vazar para dentro do pacote.)
- Socket do daemon por usuário em `$XDG_RUNTIME_DIR`
  (`jcl-clicker-ydotool.socket`): sem colisão com sockets root-owned de
  daemons do sistema.
- O app espera o socket ficar **acessível** (não apenas existente) — eliminava
  corrida que subia dois daemons.
- Daemon que morre na inicialização vira erro claro com instrução de
  permissão (`/dev/uinput`), em vez de falha genérica do cliente.
- `JCL_CLICKER_DEBUG=1` registra no stderr vendor dir, binário e daemon usados.

### 🖼️ Ícone e AppImage

- Ícone próprio 256x256 (`packaging/icons/jcl-clicker.png`) incluído nos três
  alvos; os builds **falham** se o ícone não existir (antes pulavam em
  silêncio).
- **AppImage disponível** (`scripts/build-appimage.sh`): reaproveita o binário
  standalone, monta a AppDir (desktop + ícone + AppRun) e empacota via
  appimagetool.

---

## Mudanças

### Correções
- ydotool vendorizado não chegava aos pacotes (crítico) — corrigido
- Pacotes ~100MB por duplicação de GTK4/Python — corrigido (tabela acima)
- `Depends: ydotool` puxava a versão lenta do snap/sistema — removido
- Socket compartilhado com daemon do sistema causava falhas — socket por usuário
- Corrida na subida do daemon (spawn duplicado) — corrigida
- Config de instalações antigas (`~/.config/autoclicker/`) migrada automaticamente

### Rebranding
- `application_id` → `io.github.jotaomh.jclclicker`
- Título da janela → "JCL Clicker"
- Pacote/binário/comando → `jcl-clicker`; diretórios `/usr/lib/jcl-clicker/`,
  `~/.local/opt/jcl-clicker/`, `~/.config/jcl-clicker/`
- Maintainer/URL → jotaomh (repo github.com/jotaomh/AutoClicker-Linux)
- Classes internas → `JCLClicker`, `JCLClickerApp`, `JCLClickerWindow`
- Ícone `jcl-clicker.png` gerado (256x256)

### Empacotamento
- `.deb`/`.rpm`: apps Python nativos sem PyInstaller, com launcher fino
- standalone: spec sob medida (`hooksconfig` do `gi`, filtro GTK3, excludes)
- AppImage: novo alvo (`scripts/build-appimage.sh`)
- Ícone obrigatório nos builds (falha explícita se ausente)
- `requirements.txt`: pins validados no PyPI; `six` mantido (dependência
  declarada do `python-xlib` 0.33); `requirements-dev.txt` não entra nos
  artefatos

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

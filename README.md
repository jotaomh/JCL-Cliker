# JCL Clicker (Linux)

Auto clicker com suporte a **X11** e **Wayland**, interface GTK4 e atalho global de teclado.

Projeto desenvolvido em Python com foco em compatibilidade com diferentes ambientes gráficos Linux.

---

## Status

Versão atual: **v0.9.0**

---

## Changelog

### v0.9.0 — tema claro/escuro, logo na interface e bugs de abertura corrigidos

- **Corrigido (crítico): o app às vezes "não abria"** — uma instância
  anterior (mesmo apontando para um display morto ou de outra sessão)
  segurava o nome da aplicação no D-Bus e toda nova execução saía
  silenciosamente, sem abrir janela. Agora cada execução é independente
  (`GApplication NON_UNIQUE`) e sempre abre sua janela.
- **Corrigido:** fechar a janela com o clicker rodando podia deixar callbacks
  GTK pendentes após a destruição da janela — o fechamento agora para o
  clicker e aguarda a thread terminar (com timeout).
- **Corrigido:** `config.json` válido mas com tipos errados (ex:
  `"interval": "0.5"`) derrubava o app com `TypeError` no startup — o config
  agora é sanitizado (tipos e faixas) na leitura.
- **Tema claro/escuro**: switch "Tema escuro" no topo da janela; aplica o
  `prefer-dark` do GTK e complementa com CSS próprio (fundo/texto) para
  contraste garantido mesmo sem a variante escura do tema instalada.
  Preferência salva em `config.json` (`theme`).
- **Logo do Corinthians no cabeçalho** da janela (`Gtk.Picture`, proporção
  preservada, com cartão claro no tema escuro). Asset incluído em todos os
  alvos: source, `.deb`, `.rpm`, standalone e AppImage.
- **Limpeza do nome antigo do repositório**: todas as referências a
  `AutoClicker-Linux` atualizadas para `jotaomh/JCL-Cliker` (README, README
  do standalone, spec do `.rpm`).

### v0.8.0 — rebranding JCL Clicker + pacotamento consertado

- **Rebranding completo para JCL Clicker**: janela, `application_id`
  (`io.github.jotaomh.jclclicker`), nome de pacote/binário/comando
  (`jcl-clicker`), diretório de config (`~/.config/jcl-clicker/`) e ícone.
  Nomes de arquivo históricos mantidos (ex: `autoclicker.desktop`).
- **Migração de config**: instalações antigas em `~/.config/autoclicker/` são
  migradas automaticamente na primeira execução — nada é perdido no rebranding.
- **Corrigido (crítico): o ydotool vendorizado não ia para os pacotes finais**
  - o caminho `vendor/` só era resolvido rodando do source; no binário
    PyInstaller e nas instalações `.deb`/`.rpm` o app caía no ydotool do
    sistema (a origem do bug de clique lento no Wayland)
  - agora o caminho é resolvido por contexto: `sys._MEIPASS` (frozen),
    relativo ao pacote (source e `/usr/lib/jcl-clicker/`) e caminho fixo
  - `.deb`/`.rpm`/standalone/AppImage **instalam/embutem** o ydotool vendorizado
- **Corrigido: pacotes de ~100MB**
  - `.deb`/`.rpm` não usam mais PyInstaller: viraram apps Python nativos que
    usam o GTK4/PyGObject do sistema (73MB → ~230KB no `.deb`)
  - standalone/AppImage seguem com PyInstaller, mas sem os ~135MB de temas de
    ícones que o hook do `gi` coletava por padrão e sem o GTK3 (84MB → 40MB)
- **`Depends: ydotool` removido** do `.deb`/`.rpm` (vira `Recommends`, só
  fallback) — era isso que puxava o ydotool do sistema/snap
- **Socket do ydotoold por usuário** (`$XDG_RUNTIME_DIR`), sem colisão com
  daemon do sistema; detecção de daemon morto com erro claro
- **AppImage disponível** (antes era só plano)
- **Ícone próprio** (256x256) incluído nos três alvos

### v0.7.0

- **Corrigido:** clicker no Wayland não funcionava de fato (vários bugs em cadeia)
  - `--repeat`/`--next-delay` não existiam na versão de `ydotool` disponível
  - Erro real estava sendo engolido por `stderr=DEVNULL`
  - Binário `ydotool` do snap tinha overhead alto por chamada — agora **vendorizado** (compilado do source) em `vendor/ydotool/`
  - Mismatch de caminho de socket entre cliente e daemon
  - `ydotoold` agora sobe **automaticamente**, detectando e limpando sockets órfãos
  - Mapa de botão do mouse corrigido: `ydotool` espera códigos hexadecimais de tecla-mouse (`0xC0`=esquerdo, `0xC1`=direito, `0xC2`=meio), não números decimais simples
- **Empacotamento:** scripts de build para `.deb`, `.rpm` e binário standalone (via PyInstaller)
- **Resultado:** clique estável no Wayland, ~14 cliques/segundo pela interface gráfica (antes: travado em 0)

### v0.6.0 e anteriores

- Base funcional com suporte X11/Wayland, interface GTK4, atalho global de teclado

> Notas de release completas em [RELEASE_NOTES.md](RELEASE_NOTES.md).

---

## Recursos

✅ Controle de mouse no **X11** usando `pynput`  
✅ Controle de mouse no **Wayland** usando `ydotool` (binário vendorizado, com auto-start do daemon)  
✅ Detecção automática da sessão gráfica  
✅ Motor de cliques independente da interface gráfica  
✅ Sistema de callbacks para eventos  
✅ Controle de estados do programa  
✅ Configuração salva em `~/.config/jcl-clicker/config.json` (XDG)  
✅ Execução em thread separada  
✅ Interface gráfica em GTK4  
✅ Tema claro/escuro com switch na interface e persistência da preferência  
✅ Logo de destaque no cabeçalho da janela  
✅ Tratamento de erros (mouse indisponível, ydotool ausente, config corrompida)  
✅ Atalho global de teclado para iniciar/parar (F1-F12, Pause, Scroll Lock)

---

## Arquitetura

O projeto é dividido em módulos para facilitar manutenção e evolução.

| Módulo | Responsabilidade |
|---|---|
| `clicker.py` | Lógica do clicker: intervalo entre cliques, quantidade, execução em segundo plano, eventos, iniciar/parar |
| `mouse.py` | Comunicação com o sistema: `pynput` no X11, `ydotool` vendorizado no Wayland (detecção automática da sessão via `XDG_SESSION_TYPE`) |
| `state.py` | Estados do programa (IDLE, RUNNING, FINISHED, STOPPED, ERROR) |
| `config.py` | Leitura/gravação da configuração em `~/.config/jcl-clicker/config.json` e migração de configs legados |
| `gui.py` | Interface gráfica GTK4 |
| `hotkeys.py` | Atalho global: `pynput` no X11, `evdev` no Wayland |

### Estados do programa

```
        IDLE
          |
       start()
          |
          v
       RUNNING
       /     \
      /       \
FINISHED     STOPPED
```

- `IDLE` → aguardando iniciar
- `RUNNING` → executando cliques
- `FINISHED` → terminou a quantidade configurada
- `STOPPED` → interrompido pelo usuário
- `ERROR` → falha durante a execução

### Configuração

Armazenada em `~/.config/jcl-clicker/config.json` (XDG Base Directory Specification).

| Chave | Padrão | Descrição |
|---|---|---|
| `interval` | `0.1` | Intervalo entre cliques (segundos) |
| `button` | `1` | Botão: 1 = esquerdo, 2 = meio, 3 = direito |
| `amount` | `0` | Quantidade de cliques (0 = infinito) |
| `hotkey` | `f6` | Atalho global iniciar/parar |
| `theme` | `dark` | Tema da interface: `dark` (escuro) ou `light` (claro) |

Valores com tipo ou faixa inválidos são substituídos pelo padrão na leitura
(ex: `"interval": "0.5"` volta para `0.1`) — config malformada nunca impede
o app de abrir.

Configs legadas são migradas automaticamente na primeira execução:

- `config.json` na raiz do projeto (versão pré-XDG)
- `~/.config/autoclicker/config.json` (instalação anterior ao rebranding)

Se houver mais de um, prevalece o modificado por último.

---

## Estrutura do projeto

```
JCL-Cliker
├── app/
│   ├── __init__.py
│   ├── assets/
│   │   └── corinthians.png          (logo exibido no cabeçalho da janela)
│   ├── clicker.py
│   ├── config.py
│   ├── gui.py
│   ├── hotkeys.py
│   ├── main.py
│   ├── mouse.py
│   └── state.py
│
├── vendor/
│   └── ydotool/
│       ├── ydotool                  (cliente, compilado do source)
│       └── ydotoold                 (daemon, compilado do source)
│
├── packaging/
│   ├── autoclicker.desktop          (nome de arquivo histórico; conteúdo → jcl-clicker)
│   ├── postinst.sh
│   ├── icons/
│   │   └── jcl-clicker.png          (256x256)
│   └── standalone/
│       ├── autoclicker.desktop
│       ├── install.sh
│       └── README.txt
│
├── scripts/
│   ├── build-packages.sh            (.deb / .rpm — app Python nativo)
│   ├── build-standalone.sh          (binário standalone via PyInstaller + tar.gz)
│   └── build-appimage.sh            (AppImage)
│
├── tests/
│   └── ...
│
├── README.md
├── config.json                      (legado, migrado no primeiro uso)
└── requirements.txt
```

---

## Tecnologias

| Dependência | Tipo | Finalidade |
|---|---|---|
| Python 3 | Runtime | Linguagem principal |
| pynput | pip | Controle de mouse/teclado no X11 |
| python-xlib | pip | Bindings X11 (dependência do pynput) |
| evdev | pip | Leitura de dispositivos de entrada no Wayland |
| six | pip | Compatibilidade — **mantida**: é dependência declarada do `python-xlib` 0.33, que a importa em runtime |
| GTK4 (PyGObject) | **sistema** | Interface gráfica |
| PyInstaller | pip | Empacotamento standalone/AppImage |
| ydotool | **vendorizado** (`vendor/ydotool/`) | Controle de mouse no Wayland |

---

## Compatibilidade

Testado em:

- Pop!_OS 24.04 LTS (GNOME X11 / COSMIC Wayland)
- Fedora 44 (GNOME Wayland)

---

## Instalação

Existem quatro formas de instalar. O que cada uma precisa do sistema:

| Alvo | GTK4/PyGObject | libs pip (pynput etc.) | ydotool | Tamanho |
|---|---|---|---|---|
| `.deb` / `.rpm` | **do sistema** (dependência do pacote) | vendorizadas no pacote | vendorizado | ~0,3MB |
| standalone | **embutida** no binário | embutidas | vendorizado | ~40MB |
| AppImage | **embutida** no binário | embutidas | vendorizado | ~41MB |
| source | do sistema (via distro) | via pip (`requirements.txt`) | vendorizado no repo | — |

Ou seja: **só o source exige preparar dependências na mão**. Os demais alvos são autossuficientes (o standalone/AppImage até prescindem de GTK instalado, por isso pesam mais).

### Via pacote `.deb` (Debian / Ubuntu / Pop!_OS)

```bash
sudo dpkg -i jcl-clicker_*.deb
sudo apt-get install -f   # resolve dependências, se necessário
```

O pacote declara `python3`, `python3-gi`, `gir1.2-gtk-4.0` e `python3-evdev`
como dependências e instala o comando `jcl-clicker`.

### Via pacote `.rpm` (Fedora / RHEL / openSUSE)

```bash
sudo rpm -i jcl-clicker-*.rpm
```

Dependências equivalentes: `python3`, `python3-gobject`, `gtk4`, `python3-evdev`.

### AppImage (qualquer distro)

Baixe `jcl-clicker-*-x86_64.AppImage` da release e:

```bash
chmod +x jcl-clicker-*-x86_64.AppImage
./jcl-clicker-*-x86_64.AppImage
```

Não requer instalação nem dependências pré-existentes. Para integrar ao menu
do sistema, rode o `install.sh` do tarball standalone (o AppImage em si pode
viver em qualquer pasta).

### Binário standalone (qualquer distro)

Extraia o `jcl-clicker-linux-*-standalone.tar.gz` da release:

```bash
tar -xzf jcl-clicker-linux-*-standalone.tar.gz
cd jcl-clicker
chmod +x install.sh
./install.sh
```

O script instala em `~/.local/opt/jcl-clicker/` e registra o atalho no menu do sistema.

> **Nota sobre tamanho:** standalone e AppImage embutem Python + GTK4
> inteiros — é o preço de rodarem em qualquer distro sem dependências.
> Os `.deb`/`.rpm` usam o GTK do sistema e por isso são ~100x menores.

### A partir do código-fonte (desenvolvimento)

#### 1. Clone o projeto

```bash
git clone https://github.com/jotaomh/JCL-Cliker.git
cd JCL-Cliker
```

#### 2. Crie e ative o ambiente virtual

```bash
python3 -m venv venv --system-site-packages
source venv/bin/activate
```

#### 3. Instale as dependências Python (pip)

```bash
pip install -r requirements.txt
```

#### 4. Instale as dependências do sistema

Os bindings do GTK4 não são instaláveis via pip. O `ydotool`/`ydotoold` já vêm vendorizados no repositório (`vendor/ydotool/`), não é preciso instalá-los separadamente.

<details>
<summary><b>Ubuntu / Pop!_OS / Debian</b></summary>

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 python3-evdev
```

</details>

<details>
<summary><b>Fedora</b></summary>

```bash
sudo dnf install python3-gobject gtk4 python3-evdev
```

</details>

<details>
<summary><b>Arch Linux / Manjaro</b></summary>

```bash
sudo pacman -S python-gobject gtk4 python-evdev
```

</details>

<details>
<summary><b>openSUSE</b></summary>

```bash
sudo zypper install python3-gobject gtk4 python3-evdev
```

</details>

#### 5. Permissão de input (Wayland)

O `ydotoold` precisa acessar `/dev/uinput` no Wayland. Crie a regra `udev` e adicione seu usuário ao grupo `input`:

```bash
echo 'KERNEL=="uinput", GROUP="input", MODE="0660"' | sudo tee /etc/udev/rules.d/80-uinput.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
sudo usermod -aG input $USER
```

Faça **logout/login** (ou reinicie) para a mudança de grupo ter efeito.

> **Nota:** No X11 essa etapa não é necessária.

---

## Executando

```bash
jcl-clicker            # instalado via .deb/.rpm/standalone
```

ou, do source:

```bash
python3 -m app.main
```

> **Depuração:** `JCL_CLICKER_DEBUG=1` registra no stderr qual binário
> ydotool/vendor está em uso e o caminho do socket do daemon.

---

## Atalho global de teclado

O atalho funciona mesmo com a janela sem foco:

- **X11** → via `pynput`
- **Wayland** → leitura direta dos dispositivos em `/dev/input` via `evdev` (o Wayland não permite escuta global de teclado por questões de segurança)

Veja a seção [5. Permissão de input (Wayland)](#5-permissão-de-input-wayland) para configurar os direitos de acesso.

---

## Executando testes

```bash
python3 -m pytest tests/
```

Ou módulo a módulo (alguns executam cliques reais na sessão atual):

```bash
python3 -m tests.test_click
python3 -m tests.test_clicker
python3 -m tests.test_config
python3 -m tests.test_mouse
python3 -m tests.test_save_config
python3 -m tests.test_stop
python3 -m tests.test_x11
python3 -m tests.test_xdg_config
```

> `test_click`, `test_mouse` e `test_x11` executam **cliques reais** na
> sessão gráfica atual.

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'gi'`

O módulo `gi` (PyGObject) é um pacote do sistema, não é instalável via pip. Se o ambiente virtual não tem acesso aos pacotes do sistema, esse erro ocorre ao executar o programa.

**Solução:** recrie o venv com a flag `--system-site-packages`:

```bash
rm -rf venv
python3 -m venv venv --system-site-packages
source venv/bin/activate
pip install -r requirements.txt
```

Ou, se o venv já existe, edite `venv/pyvenv.cfg` e altere `include-system-site-packages = false` para `true`.

### Clicker "roda" mas não clica em nada no Wayland

1. Confirme qual binário/daemon está em uso:

   ```bash
   JCL_CLICKER_DEBUG=1 python3 -m app.main
   ```

   O stderr deve mostrar o ydotool **vendorizado** e o socket em
   `$XDG_RUNTIME_DIR/jcl-clicker-ydotool.socket`.

2. Verifique o acesso a `/dev/uinput` (seção *Permissão de input*).

3. Se um daemon `ydotoold` do sistema estiver rodando com um dispositivo
   virtual ativo, pode haver conflito de nome no X11 — encerre-o
   (`sudo systemctl stop ydotool`) e tente de novo; o app prefere sempre o
   daemon vendorizado.

---

## Próximos passos

### Rebranding — **concluído nesta versão**

- [x] Escolher novo nome: **JCL Clicker** (J = Jônatas, C = Corinthians, L = Linux)
- [x] Atualizar `application_id` do GTK, `APP_NAME` do config, nome de pacote no `build-packages.sh`, `.desktop`, ícone
- [x] Renomear repositório no GitHub (jotaomh/JCL-Cliker)

### Empacotamento — **concluído nesta versão**

- [x] Gerar artefatos `.deb`/`.rpm` das releases (`scripts/build-packages.sh`)
- [x] AppImage (`scripts/build-appimage.sh`)

### Interface gráfica

- [x] Tema claro/escuro com persistência (v0.9.0)
- [x] Logo de destaque no cabeçalho da janela (v0.9.0)
- [ ] Redesenho visual da GUI (estilo próprio, além do GTK4 padrão)
- [ ] Ícone na bandeja do sistema

### Funcionalidades

- [ ] Perfis de configuração

---

# Licença

Projeto em desenvolvimento.

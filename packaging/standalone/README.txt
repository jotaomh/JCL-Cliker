JCL Clicker
===========

Automação de cliques de mouse para Linux com suporte a X11 e Wayland.

Arquivos incluídos
------------------
  jcl-clicker           Binário standalone (não requer Python instalado)
  jcl-clicker.png       Ícone do aplicativo (256x256)
  autoclicker.desktop   Arquivo .desktop para integração com o menu do sistema
  install.sh            Script de instalação automática
  README.txt            Este arquivo

Instalação automática
---------------------
  ./install.sh

O script instala o aplicativo em ~/.local/opt/jcl-clicker/ e registra
o .desktop no diretório do usuário.

Instalação manual
-----------------
  1. Copie os arquivos para um diretório de sua preferência:

     mkdir -p ~/.local/opt/jcl-clicker
     cp jcl-clicker jcl-clicker.png ~/.local/opt/jcl-clicker/
     chmod +x ~/.local/opt/jcl-clicker/jcl-clicker

  2. Instale o .desktop:

     mkdir -p ~/.local/share/applications
     sed 's|/opt/jcl-clicker|$HOME/.local/opt/jcl-clicker|g' \
         autoclicker.desktop > ~/.local/share/applications/autoclicker.desktop
     chmod +x ~/.local/share/applications/autoclicker.desktop
     update-desktop-database ~/.local/share/applications 2>/dev/null

Desinstalação
-------------
  rm -rf ~/.local/opt/jcl-clicker
  rm ~/.local/share/applications/autoclicker.desktop
  update-desktop-database ~/.local/share/applications 2>/dev/null

Arquivo de configuração
-----------------------
As preferências são salvas em:

  ~/.config/jcl-clicker/config.json

Se você usava uma versão anterior ao rebranding, a configuração em
~/.config/autoclicker/config.json é migrada automaticamente na primeira
execução.

Wayland
-------
O binário já traz o ydotool/ydotoold vendorizados — não é preciso instalar
nada do sistema. O daemon precisa de acesso a /dev/uinput; veja o README do
repositório para configurar a permissão (grupo input).

Repositório
-----------
  https://github.com/jotaomh/JCL-Cliker

Licença
-------
Projeto open source. Veja o repositório para mais detalhes.

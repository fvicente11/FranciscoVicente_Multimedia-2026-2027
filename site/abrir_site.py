# -*- coding: utf-8 -*-
"""
abrir_site.py - abre a "Sala de Jogos": liga os 3 jogos e mostra o site no browser.

COMO USAR
    A pasta tem de estar organizada assim:
        SITE/
            abrir_site.py          (este ficheiro)
            site.html              (a página do site, com os 3 jogos)
            site.css               (o aspeto do site: cores, cartões e animações)
            banco_ou_falencia/     (banco_ou_falencia.py, paginas.html, estilo.css)
            palavra_secreta/       (palavra_secreta.py, paginas.html, estilo.css)
            rota_especiarias/      (rota_especiarias.py, paginas.html, estilo.css)
    Depois, corre este ficheiro no VS Code (ou: python abrir_site.py).
    O site abre em http://127.0.0.1:8080 e cada jogo fica na sua porta (8000, 8001 e 8002).
    Para parar tudo, carrega em Ctrl+C no terminal.

COMO FUNCIONA
    Cada jogo já tem o seu próprio servidor. Este ficheiro carrega o código de cada jogo
    (importlib) e põe os 3 servidores a funcionar ao mesmo tempo, cada um numa "thread"
    (um trabalho que corre em paralelo). Depois serve a página site.html na porta 8080.
"""
import importlib.util                          # carregar o código de cada jogo a partir da sua pasta
import sys
import threading                               # pôr vários servidores a funcionar ao mesmo tempo
import webbrowser                              # abrir o browser sozinho
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PASTA = Path(__file__).parent
PORTA_SITE = 8080
JOGOS = [                                      # (pasta, ficheiro, nome do jogo)
    ("banco_ou_falencia", "banco_ou_falencia.py", "Banco ou Falência"),
    ("palavra_secreta", "palavra_secreta.py", "Palavra Secreta"),
    ("rota_especiarias", "rota_especiarias.py", "Rota das Especiarias"),
]


def ligar_jogo(pasta, ficheiro, nome):
    """Carrega o código de um jogo e põe o servidor dele a funcionar numa thread."""
    caminho = PASTA / pasta / ficheiro
    if not caminho.exists():
        print(f"  [ERRO] {nome}: não encontrei o ficheiro {pasta}/{ficheiro}")
        print(f"         Confirma que a pasta '{pasta}' está ao lado do abrir_site.py e que o ficheiro tem este nome exato.")
        return
    try:
        modulo_nome = ficheiro[:-3]
        especificacao = importlib.util.spec_from_file_location(modulo_nome, caminho)
        jogo = importlib.util.module_from_spec(especificacao)
        sys.modules[modulo_nome] = jogo        # o Python precisa disto para as classes do jogo funcionarem
        especificacao.loader.exec_module(jogo)
        if hasattr(jogo, "verificar_dados"):   # a Palavra Secreta verifica as palavras ao arrancar
            jogo.verificar_dados()
    except Exception as erro:
        print(f"  [ERRO] {nome}: o jogo não arrancou ({erro})")
        return
    try:
        servidor = ThreadingHTTPServer(("127.0.0.1", jogo.PORTA), jogo.Manipulador)
    except OSError:
        print(f"  [AVISO] {nome}: a porta {jogo.PORTA} já está ocupada (o jogo já está aberto noutro terminal?)")
        return
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    print(f"  [OK] {nome} a correr em http://127.0.0.1:{jogo.PORTA}")


class Site(BaseHTTPRequestHandler):
    """Servidor do site: envia a página (site.html) e o estilo (site.css)."""

    def do_GET(self):
        caminho = self.path.split("?")[0]
        if caminho in ("/", "/index.html", "/site.html"):
            self._enviar("site.html", "text/html; charset=utf-8")
        elif caminho == "/site.css":
            self._enviar("site.css", "text/css; charset=utf-8")
        else:
            self.send_response(404)
            self.end_headers()

    def _enviar(self, nome, tipo):
        corpo = (PASTA / nome).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")   # F5 mostra sempre a versão mais recente
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, formato, *argumentos):
        """Não enche o terminal com uma linha por cada pedido."""


def main():
    for nome in ("site.html", "site.css"):
        if not (PASTA / nome).exists():
            print(f"ERRO: não encontrei o {nome}. Põe-no na mesma pasta que o abrir_site.py.")
            return
    print("A ligar os jogos...")
    for pasta, ficheiro, nome in JOGOS:
        ligar_jogo(pasta, ficheiro, nome)
    try:
        servidor = ThreadingHTTPServer(("127.0.0.1", PORTA_SITE), Site)
    except OSError:
        print(f"ERRO: a porta {PORTA_SITE} já está ocupada. O site já está aberto noutro terminal?")
        return
    url = f"http://127.0.0.1:{PORTA_SITE}"
    print(f"\nSala de Jogos aberta em {url}  (Ctrl+C para parar tudo)")
    webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nTudo desligado. Até à próxima!")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
banco_ou_falencia.py - TODO o código Python do jogo "Banco ou Falência".

COMO JOGAR
    1. Põe estes 3 ficheiros na MESMA pasta:
         banco_ou_falencia.py   (este ficheiro: toda a lógica em Python)
         paginas.html           (todo o HTML)
         estilo.css             (todo o CSS)
    2. Abre a pasta no Visual Studio Code e corre este ficheiro
       (botão "Run Python File" ou, no terminal: python banco_ou_falencia.py).
    3. O browser abre sozinho em http://127.0.0.1:8000
       (para parar o jogo, carrega em Ctrl+C no terminal).
    Não é preciso instalar nada: só usa a biblioteca standard do Python.

COMO ESTÁ ORGANIZADO ESTE FICHEIRO
    1. Importações
    2. Constantes do jogo     (mexe aqui para tornar o jogo mais fácil ou mais difícil)
    3. Dados                  (todas as DECISÕES e EVENTOS: acrescenta aqui as tuas)
    4. Regras do jogo         (classes Jogador e Jogo: turnos, efeitos, finais)
    5. Páginas                (prepara os dados e preenche o HTML de paginas.html)
    5b. Personagem            (desenha em SVG a personagem que muda com a vida do jogador)
    6. Servidor web           (recebe os cliques do browser e responde)
    7. Arranque               (função main)
"""

# =====================================================================
# 1. IMPORTAÇÕES (só bibliotecas que já vêm com o Python)
# =====================================================================
import html                                   # escapar texto antes de o pôr no HTML
import random                                 # sorteios: riscos, eventos e decisões
import re                                     # separar as páginas dentro do paginas.html
import secrets                                # gerar o identificador de sessão de cada jogador
import traceback                              # mostrar erros no terminal
import webbrowser                             # abrir o browser sozinho
from dataclasses import dataclass, field      # para a classe Jogador ficar curta e clara
from http.cookies import SimpleCookie         # ler a cookie que identifica o jogador
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer   # o servidor web
from pathlib import Path                      # caminhos de ficheiros
from string import Template                   # preencher os campos do HTML
from urllib.parse import parse_qs             # ler os dados dos formulários


# =====================================================================
# 2. CONSTANTES DO JOGO
# Mexe nestes valores para tornar o jogo mais fácil ou mais difícil.
# =====================================================================
IDADE_INICIAL = 18
IDADE_REFORMA = 65
DINHEIRO_INICIAL = 100_000       # herança inicial
DESPESAS_INICIAIS = 12_000       # custo de vida por ano
ESPERANCA_BASE = 75              # esperança de vida de partida
ANOS_POR_TURNO = 3               # cada decisão avança 3 anos
TAXA_JUROS = 0.02                # juros anuais sobre dinheiro positivo
PROB_EVENTO = 0.65               # probabilidade de haver evento em cada turno
TURNOS_NEGATIVOS_MAX = 3         # turnos seguidos com dinheiro < 0 = falência
RENDIMENTO_MINIMO = 10_000       # trabalho básico: ninguém ganha menos do que isto por ano
FATOR_DESPESAS_REFORMA = 1.0     # fração das despesas que se mantém na reforma
TAXA_PENSAO = 0.35               # pensão do Estado = 35% do último rendimento
TAXA_RETIRADA = 0.025            # rendimento passivo = 2,5% do património por ano
FASES = [(18, 25, "18-25"), (26, 40, "26-40"), (41, 55, "41-55"), (56, 65, "56-65")]
PRIMEIRA_DECISAO = "O que fazer depois da escola?"   # é sempre a 1.ª pergunta (as outras são sorteadas)

# --- Personagem (só mudam o DESENHO, não mudam as regras do jogo) ---
# Níveis de riqueza, conforme o dinheiro que o jogador tem:
#   abaixo de LIMITE_POBRE -> 1 Falido      | abaixo de LIMITE_MEDIA     -> 2 Pobre
#   abaixo de LIMITE_RICO  -> 3 Classe média | abaixo de LIMITE_MUITO_RICO -> 4 Rico
#   a partir de LIMITE_MUITO_RICO -> 5 Muito rico
LIMITE_POBRE = 0
LIMITE_MEDIA = 50_000
LIMITE_RICO = 200_000
LIMITE_MUITO_RICO = 600_000
SAUDE_FRACA = 70                 # esperança de vida até aqui: personagem com ar doente
SAUDE_BOA = 80                   # esperança de vida a partir daqui: personagem corada e em forma


# =====================================================================
# 3. DADOS: DECISÕES E EVENTOS
# Está separado das regras para poderes acrescentar conteúdo sem mexer no resto.
#
# Como adicionar uma decisão: copia um bloco de DECISOES, muda os textos e os efeitos.
# Como adicionar um evento: copia um bloco de EVENTOS (com "efeitos" = acontece sozinho,
# ou com "opcoes" = o jogador tem de escolher).
# =====================================================================
def ef(dinheiro=0, rendimento=0, despesas=0, vida=0):
    """Cria um dicionário de EFEITOS.
    dinheiro   -> € que se ganham/perdem uma só vez
    rendimento -> € por ano que passam a entrar (permanente)
    despesas   -> € por ano que passam a sair (permanente)
    vida       -> anos somados (ou tirados) à esperança de vida"""
    return {"dinheiro": dinheiro, "rendimento": rendimento,
            "despesas": despesas, "vida": vida}


def risco(prob, msg_ok, ef_ok, msg_mal, ef_mal):
    """Cria um RISCO: com probabilidade 'prob' (0 a 1) acontece o sucesso,
    caso contrário a falha. Os efeitos somam-se aos efeitos certos da opção."""
    return {"prob": prob,
            "sucesso": {"msg": msg_ok, "efeitos": ef_ok},
            "falha": {"msg": msg_mal, "efeitos": ef_mal}}


def op(texto, efeitos=None, sorteio=None):
    """Cria uma OPÇÃO de uma decisão ou evento."""
    return {"texto": texto, "efeitos": efeitos or ef(), "risco": sorteio}


# ----------------------------------------------------------------------
# DECISÕES, organizadas por fase da vida (a chave é o nome da fase)
# ----------------------------------------------------------------------
DECISOES = {
    "18-25": [
        {"titulo": "O que fazer depois da escola?",
         "descricao": "Tens 100.000 € no banco e o futuro pela frente.",
         "opcoes": [
             op("Ir para a universidade", ef(dinheiro=-25000, rendimento=18200, vida=1)),
             op("Começar logo a trabalhar", ef(rendimento=10500)),
             op("Abrir uma start-up", ef(dinheiro=-30000),
                risco(0.35, "A start-up foi um sucesso!", ef(rendimento=28000),
                      "A start-up falhou.", ef(dinheiro=-15000)))]},
        {"titulo": "Onde vais viver?",
         "descricao": "Está na altura de sair de casa... ou não.",
         "opcoes": [
             op("Ficar em casa dos pais", ef(despesas=-4000)),
             op("Arrendar um apartamento", ef(despesas=3000)),
             op("Comprar um apartamento", ef(dinheiro=-45000, despesas=1500),
                risco(0.6, "A casa valorizou!", ef(dinheiro=35000),
                      "O mercado imobiliário caiu.", ef(dinheiro=-10000)))]},
        {"titulo": "Um ano sabático",
         "descricao": "Os amigos vão viajar. E tu?",
         "opcoes": [
             op("Viajar pelo mundo", ef(dinheiro=-9000, vida=2)),
             op("Trabalhar nas férias", ef(dinheiro=4000)),
             op("Fazer voluntariado", ef(dinheiro=-1500, vida=1))]},
        {"titulo": "Hábitos de saúde",
         "descricao": "O corpo que tens agora é o que vais ter amanhã.",
         "opcoes": [
             op("Ginásio e alimentação cuidada", ef(dinheiro=-1500, despesas=600, vida=4)),
             op("Fast food e sofá", ef(despesas=-600, vida=-3)),
             op("Uma vida equilibrada", ef(vida=1))]},
        {"titulo": "Tirar a carta e ter carro",
         "descricao": "Já tens idade para conduzir. Precisas mesmo de um carro?",
         "opcoes": [
             op("Comprar um carro usado", ef(dinheiro=-5000, despesas=500)),
             op("Carro novo a prestações", ef(dinheiro=-3000, despesas=1500, vida=1)),
             op("Bicicleta e transportes públicos", ef(despesas=-500, vida=1))]},
        {"titulo": "Programa Erasmus",
         "descricao": "Podes estudar ou estagiar um semestre no estrangeiro.",
         "opcoes": [
             op("Ir de Erasmus", ef(dinheiro=-5000, rendimento=2100, vida=1)),
             op("Fazer um estágio cá", ef(rendimento=1400)),
             op("Ficar como estou")]},
        {"titulo": "O primeiro cartão de crédito",
         "descricao": "O banco oferece-te um cartão com um limite generoso.",
         "opcoes": [
             op("Gastar à vontade", ef(dinheiro=-8000, despesas=800, vida=1)),
             op("Usar só em emergências"),
             op("Recusar e poupar", ef(dinheiro=1000))]},
        {"titulo": "O primeiro investimento",
         "descricao": "Juntaste algum dinheiro. Onde o pões?",
         "opcoes": [
             op("Fundo de índice", ef(dinheiro=-5000),
                risco(0.75, "O fundo cresceu com o mercado.", ef(dinheiro=9000),
                      "O mercado caiu e perdeste parte.", ef(dinheiro=3500))),
             op("Apostas desportivas", ef(dinheiro=-3000),
                risco(0.15, "Acertaste numa aposta enorme!", ef(dinheiro=15000),
                      "Perdeste tudo nas apostas.", ef())),
             op("Guardar no mealheiro")]},
        {"titulo": "Aprender algo novo",
         "descricao": "Há cursos que podem dar-te um empurrão na carreira.",
         "opcoes": [
             op("Aprender programação", ef(dinheiro=-3000, rendimento=4200)),
             op("Curso de línguas", ef(dinheiro=-1500, rendimento=1400, vida=1)),
             op("Aproveitar o tempo livre", ef(vida=1))]},
        {"titulo": "Uma relação séria",
         "descricao": "Estás apaixonado(a). E agora?",
         "opcoes": [
             op("Ir viver juntos", ef(despesas=-2500, vida=2)),
             op("Casamento com festa grande", ef(dinheiro=-15000, despesas=-2000, vida=2)),
             op("Ir com calma", ef())]},
    ],
    "26-40": [
        {"titulo": "Proposta de emprego",
         "descricao": "Recebeste uma boa oferta de trabalho.",
         "opcoes": [
             op("Multinacional exigente", ef(rendimento=12600, vida=-2)),
             op("Emprego estável no Estado", ef(rendimento=4900, vida=1)),
             op("Emigrar para a Suíça", ef(dinheiro=-6000, rendimento=16800, despesas=6000, vida=-1))]},
        {"titulo": "Investir as poupanças",
         "descricao": "O teu dinheiro pode trabalhar por ti.",
         "opcoes": [
             op("Comprar ações", ef(dinheiro=-30000),
                risco(0.55, "As ações subiram muito!", ef(dinheiro=62000),
                      "As ações caíram.", ef(dinheiro=12000))),
             op("Depósito a prazo", ef(dinheiro=1500)),
             op("Criptomoedas", ef(dinheiro=-20000),
                risco(0.35, "A criptomoeda disparou!", ef(dinheiro=75000),
                      "A criptomoeda colapsou.", ef(dinheiro=2000)))]},
        {"titulo": "Comprar casa",
         "descricao": "Os bancos oferecem crédito à habitação.",
         "opcoes": [
             op("Casa grande com jardim", ef(dinheiro=-60000, despesas=3000, vida=1)),
             op("Casa pequena", ef(dinheiro=-35000, despesas=1000, vida=1)),
             op("Continuar a arrendar", ef(despesas=500))]},
        {"titulo": "Ter filhos?",
         "descricao": "Uma decisão que muda tudo, incluindo a conta bancária.",
         "opcoes": [
             op("Ter dois filhos", ef(dinheiro=-15000, despesas=8000, vida=3)),
             op("Ter um filho", ef(dinheiro=-8000, despesas=4500, vida=2)),
             op("Não ter filhos", ef(dinheiro=5000, rendimento=1400))]},
        {"titulo": "Abrir um negócio",
         "descricao": "Aparece-te uma oportunidade de seres o teu próprio patrão.",
         "opcoes": [
             op("Abrir um restaurante", ef(dinheiro=-50000),
                risco(0.4, "O restaurante enche todos os dias!", ef(rendimento=26600),
                      "O restaurante fechou.", ef(dinheiro=-15000))),
             op("Comprar uma franquia", ef(dinheiro=-30000),
                risco(0.65, "A franquia dá lucro.", ef(rendimento=11200),
                      "A franquia não rendeu.", ef(dinheiro=-8000))),
             op("Investir numa formação", ef(dinheiro=-4000, rendimento=3500))]},
        {"titulo": "O carro da família",
         "descricao": "O carro velho já não dá para tudo.",
         "opcoes": [
             op("SUV novo", ef(dinheiro=-25000, despesas=1200, vida=1)),
             op("Carro usado em bom estado", ef(dinheiro=-7000, despesas=500)),
             op("Viver sem carro", ef(despesas=-500, vida=1))]},
        {"titulo": "Mestrado ou MBA?",
         "descricao": "Mais estudos podem abrir portas... ou não.",
         "opcoes": [
             op("MBA numa escola cara", ef(dinheiro=-30000),
                risco(0.6, "O MBA deu-te um cargo muito melhor!", ef(rendimento=16800),
                      "O MBA ajudou pouco.", ef(rendimento=4200))),
             op("Mestrado à noite", ef(dinheiro=-8000, rendimento=5600, vida=-1)),
             op("Não estudar mais")]},
        {"titulo": "Trabalho remoto",
         "descricao": "A empresa deixa-te trabalhar a partir de casa.",
         "opcoes": [
             op("Mudar para o campo", ef(rendimento=-1400, despesas=-3000, vida=2)),
             op("Ser nómada digital", ef(dinheiro=-5000, vida=2)),
             op("Continuar no escritório", ef(rendimento=1400))]},
        {"titulo": "Um animal de estimação",
         "descricao": "A casa anda muito silenciosa...",
         "opcoes": [
             op("Adotar um cão", ef(dinheiro=-1000, despesas=900, vida=2)),
             op("Adotar um gato", ef(dinheiro=-500, despesas=500, vida=1)),
             op("Nenhum animal")]},
        {"titulo": "Uma casa para restaurar",
         "descricao": "Há uma casa antiga à venda por um preço muito baixo.",
         "opcoes": [
             op("Comprar e restaurar", ef(dinheiro=-40000),
                risco(0.55, "Vendeste a casa restaurada com lucro!", ef(dinheiro=70000),
                      "As obras correram mal e venderam-se com prejuízo.", ef(dinheiro=25000))),
             op("Deixar passar")]},
    ],
    "41-55": [
        {"titulo": "Poupar ou gastar?",
         "descricao": "O dinheiro está a entrar. O que fazes com ele?",
         "opcoes": [
             op("Poupar a sério", ef(despesas=-4000)),
             op("Comprar um carro de luxo", ef(dinheiro=-40000, despesas=3000)),
             op("Viver normalmente")]},
        {"titulo": "Seguro de saúde e de vida",
         "descricao": "O corretor insiste que precisas de um seguro.",
         "opcoes": [
             op("Fazer o seguro", ef(despesas=900, vida=2)),
             op("Dispensar o seguro", ef(),
                risco(0.7, "Não precisaste dele.", ef(),
                      "Surgiu uma doença sem cobertura.", ef(dinheiro=-35000, vida=-3)))]},
        {"titulo": "Proposta de promoção",
         "descricao": "A empresa quer-te numa posição de chefia.",
         "opcoes": [
             op("Aceitar o cargo de chefia", ef(rendimento=14000, vida=-3)),
             op("Ficar como estás", ef(vida=1)),
             op("Reduzir o horário de trabalho", ef(rendimento=-5600, vida=3))]},
        {"titulo": "Crise de meia-idade",
         "descricao": "Será que é isto que queres para o resto da vida?",
         "opcoes": [
             op("Mudar de carreira", ef(dinheiro=-10000),
                risco(0.5, "A nova carreira correu bem!", ef(rendimento=9800),
                      "A nova carreira não pegou.", ef(rendimento=-3500))),
             op("Viver um sonho (mota, viagem...)", ef(dinheiro=-9000, vida=2)),
             op("Ignorar e seguir em frente")]},
        {"titulo": "Pensar no futuro",
         "descricao": "A reforma já se vê ao longe.",
         "opcoes": [
             op("Comprar uma casa para arrendar", ef(dinheiro=-80000, rendimento=5600, despesas=1000)),
             op("Fazer um PPR (poupança-reforma)", ef(dinheiro=-20000, rendimento=2100)),
             op("Pagar a universidade dos filhos", ef(dinheiro=-30000, vida=1))]},
        {"titulo": "Os pais estão a envelhecer",
         "descricao": "Os teus pais já precisam de ajuda no dia a dia.",
         "opcoes": [
             op("Pagar um bom lar", ef(dinheiro=-10000, despesas=2500, vida=1)),
             op("Cuidar deles em casa", ef(rendimento=-2100, vida=1)),
             op("Os irmãos que tratem disso", ef(vida=-1))]},
        {"titulo": "A bolsa está a cair",
         "descricao": "As notícias só falam da queda dos mercados.",
         "opcoes": [
             op("Comprar ações baratas", ef(dinheiro=-30000),
                risco(0.65, "O mercado recuperou e lucraste muito!", ef(dinheiro=60000),
                      "A queda continuou durante anos.", ef(dinheiro=15000))),
             op("Vender tudo por medo", ef(dinheiro=-6000)),
             op("Não mexer em nada")]},
        {"titulo": "Remodelar a casa",
         "descricao": "A casa já precisa de obras.",
         "opcoes": [
             op("Obras completas", ef(dinheiro=-20000, despesas=-800, vida=1)),
             op("Painéis solares", ef(dinheiro=-8000, despesas=-1200)),
             op("Deixar como está")]},
        {"titulo": "Casa de férias",
         "descricao": "Sempre sonhaste com uma casa no Algarve.",
         "opcoes": [
             op("Comprar a casa", ef(dinheiro=-70000, despesas=1200, vida=2),
                risco(0.5, "A casa valorizou bastante.", ef(dinheiro=60000),
                      "O mercado do Algarve arrefeceu.", ef(dinheiro=-10000))),
             op("Alugar casas nas férias", ef(despesas=1500, vida=1)),
             op("Férias em casa")]},
        {"titulo": "Despedimento coletivo",
         "descricao": "A empresa vai despedir muita gente. O teu lugar está em risco.",
         "opcoes": [
             op("Aceitar a indemnização e sair", ef(dinheiro=40000, rendimento=-4200)),
             op("Lutar pelo lugar", ef(),
                risco(0.5, "Ficaste com o emprego.", ef(),
                      "Foste despromovido.", ef(rendimento=-4200))),
             op("Procurar outro emprego", ef(),
                risco(0.6, "Encontraste um emprego melhor!", ef(rendimento=5600),
                      "Ficaste uns meses parado.", ef(dinheiro=-6000)))]},
        {"titulo": "Desporto aos 50",
         "descricao": "O médico diz que precisas de te mexer mais.",
         "opcoes": [
             op("Treinar para uma maratona", ef(dinheiro=-2000, vida=3)),
             op("Entrar num clube de golfe", ef(dinheiro=-3000, despesas=1200, vida=2)),
             op("Amanhã começo...", ef(vida=-1))]},
    ],
    "56-65": [
        {"titulo": "Quanto tempo vais ainda trabalhar?",
         "descricao": "Já se começa a sentir o cansaço.",
         "opcoes": [
             op("Trabalhar a tempo inteiro até ao fim", ef(vida=-1)),
             op("Passar a part-time", ef(rendimento=-8400, vida=2)),
             op("Fazer consultoria", ef(rendimento=4200, vida=-1))]},
        {"titulo": "Viver bem",
         "descricao": "Sobrou algum dinheiro. O que fazes?",
         "opcoes": [
             op("Viagem de sonho", ef(dinheiro=-15000, vida=2)),
             op("Pagar dívidas e poupar", ef(despesas=-1500)),
             op("Dar uma grande festa", ef(dinheiro=-5000, vida=1))]},
        {"titulo": "Saúde na reta final",
         "descricao": "O corpo começa a dar sinais.",
         "opcoes": [
             op("Check-up completo e exercício", ef(despesas=500, vida=3)),
             op("Ignorar os sintomas", ef(),
                risco(0.5, "Não era nada.", ef(),
                      "Era mais grave do que parecia.", ef(dinheiro=-20000, vida=-4))),
             op("Mudar de dieta e fazer caminhadas", ef(vida=2))]},
        {"titulo": "Onde te vais reformar?",
         "descricao": "É altura de escolher a casa para a reforma.",
         "opcoes": [
             op("Mudar para o interior (mais barato)", ef(dinheiro=25000, despesas=-3000, vida=1)),
             op("Ficar onde estás"),
             op("Mudar para o litoral", ef(dinheiro=-20000, despesas=2500, vida=2))]},
        {"titulo": "Os netos chegaram",
         "descricao": "Os teus filhos precisam de ajuda com as crianças.",
         "opcoes": [
             op("Tomar conta dos netos", ef(rendimento=-1400, vida=2)),
             op("Pagar uma ama", ef(dinheiro=-8000, vida=1)),
             op("Viver a minha vida")]},
        {"titulo": "Reforma antecipada?",
         "descricao": "A empresa oferece-te a reforma antecipada.",
         "opcoes": [
             op("Aceitar e descansar", ef(dinheiro=15000, rendimento=-7000, vida=3)),
             op("Continuar como estou"),
             op("Trabalhar ainda mais", ef(rendimento=4200, vida=-2))]},
        {"titulo": "Ajudar os filhos a comprar casa",
         "descricao": "Os teus filhos não conseguem dar a entrada para uma casa.",
         "opcoes": [
             op("Dar 25.000 €", ef(dinheiro=-25000, vida=2)),
             op("Emprestar 20.000 €", ef(dinheiro=-20000),
                risco(0.7, "Os filhos devolveram o dinheiro.", ef(dinheiro=20000),
                      "Nunca conseguiram devolver.", ef())),
             op("Eles que se arranjem")]},
        {"titulo": "Vender a casa?",
         "descricao": "A tua casa vale hoje muito mais do que pagaste.",
         "opcoes": [
             op("Vender e passar a arrendar", ef(dinheiro=80000, despesas=6000)),
             op("Vender e comprar uma mais pequena", ef(dinheiro=40000, despesas=-1000)),
             op("Ficar na casa")]},
        {"titulo": "Dar à comunidade",
         "descricao": "Tens experiência que pode ajudar os outros.",
         "opcoes": [
             op("Voluntariado numa associação", ef(vida=2)),
             op("Cargo pago numa fundação", ef(rendimento=2800)),
             op("Nada disso")]},
    ],
}

# ----------------------------------------------------------------------
# EVENTOS ALEATÓRIOS
# "efeitos"  -> acontece sozinho
# "opcoes"   -> o jogador tem de escolher
# "idades"   -> (opcional) só acontece entre estas idades, ex.: (26, 65)
# Em cada partida, o mesmo evento não se repete (até se esgotarem).
# ----------------------------------------------------------------------
EVENTOS = [
    # --- Automáticos que tiram dinheiro / vida ---
    {"titulo": "Doença grave", "descricao": "Tiveste um problema de saúde sério e precisaste de tratamentos.",
     "efeitos": ef(dinheiro=-12000, vida=-4)},
    {"titulo": "Acidente de viação", "descricao": "Um acidente deixou-te com despesas médicas e o carro na oficina.",
     "efeitos": ef(dinheiro=-6000, vida=-1)},
    {"titulo": "Crise económica", "descricao": "Uma crise abalou os mercados e o teu rendimento caiu.",
     "efeitos": ef(dinheiro=-15000, rendimento=-2100)},
    {"titulo": "Avaria em casa", "descricao": "O telhado precisou de obras urgentes.",
     "efeitos": ef(dinheiro=-4000)},
    # --- Automáticos que dão dinheiro ---
    {"titulo": "Prémio da lotaria", "descricao": "Acertaste num prémio de lotaria!",
     "efeitos": ef(dinheiro=15000)},
    {"titulo": "Herança de um tio", "descricao": "Um tio distante deixou-te uma herança.",
     "efeitos": ef(dinheiro=30000)},
    {"titulo": "Promoção inesperada", "descricao": "O teu trabalho foi reconhecido pela empresa.",
     "efeitos": ef(rendimento=4200)},
    {"titulo": "Bónus de empresa", "descricao": "A empresa teve um ótimo ano e partilhou os lucros.",
     "efeitos": ef(dinheiro=8000)},
    # --- Eventos com escolha ---
    {"titulo": "Um amigo pede-te um empréstimo",
     "descricao": "Um velho amigo está em apuros e precisa de dinheiro.",
     "opcoes": [
         op("Emprestar 10.000 €", ef(dinheiro=-10000),
            risco(0.5, "O amigo devolveu o dinheiro com um extra.", ef(dinheiro=12000),
                  "O amigo nunca devolveu.", ef())),
         op("Dizer que não")]},
    {"titulo": "Oportunidade de negócio arriscada",
     "descricao": "Um conhecido garante-te lucros enormes se investires já.",
     "opcoes": [
         op("Investir 25.000 €", ef(dinheiro=-25000),
            risco(0.4, "O negócio disparou!", ef(dinheiro=70000),
                  "O negócio era uma burla.", ef())),
         op("Recusar")]},
    {"titulo": "Familiar com problemas de saúde",
     "descricao": "Um familiar próximo precisa de um tratamento caro.",
     "opcoes": [
         op("Pagar o tratamento", ef(dinheiro=-10000, vida=1)),
         op("Dizer que não podes ajudar", ef(vida=-1))]},

    # --- Crises e azares (automáticos) ---
    {"titulo": "Crise financeira mundial", "descricao": "Os bancos entraram em pânico e a economia parou.",
     "efeitos": ef(dinheiro=-20000, rendimento=-2100)},
    {"titulo": "A bolha imobiliária rebentou", "descricao": "O preço das casas caiu a pique.",
     "efeitos": ef(dinheiro=-15000), "idades": (26, 65)},
    {"titulo": "A inflação disparou", "descricao": "Tudo ficou mais caro: comida, luz, combustível...",
     "efeitos": ef(despesas=1500)},
    {"titulo": "Subida das taxas de juro", "descricao": "Os créditos e as rendas ficaram mais caros.",
     "efeitos": ef(despesas=1000)},
    {"titulo": "Pandemia", "descricao": "Um vírus fechou o país durante meses.",
     "efeitos": ef(dinheiro=-8000, rendimento=-1400, vida=-1)},
    {"titulo": "Assalto em casa", "descricao": "Entraram em tua casa e levaram coisas de valor.",
     "efeitos": ef(dinheiro=-5000)},
    {"titulo": "Problemas com as Finanças", "descricao": "Havia um erro na tua declaração de impostos.",
     "efeitos": ef(dinheiro=-4000)},
    {"titulo": "Burla na internet", "descricao": "Compraste numa loja online que afinal não existia.",
     "efeitos": ef(dinheiro=-3000)},
    {"titulo": "Despedimento", "descricao": "A empresa fechou e tiveste de aceitar um emprego pior.",
     "efeitos": ef(rendimento=-4900), "idades": (24, 60)},
    {"titulo": "Lesão desportiva", "descricao": "Partiste uma perna a jogar futebol.",
     "efeitos": ef(dinheiro=-3000, vida=-1)},
    {"titulo": "Inundação", "descricao": "Uma tempestade inundou a tua casa.",
     "efeitos": ef(dinheiro=-6000)},
    {"titulo": "O carro avariou", "descricao": "O motor foi-se e a reparação saiu cara.",
     "efeitos": ef(dinheiro=-2500)},
    {"titulo": "O teu banco faliu", "descricao": "Só recuperaste parte das tuas poupanças.",
     "efeitos": ef(dinheiro=-10000), "idades": (30, 65)},
    {"titulo": "Problemas de coluna", "descricao": "Anos ao computador cobraram o seu preço.",
     "efeitos": ef(dinheiro=-2000, vida=-1), "idades": (35, 65)},

    # --- Sorte (automáticos) ---
    {"titulo": "Aumento de salário", "descricao": "Finalmente reconheceram o teu trabalho.",
     "efeitos": ef(rendimento=2100), "idades": (20, 60)},
    {"titulo": "Mercados em alta", "descricao": "As bolsas tiveram um ano fantástico.",
     "efeitos": ef(dinheiro=10000), "idades": (26, 65)},
    {"titulo": "Reembolso do IRS", "descricao": "As Finanças devolveram-te mais do que esperavas.",
     "efeitos": ef(dinheiro=2500)},
    {"titulo": "Ganhaste um concurso", "descricao": "O teu projeto ganhou o primeiro prémio.",
     "efeitos": ef(dinheiro=5000)},
    {"titulo": "Herança da avó", "descricao": "A tua avó deixou-te as poupanças de uma vida.",
     "efeitos": ef(dinheiro=12000), "idades": (18, 50)},
    {"titulo": "Descida dos juros", "descricao": "O crédito da casa ficou mais barato.",
     "efeitos": ef(despesas=-500), "idades": (26, 65)},
    {"titulo": "Grupo de caminhadas", "descricao": "Uns amigos convenceram-te a caminhar todas as semanas.",
     "efeitos": ef(vida=2)},
    {"titulo": "Limpeza do sótão", "descricao": "Vendeste coisas antigas na internet.",
     "efeitos": ef(dinheiro=1500)},
    {"titulo": "Raspadinha premiada", "descricao": "Uma raspadinha deu-te um pequeno prémio.",
     "efeitos": ef(dinheiro=1000)},
    {"titulo": "Projeto paralelo", "descricao": "O teu passatempo começou a dar algum dinheiro.",
     "efeitos": ef(rendimento=700)},

    # --- Mais eventos com escolha ---
    {"titulo": "Um quadro no sótão",
     "descricao": "Encontraste um quadro antigo que pode valer alguma coisa.",
     "opcoes": [
         op("Vender já numa feira", ef(dinheiro=2000)),
         op("Pagar a um perito para o avaliar", ef(dinheiro=-500),
            risco(0.3, "Era de um pintor famoso!", ef(dinheiro=25000),
                  "Não valia quase nada.", ef(dinheiro=300)))]},
    {"titulo": "Crash na bolsa",
     "descricao": "As bolsas caíram 30% numa semana. O que fazes?",
     "opcoes": [
         op("Vender tudo antes que piore", ef(dinheiro=-15000)),
         op("Aguentar e esperar", ef(),
            risco(0.6, "O mercado recuperou.", ef(dinheiro=5000),
                  "Ainda caiu mais.", ef(dinheiro=-20000))),
         op("Aproveitar e comprar mais", ef(dinheiro=-10000),
            risco(0.5, "Compraste no ponto mais baixo!", ef(dinheiro=35000),
                  "Compraste cedo demais.", ef()))],
     "idades": (26, 65)},
    {"titulo": "Proposta para ir para o estrangeiro",
     "descricao": "Uma empresa em Londres quer contratar-te.",
     "opcoes": [
         op("Aceitar e emigrar", ef(dinheiro=-5000, rendimento=9800, despesas=4000, vida=-1)),
         op("Ficar perto da família", ef(vida=1))],
     "idades": (22, 50)},
    {"titulo": "Padrinho de casamento",
     "descricao": "Um grande amigo convida-te para padrinho.",
     "opcoes": [
         op("Aceitar com orgulho", ef(dinheiro=-2000, vida=1)),
         op("Inventar uma desculpa")],
     "idades": (22, 50)},
    {"titulo": "Ações da empresa",
     "descricao": "A tua empresa oferece ações aos trabalhadores com desconto.",
     "opcoes": [
         op("Comprar 10.000 € em ações", ef(dinheiro=-10000),
            risco(0.6, "A empresa cresceu e as ações subiram!", ef(dinheiro=25000),
                  "A empresa teve problemas.", ef(dinheiro=2000))),
         op("Não comprar")],
     "idades": (24, 60)},
    {"titulo": "O carro dos teus sonhos",
     "descricao": "Está em promoção o carro que sempre quiseste.",
     "opcoes": [
         op("Comprar!", ef(dinheiro=-30000, despesas=1500, vida=1)),
         op("Sonhar não custa nada")]},
    {"titulo": "SMS do \"teu banco\"",
     "descricao": "Recebes uma mensagem a pedir para confirmares os dados num link.",
     "opcoes": [
         op("Clicar no link e preencher", ef(dinheiro=-8000)),
         op("Ligar ao banco a confirmar")]},
    {"titulo": "Um familiar pede para ficar contigo",
     "descricao": "Um primo perdeu a casa e não tem para onde ir.",
     "opcoes": [
         op("Recebê-lo em casa", ef(despesas=2000, vida=1)),
         op("Ajudar a pagar um quarto", ef(dinheiro=-3000)),
         op("Dizer que não dá", ef(vida=-1))]},
    {"titulo": "Greve geral",
     "descricao": "Os colegas vão fazer greve por salários melhores.",
     "opcoes": [
         op("Fazer greve", ef(dinheiro=-1000),
            risco(0.6, "A greve resultou: aumento para todos!", ef(rendimento=2100),
                  "Nada mudou.", ef())),
         op("Ir trabalhar")],
     "idades": (20, 64)},
]


# =====================================================================
# 4. REGRAS DO JOGO
# Funções auxiliares, classe Jogador (os dados do jogador) e classe Jogo (os turnos,
# os efeitos, os eventos e os finais). Esta parte não sabe nada de HTML nem de servidores.
# =====================================================================
# ---------------------- FUNÇÕES AUXILIARES ----------------------
def eur(valor, sinal=False):
    """Formata dinheiro: 100000 -> '100.000 €'. Com sinal=True mostra '+' nos positivos."""
    valor = round(valor)
    texto = f"{abs(valor):,}".replace(",", ".")
    prefixo = "-" if valor < 0 else ("+" if sinal else "")
    return f"{prefixo}{texto} €"


def lista_efeitos(efeitos):
    """Converte efeitos em lista de (texto, é_bom). Usado nos botões e nas mensagens."""
    itens = []
    d, r = efeitos.get("dinheiro", 0), efeitos.get("rendimento", 0)
    s, v = efeitos.get("despesas", 0), efeitos.get("vida", 0)
    if d: itens.append((eur(d, True), d > 0))
    if r: itens.append((eur(r, True) + "/ano de rendimento", r > 0))
    if s: itens.append((eur(s, True) + "/ano de despesas", s < 0))
    if v: itens.append((f"{v:+d} " + ("ano" if abs(v) == 1 else "anos") + " de vida", v > 0))
    return itens


def texto_efeitos(efeitos):
    """Versão em texto simples dos efeitos, ex.: '-25.000 €, +1 ano de vida'."""
    return ", ".join(t for t, _ in lista_efeitos(efeitos)) or "sem efeitos"


def fase_da_idade(idade):
    """Devolve o nome da fase da vida ('18-25', '26-40', ...) para uma idade."""
    for inicio, fim, nome in FASES:
        if inicio <= idade <= fim:
            return nome
    return FASES[-1][2]


# ---------------------- JOGADOR ----------------------
@dataclass
class Jogador:
    """Guarda tudo o que se sabe sobre o jogador."""
    nome: str
    sexo: str
    pais: str
    idade: int = IDADE_INICIAL
    dinheiro: float = DINHEIRO_INICIAL
    rendimento: float = 0                 # € que entram por ano
    despesas: float = DESPESAS_INICIAIS   # € que saem por ano
    esperanca: int = ESPERANCA_BASE       # idade até à qual se espera viver
    turnos_negativos: int = 0             # turnos seguidos com dinheiro negativo
    historico: list = field(default_factory=list)           # textos para o resumo final
    historico_dinheiro: list = field(default_factory=list)  # (idade, dinheiro) para o gráfico


# ---------------------- JOGO ----------------------
class Jogo:
    """Controla o fluxo do jogo.
    self.fase pode ser: 'decisao', 'evento' (escolha), 'resultado' ou 'fim'."""

    def __init__(self, nome, sexo, pais):
        self.jogador = Jogador(nome, sexo, pais)
        self.jogador.historico_dinheiro.append((IDADE_INICIAL, DINHEIRO_INICIAL))
        self.usadas = set()      # decisões já mostradas (para não repetir)
        self.eventos_vistos = set()   # eventos que já aconteceram (para não repetir)
        self.final = None        # dicionário com o final, quando o jogo acaba
        self.decisao = None
        self.evento = None
        self.mensagens = []
        self.fase = "decisao"
        self.nivel_visto = None  # último nível de riqueza desenhado (só serve para a animação da personagem)
        self.novo_turno()

    # ----- início de turno -----
    def novo_turno(self):
        """Prepara a próxima decisão, escolhida ao acaso entre as da fase atual."""
        self.mensagens = []
        self.evento = None
        candidatas = DECISOES[fase_da_idade(self.jogador.idade)]
        livres = [d for d in candidatas if d["titulo"] not in self.usadas] or candidatas
        primeira = [d for d in candidatas if d["titulo"] == PRIMEIRA_DECISAO]
        if self.jogador.idade == IDADE_INICIAL and primeira:
            self.decisao = primeira[0]          # o jogo começa sempre pela escolha de estudos/trabalho
        else:
            self.decisao = random.choice(livres)
        self.usadas.add(self.decisao["titulo"])
        self.fase = "decisao"

    # ----- efeitos -----
    def aplicar_efeitos(self, efeitos):
        """Soma os efeitos ao jogador (com limites para não haver valores absurdos)."""
        j = self.jogador
        j.dinheiro += efeitos.get("dinheiro", 0)
        j.rendimento = max(0, j.rendimento + efeitos.get("rendimento", 0))
        j.despesas = max(3000, j.despesas + efeitos.get("despesas", 0))
        j.esperanca = max(30, j.esperanca + efeitos.get("vida", 0))

    def resolver_opcao(self, opcao):
        """Aplica uma opção (efeitos certos + risco, se houver) e devolve mensagens."""
        linhas = [f"Escolheste: {opcao['texto']} ({texto_efeitos(opcao['efeitos'])})."]
        self.aplicar_efeitos(opcao["efeitos"])
        risco = opcao.get("risco")
        if risco:
            correu_bem = random.random() < risco["prob"]       # sorteio do risco
            resultado = risco["sucesso"] if correu_bem else risco["falha"]
            self.aplicar_efeitos(resultado["efeitos"])
            sufixo = f" ({texto_efeitos(resultado['efeitos'])})" if lista_efeitos(resultado["efeitos"]) else ""
            linhas.append(("Correu bem: " if correu_bem else "Correu mal: ") + resultado["msg"] + sufixo)
        return linhas

    # ----- passagem do tempo -----
    def avancar_anos(self):
        """Passa ANOS_POR_TURNO anos: entra rendimento, saem despesas, vencem juros."""
        j = self.jogador
        idade_antes = j.idade
        saldo = max(j.rendimento, RENDIMENTO_MINIMO) - j.despesas   # nunca ganhas menos que o mínimo
        for _ in range(ANOS_POR_TURNO):
            if j.idade >= IDADE_REFORMA:
                break
            j.dinheiro += saldo
            if j.dinheiro > 0:
                j.dinheiro *= 1 + TAXA_JUROS
            j.idade += 1
            if self._verificar_morte():
                break
        j.historico_dinheiro.append((j.idade, round(j.dinheiro)))
        return [f"Passaram {j.idade - idade_antes} anos (saldo anual: {eur(saldo, True)}). "
                f"Tens {j.idade} anos e {eur(j.dinheiro)}."]

    def sortear_evento(self):
        """Escolhe um evento ao acaso, entre os que servem para esta idade e ainda não aconteceram.
        Se for automático aplica já; se tiver opções, espera pela escolha do jogador."""
        idade = self.jogador.idade
        da_idade = [e for e in EVENTOS if e.get("idades", (0, 200))[0] <= idade <= e.get("idades", (0, 200))[1]]
        novos = [e for e in da_idade if e["titulo"] not in self.eventos_vistos] or da_idade
        self.evento = random.choice(novos)
        self.eventos_vistos.add(self.evento["titulo"])
        if "opcoes" in self.evento:
            self.fase = "evento"
        else:
            self.aplicar_efeitos(self.evento["efeitos"])
            self.mensagens.append(f"Evento: {self.evento['titulo']}. {self.evento['descricao']} "
                                  f"({texto_efeitos(self.evento['efeitos'])})")
            self.jogador.historico.append(f"{self.jogador.idade} anos - Evento: {self.evento['titulo']}")

    # ----- ação do jogador -----
    def escolher(self, indice):
        """Chamado quando o jogador clica numa opção. Devolve False se for inválido."""
        if self.fase == "decisao":
            situacao = self.decisao
        elif self.fase == "evento":
            situacao = self.evento
        else:
            return False
        if not 0 <= indice < len(situacao["opcoes"]):
            return False
        opcao = situacao["opcoes"][indice]
        j = self.jogador
        rotulo = "Evento: " if self.fase == "evento" else ""
        j.historico.append(f"{j.idade} anos - {rotulo}{situacao['titulo']} -> {opcao['texto']}")
        self.mensagens += self.resolver_opcao(opcao)

        if self.fase == "decisao":
            self.mensagens += self.avancar_anos()
            if self.final is None and random.random() < PROB_EVENTO:
                self.sortear_evento()
                if self.fase == "evento":   # evento com escolha: espera pela resposta
                    return True
        self.fechar_turno()
        return True

    def continuar(self):
        """Depois de ler o resultado, passa ao turno seguinte."""
        if self.fase == "resultado":
            self.novo_turno()

    # ----- fim de turno e finais -----
    def fechar_turno(self):
        """Verifica morte, falência e reforma. Define a fase seguinte."""
        j = self.jogador
        self._verificar_morte()
        if self.final is None:
            j.turnos_negativos = j.turnos_negativos + 1 if j.dinheiro < 0 else 0
            if j.turnos_negativos >= TURNOS_NEGATIVOS_MAX:
                self.final = {"titulo": "Falência!", "classe": "mau",
                              "explicacao": f"Ficaste com {eur(j.dinheiro)} durante demasiado tempo e "
                                            f"os bancos ficaram com tudo. O sonho acabou aos {j.idade} anos."}
            elif j.idade >= IDADE_REFORMA:
                self._reforma()
        self.fase = "fim" if self.final else "resultado"

    def _verificar_morte(self):
        """Se a idade chegou à esperança de vida antes da reforma, o jogo acaba."""
        j = self.jogador
        if self.final is None and j.idade >= j.esperanca and j.idade < IDADE_REFORMA:
            self.final = {"titulo": "Morreste antes da reforma", "classe": "mau",
                          "explicacao": f"Morreste aos {j.idade} anos, sem chegar a ver a reforma. "
                                        f"Tinhas {eur(j.dinheiro)}."}
        return self.final is not None

    def _reforma(self):
        """Aos 65 anos: compara rendimentos e despesas e atribui o final."""
        j = self.jogador
        patrimonio = max(0, j.dinheiro)
        despesas = j.despesas * FATOR_DESPESAS_REFORMA
        pensao = max(j.rendimento, RENDIMENTO_MINIMO) * TAXA_PENSAO
        passivo = patrimonio * TAXA_RETIRADA
        anos_reforma = max(1, j.esperanca - IDADE_REFORMA)
        resumo = (f"Património: {eur(patrimonio)}. Despesas na reforma: {eur(despesas)}/ano. "
                  f"Pensão do Estado: {eur(pensao)}/ano. Rendimento passivo ({TAXA_RETIRADA * 100:.1f}% do património): "
                  f"{eur(passivo)}/ano. Esperas viver mais {anos_reforma} anos.")
        if passivo >= despesas:
            titulo, classe = "Liberdade financeira!", "bom"
            motivo = "O rendimento passivo paga sozinho todas as despesas. Nunca mais precisas de trabalhar."
        elif passivo + pensao >= despesas:
            titulo, classe = "Reforma confortável", "bom"
            motivo = "Pensão e rendimento passivo juntos cobrem as despesas, sem gastar o capital."
        else:
            anos_dura = patrimonio / (despesas - pensao)   # anos que o capital aguenta
            if anos_dura >= anos_reforma:
                titulo, classe = "Reforma apertada", "medio"
                motivo = (f"Tens de ir gastando o património: dura cerca de {anos_dura:.0f} anos "
                          f"e esperas viver mais {anos_reforma}. Dá mesmo para chegar ao fim.")
            else:
                titulo, classe = "Reforma pobre", "mau"
                motivo = (f"O dinheiro só dura cerca de {anos_dura:.0f} anos, mas esperas viver mais "
                          f"{anos_reforma}. Vais ter de viver com muito pouco.")
        self.final = {"titulo": titulo, "classe": classe, "explicacao": f"{motivo} {resumo}"}


# =====================================================================
# 5. PÁGINAS (preenche o HTML do ficheiro paginas.html)
# Aqui o Python prepara os dados do jogo e mete-os nos campos do HTML.
# =====================================================================
PASTA = Path(__file__).parent                 # pasta onde estão os 3 ficheiros do jogo
FICHEIRO_HTML = PASTA / "paginas.html"        # todo o HTML
FICHEIRO_CSS = PASTA / "estilo.css"           # todo o CSS

# Nome de cada fase da vida (aparece no painel de estado)
NOMES_FASES = {
    "18-25": "Juventude",
    "26-40": "Início de carreira",
    "41-55": "Maturidade",
    "56-65": "Pré-reforma",
}

# Emoji do ecrã final, consoante o final que o jogador teve
ICONES_FINAIS = {
    "Liberdade financeira!": "🏆",
    "Reforma confortável": "😊",
    "Reforma apertada": "😅",
    "Reforma pobre": "😟",
    "Falência!": "🏚️",
    "Morreste antes da reforma": "💀",
}

# Dica para a próxima partida, consoante o final
DICAS = {
    "Liberdade financeira!": "Experimenta outro caminho (por exemplo, abrir um negócio ou emigrar) e vê se consegues chegar lá de forma diferente.",
    "Reforma confortável": "Por pouco! Poupar e investir cedo faz o dinheiro render durante mais anos e aproxima-te da liberdade financeira.",
    "Reforma apertada": "Cuidado com as despesas fixas: casas e carros caros custam dinheiro todos os anos. Investir cedo ajuda muito.",
    "Reforma pobre": "Procura aumentar o rendimento anual e não deixes as despesas crescerem mais do que o rendimento.",
    "Falência!": "Evita investimentos muito arriscados quando já tens pouco dinheiro e não deixes as despesas passarem o rendimento durante muito tempo.",
    "Morreste antes da reforma": "A saúde também é um investimento: as opções que dão anos de vida contam muito para chegares aos 65.",
}


def carregar_paginas():
    """Lê o paginas.html e separa as páginas pelos marcadores (arroba + nome da página).
    Devolve um dicionário {nome da página: Template}.
    O ficheiro é lido em cada pedido, por isso basta carregares em F5 depois de o alterares."""
    texto = FICHEIRO_HTML.read_text(encoding="utf-8")
    # re.split devolve: [cabeçalho, nome1, corpo1, nome2, corpo2, ...]
    partes = re.split(r"<!--@ (\w+) -->", texto)
    return {partes[i]: Template(partes[i + 1]) for i in range(1, len(partes), 2)}


def montar(paginas, ecra, larga=False, **campos):
    """Preenche a página 'ecra' com os campos e mete-a dentro da página-base (cabeçalho e rodapé).
    larga=True deixa a página mais larga, para caberem as duas colunas (personagem + jogo)."""
    corpo = paginas[ecra].substitute(campos)
    return paginas["base"].substitute(titulo="Banco ou Falência", conteudo=corpo,
                                      classe_caixa="larga" if larga else "")


def classe_da_linha(texto):
    """Escolhe a cor do ponto na linha do tempo:
    verde = correu bem, vermelho = correu mal, dourado = evento aleatório."""
    if texto.startswith("Correu bem"):
        return "bom"
    if texto.startswith("Correu mal"):
        return "mau"
    if texto.startswith("Evento") or " - Evento:" in texto:
        return "evento"
    return ""


def lista_html(textos):
    """Transforma uma lista de textos em itens <li> (com a cor certa e o texto protegido)."""
    itens = []
    for texto in textos:
        bonito = html.escape(texto.replace(" -> ", " → "))   # seta mais bonita
        itens.append(f'<li class="{classe_da_linha(texto)}">{bonito}</li>')
    return "\n".join(itens)


def linha_fases(idade):
    """As 4 fases da vida: as já vividas ficam a verde, a atual a dourado, as futuras normais."""
    posicao_atual = [chave for _, _, chave in FASES].index(fase_da_idade(idade))
    itens = []
    for i, (_, _, chave) in enumerate(FASES):
        if i < posicao_atual:
            estado = "feita"
        elif i == posicao_atual:
            estado = "atual"
        else:
            estado = ""
        marca = ' aria-current="step"' if estado == "atual" else ""
        itens.append(f'<li class="fase {estado}"{marca}>'
                     f'<span class="fase-nome">{NOMES_FASES[chave]}</span><small>{chave}</small></li>')
    return "".join(itens)


def painel(jogo, paginas):
    """Painel de estado (idade, dinheiro, rendimento, despesas, saldo, esperança de vida)."""
    j = jogo.jogador
    rendimento = max(j.rendimento, RENDIMENTO_MINIMO)   # o rendimento nunca é menor que o mínimo
    saldo = rendimento - j.despesas                     # o que sobra (ou falta) por ano
    # número de turnos do jogo (arredondado para cima) e turno em que o jogador está
    total_turnos = -(-(IDADE_REFORMA - IDADE_INICIAL) // ANOS_POR_TURNO)
    turno = min(total_turnos, (j.idade - IDADE_INICIAL) // ANOS_POR_TURNO + 1)
    progresso = round((j.idade - IDADE_INICIAL) / (IDADE_REFORMA - IDADE_INICIAL) * 100)
    return paginas["painel"].substitute(
        inicial=html.escape(j.nome[:1].upper()),
        nome=html.escape(j.nome), sexo=html.escape(j.sexo), pais=html.escape(j.pais),
        turno=turno, total_turnos=total_turnos,
        idade=j.idade, progresso=min(100, progresso), fases=linha_fases(j.idade),
        dinheiro=eur(j.dinheiro), classe_dinheiro="pos" if j.dinheiro >= 0 else "neg",
        rendimento=eur(rendimento), despesas=eur(j.despesas),
        saldo=eur(saldo, True), classe_saldo="pos" if saldo >= 0 else "neg",
        esperanca=j.esperanca)


def chip(texto, classe):
    """Pequena etiqueta com um efeito (verde = bom, vermelho = mau, dourado = arriscado)."""
    return f'<span class="chip {classe}">{html.escape(texto)}</span>'


def botoes(opcoes):
    """Um botão por cada opção, com as etiquetas dos efeitos. O botão envia o número da opção."""
    saida = []
    for i, opcao in enumerate(opcoes):
        chips = "".join(chip(t, "bom" if bom else "mau") for t, bom in lista_efeitos(opcao["efeitos"]))
        if opcao.get("risco"):
            chips += chip("arriscado", "risco")
        saida.append(f'<button class="opcao" type="submit" name="opcao" value="{i}">'
                     f'<span class="texto">{html.escape(opcao["texto"])}</span>'
                     f'<span class="chips">{chips}</span></button>')
    return "\n".join(saida)


def grafico(historico_dinheiro):
    """Gráfico de barras só com HTML e CSS: uma linha por turno (verde = positivo, vermelho = dívida)."""
    maximo = max(abs(v) for _, v in historico_dinheiro) or 1
    linhas = []
    for idade, valor in historico_dinheiro:
        largura = max(1, round(abs(valor) / maximo * 100))     # largura da barra em %
        classe = "pos" if valor >= 0 else "neg"
        linhas.append(f'<div class="linha"><span class="idade">{idade}</span>'
                      f'<div class="trilho"><div class="barra-valor {classe}" style="width:{largura}%"></div></div>'
                      f'<span class="valor">{eur(valor)}</span></div>')
    return "\n".join(linhas)


def detalhes_finais(j):
    """Cartões com o balanço final (dinheiro máximo, mínimo, decisões, eventos...)."""
    valores = [dinheiro for _, dinheiro in j.historico_dinheiro]
    eventos = sum(1 for texto in j.historico if "Evento:" in texto)
    decisoes = len(j.historico) - eventos
    cartoes = [
        ("Idade final", f"{j.idade} anos", ""),
        ("Dinheiro final", eur(j.dinheiro), "pos" if j.dinheiro >= 0 else "neg"),
        ("Dinheiro máximo", eur(max(valores)), "pos"),
        ("Dinheiro mínimo", eur(min(valores)), "pos" if min(valores) >= 0 else "neg"),
        ("Decisões tomadas", str(decisoes), ""),
        ("Eventos vividos", str(eventos), ""),
        ("Rendimento por ano", eur(max(j.rendimento, RENDIMENTO_MINIMO)), ""),
        ("Despesas por ano", eur(j.despesas), ""),
    ]
    return "".join(f'<div class="cartao-final"><span>{nome}</span><strong class="{classe}">{valor}</strong></div>'
                   for nome, valor, classe in cartoes)


# =====================================================================
# 5b. PERSONAGEM (desenho em SVG feito pelo Python)
# SVG é uma forma de desenhar com código: retângulos (rect), círculos (circle),
# elipses (ellipse), polígonos (polygon) e caminhos (path). O browser desenha-os.
#
# O desenho mede 300 x 400 e o ponto (0, 0) é o canto de cima à esquerda
# (o y cresce para BAIXO). A personagem está ao centro, com os pés em y = 356.
#
# A função desenhar_personagem() junta CAMADAS, da mais funda para a da frente:
#   céu -> chão -> cenário (casa, carro...) -> personagem -> extras (moedas, confettis...)
# Cada camada é feita por uma função pequena que devolve um pedaço de texto SVG.
# =====================================================================
OURO = "#f2b705"                  # cor dourada usada nas joias, no relógio e nas moedas

# Informação de cada nível de riqueza (o número vem da função nivel_riqueza)
NIVEIS = {
    1: {"nome": "Falido", "icone": "💸",
        "frase": "Os bolsos estão vazios... e a roupa já viu melhores dias.",
        "descricao": "com a roupa rasgada e descalço, ao lado de uma caixa de cartão"},
    2: {"nome": "Pobre", "icone": "🪙",
        "frase": "Dá para ir vivendo, mas cada euro conta.",
        "descricao": "com roupa velha e remendada, numa rua modesta"},
    3: {"nome": "Classe média", "icone": "💶",
        "frase": "Uma vida tranquila, com as contas em dia.",
        "descricao": "com roupa casual, em frente a um prédio de apartamentos"},
    4: {"nome": "Rico", "icone": "💰",
        "frase": "O dinheiro está a render: já há carro e casa grande!",
        "descricao": "de fato e relógio, com um carro e uma casa grande"},
    5: {"nome": "Muito rico", "icone": "💎",
        "frase": "Mansão, carro desportivo... até o dinheiro voa!",
        "descricao": "com fato de luxo, óculos de sol e joias, um carro desportivo e uma mansão com piscina"},
}

# Frase debaixo da personagem no ecrã final (substitui a frase do nível)
FRASES_FINAIS = {
    "Liberdade financeira!": "De braços no ar: nunca mais precisas de trabalhar!",
    "Reforma confortável": "Uma reforma tranquila, sem preocupações.",
    "Reforma apertada": "Vai dar, mas é preciso contar os tostões.",
    "Reforma pobre": "De bengala na mão e com a carteira quase vazia.",
    "Falência!": "Os bancos ficaram com tudo...",
    "Morreste antes da reforma": "Descansa em paz.",
}

# Cores do céu (de cima, de baixo) e do chão para cada nível
CEUS = {1: ("#c9d1d9", "#eef1f4"), 2: ("#d3e4ee", "#f4f8fa"), 3: ("#9fdcff", "#eaf8ff"),
        4: ("#86d0ff", "#e4f6ff"), 5: ("#ffc98a", "#fff1d6")}
CHAOS = {1: "#b3b9c0", 2: "#c8c1b2", 3: "#9edb98", 4: "#8fd48a", 5: "#86d08a"}

# Roupa de cada nível: cor da camisola/casaco, das calças e dos sapatos (None = descalço)
ROUPAS = {
    1: {"camisola": "#9c907c", "calcas": "#6e6557", "sapatos": None, "mangas_curtas": True},
    2: {"camisola": "#9fb2bb", "calcas": "#5c6872", "sapatos": "#6b5140", "mangas_curtas": False},
    3: {"camisola": "#ff8a65", "calcas": "#3d6fb6", "sapatos": "#ffffff", "mangas_curtas": True},
    4: {"camisola": "#2f4366", "calcas": "#2f4366", "sapatos": "#1f1f1f", "mangas_curtas": False},
    5: {"camisola": "#7a1f3d", "calcas": "#7a1f3d", "sapatos": "#141414", "mangas_curtas": False},
}


# ---------------------- ESTADO DA PERSONAGEM ----------------------
def nivel_riqueza(dinheiro):
    """Devolve o nível de riqueza (1 = falido ... 5 = muito rico), usando os limites do início do ficheiro."""
    if dinheiro < LIMITE_POBRE:
        return 1
    if dinheiro < LIMITE_MEDIA:
        return 2
    if dinheiro < LIMITE_RICO:
        return 3
    if dinheiro < LIMITE_MUITO_RICO:
        return 4
    return 5


def cor_pele(esperanca):
    """Pele normal, ou pálida se a saúde (esperança de vida) estiver fraca."""
    return "#e2dccb" if esperanca <= SAUDE_FRACA else "#f2c9a0"


def cor_cabelo(idade):
    """O cabelo vai ficando grisalho com a idade."""
    if idade < 40:
        return "#5b3a29"     # castanho
    if idade < 50:
        return "#806b5e"     # primeiros cabelos brancos
    if idade < 58:
        return "#a9a39e"     # grisalho
    return "#dadada"         # branco


def humor_da_personagem(jogo, nivel):
    """Expressão da cara: 'feliz', 'contente', 'normal', 'triste' ou 'preocupado'."""
    if jogo.fase == "fim":
        return {"Liberdade financeira!": "feliz", "Reforma confortável": "feliz",
                "Reforma apertada": "normal"}.get(jogo.final["titulo"], "triste")
    if jogo.fase == "resultado":
        # reage ao último risco do turno: correu bem = feliz, correu mal = preocupado
        for texto in reversed(jogo.mensagens):
            if texto.startswith("Correu bem"):
                return "feliz"
            if texto.startswith("Correu mal"):
                return "preocupado"
    return {1: "triste", 2: "normal"}.get(nivel, "contente")


# ---------------------- CAMADAS DE FUNDO ----------------------
def camada_ceu(nivel):
    """Céu com um degradê (linearGradient) que muda de cor com o nível.
    Também define os dois FILTROS que dão o ar de desenho feito à mão:
      - "lapis": usa ruído (feTurbulence) para entortar ligeiramente os traços (feDisplacementMap);
      - "papel": um grão muito suave por cima de tudo, como papel de desenho."""
    cima, baixo = CEUS[nivel]
    return ('<defs><linearGradient id="ceu" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{cima}"/><stop offset="1" stop-color="{baixo}"/></linearGradient>'
            '<filter id="lapis" x="-5%" y="-5%" width="110%" height="110%">'
            '<feTurbulence type="fractalNoise" baseFrequency=".04" numOctaves="2" seed="4" result="ruido"/>'
            '<feDisplacementMap in="SourceGraphic" in2="ruido" scale="2.6" xChannelSelector="R" yChannelSelector="G"/></filter>'
            '<filter id="papel" x="0" y="0" width="100%" height="100%">'
            '<feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2" seed="9"/>'
            '<feColorMatrix values="0 0 0 0 .35  0 0 0 0 .28  0 0 0 0 .2  .32 0 0 0 -.08"/></filter></defs>'
            '<rect width="300" height="400" fill="url(#ceu)"/>')


def nuvem(x, y, escala=1.0, cor="#ffffff"):
    """Uma nuvem fofa feita com três círculos e uma base."""
    return (f'<g transform="translate({x} {y}) scale({escala})" fill="{cor}" stroke="{TINTA}" stroke-opacity=".35" stroke-width="1.5">'
            '<path d="M-30 10 Q-34 -4 -20 -6 Q-16 -22 2 -18 Q14 -28 24 -12 Q38 -12 34 4 Q34 12 24 12 L-24 12 Q-32 12 -30 10 Z"/></g>')


def camada_chao(nivel):
    """Chão (passeio cinzento quando se é pobre, relva quando se tem dinheiro)."""
    chao = (f'<path d="M0 334 Q70 324 150 332 T300 328 L300 400 L0 400 Z" fill="{CHAOS[nivel]}" '
            f'stroke="{TINTA}" stroke-opacity=".4" stroke-width="1.8"/>')
    if nivel >= 3:   # tufos de relva
        chao += "".join(f'<path d="M{x} 388 l3 -7 l2 6 l3 -8 l2 8" stroke="#3f8f45" stroke-width="1.4" fill="none" opacity=".7"/>'
                        for x in (20, 70, 118, 214, 262))
    return chao


def sol(x, y, raio):
    """Um sol amarelo com um brilho à volta."""
    return (f'<circle cx="{x}" cy="{y}" r="{raio + 10}" fill="#ffe680" opacity=".45" stroke="none"/>'
            f'<circle cx="{x}" cy="{y}" r="{raio}" fill="#ffd23f" stroke="#e0a800" stroke-width="2"/>')


def cenario_falido():
    """Nível 1: nuvem cinzenta, banco de jardim e uma caixa de cartão."""
    return (nuvem(86, 70, 1.3, "#99a2ac") + nuvem(200, 46, .8, "#aab2bb") +
            '<g fill="#8b6b4a">'                                              # banco de jardim
            '<rect x="12" y="266" width="86" height="7" rx="2"/><rect x="12" y="280" width="86" height="7" rx="2"/>'
            '<rect x="10" y="293" width="90" height="8" rx="2"/>'
            '<rect x="18" y="301" width="6" height="29"/><rect x="86" y="301" width="6" height="29"/></g>'
            '<g stroke="#9c7643" stroke-width="2">'                           # caixa de cartão
            '<rect x="204" y="286" width="82" height="44" fill="#c9a06a"/>'
            '<polygon points="204,286 188,268 240,276" fill="#d8b27e"/>'
            '<polygon points="286,286 298,264 250,276" fill="#d8b27e"/>'
            '<path d="M222 304 h46"/></g>')


def cenario_pobre():
    """Nível 2: prédio velho (com um vidro partido), candeeiro de rua e caixote do lixo."""
    janelas = "".join(f'<rect x="{x}" y="{y}" width="20" height="24" fill="#b8c7cf"/>'
                      for x in (22, 64) for y in (200, 240))
    return ('<rect x="10" y="180" width="90" height="150" fill="#d6c8ae"/>'
            '<rect x="6" y="174" width="98" height="8" fill="#b9a98c"/>'
            + janelas +
            '<path d="M66 242 l8 9 l-4 6 l9 9" stroke="#6b7a82" stroke-width="1.5" fill="none"/>'
            '<rect x="40" y="288" width="26" height="42" fill="#8d6e55"/>'
            '<rect x="252" y="200" width="6" height="130" fill="#69717a"/>'     # candeeiro
            '<path d="M255 202 q0 -16 -16 -16" stroke="#69717a" stroke-width="5" fill="none"/>'
            '<circle cx="238" cy="192" r="7" fill="#fff1a8"/>'
            '<rect x="266" y="304" width="26" height="26" rx="3" fill="#7f8c78"/>')   # caixote do lixo


def cenario_medio():
    """Nível 3: sol, prédio de apartamentos e uma árvore."""
    janelas = "".join(f'<rect x="{x}" y="{y}" width="16" height="18" rx="2" fill="#cdeeff"/>'
                      for x in (20, 46, 72) for y in (168, 198, 228, 258))
    return (sol(250, 62, 24) + nuvem(150, 50, .9) +
            '<rect x="10" y="150" width="96" height="180" rx="4" fill="#f7c9a6"/>' + janelas +
            '<rect x="45" y="292" width="24" height="38" rx="3" fill="#c98a5e"/>'
            '<rect x="244" y="258" width="12" height="72" fill="#8b5e3c"/>'     # árvore
            '<circle cx="250" cy="240" r="34" fill="#5cc46a"/>'
            '<circle cx="228" cy="262" r="20" fill="#4fb35e"/><circle cx="272" cy="260" r="20" fill="#4fb35e"/>')


def carro_normal():
    """Um carro familiar azul (nível 4)."""
    return ('<rect x="188" y="296" width="108" height="28" rx="9" fill="#2f8fe0"/>'
            '<path d="M206 296 L222 274 L266 274 L284 296 Z" fill="#2f8fe0"/>'
            '<path d="M214 294 L226 279 L243 279 L243 294 Z M248 294 L248 279 L262 279 L275 294 Z" fill="#dff4ff"/>'
            '<circle cx="292" cy="306" r="3" fill="#fff3a0"/>'
            + rodas(212, 272, 326))


def carro_desportivo():
    """Um carro desportivo vermelho, baixinho (nível 5)."""
    return ('<path d="M182 320 Q182 302 208 299 L236 286 Q258 279 278 292 L294 300 Q300 312 296 322 Z" fill="#e63946"/>'
            '<path d="M242 292 Q258 285 272 295 L244 297 Z" fill="#dff4ff"/>'
            '<rect x="182" y="292" width="6" height="12" fill="#b52430"/>'      # asa traseira
            '<circle cx="293" cy="309" r="3" fill="#fff3a0"/>'
            + rodas(208, 274, 324))


def rodas(x1, x2, y):
    """Duas rodas pretas com o centro cinzento."""
    return "".join(f'<circle cx="{x}" cy="{y}" r="11" fill="#2b2b2b"/><circle cx="{x}" cy="{y}" r="4" fill="#cfd5db"/>'
                   for x in (x1, x2))


def cenario_rico():
    """Nível 4: sol, casa grande com chaminé e sebe, e um carro."""
    sebe = "".join(f'<ellipse cx="{x}" cy="330" rx="16" ry="10" fill="#5dbb63"/>' for x in range(14, 140, 28))
    return (sol(250, 60, 24) + nuvem(70, 70) + nuvem(175, 40, .7) +
            '<rect x="8" y="226" width="124" height="104" fill="#fff4e0" stroke="#e9d6b5" stroke-width="2"/>'
            '<rect x="96" y="178" width="14" height="34" fill="#b55a44"/>'      # chaminé
            '<polygon points="0,230 70,172 140,230" fill="#e4684d"/>'            # telhado
            '<rect x="22" y="246" width="26" height="24" fill="#cdeeff" stroke="#ffffff" stroke-width="3"/>'
            '<rect x="92" y="246" width="26" height="24" fill="#cdeeff" stroke="#ffffff" stroke-width="3"/>'
            '<rect x="58" y="284" width="24" height="46" fill="#8b5e3c"/><circle cx="77" cy="308" r="2" fill="#f2b705"/>'
            + sebe + carro_normal())


def palmeira():
    """Palmeira: um tronco curvo e várias folhas (elipses rodadas à volta do topo)."""
    folhas = "".join(f'<ellipse cx="254" cy="196" rx="34" ry="8" fill="#3fb26b" '
                     f'transform="rotate({angulo} 254 196) translate(28 0)"/>'
                     for angulo in (-170, -130, -50, -10, 30, 150))
    return ('<path d="M262 330 Q272 262 254 196" stroke="#9b6b3d" stroke-width="10" fill="none" stroke-linecap="round"/>'
            + folhas + '<circle cx="250" cy="203" r="5" fill="#7a4e2a"/><circle cx="259" cy="204" r="5" fill="#7a4e2a"/>')


def cenario_muito_rico():
    """Nível 5: sol de fim de tarde, mansão com colunas, piscina, palmeira e carro desportivo."""
    colunas = "".join(f'<rect x="{x}" y="214" width="10" height="116" fill="#ffffff" stroke="#e6dcc8"/>'
                      for x in (20, 48, 102, 130))
    janelas = "".join(f'<rect x="{x}" y="{y}" width="14" height="22" rx="7" fill="#cdeeff"/>'
                      for x in (31, 115) for y in (226, 276))
    return (sol(70, 70, 26) + palmeira() +
            '<rect x="4" y="204" width="152" height="126" fill="#fffaf0" stroke="#eadfc8" stroke-width="2"/>'
            '<polygon points="0,208 80,156 160,208" fill="#c98b2a"/>'            # telhado
            '<polygon points="22,204 80,168 138,204" fill="#e0a640"/>'
            + colunas + janelas +
            '<rect x="66" y="270" width="28" height="60" rx="14" fill="#a0522d"/><circle cx="88" cy="302" r="2.5" fill="#f2b705"/>'
            '<rect x="6" y="346" width="100" height="30" rx="10" fill="#5ccbf2" stroke="#ffffff" stroke-width="3"/>'  # piscina
            '<path d="M20 360 q8 -5 16 0 t16 0 t16 0 t16 0" stroke="#ffffff" stroke-width="2" fill="none"/>'
            + carro_desportivo())


# Que cenário desenhar em cada nível
CENARIOS = {1: cenario_falido, 2: cenario_pobre, 3: cenario_medio, 4: cenario_rico, 5: cenario_muito_rico}


# ---------------------- A PERSONAGEM (de trás para a frente) ----------------------
# Para o desenho não parecer "de computador":
#   - tudo tem um contorno escuro, como se fosse desenhado a caneta (cor TINTA);
#   - braços e pernas são LINHAS GROSSAS e curvas (função membro), não retângulos;
#   - a pose não é simétrica (o peso está mais numa perna, um braço mais aberto);
#   - a cabeça está ligeiramente inclinada e há sombras na roupa e no chão;
#   - no fim, um filtro SVG ("lapis") faz os traços tremer um pouco, como num desenho à mão.
TINTA = "#3b2f2a"                 # cor dos contornos

# Pernas (do quadril ao tornozelo). A direita está mais aberta: o peso está na esquerda.
PERNA_ESQ = "M138 256 Q136 304 134 348"
PERNA_DIR = "M162 256 Q167 304 167 348"

# Braços: (caminho do braço, caminho da manga curta, mão, cotovelo, pulso)
POSES = {
    False: {"esq": ("M121 190 Q107 222 111 254", "M121 190 Q114 202 112 213", (111, 259), (109, 224), (111, 245)),
            "dir": ("M179 190 Q195 220 189 252", "M179 190 Q186 202 188 212", (189, 257), (191, 222), (190, 243))},
    True: {"esq": ("M121 190 Q102 166 106 132", "M121 190 Q112 181 109 172", (106, 126), (108, 162), (106, 141)),
           "dir": ("M179 190 Q198 166 194 132", "M179 190 Q188 181 191 172", (194, 126), (192, 162), (194, 141))},
}


def membro(caminho, cor, largura, ponta="round"):
    """Braço ou perna: uma linha grossa e curva, com contorno.
    Desenha primeiro a linha mais larga (escura) e por cima a linha da cor certa."""
    return (f'<path d="{caminho}" stroke="{TINTA}" stroke-width="{largura + 4}" fill="none" stroke-linecap="{ponta}"/>'
            f'<path d="{caminho}" stroke="{cor}" stroke-width="{largura}" fill="none" stroke-linecap="{ponta}"/>')


def sombra_no_chao():
    """Sombra suave debaixo dos pés (faz a personagem "assentar" no chão)."""
    return '<ellipse cx="151" cy="358" rx="46" ry="7" fill="#000000" opacity=".15"/>'


def cabelo_atras(sexo, cor):
    """Parte do cabelo que fica ATRÁS da cabeça: comprido e ondulado (Feminino), pelo queixo (Outro)."""
    if sexo == "Feminino":
        caminho = ("M120 128 Q116 98 150 96 Q184 98 180 128 Q186 170 190 204 Q178 214 166 206 "
                   "Q150 214 134 206 Q122 214 110 204 Q114 170 120 128 Z")
    elif sexo == "Outro":
        caminho = "M119 130 Q115 98 150 97 Q185 98 181 130 L184 168 Q176 175 168 168 Q150 175 132 168 Q124 175 116 168 Z"
    else:
        return ""
    return f'<path d="{caminho}" fill="{cor}" stroke="{TINTA}" stroke-width="2.2"/>'


def cabelo_frente(sexo, cor):
    """Franja e madeixas por cima da cabeça. Os traços finos fazem de fios de cabelo."""
    if sexo == "Masculino":   # cabelo curto e despenteado
        caminho = ("M121 133 Q117 104 142 99 Q160 94 174 106 Q182 115 179 133 Q174 120 166 116 "
                   "Q163 124 154 117 Q146 124 138 116 Q130 122 121 133 Z")
        fios = "M141 103 q4 6 1 12 M157 100 q3 7 -2 13 M168 107 q2 5 -1 9"
    else:                     # franja de lado
        caminho = "M121 136 Q116 100 150 98 Q182 100 180 132 Q171 115 151 113 Q141 121 129 123 Q124 128 121 136 Z"
        fios = "M146 101 q-8 6 -14 16 M160 102 q6 5 12 14"
    return (f'<path d="{caminho}" fill="{cor}" stroke="{TINTA}" stroke-width="2.2"/>'
            f'<path d="{fios}" stroke="{TINTA}" stroke-width="1.3" fill="none" opacity=".45"/>')


def sapato(x, lado, cor, pele):
    """Um sapato com bico (ou um pé descalço com dedos, se cor for None)."""
    s = -1 if lado == "esq" else 1          # o pé esquerdo aponta para a esquerda, o direito para a direita
    forma = (f"M{x + 14 * s} 352 Q{x + 12 * s} 344 {x} 345 Q{x - 10 * s} 346 {x - 12 * s} 352 "
             f"Q{x - 12 * s} 358 {x} 358 L{x + 12 * s} 358 Q{x + 16 * s} 357 {x + 14 * s} 352 Z")
    if cor is None:   # descalço
        dedos = f'<path d="M{x + 8 * s} 352 v4 M{x + 11 * s} 351 v4" stroke="{TINTA}" stroke-width="1.2" opacity=".6"/>'
        return f'<path d="{forma}" fill="{pele}" stroke="{TINTA}" stroke-width="2"/>{dedos}'
    brilho = f'<path d="M{x + 3 * s} 348 q4 0 7 2" stroke="#ffffff" stroke-width="1.5" fill="none" opacity=".5"/>'
    return f'<path d="{forma}" fill="{cor}" stroke="{TINTA}" stroke-width="2"/>{brilho}'


def pernas(nivel, sexo, pele, roupa):
    """Pernas, calças (ou saia) e sapatos. No nível 1 as calças estão rasgadas e não há sapatos."""
    saia = sexo == "Feminino" and nivel >= 3
    partes = []
    if saia:
        partes += [membro(PERNA_ESQ, pele, 17), membro(PERNA_DIR, pele, 17)]
    elif nivel == 1:   # calças rasgadas: pele à mostra em baixo e bainha em bico
        partes += [membro(PERNA_ESQ, pele, 16), membro(PERNA_DIR, pele, 16),
                   membro("M138 256 Q136 292 135 324", roupa["calcas"], 22, "butt"),
                   membro("M162 256 Q166 292 166 324", roupa["calcas"], 22, "butt")]
        for x in (135, 166):
            partes.append(f'<polygon points="{x - 13},323 {x - 7},331 {x - 1},323 {x + 5},332 {x + 13},323" '
                          f'fill="{roupa["calcas"]}" stroke="{TINTA}" stroke-width="1.8" stroke-linejoin="round"/>')
        partes.append('<rect x="128" y="284" width="14" height="13" fill="#b5a27e" stroke="#6f5f47" '
                      'stroke-dasharray="2 2" transform="rotate(-6 135 290)"/>')               # remendo no joelho
        partes.append(f'<path d="M161 294 l8 -3 l5 7 l-9 5 Z" fill="{pele}" stroke="{TINTA}" stroke-width="1.3"/>')  # buraco
    else:
        partes += [membro(PERNA_ESQ, roupa["calcas"], 22), membro(PERNA_DIR, roupa["calcas"], 22),
                   f'<path d="M144 262 L145 300" stroke="{TINTA}" stroke-width="1.2" opacity=".35"/>']   # vinco
    if saia:
        partes.append(f'<path d="M118 254 Q150 248 182 254 L192 312 Q150 320 108 312 Z" fill="{roupa["calcas"]}" '
                      f'stroke="{TINTA}" stroke-width="2.2" stroke-linejoin="round"/>'
                      f'<path d="M140 262 L134 312 M162 262 L168 312" stroke="{TINTA}" stroke-width="1.2" opacity=".35"/>')
    partes += [sapato(134, "esq", roupa["sapatos"], pele), sapato(167, "dir", roupa["sapatos"], pele)]
    return "".join(partes)


def tronco(nivel, pele, roupa):
    """Camisola, t-shirt ou casaco: ombros largos e cintura mais estreita, com sombra de um lado."""
    corpo = "M121 182 Q150 172 179 182 Q187 186 187 198 L183 262 Q150 270 117 262 L113 198 Q113 186 121 182 Z"
    sombra = "M168 180 Q187 186 187 198 L183 262 Q174 266 166 266 Q173 222 168 180 Z"
    pregas = '<path d="M127 246 q8 5 16 2 M158 240 q6 -3 12 1" stroke="#3b2f2a" stroke-width="1.4" fill="none" opacity=".35"/>'
    partes = [f'<path d="{corpo}" fill="{roupa["camisola"]}" stroke="{TINTA}" stroke-width="2.4"/>',
              f'<path d="{sombra}" fill="#000000" opacity=".12"/>']
    if nivel >= 4:                       # fato: camisa, gravata, lapelas, botões e bolso
        gravata = OURO if nivel == 5 else "#d03b3b"
        lapela = OURO if nivel == 5 else "#00000066"
        partes += [f'<path d="M139 176 L150 206 L161 176 Z" fill="#ffffff" stroke="{TINTA}" stroke-width="1.6"/>',
                   f'<path d="M147 183 L153 183 L156 220 L150 229 L144 220 Z" fill="{gravata}" stroke="{TINTA}" stroke-width="1.6"/>',
                   f'<path d="M139 176 L131 198 L141 197 L150 214 M161 176 L169 198 L159 197 L150 214" '
                   f'stroke="{lapela}" stroke-width="2" fill="none"/>',
                   '<circle cx="150" cy="240" r="2.3" fill="#00000066"/><circle cx="150" cy="253" r="2.3" fill="#00000066"/>',
                   '<path d="M160 236 h15" stroke="#00000055" stroke-width="1.6"/>']
        if nivel == 5:
            partes.append(f'<path d="M164 199 l5 -8 l3 6 l4 -4 l0 7 Z" fill="{OURO}" stroke="{TINTA}" stroke-width="1"/>')  # lenço
    elif nivel == 3:                     # t-shirt com decote e uma risca
        partes += [f'<path d="M138 177 Q150 192 162 177" fill="{pele}" stroke="{TINTA}" stroke-width="1.8"/>',
                   '<path d="M115 226 Q150 232 185 226" stroke="#ffffff" stroke-width="6" fill="none" opacity=".6"/>',
                   pregas]
    elif nivel == 2:                     # camisola velha, com nódoa e pregas
        partes += ['<ellipse cx="163" cy="232" rx="8" ry="5" fill="#000000" opacity=".1" transform="rotate(-15 163 232)"/>',
                   f'<path d="M140 178 Q150 186 160 178" stroke="{TINTA}" stroke-width="1.6" fill="none"/>', pregas]
    else:                                # nível 1: decote lasso, rasgão, remendo e bainha desfiada
        partes += [f'<path d="M136 177 Q150 197 164 177" fill="{pele}" stroke="{TINTA}" stroke-width="1.8"/>',
                   f'<path d="M156 204 l10 7 l-7 7 l10 9 l-15 -1 Z" fill="{pele}" stroke="{TINTA}" stroke-width="1.3"/>',
                   '<rect x="124" y="231" width="16" height="14" fill="#c9b58f" stroke="#6f5f47" stroke-dasharray="2 2" '
                   'transform="rotate(8 132 238)"/>',
                   f'<path d="M124 263 l3 6 l3 -5 l3 7 l3 -6 M166 264 l3 6 l3 -6 l3 5" stroke="{TINTA}" stroke-width="1.4" fill="none"/>',
                   pregas]
    return "".join(partes)


def bracos(nivel, pele, roupa, bracos_no_ar):
    """Os dois braços (linhas grossas e curvas) com as mãos. Com bracos_no_ar=True ficam levantados."""
    partes = []
    for lado in ("esq", "dir"):
        caminho, manga, (mx, my), (cx, cy), (px, py) = POSES[bracos_no_ar][lado]
        if roupa["mangas_curtas"]:   # braço à mostra e só um bocadinho de manga
            partes += [membro(caminho, pele, 15), membro(manga, roupa["camisola"], 20)]
        else:
            partes.append(membro(caminho, roupa["camisola"], 17))
        if lado == "esq" and nivel == 2:   # remendo no cotovelo
            partes.append(f'<circle cx="{cx}" cy="{cy}" r="6" fill="#8a9aa2" stroke="#5c6870" stroke-dasharray="2 1.5"/>')
        if lado == "esq" and nivel >= 4:   # relógio no pulso
            relogio = OURO if nivel == 5 else "#c0c7cf"
            partes.append(f'<rect x="{px - 10}" y="{py - 3}" width="20" height="7" rx="2" fill="{relogio}" '
                          f'stroke="{TINTA}" stroke-width="1.4"/>')
        partes.append(f'<ellipse cx="{mx}" cy="{my}" rx="7.5" ry="8.5" fill="{pele}" stroke="{TINTA}" stroke-width="2"/>')  # mão
        if lado == "dir" and nivel == 5:   # anel
            partes.append(f'<circle cx="{mx - 4}" cy="{my + 3}" r="2.4" fill="{OURO}" stroke="{TINTA}" stroke-width="1"/>')
    return "".join(partes)


def boca(humor):
    """A boca muda com o humor (as curvas não são perfeitas de propósito)."""
    if humor == "feliz":
        return (f'<path d="M139 151 Q150 165 161 151 Q150 155 139 151 Z" fill="#9c3434" stroke="{TINTA}" stroke-width="1.8"/>'
                '<path d="M145 158 q5 3 10 0" stroke="#e46a6a" stroke-width="2.5" fill="none"/>')   # língua
    caminho = {"contente": "M140 153 Q150 160.5 160 152.5",
               "normal": "M142 155 Q150 156.5 158 154.5"}.get(humor, "M140 158 Q150 151 160 157.5")   # triste/preocupado
    return f'<path d="{caminho}" stroke="{TINTA}" stroke-width="2.3" fill="none" stroke-linecap="round"/>'


def olhos(humor):
    """Olhos com branco, pupila e um pontinho de brilho (fechados em arco quando está feliz)."""
    if humor == "feliz":
        return f'<path d="M135 136 q5 -6 10 0 M155 136 q5 -6 10 0" stroke="{TINTA}" stroke-width="2.4" fill="none"/>'
    dy = -1.2 if humor == "preocupado" else 0.5     # preocupado: olha para cima
    partes = []
    for x in (140, 160):
        partes.append(f'<ellipse cx="{x}" cy="135" rx="5" ry="5.8" fill="#ffffff" stroke="{TINTA}" stroke-width="1.6"/>'
                      f'<circle cx="{x + 1}" cy="{135 + dy}" r="2.8" fill="{TINTA}"/>'
                      f'<circle cx="{x + 2}" cy="{134 + dy}" r=".9" fill="#ffffff"/>')
    return "".join(partes)


def cara(pele, idade, esperanca, humor, nivel):
    """Orelhas, cara (com queixo), olhos, sobrancelhas, nariz, boca, rugas e sinais de saúde."""
    partes = [f'<ellipse cx="122" cy="135" rx="6" ry="8" fill="{pele}" stroke="{TINTA}" stroke-width="2"/>'
              f'<ellipse cx="178" cy="135" rx="6" ry="8" fill="{pele}" stroke="{TINTA}" stroke-width="2"/>',
              f'<path d="M122 130 Q122 102 150 102 Q178 102 178 130 Q178 158 157 166 Q150 168 143 166 '
              f'Q122 158 122 130 Z" fill="{pele}" stroke="{TINTA}" stroke-width="2.4"/>',
              olhos(humor)]
    if humor in ("triste", "preocupado"):   # sobrancelhas levantadas no meio
        sobrancelhas = "M134 128 Q140 125 145 122 M155 122 Q160 125 166 128"
    else:
        sobrancelhas = "M134 126 Q140 123 145 125 M155 124.5 Q160 122.5 166 125.5"
    cor_sobrancelhas = "#4a3428" if idade < 50 else "#8f8a86"   # ficam grisalhas mais tarde
    partes.append(f'<path d="{sobrancelhas}" stroke="{cor_sobrancelhas}" stroke-width="2.8" fill="none" stroke-linecap="round"/>')
    partes.append(f'<path d="M150 136 Q146 146 151 147" stroke="{TINTA}" stroke-width="1.8" fill="none" stroke-linecap="round"/>')
    partes.append(boca(humor))
    if esperanca <= SAUDE_FRACA or nivel <= 2:   # olheiras (doente ou cansado)
        partes.append('<path d="M135 142 q5 3 10 0 M155 142 q5 3 10 0" stroke="#8d6f9c" stroke-width="1.6" fill="none" opacity=".7"/>')
    if esperanca >= SAUDE_BOA:                   # bochechas coradas
        partes.append('<ellipse cx="132" cy="147" rx="5.5" ry="3.5" fill="#ff7f7f" opacity=".45"/>'
                      '<ellipse cx="168" cy="147" rx="5.5" ry="3.5" fill="#ff7f7f" opacity=".45"/>')
    if idade >= 45:   # rugas na testa
        partes.append(f'<path d="M142 119 q8 -2 16 0" stroke="{TINTA}" stroke-width="1.2" fill="none" opacity=".35"/>')
    if idade >= 55:   # rugas ao lado dos olhos
        partes.append(f'<path d="M130 132 l-4 -2 M130 137 l-4 1 M170 132 l4 -2 M170 137 l4 1" stroke="{TINTA}" '
                      f'stroke-width="1.2" opacity=".4"/>')
    if humor == "preocupado":   # gota de suor
        partes.append('<path d="M177 116 q6 9 0 12 q-6 -3 0 -12 Z" fill="#8fd3ff" stroke="#3d8fc4" stroke-width="1"/>')
    return "".join(partes)


def acessorios(nivel, sexo):
    """Óculos de sol e fio de ouro (nível 5) e brincos (Feminino, níveis 4 e 5)."""
    partes = []
    if nivel == 5:
        partes.append(f'<g fill="#1b1b1b" stroke="{TINTA}" stroke-width="1.2"><path d="M131 130 h18 q0 11 -9 11 q-9 0 -9 -11 Z"/>'
                      '<path d="M151 130 h18 q0 11 -9 11 q-9 0 -9 -11 Z"/><path d="M149 131 h2" stroke-width="2.5"/></g>'
                      '<path d="M134 132 l5 0 M154 132 l5 0" stroke="#ffffff" stroke-width="1.5" opacity=".7"/>'
                      f'<path d="M137 178 Q150 196 163 178" stroke="{OURO}" stroke-width="3" fill="none" stroke-dasharray="3 1"/>')
    if sexo == "Feminino" and nivel >= 4:
        partes.append(f'<circle cx="122" cy="147" r="3" fill="{OURO}" stroke="{TINTA}" stroke-width="1"/>'
                      f'<circle cx="178" cy="147" r="3" fill="{OURO}" stroke="{TINTA}" stroke-width="1"/>')
    return "".join(partes)


def bengala():
    """Bengala de madeira na mão direita (reforma pobre)."""
    return membro("M190 260 L201 357", "#8a5c34", 5) + membro("M190 260 q-1 -12 -12 -9", "#8a5c34", 5)


def figura(jogador, nivel, humor, bracos_no_ar=False, com_bengala=False, com_sombra=True):
    """Junta todas as partes da personagem, de trás para a frente.
    A cabeça fica um pouco inclinada (mais caída quando está triste), para a pose ser natural."""
    pele = cor_pele(jogador.esperanca)
    cabelo = cor_cabelo(jogador.idade)
    roupa = ROUPAS[nivel]
    inclinacao = {"feliz": 4, "triste": -5, "preocupado": -3}.get(humor, -2)
    girar = f'transform="rotate({inclinacao} 150 168)"'   # a cabeça e o cabelo rodam juntos
    cabeca = (cara(pele, jogador.idade, jogador.esperanca, humor, nivel)
              + cabelo_frente(jogador.sexo, cabelo)
              + acessorios(nivel, jogador.sexo))
    return ('<g stroke-linejoin="round" stroke-linecap="round">'
            + (sombra_no_chao() if com_sombra else "")   # o anjo flutua, não tem sombra
            + f'<g {girar}>{cabelo_atras(jogador.sexo, cabelo)}</g>'   # cabelo comprido fica atrás do corpo
            + pernas(nivel, jogador.sexo, pele, roupa)
            + f'<path d="M142 156 L142 182 Q150 186 158 182 L158 156 Z" fill="{pele}" stroke="{TINTA}" stroke-width="2"/>'
            + (bengala() if com_bengala else "")          # antes dos braços: a mão fica por cima da bengala
            + bracos(nivel, pele, roupa, bracos_no_ar)    # antes do tronco: os braços saem de dentro das mangas
            + tronco(nivel, pele, roupa)
            + f'<g {girar}>{cabeca}</g>'
            + '</g>')


# ---------------------- EXTRAS ----------------------
def dinheiro_a_voar():
    """Moedas e notas a flutuar no céu (nível 5). A animação está no CSS (classe 'voa')."""
    moedas = "".join(f'<g class="voa" style="animation-delay:{i * .5}s">'
                     f'<circle cx="{x}" cy="{y}" r="11" fill="{OURO}" stroke="#c78f00" stroke-width="2"/>'
                     f'<text x="{x}" y="{y + 4}" font-size="12" font-weight="700" fill="#8a5a00" text-anchor="middle">€</text></g>'
                     for i, (x, y) in enumerate([(130, 40), (196, 104), (112, 118), (236, 150)]))
    notas = "".join(f'<g class="voa" style="animation-delay:{i * .7 + .3}s">'
                    f'<rect x="{x}" y="{y}" width="30" height="16" rx="2" fill="#7bc96f" stroke="#4f9a45" '
                    f'transform="rotate({angulo} {x + 15} {y + 8})"/></g>'
                    for i, (x, y, angulo) in enumerate([(160, 60, -15), (200, 30, 12)]))
    return moedas + notas


def confettis():
    """Papelinhos coloridos para a festa da liberdade financeira."""
    cores = ["#ff7a59", "#3cc7a6", "#2f8fe0", "#ffc93c", "#b46cf0"]
    posicoes = [(30, 40), (70, 90), (110, 30), (190, 50), (230, 100), (270, 40), (50, 150), (250, 170), (150, 70)]
    # o <g class="voa"> anima; o <rect> lá dentro fica com a sua rotação (a animação não a apaga)
    return "".join(f'<g class="voa" style="animation-delay:{i * .3}s"><rect x="{x}" y="{y}" width="8" height="4" '
                   f'fill="{cores[i % len(cores)]}" transform="rotate({i * 37} {x} {y})"/></g>'
                   for i, (x, y) in enumerate(posicoes))


def lapide(jogador):
    """Lápide com o nome e as idades, e umas flores (morte antes da reforma)."""
    nome = html.escape(jogador.nome[:12])
    return ('<path d="M110 358 L110 292 Q110 256 150 256 Q190 256 190 292 L190 358 Z" fill="#aab2bb" stroke="#8a939c" stroke-width="3"/>'
            '<text x="150" y="292" font-size="15" font-weight="700" fill="#4a535c" text-anchor="middle">R.I.P.</text>'
            f'<text x="150" y="315" font-size="12" fill="#4a535c" text-anchor="middle">{nome}</text>'
            f'<text x="150" y="334" font-size="11" fill="#4a535c" text-anchor="middle">{IDADE_INICIAL}–{jogador.idade}</text>'
            '<g><circle cx="104" cy="354" r="6" fill="#ff7a8a"/><circle cx="196" cy="354" r="6" fill="#ffd23f"/>'
            '<circle cx="114" cy="358" r="5" fill="#b46cf0"/><circle cx="186" cy="358" r="5" fill="#ff7a59"/></g>')


def anjo(jogador, nivel):
    """A personagem em pequeno, com asas e auréola, a flutuar por cima da lápide."""
    asas = ('<ellipse cx="102" cy="210" rx="30" ry="16" fill="#ffffff" stroke="#dfe7ee" transform="rotate(-25 102 210)"/>'
            '<ellipse cx="198" cy="210" rx="30" ry="16" fill="#ffffff" stroke="#dfe7ee" transform="rotate(25 198 210)"/>')
    aureola = f'<ellipse cx="150" cy="100" rx="22" ry="6" stroke="{OURO}" stroke-width="4" fill="none"/>'
    return (f'<g class="voa"><g opacity=".9" transform="translate(67.5 -35) scale(.55)">'
            f'{asas}{figura(jogador, nivel, "contente", com_sombra=False)}{aureola}</g></g>')


# ---------------------- JUNTAR TUDO ----------------------
def desenhar_personagem(jogo):
    """Desenha a personagem completa em SVG.
    Devolve um dicionário com o SVG, o nível de riqueza e o humor."""
    j = jogo.jogador
    titulo_final = jogo.final["titulo"] if jogo.fase == "fim" else None
    nivel = 1 if titulo_final == "Falência!" else nivel_riqueza(j.dinheiro)
    humor = humor_da_personagem(jogo, nivel)

    # o cenário só aparece com animação quando o jogador SOBE de nível
    subiu = jogo.nivel_visto is not None and nivel > jogo.nivel_visto
    jogo.nivel_visto = nivel

    # descrição para leitores de ecrã (acessibilidade)
    descricao = f"{j.nome}, {j.idade} anos, {NIVEIS[nivel]['nome'].lower()}: {NIVEIS[nivel]['descricao']}."
    if j.esperanca <= SAUDE_FRACA:
        descricao += " Tem ar doente."
    elif j.esperanca >= SAUDE_BOA:
        descricao += " Está em boa forma."

    # o cenário leva um contorno suave; cenário e personagem passam pelo filtro "lapis"
    camadas = [camada_ceu(nivel),
               f'<g filter="url(#lapis)" stroke="{TINTA}" stroke-opacity=".6" stroke-width="1.6" stroke-linejoin="round">'
               f'{camada_chao(nivel)}<g class="cenario{" subiu" if subiu else ""}">{CENARIOS[nivel]()}</g></g>']
    if titulo_final == "Morreste antes da reforma":
        camadas += [f'<g filter="url(#lapis)">{lapide(j)}{anjo(j, nivel)}</g>']
        descricao = f"Uma lápide com o nome de {j.nome}, que morreu aos {j.idade} anos, e um anjo por cima."
    else:
        no_ar = titulo_final == "Liberdade financeira!"
        com_bengala = titulo_final == "Reforma pobre"
        camadas.append(f'<g filter="url(#lapis)"><g class="figura">{figura(j, nivel, humor, no_ar, com_bengala)}</g></g>')
        if no_ar:
            camadas.append(confettis())
            descricao += " Está a celebrar de braços no ar."
        if com_bengala:
            descricao += " Anda de bengala."
        if nivel == 5:
            camadas.append(dinheiro_a_voar())

    camadas.append('<rect width="300" height="400" filter="url(#papel)"/>')   # grão de papel por cima de tudo
    svg = ('<svg class="personagem-svg" viewBox="0 0 300 400" role="img" aria-labelledby="personagem-titulo">'
           f'<title id="personagem-titulo">{html.escape(descricao)}</title>'
           + "".join(camadas) + '</svg>')
    return {"svg": svg, "nivel": nivel, "humor": humor}


def caixa_personagem(jogo, paginas):
    """Preenche a página 'personagem' do paginas.html (desenho + legenda com o nível)."""
    desenho = desenhar_personagem(jogo)
    info = NIVEIS[desenho["nivel"]]
    frase = info["frase"]
    if jogo.fase == "fim":
        frase = FRASES_FINAIS.get(jogo.final["titulo"], frase)
    elif desenho["humor"] == "feliz":
        frase = "Que alegria: a sorte esteve do teu lado!"
    elif desenho["humor"] == "preocupado":
        frase = "Ui... isto não correu nada bem."
    return paginas["personagem"].substitute(
        svg=desenho["svg"], nivel=desenho["nivel"], icone=info["icone"],
        nome_nivel=info["nome"], frase=html.escape(frase))


def pagina_inicio(erro=""):
    """Ecrã inicial: pede nome, sexo e país. Se houver erro, mostra a mensagem."""
    paginas = carregar_paginas()
    caixa_erro = f'<p class="erro">{html.escape(erro)}</p>' if erro else ""
    return montar(paginas, "inicio", erro=caixa_erro)


def pagina_do_jogo(jogo):
    """Escolhe a página certa consoante a fase do jogo (decisão, evento, resultado ou fim)."""
    paginas = carregar_paginas()
    estado = painel(jogo, paginas)
    personagem = caixa_personagem(jogo, paginas)   # desenho da personagem (coluna da esquerda)

    # --- decisão da vida ou evento com escolha ---
    if jogo.fase in ("decisao", "evento"):
        if jogo.fase == "decisao":
            situacao = jogo.decisao
            etiqueta = f"Decisão · fase dos {fase_da_idade(jogo.jogador.idade)} anos"
        else:
            situacao = jogo.evento
            etiqueta = "Evento aleatório!"
        return montar(paginas, "decisao", larga=True, personagem=personagem,
                      painel=estado, tipo=jogo.fase, etiqueta=etiqueta,
                      titulo=html.escape(situacao["titulo"]),
                      descricao=html.escape(situacao["descricao"]),
                      botoes=botoes(situacao["opcoes"]))

    # --- o que aconteceu depois da escolha ---
    if jogo.fase == "resultado":
        return montar(paginas, "resultado", larga=True, personagem=personagem,
                      painel=estado, mensagens=lista_html(jogo.mensagens))

    # --- fim do jogo ---
    j = jogo.jogador
    final = jogo.final
    return montar(paginas, "fim", larga=True, personagem=personagem, painel=estado,
                  classe_final=final["classe"],
                  icone=ICONES_FINAIS.get(final["titulo"], "🏁"),
                  titulo_final=html.escape(final["titulo"]),
                  explicacao=html.escape(final["explicacao"]),
                  dica=html.escape(DICAS.get(final["titulo"], "Experimenta outras decisões e vê o que muda.")),
                  detalhes=detalhes_finais(j),
                  grafico=grafico(j.historico_dinheiro),
                  historico=lista_html(j.historico))


# =====================================================================
# 6. SERVIDOR WEB
# Pequeno servidor feito só com a biblioteca standard (http.server).
# Recebe os cliques do browser, atualiza o jogo e devolve a página seguinte.
# =====================================================================
PORTA = 8000                                  # o jogo abre em http://127.0.0.1:8000
SESSOES = {}                                  # cookie 'sid' -> Jogo (cada visitante tem o seu jogo, em memória)
SEXOS = ("Masculino", "Feminino", "Outro")    # opções de sexo aceites
TAMANHO_MAXIMO_POST = 10_000                  # limite de segurança para os dados de um formulário


class Manipulador(BaseHTTPRequestHandler):
    """Trata cada pedido do browser. GET = mostrar páginas, POST = ações do jogador."""

    def _sid(self):
        """Lê o identificador de sessão da cookie (ou None se ainda não existir)."""
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        return cookie["sid"].value if "sid" in cookie else None

    def _responder(self, texto, tipo="text/html; charset=utf-8", codigo=200):
        """Envia uma resposta de texto (HTML ou CSS) ao browser."""
        corpo = texto.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")     # o browser não guarda cópias: F5 mostra as alterações
        self.end_headers()
        self.wfile.write(corpo)

    def _redirecionar(self, novo_sid=None):
        """Volta à página inicial '/' (assim, carregar em F5 não reenvia o formulário)."""
        self.send_response(303)
        self.send_header("Location", "/")
        if novo_sid:
            self.send_header("Set-Cookie", f"sid={novo_sid}; Path=/; HttpOnly; SameSite=Lax")
        self.end_headers()

    def do_GET(self):
        """O browser pede uma página (GET)."""
        caminho = self.path.split("?")[0]
        try:
            if caminho == "/estilo.css":
                self._responder(FICHEIRO_CSS.read_text(encoding="utf-8"), "text/css; charset=utf-8")
            elif caminho == "/":
                jogo = SESSOES.get(self._sid())
                self._responder(pagina_inicio() if jogo is None else pagina_do_jogo(jogo))
            elif caminho == "/favicon.ico":
                self.send_response(204)                    # sem conteúdo (o ícone já vem no HTML)
                self.end_headers()
            else:
                self._responder("Página não encontrada.", codigo=404)
        except Exception as erro:                          # mostra o erro no terminal e no browser
            traceback.print_exc()
            self._responder(f"Erro no servidor: {html.escape(str(erro))}", codigo=500)

    def do_POST(self):
        """O jogador clicou num botão (POST): começar, escolher uma opção, continuar ou reiniciar."""
        try:
            tamanho = min(int(self.headers.get("Content-Length", 0)), TAMANHO_MAXIMO_POST)
            campos = parse_qs(self.rfile.read(tamanho).decode("utf-8"))
            pedir = lambda nome: campos.get(nome, [""])[0].strip()      # lê um campo do formulário
            jogo = SESSOES.get(self._sid())

            if self.path == "/comecar":
                nome, sexo, pais = pedir("nome"), pedir("sexo"), pedir("pais")
                # validação feita no servidor (nunca confiar no que vem do formulário)
                if not 1 <= len(nome) <= 30:
                    return self._responder(pagina_inicio("Escreve um nome (até 30 letras)."))
                if sexo not in SEXOS:
                    return self._responder(pagina_inicio("Escolhe uma opção de sexo válida."))
                if not 1 <= len(pais) <= 40:
                    return self._responder(pagina_inicio("Escreve o teu país."))
                sid = secrets.token_hex(16)                 # identificador novo para este jogador
                SESSOES[sid] = Jogo(nome, sexo, pais)
                return self._redirecionar(sid)

            if jogo is not None:
                if self.path == "/escolher" and pedir("opcao").isdigit():
                    jogo.escolher(int(pedir("opcao")))
                elif self.path == "/continuar":
                    jogo.continuar()
                elif self.path == "/reiniciar":
                    SESSOES.pop(self._sid(), None)          # apaga o jogo: volta ao ecrã inicial
            self._redirecionar()
        except Exception as erro:
            traceback.print_exc()
            self._responder(f"Erro no servidor: {html.escape(str(erro))}", codigo=500)


# =====================================================================
# 7. ARRANQUE
# =====================================================================
def main():
    """Verifica os ficheiros, arranca o servidor e abre o browser."""
    for ficheiro in (FICHEIRO_HTML, FICHEIRO_CSS):
        if not ficheiro.exists():
            print(f"ERRO: não encontrei o ficheiro {ficheiro.name}. "
                  "Põe o banco_ou_falencia.py, o paginas.html e o estilo.css na mesma pasta.")
            return
    servidor = ThreadingHTTPServer(("127.0.0.1", PORTA), Manipulador)
    url = f"http://127.0.0.1:{PORTA}"
    print(f"Banco ou Falência a correr em {url}  (Ctrl+C para parar)")
    webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor terminado.")


# Só arranca o jogo quando este ficheiro é executado diretamente
if __name__ == "__main__":
    main()

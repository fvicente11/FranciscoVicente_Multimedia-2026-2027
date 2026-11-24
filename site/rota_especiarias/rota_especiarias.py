# -*- coding: utf-8 -*-
"""
rota_especiarias.py - TODO o código Python do jogo "Rota das Especiarias".

A HISTÓRIA
    Estamos em 1515. O Rei D. Manuel I dá-te uma caravela e 2 anos para correres os portos
    do mundo a comprar barato e a vender caro. No fim, tens de voltar a Lisboa e mostrar ao
    Rei o resultado do teu trabalho: ele dá-te uma honra conforme a fortuna que juntaste,
    os portos que conheceste e os amigos que fizeste.

COMO JOGAR
    1. Põe estes 3 ficheiros na MESMA pasta:
         rota_especiarias.py   (este ficheiro: toda a lógica em Python)
         paginas.html          (todo o HTML)
         estilo.css            (todo o CSS)
    2. Abre a pasta no Visual Studio Code e corre este ficheiro
       (botão "Run Python File" ou, no terminal: python rota_especiarias.py).
    3. O browser abre sozinho em http://127.0.0.1:8002
       (para parar o jogo, carrega em Ctrl+C no terminal).
    Não é preciso instalar nada: só usa a biblioteca standard do Python.

COMO ESTÁ ORGANIZADO ESTE FICHEIRO
    1. Importações
    2. Constantes          (duração do jogo, tamanho do porão, preços da reparação...)
    3. Dados               (produtos, portos, mercadores, personalidades e falas, eventos no mar)
    4. Mapa e rotas        (o desenho do mundo e o cálculo dos dias de viagem)
    5. Regras do jogo      (a classe Jogo: negociar, navegar, eventos, fim do jogo)
    6. Páginas             (preenche os blocos de HTML que estão no paginas.html)
    7. Desenhos SVG        (portos, mercadores, mar, mapa e palácio)
    7b. Música de fundo    (o Python compõe e "toca" a música, sem ficheiros de som)
    8. Servidor web        (recebe os cliques do browser e responde)
    9. Arranque            (função main)

REGRA IMPORTANTE DESTE PROJETO
    Aqui NÃO há HTML nem CSS: os pedaços de HTML são blocos do paginas.html e este
    ficheiro só os preenche com dados. A única exceção são os desenhos SVG (secções 4 e 7).
    Também não há JavaScript: cada clique é um link ou um formulário enviado ao servidor.
"""

# =====================================================================
# 1. IMPORTAÇÕES (só bibliotecas que já vêm com o Python)
# =====================================================================
import array                                  # lista compacta de números (as amostras da música)
import heapq                                  # fila de prioridade (para o caminho mais curto no mar)
import html                                   # escapar texto antes de o pôr no HTML
import io                                     # 'ficheiro' em memória (para a música)
import math                                   # distâncias e ângulos
import random                                 # o acaso: preços, eventos, negociações
import re                                     # separar os blocos dentro do paginas.html
import secrets                                # gerar o identificador de sessão de cada jogador
import traceback                              # mostrar erros no terminal
import wave                                   # criar o ficheiro de som .wav (a música de fundo)
import webbrowser                             # abrir o browser sozinho
from http.cookies import SimpleCookie         # ler a cookie que identifica o jogador
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer   # o servidor web
from pathlib import Path                      # caminhos de ficheiros
from string import Template                   # preencher os campos ($campo) do HTML
from urllib.parse import parse_qs, urlparse   # ler os dados dos formulários e dos links


# =====================================================================
# 2. CONSTANTES (mexe aqui para mudar a dificuldade)
# =====================================================================
DIAS_TOTAIS = 730               # 2 anos de jogo
CAPACIDADE_PORAO = 40           # quantas caixas cabem no porão
DIAS_FIXOS_VIAGEM = 32          # dias que qualquer viagem gasta: esperar pelo vento, abastecer, sair a barra...
DIAS_POR_UNIDADE = 0.105        # ...mais estes dias por cada unidade de distância no mapa
DIAS_MINIMOS_VIAGEM = 10        # nenhuma viagem demora menos do que isto (mesmo com ventos favoráveis)
DIAS_NO_PORTO = 5               # dias gastos a atracar, descarregar e abastecer em cada chegada
DIAS_POR_NEGOCIO = 1            # cada negócio fechado gasta 1 dia
CUSTO_REPARACAO = 3             # cruzados por cada ponto de estado do navio reparado
DIAS_REPARACAO = 3              # dias no estaleiro
AMIGO = 50                      # a partir desta amizade, o mercador é teu amigo
PENALIZACAO_ATRASO = 0.25       # chegar a Lisboa depois do prazo: perdes 25%
PENALIZACAO_LONGE = 0.5         # o prazo acabar longe de Lisboa: perdes 50%
# Medalhas do Rei: valores para bronze, prata e ouro
LIMITES_MEDALHAS = {"fortuna": [2000, 4500, 7500],      # cruzados (dinheiro + carga)
                    "descoberta": [3, 6, 9],             # portos visitados (sem contar Lisboa)
                    "amizades": [2, 4, 7]}               # amigos + 2 por cada encomenda cumprida

# Calendário: o jogo começa a 1 de março de 1515 (as armadas da Índia partiam na primavera)
ANO_INICIAL, MES_INICIAL = 1515, 3
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]
DIAS_DO_MES = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


# =====================================================================
# 3. DADOS
# =====================================================================

# ---------------------- PRODUTOS ----------------------
# preço: valor "normal" de uma caixa (em cruzados). Nos portos que PRODUZEM o produto é
# muito mais barato; nos que o PROCURAM é muito mais caro.
# perecível: pode estragar-se durante a viagem (humidade, bolor, ratos...).
# margem: as mercadorias do Oriente (alta) dão muito mais lucro do que as da Europa (baixa):
# é isso que faz valer a pena a longa viagem até à Índia!
PRODUTOS = {
    "pimenta":  {"nome": "Pimenta",     "icone": "🌶️", "preco": 16, "perecivel": False, "margem": "alta"},
    "canela":   {"nome": "Canela",      "icone": "🪵", "preco": 20, "perecivel": False, "margem": "alta"},
    "cravinho": {"nome": "Cravinho",    "icone": "🌸", "preco": 26, "perecivel": False, "margem": "alta"},
    "noz":      {"nome": "Noz-moscada", "icone": "🌰", "preco": 28, "perecivel": False, "margem": "alta"},
    "gengibre": {"nome": "Gengibre",    "icone": "🌿", "preco": 12, "perecivel": True, "margem": "alta"},
    "seda":     {"nome": "Seda",        "icone": "🧵", "preco": 30, "perecivel": False, "margem": "alta"},
    "porcelana": {"nome": "Porcelana",  "icone": "🏺", "preco": 24, "perecivel": False, "margem": "alta"},
    "ouro":     {"nome": "Ouro",        "icone": "🪙", "preco": 35, "perecivel": False, "margem": "media"},
    "marfim":   {"nome": "Marfim",      "icone": "🐘", "preco": 22, "perecivel": False, "margem": "media"},
    "acucar":   {"nome": "Açúcar",      "icone": "🍬", "preco": 10, "perecivel": True, "margem": "baixa"},
    "vinho":    {"nome": "Vinho",       "icone": "🍷", "preco": 6,  "perecivel": True, "margem": "baixa"},
    "tecidos":  {"nome": "Tecidos",     "icone": "🧶", "preco": 8,  "perecivel": True, "margem": "baixa"},
}
ESPECIARIAS = ["pimenta", "canela", "cravinho", "noz", "gengibre"]
# (fator do preço onde se produz, fator onde se procura) para cada tipo de margem
FATORES_MARGEM = {"baixa": (0.65, 1.6), "media": (0.45, 1.9), "alta": (0.32, 2.2)}

# ---------------------- PORTOS ----------------------
# lon/lat: posição no mapa (longitude e latitude aproximadas, em graus)
# estilo: tipo de cenário desenhado; zona: que tipo de eventos acontecem a caminho deste porto
# secreto: só aparece no mapa depois de alguém te contar onde fica
PORTOS = {
    "lisboa": {"nome": "Lisboa", "regiao": "Reino de Portugal", "lon": -9.2, "lat": 38.7,
               "estilo": "lisboa", "zona": "europa", "produz": ["vinho", "tecidos"],
               "procura": ["pimenta", "canela", "cravinho", "seda", "porcelana", "ouro"],
               "texto": "A capital do Reino, onde chegam as naus da Índia. O Paço Real fica mesmo junto ao rio."},
    "lagos": {"nome": "Lagos", "regiao": "Algarve", "lon": -8.7, "lat": 37.0,
              "estilo": "algarve", "zona": "europa", "produz": ["vinho"],
              "procura": ["ouro", "marfim", "acucar"],
              "texto": "Porto antigo do Infante D. Henrique, de onde partiram as primeiras viagens para África."},
    "londres": {"nome": "Londres", "regiao": "Reino de Inglaterra", "lon": 0.7, "lat": 51.5,
                "estilo": "londres", "zona": "europa", "produz": ["tecidos"],
                "procura": ["vinho", "acucar", "pimenta", "canela"],
                "texto": "Cidade de nevoeiro e lã. Os ingleses adoram vinho português e açúcar."},
    "antuerpia": {"nome": "Antuérpia", "regiao": "Flandres", "lon": 4.4, "lat": 51.2,
                  "estilo": "flandres", "zona": "europa", "produz": ["tecidos"],
                  "procura": ["pimenta", "cravinho", "noz", "acucar", "canela"],
                  "texto": "O grande mercado da Europa: aqui as especiarias valem uma fortuna."},
    "veneza": {"nome": "Veneza", "regiao": "República de Veneza", "lon": 12.3, "lat": 45.4,
               "estilo": "veneza", "zona": "europa", "produz": ["tecidos"],
               "procura": ["pimenta", "gengibre", "seda", "noz"],
               "texto": "Cidade de canais e de mercadores ricos, rival dos portugueses no negócio das especiarias."},
    "atenas": {"nome": "Atenas", "regiao": "Grécia", "lon": 23.6, "lat": 37.9,
               "estilo": "grecia", "zona": "europa", "produz": ["vinho"],
               "procura": ["tecidos", "acucar", "pimenta"],
               "texto": "Cidade antiga, com o Pártenon lá no alto da colina."},
    "funchal": {"nome": "Funchal", "regiao": "Ilha da Madeira", "lon": -16.9, "lat": 32.7,
                "estilo": "madeira", "zona": "atlantico", "produz": ["acucar", "vinho"],
                "procura": ["tecidos", "ouro"],
                "texto": "Ilha verde de montanhas altas: o açúcar da Madeira é famoso em toda a Europa."},
    "caboverde": {"nome": "Cabo Verde", "regiao": "Ilha de Santiago", "lon": -23.5, "lat": 15.0,
                  "estilo": "caboverde", "zona": "atlantico", "produz": ["tecidos", "acucar"],
                  "procura": ["vinho", "porcelana"],
                  "texto": "Paragem obrigatória das armadas: água fresca, panos de algodão e muito sol."},
    "mina": {"nome": "São Jorge da Mina", "regiao": "Costa do Ouro", "lon": -1.4, "lat": 5.1,
             "estilo": "mina", "zona": "africa", "produz": ["ouro", "marfim"],
             "procura": ["tecidos", "vinho"],
             "texto": "O castelo branco dos portugueses guarda o comércio do ouro africano."},
    "congo": {"nome": "Congo", "regiao": "Reino do Congo", "lon": 12.3, "lat": -6.1,
              "estilo": "congo", "zona": "africa", "produz": ["marfim"],
              "procura": ["tecidos", "vinho", "porcelana"],
              "texto": "Na foz do grande rio, o reino do Congo é amigo de Portugal."},
    "sofala": {"nome": "Sofala", "regiao": "Costa Oriental de África", "lon": 36.2, "lat": -20.2,
               "estilo": "suaili", "zona": "africa", "produz": ["ouro", "marfim"],
               "procura": ["tecidos", "porcelana"],
               "texto": "Daqui sai o ouro do Monomotapa, trazido do interior por caravanas."},
    "mocambique": {"nome": "Moçambique", "regiao": "Ilha de Moçambique", "lon": 40.8, "lat": -15.0,
                   "estilo": "suaili", "zona": "africa", "produz": ["marfim"],
                   "procura": ["tecidos", "vinho", "pimenta"],
                   "texto": "Pequena ilha de pedra e coral onde as armadas esperam pelas monções."},
    "melinde": {"nome": "Melinde", "regiao": "Costa Suaíli", "lon": 40.3, "lat": -3.2,
                "estilo": "melinde", "zona": "africa", "produz": ["marfim", "gengibre"],
                "procura": ["tecidos", "porcelana", "vinho"],
                "texto": "Foi aqui que Vasco da Gama encontrou o piloto que o levou à Índia. Ainda lá está o padrão."},
    "ormuz": {"nome": "Ormuz", "regiao": "Golfo Pérsico", "lon": 56.5, "lat": 27.1,
              "estilo": "ormuz", "zona": "indico", "produz": ["seda"],
              "procura": ["pimenta", "cravinho", "ouro", "acucar", "gengibre"],
              "texto": "Ilha-fortaleza à entrada do Golfo, cruzamento de caravanas da Pérsia e da Arábia."},
    "calecute": {"nome": "Calecute", "regiao": "Costa do Malabar", "lon": 75.8, "lat": 11.3,
                 "estilo": "calecute", "zona": "indico", "produz": ["pimenta", "gengibre"],
                 "procura": ["ouro", "tecidos", "marfim"],
                 "texto": "A cidade da pimenta, onde Vasco da Gama chegou em 1498."},
    "goa": {"nome": "Goa", "regiao": "Estado da Índia", "lon": 73.8, "lat": 15.5,
            "estilo": "goa", "zona": "indico", "produz": ["pimenta", "canela", "gengibre"],
            "procura": ["ouro", "vinho", "marfim"],
            "texto": "Conquistada por Afonso de Albuquerque em 1510, é a capital portuguesa no Oriente."},
    "malaca": {"nome": "Malaca", "regiao": "Península Malaia", "lon": 102.3, "lat": 2.2,
               "estilo": "malaca", "zona": "asia", "produz": ["cravinho", "noz", "porcelana", "seda"],
               "procura": ["tecidos", "pimenta", "ouro"],
               "texto": "Porto de juncos chineses e mercadores de todo o Oriente. Portuguesa desde 1511."},
    "ternate": {"nome": "Ilhas das Especiarias", "regiao": "Ternate (Molucas)", "lon": 127.4, "lat": 0.8,
                "estilo": "ternate", "zona": "asia", "produz": ["cravinho", "noz"],
                "procura": ["tecidos", "porcelana", "marfim"], "secreto": True,
                "texto": "As ilhas de onde vem o cravinho: aqui, as especiarias são baratíssimas!"},
    "enseada": {"nome": "Enseada dos Corsários", "regiao": "Costa de Madagáscar", "lon": 50.4, "lat": -16.9,
                "estilo": "piratas", "zona": "africa", "produz": ["seda", "porcelana", "ouro"],
                "procura": ["vinho", "tecidos", "acucar"], "secreto": True,
                "texto": "Um esconderijo de piratas. Vende-se de tudo... e ninguém pergunta de onde veio."},
}

# Rumores: o que os amigos te contam sobre os portos secretos
RUMORES = {
    "ternate": "Dizem que a leste de Malaca há umas ilhas onde o cravinho cresce nas árvores como mato: as Ilhas das Especiarias. Marquei-tas no teu mapa.",
    "enseada": "Na costa de Madagáscar há uma enseada escondida onde os piratas vendem o que roubam, a preço de nada. Marquei-ta no teu mapa.",
}

# ---------------------- PERSONALIDADES ----------------------
# compra / venda: multiplicam o preço do porto quando o mercador te compra ou vende.
# aceita: hipótese de aceitar quando pedes +15% (nível 1) ou +40% (nível 2).
# contra: hipótese de fazer uma contraproposta em vez de recusar.
# paciencia: quantas recusas aguenta antes de te mandar embora.
# deteta: hipótese de descobrir mercadoria falsa que lhe tentes vender.
PERSONALIDADES = {
    "honesto":     {"nome": "Honesto",     "compra": 1.0,  "venda": 1.0,  "aceita": [1, .55, .15], "contra": .55, "paciencia": 3, "deteta": .9, "humor": "neutro"},
    "generoso":    {"nome": "Generoso",    "compra": 1.1,  "venda": .9,   "aceita": [1, .75, .35], "contra": .5,  "paciencia": 4, "deteta": .8, "humor": "contente"},
    "vigarista":   {"nome": "Vigarista",   "compra": .85,  "venda": 1.15, "aceita": [1, .45, .12], "contra": .6,  "paciencia": 3, "deteta": 0,  "humor": "contente"},
    "teimoso":     {"nome": "Teimoso",     "compra": .95,  "venda": 1.05, "aceita": [1, .2, .04],  "contra": .85, "paciencia": 2, "deteta": .9, "humor": "neutro"},
    "desconfiado": {"nome": "Desconfiado", "compra": .9,   "venda": 1.1,  "aceita": [1, .4, .08],  "contra": .5,  "paciencia": 3, "deteta": 1,  "humor": "desconfiado"},
    "falabarato":  {"nome": "Fala-barato", "compra": 1.0,  "venda": 1.0,  "aceita": [1, .6, .2],   "contra": .55, "paciencia": 5, "deteta": .5, "humor": "contente"},
}
HUMORES = ["zangado", "desconfiado", "neutro", "contente"]      # do pior para o melhor
EFEITO_HUMOR = {"contente": .1, "neutro": 0, "desconfiado": -.1, "zangado": -.25}
NIVEIS_PRECO = [1.0, 1.15, 1.40]       # 0 = o preço dele, 1 = regatear um pouco, 2 = regatear muito

# Falas de cada personalidade. {nome}, {produto}, {preco} e {qtd} são trocados pelo valor certo.
FALAS = {
    "honesto": {
        "ola": ["Bom dia, senhor mercador! Aqui o preço é justo e a balança não mente.",
                "Sê bem-vindo. Diz-me o que procuras, que eu digo-te o que tenho."],
        "ola_amigo": ["{nome}! Que alegria ver-te outra vez. Para ti há sempre preço de amigo."],
        "aceita": ["Negócio fechado. Um aperto de mão vale mais do que um papel.", "Parece-me justo. Está combinado!"],
        "contra": ["Isso é um pouco demais. Que tal {preco} cruzados por caixa?",
                   "Não posso ir tão longe... Faço-te {preco} cruzados por caixa."],
        "recusa": ["Lamento, mas assim perco dinheiro. Não pode ser.", "Não, não. Isso não é justo para mim."],
        "irritado": ["Já chega de regatear. Volta noutro dia, quando estiveres mais razoável."],
        "nao_interessa": ["Isso não me interessa, amigo. Não tenho a quem o vender."],
        "falso": ["Espera... isto não é {produto} verdadeira, é casca de árvore! Alguém te enganou. Não compro isto."],
        "examinar": ["Podes ver à vontade. Mercadoria de primeira!"],
        "adeus": ["Vai com Deus e bons ventos!"],
        "encomenda": ["Se me trouxeres {qtd} caixas de {produto}, pago-te o dobro do preço. Palavra de honra."],
        "entrega": ["Cumpriste a palavra! Aqui tens o dobro, como prometi."],
        "dica": ["Um conselho de amigo:"],
    },
    "generoso": {
        "ola": ["Entra, entra! Queres um copo de água fresca? Depois falamos de negócios.",
                "Ah, um rosto novo! Hoje estou de bom humor, aproveita."],
        "ola_amigo": ["O meu mercador preferido! Senta-te, senta-te, {nome}."],
        "aceita": ["Combinado! E leva também um sorriso, que é de graça.", "Fechado! Gosto de fazer negócio contigo."],
        "contra": ["Estás a puxar muito... mas gosto de ti. {preco} cruzados por caixa, que dizes?"],
        "recusa": ["Ai, isso já é demais até para mim!", "Nem a minha bondade chega a tanto!"],
        "irritado": ["Até a minha paciência tem fim! Vai dar uma volta e volta mais calmo."],
        "nao_interessa": ["Que pena, não preciso disso... mas obrigado por perguntares!"],
        "falso": ["Oh não... isto não é {produto} verdadeira. Foste enganado, pobre amigo! Deita isso fora."],
        "examinar": ["Claro, vê tudo! Não tenho nada a esconder."],
        "adeus": ["Volta sempre! E traz histórias das tuas viagens!"],
        "encomenda": ["Fazes-me um favor? Traz-me {qtd} caixas de {produto} e pago o dobro!"],
        "entrega": ["Lembraste-te de mim! Toma, o dobro, e um abraço!"],
        "dica": ["Olha, vou contar-te uma coisa:"],
    },
    "vigarista": {
        "ola": ["Psst! Amigo! Tenho mercadoria fina, fresquinha, quase de graça. Não faças perguntas.",
                "Ah, um cliente com cara de esperto! Para ti, preço especial... só hoje."],
        "ola_amigo": ["O meu sócio preferido, {nome}! Confias em mim, não confias?"],
        "aceita": ["Hehe... negócio fechado! Não te vais arrepender. Acho eu.", "Fechado! Não contes a ninguém o preço que te fiz."],
        "contra": ["Estás a matar-me! Mas vá, {preco} cruzados por caixa e nem mais uma palavra."],
        "recusa": ["Nem pensar! Tenho filhos para alimentar... e uns credores também.", "Isso é roubo! E eu percebo de roubo."],
        "irritado": ["Estás a fazer-me perder tempo! Há outros papalvos... digo, clientes, à espera."],
        "nao_interessa": ["Isso? Não. Só compro o que dá lucro rápido."],
        "falso": ["Hmm... não faço perguntas."],
        "examinar": ["Examinar? Ofendes-me! ...Mas pronto, vê lá."],
        "examinar_falso": ["Ah... isso? Deve ter vindo misturado por engano. Acontece a qualquer um!"],
        "pista": ["É {produto} da melhor! Não cheires muito de perto, que estraga o aroma.",
                  "Preço assim só porque gosto da tua cara. Não é por mais nada, juro."],
        "adeus": ["Até à próxima! E se alguém perguntar, não me conheces."],
        "encomenda": ["Traz-me {qtd} caixas de {produto} e pago o dobro. Juro pela minha mãe! Bem, por uma das minhas tias."],
        "entrega": ["Trouxeste mesmo? Pronto, pronto, aqui tens o dobro. Até um vigarista tem palavra."],
        "dica": ["Vou contar-te um segredo, e este até é verdade:"],
    },
    "teimoso": {
        "ola": ["Hmpf. O preço é o que está escrito e não se discute.", "Se vens regatear, podes ir-te embora já."],
        "ola_amigo": ["Ah, és tu, {nome}. Contigo ainda converso."],
        "aceita": ["Pois. Assim está bem.", "Hmpf. Combinado."],
        "contra": ["Não. {preco} cruzados por caixa. É a minha última palavra. Talvez."],
        "recusa": ["Não.", "Já disse que não. Não é não."],
        "irritado": ["Chega! Fora da minha banca!"],
        "nao_interessa": ["Não compro isso. Nunca comprei e não vou começar hoje."],
        "falso": ["Isto é {produto} falsa. Vejo logo. Não compro lixo."],
        "examinar": ["Vê o que quiseres. A minha mercadoria é boa, ponto final."],
        "adeus": ["Hmpf."],
        "encomenda": ["Traz {qtd} caixas de {produto}. Pago o dobro. Não demores."],
        "entrega": ["Hmpf. Cumpriste. Aqui tens. ...Obrigado."],
        "dica": ["Vou dizer isto só uma vez:"],
    },
    "desconfiado": {
        "ola": ["Hmm... quem és tu? Mostra-me primeiro o dinheiro.", "Não te conheço. Mantém as mãos onde eu as possa ver."],
        "ola_amigo": ["Ah, és tu, {nome}. Contigo já sei com que linhas me coso."],
        "aceita": ["Está bem... mas vou contar as caixas duas vezes.", "Combinado. Mas fico de olho em ti."],
        "contra": ["Isso cheira-me a esperteza. Faço {preco} cruzados por caixa, e já é muito."],
        "recusa": ["Achas que nasci ontem? Não!", "Nem pensar. Conheço bem esse truque."],
        "irritado": ["Eu sabia que eras um aldrabão! Sai daqui!"],
        "nao_interessa": ["E para que quero eu isso? Não, não."],
        "falso": ["Ahá! Isto é {produto} falsa! Vês? Não se pode confiar em ninguém!"],
        "examinar": ["Fazes bem em verificar! Eu também verifico tudo."],
        "adeus": ["Vai... e fecha a porta ao sair."],
        "encomenda": ["Se fores de confiança, traz-me {qtd} caixas de {produto}. Pago o dobro."],
        "entrega": ["Cumpriste! Talvez afinal haja gente honesta neste mundo."],
        "dica": ["Não costumo dizer isto a ninguém, mas:"],
    },
    "falabarato": {
        "ola": ["Olá, olá! Sabias que o meu primo tem um camelo que canta? Bem, compras alguma coisa?",
                "Bem-vindo! Senta-te, que tenho tanta coisa para te contar... ah, e também vendo coisas."],
        "ola_amigo": ["{nome}! Contei a toda a gente que eras meu amigo!"],
        "aceita": ["Fechado! Já te contei da vez em que vendi um elefante? Fica para a próxima.",
                   "Combinado! Vou contar a toda a gente que fiz negócio contigo."],
        "contra": ["Hmm, hmm... que tal {preco} cruzados por caixa? A minha avó dizia: quem regateia, compra."],
        "recusa": ["Ai não, não, não! Isso nem a minha avó aceitava, e ela aceitava tudo."],
        "irritado": ["Olha, até eu fiquei sem palavras. E isso nunca me acontece! Adeus!"],
        "nao_interessa": ["Isso? Não, não preciso. Mas sabias que...? Bem, esquece."],
        "falso": ["Espera lá... isto não é {produto}! Que vergonha! Quem te vendeu isto?"],
        "examinar": ["Vê, vê! Enquanto vês, conto-te a história desta caixa..."],
        "adeus": ["Já vais? Mas eu ainda nem te contei o melhor! Boa viagem!"],
        "encomenda": ["Ouve, se me trouxeres {qtd} caixas de {produto}, pago o dobro! E conto a toda a gente que és o maior."],
        "entrega": ["Trouxeste! Vou contar isto a toda a gente! Aqui tens o dobro!"],
        "dica": ["Ouvi uma coisa no mercado:"],
    },
}


# ---------------------- MERCADORES ----------------------
def mercador(id, porto, nome, personalidade, aspeto, roupa, quer, vende, profissao, terra, idade, historia,
             acessorios=(), mulher=False, barba=False, segredo=None):
    """Cria o dicionário de um mercador (só para a lista de baixo ficar mais curta).
    aspeto: região da roupa e do rosto (europeu, africano, arabe, indiano, malaio, chines, pirata).
    acessorios: objetos desenhados no mercador (oculos, balanca, bolsa, colar, livro, cajado, pena,
    brinco, cicatriz, papagaio, macaco, gato)."""
    return {"id": id, "porto": porto, "nome": nome, "personalidade": personalidade, "aspeto": aspeto,
            "roupa": roupa, "quer": quer, "vende": vende, "profissao": profissao, "terra": terra, "idade": idade,
            "historia": historia, "acessorios": list(acessorios), "mulher": mulher, "barba": barba, "segredo": segredo}


M = mercador
MERCADORES = [
    # ---------------- LISBOA
    M("lis1", "lisboa", "Mestre Gonçalo", "honesto", "europeu", "#3d5a80", ["pimenta", "canela", "seda"], ["vinho", "tecidos"],
      "Mercador da Rua Nova", "Alfama", 52, "Negoceia no mesmo sítio há trinta anos e nunca enganou ninguém. Diz que a balança dele é tão certa que até o Rei a usa.",
      ["balanca", "oculos"], barba=True),
    M("lis2", "lisboa", "Dona Brites", "generoso", "europeu", "#9c3d54", ["cravinho", "porcelana", "ouro"], ["vinho", "acucar"],
      "Viúva de um piloto", "Belém", 47, "Desde que o marido, piloto das naus da Índia, morreu, gere o negócio da família sozinha. Trata os marinheiros como filhos.",
      ["colar", "bolsa"], mulher=True),
    M("lis3", "lisboa", "Zé Lampreia", "vigarista", "europeu", "#5b7553", ["pimenta", "ouro"], ["tecidos", "canela"],
      "Vendedor ambulante", "Mouraria", 29, "Já vendeu a mesma vaca a três pessoas diferentes. Jura que agora mudou de vida.",
      ["bolsa", "cicatriz"]),
    M("lis4", "lisboa", "Frei Bartolomeu", "desconfiado", "europeu", "#6b4f3a", ["canela", "porcelana"], ["vinho"],
      "Despenseiro do convento", "Alcobaça", 60, "Compra especiarias para os doces do convento. Desconfia de toda a gente, menos de Deus e do seu livro de contas.",
      ["livro", "oculos"]),
    # ---------------- LAGOS
    M("lag1", "lagos", "Velho Afonso", "teimoso", "europeu", "#6b4f3a", ["ouro", "marfim"], ["vinho"],
      "Antigo marinheiro", "Lagos", 71, "Navegou com o Infante D. Henrique quando era rapaz e conta essa história a quem quiser ouvir (e a quem não quiser).",
      ["cajado"], barba=True),
    M("lag2", "lagos", "Catarina Lopes", "falabarato", "europeu", "#c06c2b", ["acucar", "marfim"], ["vinho", "tecidos"],
      "Taberneira do cais", "Lagos", 38, "Sabe todas as novidades do porto antes de toda a gente. Ninguém sabe como.",
      ["colar"], mulher=True),
    M("lag3", "lagos", "Rodrigo Anes", "honesto", "europeu", "#2f4858", ["ouro", "acucar"], ["vinho"],
      "Armador de pesca", "Portimão", 44, "Tem três barcos e onze filhos. Diz que os barcos dão menos trabalho.",
      ["bolsa"], barba=True),
    M("lag4", "lagos", "Mestre Simão", "vigarista", "europeu", "#7a6c5d", ["marfim"], ["vinho", "gengibre"],
      "Boticário", "Silves", 55, "Vende remédios para tudo: dor de dentes, mau-olhado, enjoo de mar... Todos feitos com a mesma água.",
      ["oculos", "pena"], barba=True),
    # ---------------- LONDRES
    M("lon1", "londres", "Master Thomas", "desconfiado", "europeu", "#4a4e69", ["vinho", "pimenta"], ["tecidos"],
      "Mercador de lã", "Londres", 49, "Conta as moedas três vezes e morde cada uma para ver se é verdadeira.",
      ["bolsa", "livro"], barba=True),
    M("lon2", "londres", "Old Margaret", "honesto", "europeu", "#7a6c5d", ["acucar", "canela"], ["tecidos"],
      "Tecedeira", "Southwark", 63, "Tece os panos mais quentes de Inglaterra. Diz que o segredo é falar com o tear.",
      ["oculos"], mulher=True),
    M("lon3", "londres", "Sir William", "generoso", "europeu", "#7b2d26", ["vinho", "acucar"], ["tecidos"],
      "Cavaleiro arruinado", "Kent", 41, "Perdeu a fortuna nas cartas e agora vende tecidos. Continua a vestir-se como se fosse jantar com o Rei.",
      ["pena", "colar"], barba=True),
    M("lon4", "londres", "Ned Pequeno", "falabarato", "europeu", "#5d8a66", ["pimenta", "canela"], ["tecidos"],
      "Rapaz de recados", "Londres", 15, "Tem quinze anos e já trabalhou para metade dos mercadores do Tamisa. Sonha ser marinheiro.",
      ["bolsa"]),
    # ---------------- ANTUÉRPIA
    M("ant1", "antuerpia", "Jan van der Berg", "teimoso", "europeu", "#2f4858", ["pimenta", "noz", "acucar"], ["tecidos"],
      "Agente da Bolsa", "Antuérpia", 50, "Diz que sabe o preço da pimenta melhor do que o nome dos filhos.",
      ["livro", "oculos"], barba=True),
    M("ant2", "antuerpia", "Pieter Cools", "generoso", "europeu", "#a4632e", ["cravinho", "canela", "pimenta"], ["tecidos", "vinho"],
      "Cervejeiro e mercador", "Gante", 36, "Oferece cerveja a todos os clientes. Os negócios dele demoram muito, mas acabam sempre bem.",
      ["bolsa"]),
    M("ant3", "antuerpia", "Margarida Gomes", "honesto", "europeu", "#355c7d", ["acucar", "noz"], ["tecidos"],
      "Feitora de Portugal", "Lisboa", 42, "Trabalha na Feitoria de Portugal em Antuérpia e fala cinco línguas, três delas a gritar.",
      ["livro", "colar"], mulher=True),
    M("ant4", "antuerpia", "Hans Fugger", "desconfiado", "europeu", "#3f3f4a", ["cravinho", "pimenta"], ["tecidos"],
      "Banqueiro alemão", "Augsburgo", 58, "Empresta dinheiro a reis e imperadores. A ti, só se deixares o navio como garantia.",
      ["oculos", "bolsa"], barba=True),
    # ---------------- VENEZA
    M("ven1", "veneza", "Messer Lorenzo", "vigarista", "europeu", "#7b2d26", ["pimenta", "seda"], ["tecidos", "gengibre"],
      "Mercador do Rialto", "Veneza", 46, "Os venezianos detestam que os portugueses tenham descoberto o caminho para a Índia. Ele sorri-te... com os dentes todos.",
      ["colar", "bolsa"], barba=True),
    M("ven2", "veneza", "Signora Bianca", "desconfiado", "europeu", "#355c7d", ["noz", "gengibre"], ["tecidos"],
      "Vidreira de Murano", "Murano", 39, "Faz copos tão finos que partem só de olhar para eles. Trata os clientes da mesma maneira.",
      ["oculos"], mulher=True),
    M("ven3", "veneza", "Marco Contarini", "generoso", "europeu", "#2a6f97", ["seda", "pimenta"], ["tecidos"],
      "Gondoleiro", "Veneza", 31, "Leva passageiros de gôndola durante o dia e mercadoria duvidosa durante a noite. Canta nos dois casos.",
      ["pena"]),
    M("ven4", "veneza", "Dottore Salvatore", "honesto", "europeu", "#4a4e69", ["gengibre", "noz"], ["tecidos"],
      "Médico e boticário", "Pádua", 57, "Receita gengibre para tudo. Diz que é por razões médicas, mas é porque adora o sabor.",
      ["oculos", "livro"], barba=True),
    # ---------------- ATENAS
    M("ate1", "atenas", "Kyrios Nikolaos", "falabarato", "europeu", "#3a6ea5", ["tecidos", "pimenta"], ["vinho"],
      "Vinhateiro", "Plaka", 54, "Diz que o vinho dele já era servido aos deuses antigos. Os deuses nunca se queixaram.",
      ["bolsa"], barba=True),
    M("ate2", "atenas", "Eleni", "honesto", "europeu", "#5d8a66", ["acucar", "tecidos"], ["vinho"],
      "Apicultora", "Monte Himeto", 33, "Tem mais de mil abelhas e conhece-as todas pelo nome. Bem, quase todas.",
      ["colar"], mulher=True),
    M("ate3", "atenas", "Yannis", "teimoso", "europeu", "#355c7d", ["tecidos"], ["vinho"],
      "Pescador de polvos", "Pireu", 61, "Discute com os polvos antes de os apanhar. Diz que são mais teimosos do que ele.",
      ["cajado"], barba=True),
    M("ate4", "atenas", "Hassan Bey", "desconfiado", "arabe", "#9a031e", ["pimenta", "acucar"], ["vinho", "seda"],
      "Cobrador da alfândega", "Istambul", 45, "Cobra impostos sobre tudo o que entra no porto. Também cobraria sobre o ar, se pudesse.",
      ["livro", "oculos"], barba=True),
    # ---------------- FUNCHAL
    M("fun1", "funchal", "João Esmeraldo", "honesto", "europeu", "#8a5a44", ["tecidos", "ouro"], ["acucar", "vinho"],
      "Senhor de engenho", "Funchal", 48, "Dono do maior engenho de açúcar da ilha. Diz que conheceu um tal Cristóvão Colombo, que viveu na Madeira.",
      ["bolsa"], barba=True),
    M("fun2", "funchal", "Inês do Monte", "generoso", "europeu", "#3f7d5a", ["tecidos"], ["acucar"],
      "Bordadeira", "Monte", 27, "Os bordados dela vão para as damas da corte. Dá sempre um lencinho bordado a quem lhe compra açúcar.",
      ["colar"], mulher=True),
    M("fun3", "funchal", "Tristão Vaz", "teimoso", "europeu", "#6b4f3a", ["ouro"], ["vinho"],
      "Produtor de vinho", "Câmara de Lobos", 66, "Garante que o vinho dele fica melhor depois de uma viagem de navio. E não é que tem razão?",
      ["cajado"], barba=True),
    M("fun4", "funchal", "Maria da Levada", "falabarato", "europeu", "#2f7a3d", ["tecidos", "ouro"], ["acucar"],
      "Guarda das levadas", "Ribeira Brava", 35, "Cuida dos canais de água que regam a cana-de-açúcar. Conhece todas as conversas de todas as fajãs.",
      ["colar"], mulher=True),
    # ---------------- CABO VERDE
    M("cv1", "caboverde", "Diogo Afonso", "desconfiado", "europeu", "#9a6b3b", ["vinho", "porcelana"], ["tecidos"],
      "Almoxarife do Rei", "Ribeira Grande", 40, "Escreve no livro tudo o que entra e sai da ilha. Até as gaivotas.",
      ["livro"]),
    M("cv2", "caboverde", "Nha Rosa", "falabarato", "africano", "#d1495b", ["vinho"], ["tecidos", "acucar"],
      "Tecedeira de panos", "Santiago", 45, "Os panos de algodão dela são tão bonitos que se usam como dinheiro em toda a costa.",
      ["colar"], mulher=True),
    M("cv3", "caboverde", "Mestre Pêro", "generoso", "europeu", "#7a8a5a", ["porcelana"], ["acucar"],
      "Fornecedor das armadas", "Ribeira Grande", 50, "Dá água e comida a todas as naus que passam. Conhece os capitães todos pelo nome.",
      ["bolsa", "livro"], barba=True),
    M("cv4", "caboverde", "Djibril", "honesto", "africano", "#e9c46a", ["vinho", "porcelana"], ["tecidos"],
      "Mercador da Guiné", "Rio Grande", 38, "Atravessa o mar entre a costa e as ilhas numa canoa enorme. Nunca se perdeu, nem de noite.",
      ["colar"], barba=True),
    # ---------------- SÃO JORGE DA MINA
    M("min1", "mina", "Nana Kwame", "teimoso", "africano", "#d4a017", ["tecidos", "vinho"], ["ouro"],
      "Chefe de aldeia", "Elmina", 56, "Troca ouro por panos, mas só com quem lhe olha nos olhos. Detesta pressas.",
      ["colar", "cajado"], barba=True),
    M("min2", "mina", "Feitor Rui", "vigarista", "europeu", "#6d597a", ["tecidos"], ["ouro", "marfim"],
      "Feitor do castelo", "Viseu", 37, "Devia guardar o ouro do Rei. Às vezes 'esquece-se' de contar umas pepitas.",
      ["livro", "bolsa"]),
    M("min3", "mina", "Ama Serwaa", "generoso", "africano", "#f4a261", ["vinho", "tecidos"], ["ouro"],
      "Ourives", "Comenda", 41, "Faz joias de ouro tão finas que parecem renda. Dá sempre um anelzinho às crianças.",
      ["colar", "brinco"], mulher=True),
    M("min4", "mina", "Kofi", "desconfiado", "africano", "#2a9d8f", ["tecidos"], ["marfim"],
      "Caçador e guia", "Floresta do interior", 30, "Conhece os caminhos da floresta como ninguém e desconfia de tudo o que vem do mar.",
      ["cajado"]),
    # ---------------- CONGO
    M("con1", "congo", "Mani Nsaku", "generoso", "africano", "#c1440e", ["tecidos", "porcelana"], ["marfim"],
      "Fidalgo do Manicongo", "Mbanza Congo", 45, "Foi a Lisboa como embaixador e voltou a falar português melhor do que muitos portugueses.",
      ["colar"]),
    M("con2", "congo", "Tomé Vaz", "honesto", "europeu", "#4f6d7a", ["vinho", "tecidos"], ["marfim"],
      "Missionário e intérprete", "Braga", 50, "Veio ensinar a ler e acabou a aprender três línguas novas. Ajuda nos negócios para pagar a escola.",
      ["livro", "oculos"], barba=True),
    M("con3", "congo", "Nzinga", "falabarato", "africano", "#8338ec", ["porcelana", "vinho"], ["marfim"],
      "Mercadora do rio", "Mpinda", 34, "Sobe e desce o grande rio na sua canoa a vender de tudo. Canta tão alto que se ouve na outra margem.",
      ["colar", "brinco"], mulher=True),
    M("con4", "congo", "Nkuwu", "teimoso", "africano", "#6b4423", ["tecidos"], ["marfim"],
      "Escultor de marfim", "Soyo", 59, "Esculpe marfim com uma paciência infinita. Para regatear, a paciência dele é bem mais curta.",
      ["cajado"], barba=True),
    # ---------------- SOFALA
    M("sof1", "sofala", "Xeque Yusuf", "desconfiado", "arabe", "#ffffff", ["tecidos", "porcelana"], ["ouro"],
      "Xeque de Sofala", "Sofala", 63, "Governa o comércio do ouro há muitos anos e já viu chegar e partir muitos estrangeiros.",
      ["livro"], barba=True),
    M("sof2", "sofala", "Rashid", "vigarista", "arabe", "#2a9d8f", ["porcelana"], ["ouro", "marfim"],
      "Mercador de caravanas", "Quíloa", 33, "Diz que o ouro dele vem das minas do Rei Salomão. Na verdade, vem de um sítio bem menos lendário.",
      ["bolsa", "brinco"]),
    M("sof3", "sofala", "Chipo", "honesto", "africano", "#e76f51", ["tecidos"], ["ouro"],
      "Mineira", "Monomotapa", 36, "Caminhou vinte dias com o seu ouro até à costa. Não está com disposição para conversas compridas.",
      ["colar"], mulher=True),
    M("sof4", "sofala", "Abdullah", "generoso", "arabe", "#e9c46a", ["porcelana", "tecidos"], ["marfim"],
      "Construtor de barcos", "Sofala", 52, "Constrói barcos sem um único prego: as tábuas são cosidas com cordas de coco.",
      ["cajado"], barba=True),
    # ---------------- MOÇAMBIQUE
    M("moc1", "mocambique", "Amina", "honesto", "africano", "#e76f51", ["tecidos", "pimenta"], ["marfim"],
      "Vendedora de mantimentos", "Ilha de Moçambique", 40, "Vende água, galinhas e fruta às armadas. Os marinheiros chamam-lhe 'a mãe da ilha'.",
      ["colar"], mulher=True),
    M("moc2", "mocambique", "Capitão Brás", "teimoso", "europeu", "#264653", ["vinho", "tecidos"], ["marfim"],
      "Capitão da fortaleza", "Lamego", 55, "Está à espera da monção há quatro meses e já não tem paciência para nada.",
      ["cicatriz"], barba=True),
    M("moc3", "mocambique", "Said", "generoso", "arabe", "#2a9d8f", ["pimenta", "vinho"], ["marfim"],
      "Piloto do Índico", "Zanzibar", 47, "Conhece as monções como a palma da mão. Por um bom preço, ensina-te o caminho mais rápido para a Índia.",
      ["livro"]),
    M("moc4", "mocambique", "Zé Macua", "vigarista", "africano", "#9b2226", ["tecidos"], ["marfim", "gengibre"],
      "Barqueiro", "Mossuril", 28, "Leva pessoas e caixas entre a ilha e o continente. As caixas às vezes chegam mais leves.",
      ["bolsa", "macaco"]),
    # ---------------- MELINDE
    M("mel1", "melinde", "Ali bin Said", "generoso", "arabe", "#e9c46a", ["porcelana", "tecidos"], ["marfim", "gengibre"],
      "Conselheiro do Rei", "Melinde", 58, "A família dele recebeu Vasco da Gama em 1498. Ainda guarda a taça onde o capitão bebeu.",
      ["colar", "livro"], barba=True),
    M("mel2", "melinde", "Fátima", "falabarato", "arabe", "#8338ec", ["vinho", "tecidos"], ["gengibre"],
      "Vendedora de especiarias", "Melinde", 44, "Fala com toda a gente, de pescadores a piratas. É por isso que sabe segredos que mais ninguém sabe.",
      ["colar", "brinco"], mulher=True, segredo="enseada"),
    M("mel3", "melinde", "Ibrahim", "teimoso", "arabe", "#1d3557", ["porcelana"], ["marfim"],
      "Mercador de marfim", "Mombaça", 49, "Os de Mombaça e os de Melinde não se dão nada bem. Ele só cá está porque os preços são melhores.",
      ["bolsa"], barba=True),
    M("mel4", "melinde", "Mwana Kheri", "honesto", "africano", "#2a9d8f", ["tecidos", "vinho"], ["gengibre"],
      "Agricultora", "Malindi", 37, "Cultiva gengibre, coco e manga. Diz que as plantas crescem melhor se lhes cantarmos.",
      ["colar"], mulher=True),
    # ---------------- ORMUZ
    M("orm1", "ormuz", "Khwaja Ata", "teimoso", "arabe", "#1d3557", ["pimenta", "ouro", "gengibre"], ["seda"],
      "Vizir de Ormuz", "Ormuz", 60, "Governa o comércio da ilha e não gosta que lhe digam que não. Muito menos que lhe peçam desconto.",
      ["livro", "colar"], barba=True),
    M("orm2", "ormuz", "Dário", "vigarista", "arabe", "#b5179e", ["cravinho", "acucar"], ["seda"],
      "Mercador de tapetes", "Xiraz", 35, "Jura que os tapetes dele voam. Ainda ninguém o viu provar.",
      ["bolsa", "brinco"]),
    M("orm3", "ormuz", "Shirin", "generoso", "arabe", "#e85d04", ["acucar", "gengibre"], ["seda"],
      "Tecedeira de seda", "Isfahan", 39, "As sedas dela têm desenhos de jardins e pássaros. Demora um ano a tecer cada uma.",
      ["colar"], mulher=True),
    M("orm4", "ormuz", "Abu Bakr", "desconfiado", "arabe", "#6d597a", ["ouro", "pimenta"], ["seda"],
      "Astrónomo e cartógrafo", "Baçorá", 66, "Desenha mapas das estrelas e dos mares. Diz que os mapas portugueses estão cheios de erros.",
      ["oculos", "livro"], barba=True),
    # ---------------- CALECUTE
    M("cal1", "calecute", "Chetty Ramana", "desconfiado", "indiano", "#f4a261", ["ouro", "marfim"], ["pimenta", "gengibre"],
      "Mercador de pimenta", "Calecute", 50, "Viu o que aconteceu entre os portugueses e o Samorim. Por isso, conta as moedas duas vezes.",
      ["livro", "bolsa"]),
    M("cal2", "calecute", "Kunjali", "falabarato", "indiano", "#2a9d8f", ["tecidos", "ouro"], ["pimenta"],
      "Capitão do Malabar", "Calecute", 40, "Já lutou contra os portugueses e agora negoceia com eles. Diz que o mar é grande que chegue para todos.",
      ["cicatriz"], barba=True),
    M("cal3", "calecute", "Devi", "honesto", "indiano", "#d00000", ["ouro", "tecidos"], ["gengibre"],
      "Vendedora do mercado", "Calecute", 34, "Tem a banca mais cheirosa do mercado de especiarias. Os clientes encontram-na de olhos fechados.",
      ["colar"], mulher=True),
    M("cal4", "calecute", "Raman Nair", "teimoso", "indiano", "#6a4c93", ["marfim"], ["pimenta"],
      "Guarda do Samorim", "Calecute", 45, "Guarda do palácio que vende pimenta nas horas vagas. Não sorri. Nunca.",
      ["cajado"], barba=True),
    # ---------------- GOA
    M("goa1", "goa", "Krishna Naik", "honesto", "indiano", "#e85d04", ["ouro", "marfim"], ["pimenta", "canela"],
      "Intérprete e mercador", "Goa", 43, "Ajudou Afonso de Albuquerque a falar com os reis da região. Agora ajuda os mercadores a não serem enganados.",
      ["livro"]),
    M("goa2", "goa", "Sebastião Pinto", "vigarista", "europeu", "#495057", ["vinho", "ouro"], ["canela", "gengibre"],
      "Soldado e mercador", "Setúbal", 34, "Veio para a Índia como soldado e ficou para fazer fortuna. Ainda não fez, mas está sempre 'quase'.",
      ["cicatriz", "bolsa"], barba=True),
    M("goa3", "goa", "Lakshmi", "generoso", "indiano", "#d00000", ["vinho", "marfim"], ["pimenta", "gengibre"],
      "Dona de uma casa de pasto", "Pangim", 50, "Serve o caril mais famoso de Goa. Os marinheiros dizem que é picante demais... e repetem sempre.",
      ["colar", "brinco"], mulher=True),
    M("goa4", "goa", "Licenciado Afonso", "desconfiado", "europeu", "#2b2d42", ["vinho", "ouro"], ["canela", "gengibre"],
      "Físico do hospital", "Coimbra", 46, "Estuda as plantas da Índia para fazer remédios. Prova tudo o que compra, às vezes com resultados inesperados.",
      ["oculos", "livro"], barba=True),
    # ---------------- MALACA
    M("mal1", "malaca", "Tan Wei", "teimoso", "chines", "#0f4c5c", ["pimenta", "ouro"], ["porcelana", "seda"],
      "Capitão de junco", "Cantão", 52, "Atravessa o Mar da China duas vezes por ano. Chama aos portugueses 'bárbaros de nariz comprido', mas diz que pagam bem.",
      ["bolsa"]),
    M("mal2", "malaca", "Nina Chatu", "honesto", "indiano", "#5f0f40", ["tecidos", "pimenta"], ["cravinho", "noz"],
      "Chefe dos mercadores", "Coromandel", 55, "Organiza o comércio de toda a cidade e conhece mercadores de todo o Oriente. Sabe onde nascem as especiarias.",
      ["colar", "livro"], barba=True, segredo="ternate"),
    M("mal3", "malaca", "Hang Tuah", "desconfiado", "malaio", "#9a031e", ["tecidos", "ouro"], ["noz", "seda"],
      "Guerreiro do sultão", "Malaca", 38, "Ainda usa o seu kris (um punhal ondulado) à cintura e olha para os portugueses de lado. Mas negócio é negócio.",
      ["cicatriz"]),
    M("mal4", "malaca", "Mei Lin", "generoso", "chines", "#c9184a", ["pimenta", "tecidos"], ["porcelana"],
      "Vendedora de porcelana", "Fujian", 33, "Embrulha cada taça em palha de arroz e conta-lhe uma história antes de a vender.",
      ["colar"], mulher=True),
    # ---------------- ILHAS DAS ESPECIARIAS
    M("ter1", "ternate", "Sultão Bayan", "generoso", "malaio", "#fb8500", ["tecidos", "porcelana"], ["cravinho", "noz"],
      "Sultão de Ternate", "Ternate", 48, "Recebeu os primeiros portugueses em 1512 e ficou amigo deles. Gosta especialmente de presentes.",
      ["colar", "brinco"], barba=True),
    M("ter2", "ternate", "Sangaji", "desconfiado", "malaio", "#023047", ["marfim", "tecidos"], ["cravinho"],
      "Chefe de aldeia", "Tidore", 44, "Ternate e Tidore são vizinhas e rivais. Ele acha que vieste espiar.",
      ["cajado"]),
    M("ter3", "ternate", "Kaicili", "falabarato", "malaio", "#2a9d8f", ["porcelana"], ["noz"],
      "Apanhador de noz-moscada", "Banda", 26, "Sobe às árvores mais altas sem cordas e conta histórias de fantasmas da floresta.",
      ["macaco"]),
    M("ter4", "ternate", "Nyai Ratna", "honesto", "malaio", "#6a994e", ["tecidos", "marfim"], ["cravinho"],
      "Dona de um pomar", "Ternate", 52, "Cada árvore de cravinho do pomar dela tem o nome de um neto. Já vai em vinte e três.",
      ["colar"], mulher=True),
    # ---------------- ENSEADA DOS CORSÁRIOS
    M("ens1", "enseada", "Barba-Ruiva Mendes", "falabarato", "pirata", "#9b2226", ["vinho", "acucar"], ["seda", "ouro"],
      "Capitão pirata", "Peniche (fugido)", 45, "Foi marinheiro do Rei até ao dia em que achou que o tesouro do navio ficava melhor com ele.",
      ["papagaio", "brinco"], barba=True),
    M("ens2", "enseada", "Olho-de-Vidro", "vigarista", "pirata", "#3d405b", ["tecidos", "vinho"], ["porcelana", "seda"],
      "Receptador", "Ninguém sabe", 50, "Perdeu um olho numa luta e ganhou um de vidro num jogo de dados. Vende o que os outros roubam.",
      ["bolsa", "cicatriz"]),
    M("ens3", "enseada", "Ana Tempestade", "teimoso", "pirata", "#2a9d8f", ["acucar", "vinho"], ["ouro"],
      "Pirata e navegadora", "Galiza", 32, "Comanda o navio mais rápido da costa. Não regateia: ou aceitas, ou vais a nado.",
      ["brinco", "cicatriz"], mulher=True),
    M("ens4", "enseada", "Cozinheiro Salgado", "generoso", "pirata", "#7a5a3a", ["acucar", "tecidos"], ["porcelana"],
      "Cozinheiro dos piratas", "Setúbal", 58, "Faz um guisado de peixe famoso nos sete mares. Ninguém sabe o que leva, e é melhor não perguntar.",
      ["gato"], barba=True),
]
MERCADOR = {m["id"]: m for m in MERCADORES}            # acesso rápido pelo identificador


# ---------------------- EVENTOS NO MAR ----------------------
# Cada evento tem escolhas; cada escolha tem resultados possíveis com a sua probabilidade.
# Efeitos possíveis: dias, navio, dinheiro, dinheiro_pct (perder uma parte do dinheiro),
# carga_pct (perder uma parte da carga), estraga (estraga parte de um produto perecível),
# ganha (produto e quantidade), revela (mostra um porto secreto), alianca (aliança com piratas),
# dica (rumor sobre preços), amizade (mais amizade com um mercador que já conheces).
def resultado(prob, texto, **efeitos):
    return {"prob": prob, "texto": texto, "efeitos": efeitos}


def escolha(texto, *resultados):
    return {"texto": texto, "resultados": list(resultados)}


EVENTOS = [
    {"id": "tempestade", "titulo": "Tempestade!", "icone": "⛈️", "clima": "tempestade",
     "zonas": ["europa", "atlantico", "africa", "indico", "asia"],
     "texto": "O céu fica negro e as ondas parecem montanhas. O mestre do navio grita para recolher as velas!",
     "escolhas": [
         escolha("Recolher as velas e esperar que passe",
                 resultado(1, "A tempestade passa ao fim de uns dias. O navio aguentou, com alguns estragos.", dias=7, navio=-10)),
         escolha("Enfrentar a tempestade a todo o pano",
                 resultado(.45, "Que coragem! Atravessaste a tempestade sem perder tempo.", navio=-12),
                 resultado(.55, "Uma onda gigante varre o convés. O navio fica muito danificado.", navio=-28)),
         escolha("Deitar carga ao mar para o navio ficar mais leve",
                 resultado(1, "Com menos peso, o navio salva-se. Mas lá se foi parte da carga...", carga_pct=-.3, navio=-5)),
     ]},
    {"id": "piratas", "titulo": "Piratas à vista!", "icone": "🏴‍☠️", "clima": "piratas",
     "zonas": ["atlantico", "africa", "indico", "asia"], "aliados": False,
     "texto": "Um navio de velas negras aproxima-se depressa. No mastro, uma caveira sorri para ti.",
     "escolhas": [
         escolha("Pagar o que pedem",
                 resultado(1, "Os piratas levam parte do teu dinheiro e deixam-te seguir, a rir.", dinheiro_pct=-.25)),
         escolha("Fugir a todo o pano",
                 resultado("navio", "O teu navio é mais rápido! Os piratas ficam para trás.", dias=-2),
                 resultado("resto", "Apanham-te. Levam parte da carga e ainda disparam contra o navio.", carga_pct=-.4, navio=-15)),
         escolha("Lutar!",
                 resultado(.4, "Vitória! Os piratas fogem e deixam para trás parte do saque.", dinheiro=180, navio=-15),
                 resultado(.6, "A luta corre mal. Perdes metade da carga e o navio fica em mau estado.", carga_pct=-.5, navio=-30)),
         escolha("Propor uma aliança (dando-lhes parte da carga)",
                 resultado(.55, "O capitão pirata ri-se e aperta-te a mão: «Agora és dos nossos!» Contam-te onde fica o esconderijo deles.",
                           carga_pct=-.2, alianca=True, revela="enseada"),
                 resultado(.45, "Os piratas acham piada... e levam a carga na mesma.", carga_pct=-.3)),
     ]},
    {"id": "piratas_amigos", "titulo": "Os teus amigos piratas", "icone": "🏴‍☠️", "clima": "piratas",
     "zonas": ["atlantico", "africa", "indico", "asia"], "aliados": True,
     "texto": "Um navio de velas negras aproxima-se... e o capitão acena-te com o chapéu. São os teus aliados!",
     "escolhas": [
         escolha("Partilhar um barril de vinho com eles",
                 resultado(.6, "Uma noite de canções. Antes de partirem, oferecem-te uma caixa de seda «encontrada» num navio.", ganha=["seda", 3]),
                 resultado(.4, "Contam-te histórias e um segredo sobre preços.", dica=True)),
         escolha("Seguir viagem",
                 resultado(1, "Trocam saudações com tiros de canhão para o ar. Que espetáculo!")),
     ]},
    {"id": "corsarios", "titulo": "Corsários franceses", "icone": "⚔️", "clima": "piratas",
     "zonas": ["europa", "atlantico"],
     "texto": "Um navio francês, com autorização do seu rei para atacar navios portugueses, vem na tua direção.",
     "escolhas": [
         escolha("Mostrar os canhões e não ceder",
                 resultado(.5, "Os franceses pensam duas vezes e vão-se embora.", navio=-5),
                 resultado(.5, "Há troca de tiros. Escapas, mas com o navio furado.", navio=-20)),
         escolha("Esconder-se junto à costa",
                 resultado(1, "Perdes uns dias escondido numa baía, mas ninguém te encontra.", dias=6)),
     ]},
    {"id": "calmaria", "titulo": "Calmaria", "icone": "🌫️", "clima": "calmaria",
     "zonas": ["atlantico", "africa", "indico"],
     "texto": "O vento parou de soprar. As velas estão moles e o mar parece um espelho.",
     "escolhas": [
         escolha("Esperar pelo vento",
                 resultado(1, "O vento volta ao fim de quase duas semanas.", dias=12)),
         escolha("Pôr a tripulação a rebocar o navio com os batéis",
                 resultado(1, "Os marinheiros remam até não poderem mais. Ganhas uns dias, mas o navio sofre.", dias=5, navio=-6)),
     ]},
    {"id": "ilha", "titulo": "Uma ilha desconhecida", "icone": "🏝️", "clima": "ilha",
     "zonas": ["atlantico", "africa", "indico", "asia"],
     "texto": "O vigia grita «Terra à vista!». É uma ilha que não aparece em nenhum mapa.",
     "escolhas": [
         escolha("Desembarcar e explorar",
                 resultado(.4, "Encontras água fresca, fruta e madeira boa. O navio é remendado na praia.", dias=3, navio=15),
                 resultado(.3, "Numa gruta, encontras um velho baú com moedas!", dias=3, dinheiro=150),
                 resultado(.3, "Os habitantes não gostam de visitas. Fugimos com algumas setas espetadas no casco.", dias=2, navio=-10)),
         escolha("Seguir viagem",
                 resultado(1, "Fica para outra vez. Um marinheiro desenha a ilha no diário de bordo.")),
     ]},
    {"id": "naufrago", "titulo": "Um náufrago!", "icone": "🛟", "clima": "normal",
     "zonas": ["europa", "atlantico", "africa", "indico", "asia"],
     "texto": "Agarrado a uma tábua, um homem acena-te. Está queimado do sol e quase sem forças.",
     "escolhas": [
         escolha("Salvá-lo",
                 resultado(.75, "O náufrago agradece-te muito e, para te pagar, conta-te um segredo.", dias=1, revela="qualquer"),
                 resultado(.25, "Era um espião de piratas! Durante a noite, foge num batel com parte do teu dinheiro.", dias=1, dinheiro_pct=-.15)),
         escolha("Seguir viagem",
                 resultado(1, "A tripulação fica a olhar para ti em silêncio. Não foi a decisão mais bonita.")),
     ]},
    {"id": "estraga", "titulo": "Humidade no porão", "icone": "🍄", "clima": "normal", "carga": True,
     "zonas": ["europa", "atlantico", "africa", "indico", "asia"],
     "texto": "Com o calor e a humidade, cheira a bolor no porão. Parte da mercadoria está a estragar-se!",
     "escolhas": [
         escolha("Secar tudo ao sol no convés",
                 resultado(1, "Perdes uns dias, mas salvas a maior parte.", dias=2, estraga=.2)),
         escolha("Deitar fora o que está estragado",
                 resultado(1, "Lá vai uma boa parte de um produto pela borda fora.", estraga=.5)),
     ]},
    {"id": "ratos", "titulo": "Ratos no porão!", "icone": "🐀", "clima": "normal", "carga": True,
     "zonas": ["europa", "atlantico", "africa", "indico", "asia"],
     "texto": "Uma família de ratos (bem, uma aldeia de ratos) andou a banquetear-se com a carga.",
     "escolhas": [
         escolha("Arranjar um gato no próximo porto",
                 resultado(1, "Tarde demais para esta viagem: os ratos já comeram parte de um produto.", estraga=.3)),
     ]},
    {"id": "golfinhos", "titulo": "Golfinhos!", "icone": "🐬", "clima": "golfinhos",
     "zonas": ["europa", "atlantico", "africa", "indico", "asia"],
     "texto": "Um grupo de golfinhos acompanha o navio, aos saltos. Os marinheiros dizem que dá sorte!",
     "escolhas": [
         escolha("Seguir os golfinhos",
                 resultado(1, "E não é que deu sorte? Os golfinhos levam-te por uma corrente que encurta a viagem.", dias=-5)),
     ]},
    {"id": "vento", "titulo": "Ventos favoráveis", "icone": "💨", "clima": "normal",
     "zonas": ["europa", "atlantico", "africa", "indico", "asia"],
     "texto": "Um vento forte e constante enche as velas. O navio voa sobre as ondas!",
     "escolhas": [
         escolha("Aproveitar o vento",
                 resultado(1, "Chegas muito mais cedo do que esperavas.", dias=-8)),
     ]},
    {"id": "escorbuto", "titulo": "Escorbuto", "icone": "🤒", "clima": "normal", "min_dias": 40,
     "zonas": ["africa", "indico", "asia"],
     "texto": "Ao fim de tantas semanas no mar, a tripulação adoece: gengivas inchadas, cansaço... é o escorbuto.",
     "escolhas": [
         escolha("Desviar para uma praia para comprar fruta fresca",
                 resultado(1, "A fruta faz milagres. A tripulação recupera, mas perdes uns dias.", dias=8, dinheiro=-30)),
         escolha("Continuar e rezar",
                 resultado(.5, "Por sorte, a viagem acaba antes de a doença piorar.", navio=-5),
                 resultado(.5, "Com metade da tripulação de cama, o navio é mal tratado e avança devagar.", navio=-15, dias=6)),
     ]},
    {"id": "mercante", "titulo": "Navio em apuros", "icone": "🆘", "clima": "normal",
     "zonas": ["europa", "indico", "asia", "africa"],
     "texto": "Um navio mercante com o mastro partido pede ajuda com bandeiras.",
     "escolhas": [
         escolha("Ajudar a reparar o mastro",
                 resultado(.6, "O capitão é amigo de um mercador que conheces e conta-lhe o que fizeste. Também te paga pela ajuda.", dias=3, dinheiro=60, amizade=15),
                 resultado(.4, "Ajudas, e o capitão agradece com um aperto de mão. A tripulação está orgulhosa.", dias=3, amizade=8)),
         escolha("Seguir viagem",
                 resultado(1, "Não há tempo a perder. Ou há?")),
     ]},
    {"id": "monstro", "titulo": "Monstro marinho?!", "icone": "🐉", "clima": "monstro",
     "zonas": ["atlantico", "indico"],
     "texto": "Os marinheiros juram que viram uma serpente gigante nas ondas. Metade da tripulação está a rezar.",
     "escolhas": [
         escolha("Disparar os canhões",
                 resultado(1, "BUM! Era uma baleia, que foge assustada. Os marinheiros vão contar esta história durante anos.", dinheiro=-15)),
         escolha("Mudar de rumo, por via das dúvidas",
                 resultado(1, "Mais vale prevenir. A volta custa uns dias.", dias=5)),
     ]},
    {"id": "armada", "titulo": "A armada do Rei", "icone": "⚓", "clima": "normal",
     "zonas": ["atlantico", "africa", "indico"],
     "texto": "Encontras uma armada portuguesa a caminho da Índia. O capitão-mor convida-te a navegar com eles.",
     "escolhas": [
         escolha("Navegar com a armada",
                 resultado(.7, "Viagem segura e com bons pilotos. Ainda ouves uns rumores sobre preços.", dica=True),
                 resultado(.3, "A armada é lenta e perdes uns dias, mas pelo menos ninguém te ataca.", dias=5)),
         escolha("Agradecer e seguir sozinho",
                 resultado(1, "Segues o teu caminho. Ao longe, as naus do Rei parecem castelos no mar.")),
     ]},
    {"id": "garrafa", "titulo": "Uma garrafa no mar", "icone": "🍾", "clima": "noite", "segredos": True,
     "zonas": ["europa", "atlantico", "africa", "indico", "asia"],
     "texto": "À luz da lua, um marinheiro apanha uma garrafa a boiar. Lá dentro há um papel enrolado.",
     "escolhas": [
         escolha("Ler a mensagem",
                 resultado(1, "É um mapa desenhado à pressa, com uma cruz e um nome!", revela="qualquer")),
     ]},
]
EVENTO = {e["id"]: e for e in EVENTOS}

# Um naufrágio não se escolhe: acontece quando o navio está em muito mau estado
NAUFRAGIO = {"id": "naufragio", "titulo": "Naufrágio!", "icone": "🌊", "clima": "naufragio",
             "texto": "O casco, já muito danificado, não aguenta mais. Ouve-se um estalo enorme e a água entra por todo o lado. O navio está a afundar!",
             "escolhas": [escolha("Agarrar o que se puder e saltar para o mar!", resultado(1, "", naufragio=True))]}

# Frases para as viagens sem acontecimentos
VIAGENS_CALMAS = {
    "europa": "Viagem tranquila, com o vento a favor e gaivotas a seguir o navio.",
    "atlantico": "Dias de mar azul a perder de vista. À noite, as estrelas guiam o piloto.",
    "africa": "A costa de África passa devagar, verde e misteriosa, enquanto o navio desce para sul.",
    "indico": "As monções sopram a favor. O navio corta as águas quentes do Índico.",
    "asia": "Entre ilhas cobertas de floresta, cruzas juncos chineses e pequenos barcos de pescadores.",
}


# =====================================================================
# 4. MAPA E ROTAS
# O mapa vai da longitude -25 à 135 e da latitude 62 à -40, desenhado em 1000 x 600.
# Os navios não atravessam terra: andam por uma REDE DE ROTAS (pontos no mar ligados entre si)
# e o caminho mais curto é calculado com o algoritmo de Dijkstra.
# =====================================================================
MAPA_L, MAPA_A = 1000, 600
LON_MIN, LON_MAX, LAT_MAX, LAT_MIN = -25, 135, 62, -40


def mx(lon):
    """Longitude -> coordenada x no desenho do mapa."""
    return round((lon - LON_MIN) * MAPA_L / (LON_MAX - LON_MIN), 1)


def my(lat):
    """Latitude -> coordenada y no desenho do mapa."""
    return round((LAT_MAX - lat) * MAPA_A / (LAT_MAX - LAT_MIN), 1)


# Contornos (muito simplificados) das terras conhecidas em 1515: pares (longitude, latitude)
TERRAS = {
    "africa": [(-6, 35.8), (-1, 35.5), (3, 36.8), (10, 37.2), (11, 33.5), (15, 32.3), (20, 30.5), (20, 32.5), (25, 31.7),
               (29.9, 31.2), (32.4, 31.2), (32.5, 29.9), (33.8, 27), (35.5, 23.9), (37.2, 19), (39, 16), (41.7, 13.4),
               (43.2, 11.6), (44, 10.4), (47, 11.2), (51.2, 11.8), (51, 10.4), (49.5, 6), (47.9, 4.5), (45.3, 2),
               (42.5, -0.5), (40.2, -2.3), (39.3, -6.8), (40.5, -10.5), (40.7, -15), (36.9, -17.9), (35.5, -22),
               (32.9, -25.9), (32.4, -28.6), (31, -29.9), (27.9, -33), (25.6, -34), (20, -34.8), (18.4, -34.3),
               (18.2, -32), (17, -29), (15, -26.6), (14.5, -22.9), (12, -18), (11.8, -15.8), (13.2, -12.6),
               (13.2, -8.8), (12.3, -6), (11.8, -4.8), (9.3, -1), (9.5, 2.5), (9.7, 4), (8.5, 4.5), (6, 4.3),
               (3.4, 6.4), (1.2, 6.1), (-1.6, 5), (-4, 5.2), (-7.5, 4.4), (-9.5, 5.5), (-11.5, 6.9), (-13.2, 8.5),
               (-15, 11), (-16.7, 12.5), (-17.4, 14.7), (-16.5, 16.5), (-16, 19), (-17, 21), (-15, 24), (-13, 27.5),
               (-9.8, 29.5), (-9.7, 31.5), (-8.5, 33.3), (-6.8, 34)],
    "eurasia": [(-5.6, 36), (-2, 36.7), (-0.5, 38.3), (0.2, 39.5), (0.9, 41), (3.2, 42), (3.1, 43.3), (4.8, 43.4),
                (7.3, 43.7), (8.9, 44.4), (10.3, 43.5), (11.2, 42.4), (12.5, 41.7), (14.2, 40.8), (15.7, 40), (15.6, 38),
                (16.6, 38.9), (17.2, 39.4), (16.9, 40.5), (18.5, 40.1), (17.9, 40.6), (16.5, 41.3), (14, 42.6), (12.4, 44.2),
                (12.3, 45.4), (13.7, 45.6), (14.5, 45.2), (15.9, 43.5), (17.5, 43), (19.3, 42), (19.5, 41), (20, 39.6),
                (21.1, 38.4), (21.6, 37.4), (21.9, 36.8), (22.5, 36.4), (23.1, 36.5), (23, 37.6), (23.6, 37.9), (24, 37.7),
                (24.1, 38.3), (23.2, 39), (22.9, 39.5), (22.9, 40.6), (24.4, 40.9), (26, 40.8), (26.2, 39.5), (27.2, 38.4),
                (27.3, 37), (28.2, 36.7), (30.6, 36.8), (32.6, 36.1), (34.6, 36.8), (36.2, 36.6), (35.8, 35.5), (35.9, 34.5),
                (35.5, 33.9), (34.8, 32), (34.2, 31.3), (32.6, 30), (33.6, 28.3), (34.4, 27.9), (34.9, 29.5), (36.5, 26),
                (38, 24), (39.2, 21.5), (41.5, 17.5), (42.8, 14.8), (43.5, 12.7), (45, 12.8), (48.5, 14), (52.2, 15.6),
                (55.2, 17.3), (57.8, 19), (58.6, 20.5), (59.8, 22.5), (58.6, 23.6), (57.2, 24.4), (56.4, 24.9), (56.3, 26.3),
                (55.3, 25.3), (54, 24.1), (52, 24), (51.6, 25.3), (51.2, 26.1), (50.8, 24.7), (50.1, 26.3), (48.8, 27.6),
                (48, 29.4), (48.8, 30.2), (50.3, 29.3), (51.4, 27.9), (54, 26.6), (55.5, 26.6), (56.3, 27.15), (56.9, 27.05),
                (57.3, 26.4), (57.8, 25.7), (59.5, 25.4), (61.5, 25.1), (66.6, 25.4), (67, 24.8), (68.3, 23.7), (70, 22.6),
                (69, 22.3), (70.3, 20.9), (71, 20.7), (72.6, 21.2), (72.8, 19), (73.3, 17), (73.8, 15.5), (74.8, 12.9),
                (75.8, 11.25), (76.2, 9.9), (77.5, 8.1), (78.2, 8.9), (79.3, 10.3), (79.9, 13.1), (80.3, 15.8), (82.3, 16.9),
                (85.8, 19.8), (87, 21.5), (88.5, 22), (90, 21.8), (91.8, 22.3), (92.2, 20.7), (94.3, 18), (94.5, 16),
                (96, 16.8), (97.6, 16.5), (98.4, 13.5), (98.6, 10), (98.3, 8), (100.3, 5.4), (101.3, 2.8), (102.25, 2.2),
                (103.5, 1.3), (104.2, 1.4), (103.4, 3.8), (103.1, 5.3), (102.2, 6.2), (100.5, 7.5), (99.5, 9.2), (99.2, 10.8),
                (100, 12.6), (100.9, 13.5), (101.5, 12.6), (103, 11.5), (104.8, 10.4), (105.1, 8.6), (106.7, 10.3),
                (109.2, 11.7), (109.3, 13.8), (108.3, 16), (106.7, 17.5), (106.2, 20.2), (108, 21.5), (110.3, 20.9),
                (113.5, 22.2), (117, 23.5), (119.6, 25.6), (121.5, 28.5), (122, 30.8), (121, 32.5), (120, 35), (122.5, 37.3),
                (121.5, 39), (118, 39.2), (121, 40.8), (125, 39.6), (129.5, 42.5), (135, 44), (135, 62), (21.2, 62),
                (21.4, 60.8), (22.9, 59.9), (25, 60.2), (27.8, 60.5), (29.5, 60.2), (28.2, 59.4), (24, 59.4), (23.5, 58.3),
                (24, 57), (21, 57), (21, 55.5), (18.6, 54.4), (16, 54.3), (14, 53.9), (12.5, 54.4), (11, 54), (10.9, 55.5),
                (10.5, 57.6), (8.5, 57), (8.1, 55.5), (8.8, 54), (8.5, 53.6), (7, 53.5), (5, 53.3), (4.7, 52.5), (4, 51.5),
                (3.2, 51.3), (1.6, 50.9), (0.2, 49.7), (-1.3, 49.6), (-1.9, 48.7), (-3, 48.8), (-4.7, 48.4), (-4.3, 47.8),
                (-2.2, 47.2), (-1.2, 46.2), (-1.2, 44.6), (-1.5, 43.4), (-3.8, 43.5), (-6, 43.6), (-8.2, 43.5), (-9.3, 43),
                (-8.8, 42), (-8.7, 41.2), (-9, 40), (-9.4, 38.7), (-8.8, 38), (-8.9, 37), (-7.4, 37.2), (-6.4, 36.8)],
    "escandinavia": [(5, 62), (5.2, 60), (5.7, 58.9), (7, 58), (8.5, 58.2), (10.5, 59.2), (11.2, 58.9), (11.9, 57.7),
                     (12.8, 56), (14.3, 55.5), (16, 56.2), (16.6, 57.3), (18, 59.3), (17.2, 61), (17.4, 62)],
    "gra_bretanha": [(-5.7, 50.1), (-3.5, 50.3), (-1, 50.7), (1.3, 51.2), (1.6, 52.5), (0.3, 53.4), (-0.1, 54.5), (-1.4, 55),
                     (-1.8, 56), (-1.8, 57.5), (-3.3, 58.6), (-5, 58.6), (-6, 57.5), (-5.6, 56.3), (-5, 55), (-3.1, 53.4),
                     (-4.6, 53.3), (-4.2, 52.5), (-5.2, 51.7), (-3.2, 51.4), (-4.2, 51.2)],
    "irlanda": [(-6, 52.2), (-6.2, 53.4), (-5.5, 54.6), (-7.3, 55.3), (-8.5, 54.5), (-10, 54), (-9.5, 53), (-10.3, 51.9), (-8.4, 51.5)],
    "madagascar": [(49.3, -12), (50.4, -15.5), (49.4, -17.8), (48, -21), (47, -25), (45.2, -25.4), (43.7, -23.4), (43.3, -21),
                   (44.5, -16.2), (46.3, -15.7), (47.9, -13.5)],
    "ceilao": [(79.8, 9.8), (81.2, 8.5), (81.9, 7), (81.2, 6.1), (80.1, 6), (79.8, 7.5)],
    "samatra": [(95.3, 5.6), (97.5, 5.2), (100.4, 2.2), (103.8, -1), (105.9, -5.8), (104.6, -5.9), (102.3, -4), (100.3, -0.8), (98.7, 1.7)],
    "java": [(105.2, -6.8), (108.3, -6.2), (111, -6.5), (112.7, -6.9), (114.5, -7.8), (111, -8.2), (108, -7.8)],
    "borneu": [(109, 1.5), (109.6, -1), (110.2, -2.9), (114.6, -3.9), (116.3, -3.2), (117.9, 1), (119, 4.8), (117.2, 6.9),
               (116, 5.9), (113.9, 4.6), (111.3, 2.6), (109.6, 2)],
    "celebes": [(119.5, -5.5), (120.4, -1), (120.9, 1.3), (124.9, 1.5), (123.3, -0.9), (121.5, -1.9), (123.3, -4.5), (121.6, -4.7), (120.4, -5.6)],
    "halmaera": [(127.9, 2.2), (128.7, 1.5), (128.1, 0.6), (128.9, -0.6), (128.2, -0.9), (127.8, 0.2)],
    "nova_guine": [(131, -1), (134.5, -0.9), (135, -3.5), (135, -4.5), (132.5, -4), (131.3, -2.5)],
    "sicilia": [(12.4, 38.1), (13.3, 38.2), (15.6, 38.3), (15.1, 36.7), (14.3, 36.8), (12.5, 37.6)],
    "sardenha": [(8.4, 41), (9.6, 41.1), (9.8, 39.6), (9, 38.9), (8.4, 39.1)],
    "corsega": [(8.6, 42.9), (9.4, 43), (9.5, 41.9), (9.1, 41.4), (8.6, 41.9)],
    "creta": [(23.5, 35.6), (26.3, 35.3), (25.8, 35), (23.6, 35.2)],
    "chipre": [(32.3, 35.1), (34.6, 35.6), (33.9, 34.7), (32.5, 34.7)],
}
# Ilhas pequenas (desenhadas como pontinhos): Madeira, Canárias e Cabo Verde
ILHAS = [(-16.9, 32.7), (-17.3, 28.6), (-16.5, 28.3), (-15.6, 28), (-14, 28.4), (-13.6, 29), (-23.6, 15.1), (-24.4, 16.6),
         (-22.9, 16.1), (-25, 17), (-24.3, 14.9), (-23, 15.3), (127.4, 0.8), (39.3, -6.1)]

# Pontos de passagem no mar (para as rotas contornarem as terras)
PASSAGENS = {
    "w_lis": (-11, 38.6), "w_sagres": (-9.6, 36.4), "w_gib": (-5.6, 35.9), "w_alboran": (-2.5, 36.0),
    "w_medw": (1.5, 37.6), "w_sard": (8.0, 38.0), "w_canal": (11.8, 37.25), "w_malta": (14.5, 35.8),
    "w_ionio": (18.5, 37.2), "w_otranto": (18.9, 40.0), "w_adria": (15.0, 43.2), "w_peloponeso": (22.6, 35.9),
    "w_egeu": (24.2, 37.3), "w_finisterra": (-10.6, 43.3), "w_ushant": (-6, 48.4), "w_mancha": (-1.5, 50.1),
    "w_dover": (1.5, 51.05), "w_tamisa": (1.5, 51.45), "w_escalda": (3.3, 51.6), "w_canarias": (-19, 28.5),
    "w_cabobranco": (-18.6, 21), "w_dakar": (-18.8, 14.5), "w_serraleoa": (-14.8, 7.5), "w_palmas": (-8.3, 3.6),
    "w_guine": (2, 3.3), "w_saotome": (6, -0.5), "w_congo": (10.8, -6.2), "w_angola": (10.5, -14),
    "w_namibia": (11.5, -24), "w_cabo": (18, -36.5), "w_agulhas": (22, -36.6), "w_natal": (33.5, -30.8),
    "w_sofala": (37.5, -21.5), "w_canalmoz": (41.6, -18), "w_quenia": (42.3, -4), "w_madag_n": (49.4, -11.2),
    "w_madag_e": (51, -14), "w_arabico": (60, 10), "w_rashadd": (61, 22.5), "w_hormuz": (56.75, 26.55),
    "w_goa": (72.6, 15.5), "w_calecute": (74.8, 11.2), "w_comorim": (77.3, 6.9), "w_ceilao": (80.8, 5.0),
    "w_achem": (95.0, 6.6), "w_estreito": (100.0, 3.6), "w_singapura": (104.4, 1.0), "w_java": (108, -4.6),
    "w_flores": (115, -6.2), "w_flores2": (120.5, -6.8), "w_banda": (125, -4.2), "w_molucas": (127.0, -0.8),
}
# Ligações da rede de rotas (cada par é um troço de mar navegável)
LIGACOES = [
    ("lisboa", "w_lis"), ("lisboa", "w_sagres"), ("lagos", "w_sagres"), ("w_sagres", "w_gib"), ("w_lis", "w_sagres"),
    ("w_gib", "w_alboran"), ("w_alboran", "w_medw"), ("w_medw", "w_sard"), ("w_sard", "w_canal"), ("w_canal", "w_malta"),
    ("w_malta", "w_ionio"), ("w_ionio", "w_otranto"), ("w_otranto", "w_adria"), ("w_adria", "veneza"),
    ("w_ionio", "w_peloponeso"), ("w_malta", "w_peloponeso"), ("w_peloponeso", "w_egeu"), ("w_egeu", "atenas"),
    ("w_lis", "w_finisterra"), ("w_finisterra", "w_ushant"), ("w_ushant", "w_mancha"), ("w_mancha", "w_dover"),
    ("w_dover", "w_tamisa"), ("w_tamisa", "londres"), ("w_dover", "w_escalda"), ("w_escalda", "antuerpia"),
    ("w_lis", "funchal"), ("w_sagres", "funchal"), ("funchal", "w_canarias"), ("w_lis", "w_canarias"),
    ("w_sagres", "w_canarias"), ("w_canarias", "w_cabobranco"), ("w_cabobranco", "w_dakar"), ("w_dakar", "caboverde"),
    ("w_cabobranco", "caboverde"), ("w_dakar", "w_serraleoa"), ("caboverde", "w_serraleoa"), ("w_serraleoa", "w_palmas"),
    ("w_palmas", "mina"), ("mina", "w_guine"), ("w_palmas", "w_guine"), ("w_guine", "w_saotome"), ("w_saotome", "w_congo"),
    ("w_congo", "congo"), ("w_congo", "w_angola"), ("w_angola", "w_namibia"), ("w_namibia", "w_cabo"), ("w_cabo", "w_agulhas"),
    ("w_agulhas", "w_natal"), ("w_natal", "w_sofala"), ("w_sofala", "sofala"), ("w_sofala", "w_canalmoz"),
    ("w_canalmoz", "mocambique"), ("mocambique", "w_quenia"), ("w_quenia", "melinde"), ("w_quenia", "w_arabico"),
    ("mocambique", "w_madag_n"), ("w_quenia", "w_madag_n"), ("w_madag_n", "w_madag_e"), ("w_madag_e", "enseada"),
    ("w_arabico", "w_rashadd"), ("w_rashadd", "w_hormuz"), ("w_hormuz", "ormuz"), ("w_rashadd", "w_goa"),
    ("w_arabico", "w_goa"), ("w_arabico", "w_calecute"), ("w_arabico", "w_comorim"), ("w_goa", "goa"),
    ("w_goa", "w_calecute"), ("w_calecute", "calecute"), ("w_calecute", "w_comorim"), ("w_comorim", "w_ceilao"),
    ("w_ceilao", "w_achem"), ("w_achem", "w_estreito"), ("w_estreito", "malaca"), ("malaca", "w_singapura"),
    ("w_singapura", "w_java"), ("w_java", "w_flores"), ("w_flores", "w_flores2"), ("w_flores2", "w_banda"),
    ("w_banda", "w_molucas"), ("w_molucas", "ternate"),
]


def posicao(nome):
    """Coordenadas (x, y) no mapa de um porto ou de um ponto de passagem."""
    lon, lat = (PORTOS[nome]["lon"], PORTOS[nome]["lat"]) if nome in PORTOS else PASSAGENS[nome]
    return mx(lon), my(lat)


def caminho_mais_curto(origem, destino):
    """Algoritmo de Dijkstra: encontra o caminho mais curto no mar entre dois portos.
    Devolve (distância, lista de pontos (x, y) do caminho)."""
    vizinhos = {}
    for a, b in LIGACOES:
        d = math.dist(posicao(a), posicao(b))
        vizinhos.setdefault(a, []).append((b, d))
        vizinhos.setdefault(b, []).append((a, d))
    melhor = {origem: 0}
    anterior = {}
    fila = [(0, origem)]
    while fila:
        dist, no = heapq.heappop(fila)
        if no == destino:
            break
        if dist > melhor[no]:
            continue
        for vizinho, d in vizinhos.get(no, []):
            nova = dist + d
            if nova < melhor.get(vizinho, float("inf")):
                melhor[vizinho] = nova
                anterior[vizinho] = no
                heapq.heappush(fila, (nova, vizinho))
    pontos = [destino]
    while pontos[-1] != origem:
        pontos.append(anterior[pontos[-1]])
    pontos.reverse()
    return melhor[destino], [posicao(p) for p in pontos]


# Calcula de uma vez todas as rotas entre portos (são poucas: 19 x 19)
ROTAS = {}
for _a in PORTOS:
    for _b in PORTOS:
        if _a != _b:
            _dist, _pontos = caminho_mais_curto(_a, _b)
            ROTAS[_a + ">" + _b] = {"dias": DIAS_FIXOS_VIAGEM + round(_dist * DIAS_POR_UNIDADE), "pontos": _pontos}


def rota(origem, destino):
    """Dias de viagem e pontos do caminho entre dois portos."""
    return ROTAS[origem + ">" + destino]


# =====================================================================
# 5. REGRAS DO JOGO
# =====================================================================
# --- pequenas funções de acaso e de contas (usadas em todo o jogo) ---
def sorte():
    """Número ao acaso entre 0 e 1."""
    return random.random()


def inteiro(a, b):
    """Número inteiro ao acaso entre a e b (incluindo os dois)."""
    return a + int(sorte() * (b - a + 1))


def escolher(lista):
    """Um elemento ao acaso de uma lista."""
    return lista[int(sorte() * len(lista))]


def arred(x):
    """Arredonda para o inteiro mais próximo (as metades arredondam para cima)."""
    return int(math.floor(x + 0.5))


def fala(personalidade, situacao, **campos):
    """Escolhe uma fala ao acaso da personalidade e preenche os campos ({produto}, {preco}...)."""
    texto = escolher(FALAS[personalidade].get(situacao) or FALAS["honesto"][situacao])
    for chave, valor in campos.items():
        texto = texto.replace("{" + chave + "}", str(valor))
    return texto


def data_do_dia(dia):
    """Converte o número do dia de jogo numa data por extenso ('14 de março de 1516').
    Usa o calendário da época (juliano): os anos divisíveis por 4 têm 29 de fevereiro."""
    ano, mes, d = ANO_INICIAL, MES_INICIAL, 1 + dia
    while True:
        dias_mes = 29 if (mes == 2 and ano % 4 == 0) else DIAS_DO_MES[mes - 1]
        if d <= dias_mes:
            return f"{d} de {MESES[mes - 1]} de {ano}"
        d -= dias_mes
        mes += 1
        if mes > 12:
            mes, ano = 1, ano + 1


def preco_normal(porto, produto):
    """Preço 'normal' de uma caixa num porto (barato onde se produz, caro onde se procura)."""
    base = PRODUTOS[produto]["preco"]
    barato, caro = FATORES_MARGEM[PRODUTOS[produto]["margem"]]
    if produto in PORTOS[porto]["produz"]:
        return base * barato
    if produto in PORTOS[porto]["procura"]:
        return base * caro
    return base


class Jogo:
    """Tudo o que acontece num jogo: o navio, a carga, o tempo, os amigos e as negociações."""

    def __init__(self, nome):
        self.nome = nome
        self.dia = 0
        self.porto = "lisboa"
        self.navio = 100                       # estado do navio (0 a 100)
        self.porao = {}                        # produto -> número de caixas
        self.falsos = {}                       # produto -> quantas dessas caixas são falsas
        self.origem_falsos = {}                # produto -> nome de quem nos enganou
        self.custos = {}                       # produto -> total de cruzados pagos pelas caixas que estão no porão
        self.amizade = {}                      # mercador -> amizade (0 a 100)
        self.encomendas = {}                   # mercador -> {"produto", "qtd"}
        self.missoes = 0                       # encomendas cumpridas
        self.aliado_piratas = False
        self.conhecidos = []                   # portos secretos já revelados
        self.visitados = ["lisboa"]
        self.percurso = ["lisboa"]             # todos os portos por onde passou, por ordem
        self.diario = []                       # (dia, texto)
        self.eventos_recentes = []
        self.fase = "carta"                    # carta, porto, conversa, viagem, fim, derrota
        self.conversa = None
        self.viagem = None
        self.mensagem = ""
        self.final = None
        self.ganho_penalizado = 0
        # recursos iniciais ALEATÓRIOS
        tipo = escolher(["dinheiro", "especiarias", "misto"])
        if tipo == "dinheiro":
            self.dinheiro = inteiro(55, 90) * 10
            self.texto_inicial = "uma bolsa bem recheada de cruzados"
        elif tipo == "especiarias":
            self.dinheiro = inteiro(6, 12) * 10
            for _ in range(2):
                produto = escolher(ESPECIARIAS)
                self.porao[produto] = self.porao.get(produto, 0) + inteiro(8, 14)
            self.texto_inicial = "um porão com especiarias e poucas moedas"
        else:
            self.dinheiro = inteiro(25, 45) * 10
            self.porao[escolher(ESPECIARIAS)] = inteiro(8, 14)
            self.texto_inicial = "algumas moedas e umas caixas de especiarias"
        self.valor_inicial = self.fortuna()
        self.chegar_ao_porto(primeira=True)
        self.escrever_diario(f"O Rei D. Manuel I entregou-te uma caravela e {self.texto_inicial}. Começa a aventura!")

    # ------------------------------------------------ informações
    def escrever_diario(self, texto):
        self.diario.append((self.dia, texto))

    def carga_total(self):
        return sum(self.porao.values())

    def espaco_livre(self):
        return CAPACIDADE_PORAO - self.carga_total()

    def verdadeiras(self, produto):
        """Caixas verdadeiras (não falsas) de um produto."""
        return self.porao.get(produto, 0) - self.falsos.get(produto, 0)

    def custo_medio(self, produto):
        """Quanto pagaste, em média, por cada caixa deste produto (0 se as caixas foram oferecidas)."""
        if not self.porao.get(produto):
            return 0
        return arred(self.custos.get(produto, 0) / self.porao[produto])

    def retirar_custo(self, produto, qtd):
        """Quando saem caixas do porão, o custo delas sai também (na mesma proporção).
        Assim o custo médio das caixas que ficam não muda."""
        if produto in self.custos and self.porao.get(produto):
            if qtd >= self.porao[produto]:
                del self.custos[produto]
            else:
                self.custos[produto] -= self.custos[produto] * qtd / self.porao[produto]

    def fortuna(self):
        """Dinheiro + valor da carga verdadeira ao preço de Lisboa."""
        carga = sum(self.verdadeiras(p) * preco_normal("lisboa", p) for p in self.porao)
        return arred(self.dinheiro + carga)

    def dias_restantes(self):
        return max(0, DIAS_TOTAIS - self.dia)

    def portos_no_mapa(self):
        """Portos que aparecem no mapa: todos os normais e os secretos já revelados."""
        return [p for p in PORTOS if not PORTOS[p].get("secreto") or p in self.conhecidos]

    def amigos(self):
        return [m for m, a in self.amizade.items() if a >= AMIGO]

    def preco(self, produto):
        """Preço de uma caixa no porto onde estamos (com a variação desta visita)."""
        return max(1, arred(preco_normal(self.porto, produto) * self.flutuacao[produto]))

    def mercadores_aqui(self):
        return [m for m in MERCADORES if m["porto"] == self.porto]

    def mudar_amizade(self, mid, valor):
        self.amizade[mid] = max(0, min(100, self.amizade.get(mid, 0) + valor))

    # ------------------------------------------------ chegar a um porto
    def chegar_ao_porto(self, primeira=False):
        """Prepara a visita: preços desta visita, mercadoria de cada mercador e quem é vigarista hoje."""
        self.flutuacao = {p: 0.85 + sorte() * 0.3 for p in PRODUTOS}
        self.stock = {}
        self.falsos_venda = {}
        self.zangados = []
        for m in self.mercadores_aqui():
            self.stock[m["id"]] = {p: inteiro(8, 22) for p in m["vende"]}
            # o vigarista, em cada visita, tem metade da hipótese de vender cada produto falso
            self.falsos_venda[m["id"]] = [p for p in m["vende"] if m["personalidade"] == "vigarista" and sorte() < .5]
        if not primeira:
            if self.porto not in self.visitados:
                self.visitados.append(self.porto)
                self.escrever_diario(f"Chegaste pela primeira vez a {PORTOS[self.porto]['nome']}.")
            self.percurso.append(self.porto)

    def avancar_dias(self, dias):
        """O tempo passa. Se o prazo acabar, o jogo termina (com ou sem castigo)."""
        self.dia += dias
        if self.dia >= DIAS_TOTAIS and self.fase not in ("fim", "derrota"):
            self.terminar(PENALIZACAO_LONGE if self.porto != "lisboa" else 0,
                          "O prazo acabou e não estavas em Lisboa." if self.porto != "lisboa" else "")

    # ------------------------------------------------ conversas e negócios
    def abrir_conversa(self, mid):
        """Começa (ou retoma) a conversa com um mercador deste porto."""
        if self.fase not in ("porto", "conversa") or mid not in MERCADOR or MERCADOR[mid]["porto"] != self.porto:
            return
        if self.conversa and self.conversa["m"] == mid:
            self.fase = "conversa"
            return
        m = MERCADOR[mid]
        pers = PERSONALIDADES[m["personalidade"]]
        amigo = self.amizade.get(mid, 0) >= AMIGO
        c = {"m": mid, "paciencia": pers["paciencia"], "humor": "contente" if amigo else pers["humor"],
             "contra": None, "fechada": mid in self.zangados, "examinados": {}, "extra": ""}
        if c["fechada"]:
            c["fala"] = "(Vira-te as costas e finge que não te vê.)"
        else:
            c["fala"] = fala(m["personalidade"], "ola_amigo" if amigo else "ola", nome=self.nome)
            if self.falsos_venda.get(mid):
                c["fala"] += " " + fala(m["personalidade"], "pista", produto=PRODUTOS[self.falsos_venda[mid][0]]["nome"].lower())
            # amigos (e fala-baratos) contam rumores
            if amigo or (m["personalidade"] == "falabarato" and self.amizade.get(mid, 0) >= 20):
                c["extra"] = self.dar_dica(m)
            # pedir uma encomenda
            if mid not in self.encomendas and self.amizade.get(mid, 0) >= 30 and sorte() < .5:
                opcoes = [p for p in m["quer"] if p not in PORTOS[self.porto]["produz"]]
                if opcoes:
                    pedido = {"produto": escolher(opcoes), "qtd": inteiro(5, 10)}
                    self.encomendas[mid] = pedido
                    c["extra"] += (" " if c["extra"] else "") + fala(m["personalidade"], "encomenda",
                                                                     qtd=pedido["qtd"], produto=PRODUTOS[pedido["produto"]]["nome"].lower())
                    self.escrever_diario(f"{m['nome']} ({PORTOS[self.porto]['nome']}) encomendou-te {pedido['qtd']} caixas de "
                                         f"{PRODUTOS[pedido['produto']]['nome'].lower()}.")
        self.conversa = c
        self.fase = "conversa"

    def dar_dica(self, m):
        """Um rumor: onde fica um porto secreto, ou onde um produto é caro ou barato."""
        texto = fala(m["personalidade"], "dica") + " "
        segredo = m.get("segredo")
        if segredo and segredo not in self.conhecidos:
            self.conhecidos.append(segredo)
            self.escrever_diario(f"{m['nome']} contou-te onde ficam as {PORTOS[segredo]['nome']}." if segredo == "ternate"
                                 else f"{m['nome']} contou-te onde fica a {PORTOS[segredo]['nome']}.")
            return texto + RUMORES[segredo]
        return texto + self.rumor_de_precos()

    def rumor_de_precos(self):
        """Uma frase verdadeira sobre um porto onde um produto é muito caro ou muito barato."""
        produto = escolher(list(PRODUTOS))
        caros = [p for p in self.portos_no_mapa() if produto in PORTOS[p]["procura"] and p != self.porto]
        baratos = [p for p in self.portos_no_mapa() if produto in PORTOS[p]["produz"] and p != self.porto]
        nome = PRODUTOS[produto]["nome"].lower()
        if caros and (not baratos or sorte() < .5):
            return f"Em {PORTOS[escolher(caros)]['nome']} pagam muito bem por {nome}."
        if baratos:
            return f"Em {PORTOS[escolher(baratos)]['nome']} compra-se {nome} baratíssimo."
        return "Hoje não sei de nada... mas o vento está a mudar."

    def oferta(self, mid, produto, eu_vendo):
        """Preço por caixa que o mercador propõe (para comprar ou para vender)."""
        m = MERCADOR[mid]
        pers = PERSONALIDADES[m["personalidade"]]
        bonus = self.amizade.get(mid, 0) / 400                 # amizade: preços melhores
        if eu_vendo:                                           # ele compra-me
            fator = pers["compra"] * (1 if produto in m["quer"] else 0.75) * (1 + bonus)
        else:                                                  # ele vende-me
            fator = pers["venda"] * (1 - bonus)
            if produto in self.falsos_venda.get(mid, []):
                fator = 0.55                                   # PISTA: preço bom demais para ser verdade
        return max(1, arred(self.preco(produto) * fator))

    def precos_niveis(self, mid, produto, eu_vendo):
        """Os 3 preços por caixa: o preço dele, regatear um pouco (15%) e regatear muito (40%).
        Garante que os três são diferentes (quando o preço é baixo, os arredondamentos podiam igualá-los)."""
        base = self.oferta(mid, produto, eu_vendo)
        if eu_vendo:                                           # quero receber MAIS
            p1 = max(base + 1, arred(base * NIVEIS_PRECO[1]))
            return [base, p1, max(p1 + 1, arred(base * NIVEIS_PRECO[2]))]
        p1 = max(1, min(base - 1, arred(base / NIVEIS_PRECO[1])))     # quero pagar MENOS
        return [base, p1, max(1, min(p1 - 1, arred(base / NIVEIS_PRECO[2])))]

    def negociar(self, acao, produto, qtd, nivel):
        """O jogador propõe um negócio. acao: 'vender' ou 'comprar'; nivel: 0, 1 ou 2 (quanto regateia)."""
        c = self.conversa
        if self.fase != "conversa" or not c or c["fechada"] or produto not in PRODUTOS or nivel not in (0, 1, 2):
            return
        m = MERCADOR[c["m"]]
        pers = PERSONALIDADES[m["personalidade"]]
        c["contra"] = None
        eu_vendo = acao == "vender"
        # --- verificar se o negócio é possível ---
        if eu_vendo:
            qtd = min(qtd, self.porao.get(produto, 0))
            if qtd <= 0:
                c["fala"] = "Não tens isso no porão!"
                return
            if produto not in m["quer"] and m["personalidade"] in ("teimoso", "desconfiado", "vigarista") and sorte() < .5:
                c["fala"] = fala(m["personalidade"], "nao_interessa")
                return
        else:
            if produto not in m["vende"]:
                return
            qtd = min(qtd, self.stock[m["id"]].get(produto, 0), self.espaco_livre())
            if qtd <= 0:
                c["fala"] = "Já não tens espaço no porão!" if self.espaco_livre() <= 0 else "Já não tenho mais disso."
                return
        base = self.oferta(m["id"], produto, eu_vendo)
        preco = self.precos_niveis(m["id"], produto, eu_vendo)[nivel]
        if not eu_vendo and qtd * preco > self.dinheiro:
            qtd = self.dinheiro // preco
            if qtd <= 0:
                c["fala"] = "Sem dinheiro não há negócio, amigo."
                return
        # --- o mercador decide ---
        hipotese = pers["aceita"][nivel] + self.amizade.get(m["id"], 0) / 250 + EFEITO_HUMOR[c["humor"]]
        if not eu_vendo and produto in self.falsos_venda.get(m["id"], []):
            hipotese += .3                                     # o vigarista quer muito despachar o falso
        if nivel == 0 or sorte() < hipotese:
            self.fechar_negocio(acao, produto, qtd, preco, nivel)
        elif sorte() < pers["contra"]:
            meio = arred((base + preco) / 2)                   # a contraproposta fica a meio caminho
            c["contra"] = {"acao": acao, "produto": produto, "qtd": qtd, "preco": meio}
            c["fala"] = fala(m["personalidade"], "contra", preco=meio)
            c["humor"] = "neutro" if c["humor"] != "zangado" else "zangado"
            self.perder_paciencia(m)
        else:
            c["fala"] = fala(m["personalidade"], "recusa")
            self.mudar_amizade(m["id"], -3)
            c["humor"] = HUMORES[max(0, HUMORES.index(c["humor"]) - 1)]
            self.perder_paciencia(m)

    def perder_paciencia(self, m):
        """Cada recusa gasta paciência. Sem paciência, o mercador acaba a conversa."""
        c = self.conversa
        c["paciencia"] -= 1
        if c["paciencia"] <= 0:
            c["fala"] = fala(m["personalidade"], "irritado")
            c["humor"] = "zangado"
            c["fechada"] = True
            c["contra"] = None
            self.zangados.append(m["id"])
            self.mudar_amizade(m["id"], -10)

    def responder_contraproposta(self, aceitar):
        c = self.conversa
        if self.fase != "conversa" or not c or not c["contra"]:
            return
        proposta, c["contra"] = c["contra"], None
        if aceitar:
            if proposta["acao"] == "comprar":
                proposta["qtd"] = min(proposta["qtd"], self.dinheiro // proposta["preco"], self.espaco_livre())
            else:
                proposta["qtd"] = min(proposta["qtd"], self.porao.get(proposta["produto"], 0))
            if proposta["qtd"] > 0:
                self.fechar_negocio(proposta["acao"], proposta["produto"], proposta["qtd"], proposta["preco"], 1)
        else:
            m = MERCADOR[c["m"]]
            c["fala"] = "Como queiras. Diz-me se mudares de ideias."
            c["humor"] = HUMORES[max(0, HUMORES.index(c["humor"]) - 1)]
            self.perder_paciencia(m)

    def fechar_negocio(self, acao, produto, qtd, preco, nivel):
        """O negócio acontece: mexe no dinheiro, no porão, na amizade e no tempo."""
        c = self.conversa
        m = MERCADOR[c["m"]]
        pers = PERSONALIDADES[m["personalidade"]]
        nome_p = PRODUTOS[produto]["nome"].lower()
        if acao == "vender":
            # se houver caixas falsas, o mercador pode descobrir!
            if self.falsos.get(produto, 0) and sorte() < pers["deteta"]:
                falsas = self.falsos.pop(produto)
                self.retirar_custo(produto, falsas)
                self.porao[produto] -= falsas
                quem = self.origem_falsos.pop(produto, "um vigarista")
                self.escrever_diario(f"Descobriste que {falsas} caixas de {nome_p} eram falsas! Foste enganado por {quem}.")
                self.mudar_amizade(m["id"], -5)
                c["fala"] = fala(m["personalidade"], "falso", produto=nome_p)
                c["humor"] = "desconfiado"
                if self.porao[produto] <= 0:
                    del self.porao[produto]
                return
            falsas_vendidas = min(qtd, self.falsos.get(produto, 0))
            if falsas_vendidas:                                # passaram sem ninguém reparar...
                self.falsos[produto] -= falsas_vendidas
                if not self.falsos[produto]:
                    del self.falsos[produto]
            self.retirar_custo(produto, qtd)
            self.porao[produto] -= qtd
            if self.porao[produto] <= 0:
                del self.porao[produto]
            self.dinheiro += qtd * preco
            texto = f"Vendeste {qtd} caixas de {nome_p} a {m['nome']} por {qtd * preco} cruzados."
        else:
            self.dinheiro -= qtd * preco
            self.porao[produto] = self.porao.get(produto, 0) + qtd
            self.custos[produto] = self.custos.get(produto, 0) + qtd * preco     # guardar quanto pagámos
            self.stock[m["id"]][produto] -= qtd
            if produto in self.falsos_venda.get(m["id"], []):  # comprámos gato por lebre!
                self.falsos[produto] = self.falsos.get(produto, 0) + qtd
                self.origem_falsos[produto] = m["nome"]
            texto = f"Compraste {qtd} caixas de {nome_p} a {m['nome']} por {qtd * preco} cruzados."
        self.mudar_amizade(m["id"], [14, 8, 4][nivel] + (4 if m["personalidade"] == "generoso" else 0))
        c["humor"] = "contente"
        c["fala"] = fala(m["personalidade"], "aceita")
        self.mensagem = texto
        self.escrever_diario(texto)
        self.avancar_dias(DIAS_POR_NEGOCIO)

    def examinar(self, produto):
        """Olhar com atenção para a mercadoria do mercador antes de comprar (gasta 1 dia)."""
        c = self.conversa
        if self.fase != "conversa" or not c or c["fechada"]:
            return
        m = MERCADOR[c["m"]]
        if produto not in m["vende"] or produto in c["examinados"]:
            return
        if produto in self.falsos_venda.get(m["id"], []) and sorte() < .8:
            c["examinados"][produto] = "falso"
            c["fala"] = fala(m["personalidade"], "examinar_falso")
            c["humor"] = "desconfiado"
        else:
            c["examinados"][produto] = "bom"
            c["fala"] = fala(m["personalidade"], "examinar")
            if m["personalidade"] == "desconfiado":
                self.mudar_amizade(m["id"], 3)                 # gosta de quem verifica tudo
            if m["personalidade"] == "vigarista":
                c["humor"] = "desconfiado"
        self.avancar_dias(1)

    def entregar_encomenda(self):
        c = self.conversa
        if self.fase != "conversa" or not c or c["fechada"] or c["m"] not in self.encomendas:
            return
        m = MERCADOR[c["m"]]
        pedido = self.encomendas[c["m"]]
        if self.verdadeiras(pedido["produto"]) < pedido["qtd"]:
            return
        valor = 2 * pedido["qtd"] * self.preco(pedido["produto"])
        self.retirar_custo(pedido["produto"], pedido["qtd"])
        self.porao[pedido["produto"]] -= pedido["qtd"]
        if self.porao[pedido["produto"]] <= 0:
            del self.porao[pedido["produto"]]
        self.dinheiro += valor
        del self.encomendas[c["m"]]
        self.missoes += 1
        self.mudar_amizade(m["id"], 20)
        c["humor"] = "contente"
        c["fala"] = fala(m["personalidade"], "entrega")
        self.mensagem = f"Encomenda entregue a {m['nome']}: recebeste {valor} cruzados!"
        self.escrever_diario(self.mensagem)
        self.avancar_dias(DIAS_POR_NEGOCIO)

    def sair_conversa(self):
        if self.fase == "conversa":
            self.conversa = None
            self.fase = "porto"

    # ------------------------------------------------ estaleiro e partida
    def reparar(self):
        """Repara o navio (o que o dinheiro der)."""
        if self.fase != "porto" or self.navio >= 100:
            return
        pontos = min(100 - self.navio, self.dinheiro // CUSTO_REPARACAO)
        if pontos <= 0:
            self.mensagem = "Não tens dinheiro para pagar ao estaleiro."
            return
        self.dinheiro -= pontos * CUSTO_REPARACAO
        self.navio += pontos
        self.mensagem = f"Os carpinteiros repararam o navio ({pontos * CUSTO_REPARACAO} cruzados, {DIAS_REPARACAO} dias)."
        self.escrever_diario(f"Reparaste o navio em {PORTOS[self.porto]['nome']}.")
        self.avancar_dias(DIAS_REPARACAO)

    def navegar(self, destino):
        """Parte para outro porto. Decide já se vai acontecer algum evento no mar."""
        if self.fase != "porto" or destino not in self.portos_no_mapa() or destino == self.porto:
            return
        dias = rota(self.porto, destino)["dias"]
        self.viagem = {"origem": self.porto, "destino": destino, "dias": dias, "evento": None, "resultado": "",
                       "clima": "normal"}
        evento = self.sortear_evento(PORTOS[destino]["zona"], dias)
        if evento:
            self.viagem["evento"] = evento["id"]
            self.viagem["clima"] = evento["clima"]
        else:
            self.viagem["resultado"] = VIAGENS_CALMAS[PORTOS[destino]["zona"]]
        self.fase = "viagem"
        self.mensagem = ""

    def sortear_evento(self, zona, dias):
        """Escolhe (ou não) um evento para a viagem, conforme a zona, a duração e o estado do navio."""
        if self.navio < 30 and sorte() < .45:
            return NAUFRAGIO
        if sorte() > min(.85, .35 + dias / 300):
            return None
        opcoes = []
        for e in EVENTOS:
            if zona not in e["zonas"] or e["id"] in self.eventos_recentes:
                continue
            if "aliados" in e and e["aliados"] != self.aliado_piratas:
                continue
            if e.get("carga") and not self.porao:
                continue
            if e.get("min_dias", 0) > dias:
                continue
            if e.get("segredos") and all(p in self.conhecidos for p in RUMORES):
                continue
            opcoes.append(e)
        if not opcoes:
            return None
        evento = escolher(opcoes)
        self.eventos_recentes = (self.eventos_recentes + [evento["id"]])[-4:]
        return evento

    def evento_atual(self):
        if not self.viagem or not self.viagem["evento"]:
            return None
        return NAUFRAGIO if self.viagem["evento"] == "naufragio" else EVENTO[self.viagem["evento"]]

    def escolher_no_evento(self, indice):
        """O jogador escolhe uma opção do evento. Sorteia o resultado e aplica os efeitos."""
        evento = self.evento_atual()
        if self.fase != "viagem" or not evento or self.viagem["resultado"] or not 0 <= indice < len(evento["escolhas"]):
            return
        resultados = evento["escolhas"][indice]["resultados"]
        r, acumulado = sorte(), 0
        escolhido = resultados[-1]
        for res in resultados:
            prob = res["prob"]
            if prob == "navio":
                prob = .25 + self.navio / 200                  # quanto melhor o navio, mais fácil fugir
            elif prob == "resto":
                prob = 1
            acumulado += prob
            if r < acumulado:
                escolhido = res
                break
        texto = self.aplicar_efeitos(escolhido["texto"], escolhido["efeitos"])
        self.viagem["resultado"] = texto
        self.escrever_diario(f"{evento['titulo']} {texto}")

    def aplicar_efeitos(self, texto, ef):
        """Aplica os efeitos de um evento e devolve o texto final (com pormenores)."""
        partes = [texto] if texto else []
        if ef.get("naufragio"):
            return self.naufragar()
        if "dias" in ef:
            self.viagem["dias"] = max(DIAS_MINIMOS_VIAGEM, self.viagem["dias"] + ef["dias"])
        if "navio" in ef:
            self.navio = max(0, min(100, self.navio + ef["navio"]))
        if "dinheiro" in ef:
            self.dinheiro = max(0, self.dinheiro + ef["dinheiro"])
        if "dinheiro_pct" in ef:
            perda = arred(self.dinheiro * -ef["dinheiro_pct"])
            self.dinheiro -= perda
            partes.append(f"(Perdeste {perda} cruzados.)")
        if "carga_pct" in ef and self.porao:
            perdidas = self.perder_carga(-ef["carga_pct"])
            if perdidas:
                partes.append(f"(Perdeste {perdidas} caixas.)")
        if "estraga" in ef:
            pereciveis = [p for p in self.porao if PRODUTOS[p]["perecivel"]] or list(self.porao)
            if pereciveis:
                p = escolher(pereciveis)
                perda = max(1, arred(self.porao[p] * ef["estraga"]))
                self.tirar_caixas(p, perda)
                partes.append(f"(Perdeste {perda} caixas de {PRODUTOS[p]['nome'].lower()}.)")
        if "ganha" in ef:
            produto, qtd = ef["ganha"]
            qtd = min(qtd, self.espaco_livre())
            if qtd > 0:
                self.porao[produto] = self.porao.get(produto, 0) + qtd
                partes.append(f"(Ganhaste {qtd} caixas de {PRODUTOS[produto]['nome'].lower()}.)")
        if ef.get("alianca"):
            self.aliado_piratas = True
        if "revela" in ef:
            segredos = [p for p in RUMORES if p not in self.conhecidos]
            alvo = ef["revela"] if ef["revela"] in segredos else (escolher(segredos) if segredos and ef["revela"] == "qualquer" else None)
            if alvo:
                self.conhecidos.append(alvo)
                partes.append(f"Agora sabes onde ficam as {PORTOS[alvo]['nome']}!" if alvo == "ternate"
                              else f"Agora sabes onde fica a {PORTOS[alvo]['nome']}!")
            elif ef["revela"] == "qualquer":
                self.dinheiro += 80
                partes.append("Já conhecias o lugar, mas ganhaste 80 cruzados pela história.")
        if ef.get("dica"):
            partes.append("Rumor: " + self.rumor_de_precos())
        if "amizade" in ef:
            conhecidos = list(self.amizade)
            if conhecidos:
                mid = escolher(conhecidos)
                self.mudar_amizade(mid, ef["amizade"])
                partes.append(f"({MERCADOR[mid]['nome']} vai ficar a saber!)")
        return " ".join(partes)

    def tirar_caixas(self, produto, qtd):
        """Tira caixas do porão (primeiro as verdadeiras, para as falsas não 'desaparecerem' por magia)."""
        qtd = min(qtd, self.porao.get(produto, 0))
        self.retirar_custo(produto, qtd)
        self.porao[produto] -= qtd
        sobra_falsas = min(self.falsos.get(produto, 0), self.porao[produto])
        if produto in self.falsos:
            self.falsos[produto] = sobra_falsas
            if not sobra_falsas:
                del self.falsos[produto]
                self.origem_falsos.pop(produto, None)
        if self.porao[produto] <= 0:
            del self.porao[produto]
        return qtd

    def perder_carga(self, fracao):
        """Perde uma fração de cada produto do porão. Devolve quantas caixas se perderam."""
        total = 0
        for produto in list(self.porao):
            total += self.tirar_caixas(produto, arred(self.porao[produto] * fracao))
        return total

    def naufragar(self):
        """O navio afundou! Os amigos podem salvar-te... ou não."""
        amigos = self.amigos()
        salvamento = min(.9, .2 + .15 * len(amigos))
        self.perder_carga(1)
        if sorte() < salvamento:
            salvador = MERCADOR[escolher(amigos)]["nome"] if amigos else "uns pescadores"
            self.dinheiro = arred(self.dinheiro * .7)
            self.navio = 45
            self.viagem["dias"] += 15
            texto = (f"Foste salvo por {salvador}, que te reconheceu agarrado aos destroços! A carga perdeu-se, "
                     "mas emprestaram-te um navio velho para continuares.")
            if amigos:
                texto += " Os amigos valem mais do que ouro."
            return texto
        if sorte() < .5:
            self.terminar_derrota("naufragio")
            return "Ninguém apareceu para te salvar..."
        self.dinheiro = arred(self.dinheiro * .4)
        self.navio = 30
        self.viagem["dias"] += 30
        return ("Passaste três dias agarrado a um barril até chegares a uma praia. Perdeste a carga e muito dinheiro, "
                "mas compraste um barco velho para continuar.")

    def desembarcar(self):
        """Fim da viagem: o tempo passa e chega-se ao porto de destino."""
        if self.fase != "viagem" or (self.viagem["evento"] and not self.viagem["resultado"]):
            return
        destino = self.viagem["destino"]
        self.dia += self.viagem["dias"] + DIAS_NO_PORTO
        self.porto = destino
        self.fase = "porto"
        self.viagem = None
        self.chegar_ao_porto()
        if self.dia >= DIAS_TOTAIS:
            if destino == "lisboa":
                self.terminar(PENALIZACAO_ATRASO, "Chegaste a Lisboa depois do prazo.")
            else:
                self.terminar(PENALIZACAO_LONGE, "O prazo acabou e não estavas em Lisboa.")
            return
        self.mensagem = f"Chegaste a {PORTOS[destino]['nome']}! {PORTOS[destino]['texto']}"
        if not self.porao and self.dinheiro < 5:
            self.terminar_derrota("falencia")

    # ------------------------------------------------ o fim
    def terminar_derrota(self, motivo):
        self.fase = "derrota"
        self.final = {"motivo": motivo}
        self.escrever_diario("O navio afundou e ninguém te veio salvar." if motivo == "naufragio"
                             else "Ficaste sem dinheiro e sem carga. A viagem acabou aqui.")

    def terminar(self, penalizacao=0, motivo=""):
        """Cerimónia no palácio: o Rei avalia o teu trabalho e dá-te uma honra."""
        self.fase = "fim"
        self.conversa = None
        fortuna = self.fortuna()
        if penalizacao:
            perda = arred(fortuna * penalizacao)
            fortuna -= perda
            self.ganho_penalizado = perda
        portos = len([p for p in self.visitados if p != "lisboa"])
        amizades = len(self.amigos()) + 2 * self.missoes
        medalhas = {
            "fortuna": nivel_medalha(fortuna, LIMITES_MEDALHAS["fortuna"]),
            "descoberta": nivel_medalha(portos, LIMITES_MEDALHAS["descoberta"]),
            "amizades": nivel_medalha(amizades, LIMITES_MEDALHAS["amizades"]),
        }
        if fortuna < self.valor_inicial * 1.3:
            titulo = "Regressou com Histórias para Contar"
        elif self.aliado_piratas:
            titulo = "Corsário do Rei"
        elif all(n >= 2 for n in medalhas.values()):
            titulo = "Lenda dos Descobrimentos"
        else:
            # decide a melhor medalha; em caso de empate, o que estiver mais acima do limite da prata
            valores = {"fortuna": fortuna, "descoberta": portos, "amizades": amizades}
            forca = {k: medalhas[k] + valores[k] / LIMITES_MEDALHAS[k][1] / 10 for k in medalhas}
            melhor = max(forca, key=lambda k: forca[k])
            titulo = {"fortuna": "Mercador Mais Rico do Reino", "descoberta": "Grande Explorador",
                      "amizades": "Embaixador dos Sete Mares"}[melhor]
        pontos = fortuna // 10 + 60 * portos + 50 * len(self.amigos()) + 100 * self.missoes
        self.final = {"fortuna": fortuna, "portos": portos, "amigos": len(self.amigos()), "missoes": self.missoes,
                      "medalhas": medalhas, "titulo": titulo, "pontos": pontos, "motivo": motivo}
        self.escrever_diario(f"Apresentaste-te ao Rei D. Manuel I, que te deu o título de «{titulo}».")


def nivel_medalha(valor, limites):
    """0 = nenhuma, 1 = bronze, 2 = prata, 3 = ouro."""
    return sum(1 for limite in limites if valor >= limite)


# =====================================================================
# 7. DESENHOS SVG
# Tudo é desenhado com formas simples. Para não parecer "de computador":
#   - tudo tem contorno escuro, como se fosse desenhado a tinta (cor TINTA);
#   - um filtro ("lapis") entorta um pouco os traços e outro ("papel") dá um grão de papel antigo;
#   - as casas e as nuvens têm tamanhos ligeiramente diferentes (sorteados, mas sempre iguais).
# (Esta secção vem depois das regras porque só é usada pelas páginas.)
# =====================================================================
TINTA = "#3b2a1a"
PELES = {"europeu": ["#f2c9a5", "#e8b48c", "#f5d0b0"], "africano": ["#7a4a2c", "#8d5a36", "#5e3a22"],
         "arabe": ["#c99467", "#b98258", "#d6a274"], "indiano": ["#a86f44", "#9a6038", "#b57b4f"],
         "malaio": ["#b07a4a", "#a36d40", "#bf8a58"], "chines": ["#efc9a0", "#e5b98d", "#f2d2ad"],
         "pirata": ["#d9a77c", "#7a4a2c", "#c99467"]}


def defs(prefixo, cima, baixo):
    """Degradê do céu e os filtros do desenho à mão. O prefixo evita ids repetidos na mesma página."""
    return (f'<defs><linearGradient id="{prefixo}ceu" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{cima}"/><stop offset="1" stop-color="{baixo}"/></linearGradient>'
            f'<filter id="{prefixo}lapis" x="-3%" y="-3%" width="106%" height="106%">'
            '<feTurbulence type="fractalNoise" baseFrequency=".035" numOctaves="2" seed="5" result="r"/>'
            '<feDisplacementMap in="SourceGraphic" in2="r" scale="2.6" xChannelSelector="R" yChannelSelector="G"/></filter>'
            f'<filter id="{prefixo}papel" x="0" y="0" width="100%" height="100%">'
            '<feTurbulence type="fractalNoise" baseFrequency=".8" numOctaves="2" seed="11"/>'
            '<feColorMatrix values="0 0 0 0 .4  0 0 0 0 .3  0 0 0 0 .18  .35 0 0 0 -.1"/></filter></defs>')


def svg(prefixo, largura, altura, cima, baixo, conteudo, classe, descricao, extra_fundo=""):
    """Junta as camadas num <svg> completo: céu, desenho com filtro de lápis e grão de papel."""
    return (f'<svg class="{classe}" viewBox="0 0 {largura} {altura}" preserveAspectRatio="xMidYMid meet" role="img" '
            f'aria-label="{html.escape(descricao)}">{defs(prefixo, cima, baixo)}'
            f'<rect width="{largura}" height="{altura}" fill="url(#{prefixo}ceu)"/>{extra_fundo}'
            f'<g filter="url(#{prefixo}lapis)" stroke="{TINTA}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round">'
            f'{conteudo}</g><rect width="{largura}" height="{altura}" filter="url(#{prefixo}papel)" pointer-events="none"/></svg>')


def nuvem(x, y, s=1.0, cor="#ffffff"):
    return (f'<path transform="translate({x} {y}) scale({s})" fill="{cor}" stroke-opacity=".35" '
            'd="M-34 12 Q-38 -4 -22 -6 Q-18 -24 2 -20 Q16 -32 28 -14 Q44 -14 40 4 Q40 14 28 14 L-28 14 Q-36 14 -34 12 Z"/>')


def sol(x, y, r, cor="#ffd23f"):
    return (f'<circle cx="{x}" cy="{y}" r="{r + 12}" fill="#fff0a8" opacity=".5" stroke="none"/>'
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{cor}" stroke="#d99a00"/>')


def palmeira(x, y, s=1.0):
    """Palmeira: tronco curvo e folhas em leque."""
    folhas = "".join(f'<path d="M0 -90 Q{dx * .6} {-110 + dy} {dx} {-80 + dy}" fill="none" stroke="#2f7a3d" stroke-width="7"/>'
                     for dx, dy in ((-46, 10), (-30, -14), (0, -22), (30, -14), (48, 12), (-20, 20), (24, 22)))
    return (f'<g transform="translate({x} {y}) scale({s})"><path d="M-4 0 Q-10 -50 0 -90 L6 -90 Q-2 -50 6 0 Z" fill="#8b5e34"/>'
            f'{folhas}<circle cx="2" cy="-88" r="6" fill="#6b4423"/></g>')


def caravela(x, y, s=1.0, vela="#f6ecd2", preta=False, classe="navio-desenho"):
    """Uma caravela (casco, mastros, velas e bandeira). Com preta=True é um navio pirata."""
    casco = "#2b2b2b" if preta else "#8b5a2b"
    vela = "#3a3a3a" if preta else vela
    simbolo = ('<circle cx="-14" cy="-70" r="9" fill="#f0f0f0"/><path d="M-20 -58 l12 0" stroke="#f0f0f0" stroke-width="3"/>'
               if preta else '<path d="M-17 -82 h6 v7 h7 v6 h-7 v7 h-6 v-7 h-7 v-6 h7 Z" fill="#c0392b" stroke="none"/>')
    bandeira = '#1a1a1a' if preta else '#c0392b'
    # o <g class> de fora é o que o CSS anima; o de dentro tem a posição (assim a animação não a apaga)
    return (f'<g class="{classe}"><g transform="translate({x} {y}) scale({s})">'
            f'<path d="M-70 0 L70 0 Q62 26 30 30 L-38 30 Q-66 26 -70 0 Z" fill="{casco}"/>'
            f'<path d="M-62 8 H62" stroke-opacity=".5" fill="none"/>'
            f'<path d="M-14 0 V-120 M30 0 V-96 M-50 0 V-70" fill="none" stroke-width="3"/>'
            f'<path d="M-44 -104 Q-14 -96 16 -104 L12 -50 Q-14 -42 -40 -50 Z" fill="{vela}"/>'
            f'<path d="M30 -92 Q58 -60 30 -18 L10 -18 Q30 -55 30 -92 Z" fill="{vela}"/>'
            f'<path d="M-50 -66 Q-30 -46 -50 -24 L-64 -24 Q-50 -45 -50 -66 Z" fill="{vela}"/>'
            f'{simbolo}<path d="M-14 -120 l20 5 l-20 6 Z" fill="{bandeira}" class="bandeira"/></g></g>')


# ---------------------- MERCADORES ----------------------
def pele_de(m):
    """Cor da pele do mercador (sempre a mesma para o mesmo mercador)."""
    return PELES[m["aspeto"]][sum(map(ord, m["id"])) % 3]


def tom(cor, fator):
    """Escurece (fator < 1) ou clareia (fator > 1) uma cor #rrggbb."""
    r, g, b = int(cor[1:3], 16), int(cor[3:5], 16), int(cor[5:7], 16)
    if fator < 1:
        r, g, b = (int(c * fator) for c in (r, g, b))
    else:
        r, g, b = (int(c + (255 - c) * (fator - 1)) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def cabeca(m, humor):
    """A cabeça do mercador, desenhada à volta de (0, 0) com raio 30: cara, chapéu e expressão."""
    pele = pele_de(m)
    roupa = m["roupa"]
    aspeto = m["aspeto"]
    partes = []
    cabelo = "#2b1d14" if aspeto != "europeu" else ["#5a3a1e", "#2b1d14", "#a0522d", "#7a7a7a"][sum(map(ord, m["nome"])) % 4]
    if m["mulher"] and aspeto in ("europeu", "chines", "malaio", "indiano", "pirata"):
        partes.append(f'<path d="M-30 4 Q-34 -34 0 -36 Q34 -34 30 4 L32 34 Q20 40 14 26 L-14 26 Q-20 40 -32 34 Z" fill="{cabelo}"/>')
    partes.append(f'<ellipse cx="-29" cy="2" rx="6" ry="8" fill="{pele}"/><ellipse cx="29" cy="2" rx="6" ry="8" fill="{pele}"/>')
    partes.append(f'<ellipse cx="0" cy="0" rx="28" ry="31" fill="{pele}"/>')
    # olhos e sobrancelhas, conforme o humor
    if humor == "contente":
        olhos = '<path d="M-15 -2 q5 -6 10 0 M5 -2 q5 -6 10 0" fill="none" stroke-width="2.6"/>'
        sobr = '<path d="M-17 -12 q6 -4 12 -1 M5 -13 q6 -3 12 1" fill="none" stroke-width="2.4"/>'
        boca = '<path d="M-11 13 Q0 24 11 13 Q0 17 -11 13 Z" fill="#8a2f2f"/>'
    elif humor == "desconfiado":
        olhos = '<path d="M-15 -1 h10 M5 -1 h10" fill="none" stroke-width="3"/>'
        sobr = '<path d="M-17 -10 l12 2 M5 -15 q6 -2 12 2" fill="none" stroke-width="2.4"/>'
        boca = '<path d="M-9 16 Q2 13 11 10" fill="none" stroke-width="2.4"/>'
    elif humor == "zangado":
        olhos = '<circle cx="-10" cy="0" r="3" fill="#1a1a1a" stroke="none"/><circle cx="10" cy="0" r="3" fill="#1a1a1a" stroke="none"/>'
        sobr = '<path d="M-18 -12 l13 6 M18 -12 l-13 6" fill="none" stroke-width="3"/>'
        boca = '<path d="M-10 18 Q0 10 10 18" fill="none" stroke-width="2.6"/>'
        partes.append('<ellipse cx="-17" cy="10" rx="6" ry="3.5" fill="#e06666" opacity=".55" stroke="none"/>'
                      '<ellipse cx="17" cy="10" rx="6" ry="3.5" fill="#e06666" opacity=".55" stroke="none"/>')
    else:
        olhos = '<circle cx="-10" cy="0" r="3" fill="#1a1a1a" stroke="none"/><circle cx="10" cy="0" r="3" fill="#1a1a1a" stroke="none"/>'
        sobr = '<path d="M-16 -10 q6 -3 11 0 M5 -10 q6 -3 11 0" fill="none" stroke-width="2.2"/>'
        boca = '<path d="M-8 15 Q0 18 8 15" fill="none" stroke-width="2.4"/>'
    partes.append(olhos + sobr)
    partes.append('<path d="M0 0 q-4 9 1 10" fill="none" stroke-width="2"/>')
    if m["barba"]:
        partes.append(f'<path d="M-24 6 Q-24 38 0 42 Q24 38 24 6 Q20 22 10 22 Q0 26 -10 22 Q-20 22 -24 6 Z" fill="{tom(cabelo, .9)}"/>'
                      f'<path d="M-12 11 Q0 6 12 11" fill="none" stroke="{tom(cabelo, .7)}" stroke-width="4"/>')
    partes.append(boca)
    # chapéus e lenços de cada região
    if aspeto == "europeu":
        if m["mulher"]:
            partes.append('<path d="M-31 -6 Q-30 -40 0 -40 Q30 -40 31 -6 Q24 -26 0 -27 Q-24 -26 -31 -6 Z" fill="#f4efe6"/>')
        else:
            partes.append(f'<path d="M-30 -18 Q-34 -40 0 -42 Q38 -42 34 -20 Q10 -26 -30 -18 Z" fill="{tom(roupa, .6)}"/>'
                          '<path d="M22 -36 q16 -14 24 -6" fill="none" stroke="#c0392b" stroke-width="3"/>')
    elif aspeto == "arabe":
        cor = "#f4efe6" if roupa == "#ffffff" else tom(roupa, 1.5)
        if m["mulher"]:
            partes.append(f'<path d="M-36 30 Q-40 -40 0 -42 Q40 -40 36 30 L28 30 Q30 -22 0 -24 Q-30 -22 -28 30 Z" fill="{tom(roupa, .8)}"/>')
        else:
            partes.append(f'<path d="M-32 -12 Q-36 -46 0 -46 Q36 -46 32 -12 Q0 -22 -32 -12 Z" fill="{cor}"/>'
                          '<path d="M-28 -24 Q0 -34 28 -24 M-26 -34 Q0 -42 26 -34" fill="none" stroke-opacity=".5"/>')
    elif aspeto == "indiano":
        if m["mulher"]:
            partes.append(f'<path d="M-34 24 Q-36 -40 0 -40 Q36 -40 34 24 L30 24 Q28 -24 0 -26 Q-28 -24 -30 24 Z" fill="{tom(roupa, 1.2)}"/>'
                          '<circle cx="0" cy="-12" r="2.5" fill="#c0392b" stroke="none"/>')
        else:
            partes.append(f'<path d="M-31 -12 Q-34 -46 0 -48 Q34 -46 31 -12 Q0 -20 -31 -12 Z" fill="{tom(roupa, 1.15)}"/>'
                          '<path d="M-26 -22 Q4 -40 28 -18 M-24 -32 Q0 -46 26 -30" fill="none" stroke-opacity=".5"/>'
                          '<circle cx="0" cy="-34" r="4" fill="#ffd23f"/>'
                          f'<path d="M-14 9 Q-6 6 0 9 Q6 6 14 9" fill="none" stroke="{cabelo}" stroke-width="4"/>')
    elif aspeto == "africano":
        if m["mulher"]:
            partes.append(f'<path d="M-30 -6 Q-36 -56 6 -54 Q40 -50 30 -8 Q0 -22 -30 -6 Z" fill="{roupa}"/>'
                          '<path d="M-24 -26 Q0 -40 26 -24" fill="none" stroke="#ffd23f" stroke-width="3"/>')
        else:
            partes.append(f'<path d="M-24 -20 Q-26 -40 0 -40 Q26 -40 24 -20 Q0 -26 -24 -20 Z" fill="{roupa}"/>'
                          '<path d="M-20 -30 h40" stroke="#ffd23f" stroke-width="3"/>')
    elif aspeto == "chines":
        partes.append('<path d="M-46 -16 L0 -52 L46 -16 Q0 -22 -46 -16 Z" fill="#d9b26b"/><path d="M-20 -32 L20 -32" stroke-opacity=".4"/>')
    elif aspeto == "malaio":
        partes.append(f'<path d="M-26 -18 Q-26 -40 0 -40 Q26 -40 26 -18 Z" fill="{"#1a1a1a" if not m["mulher"] else tom(roupa, 1.3)}"/>')
    elif aspeto == "pirata":
        partes.append(f'<path d="M-31 -10 Q-32 -42 0 -42 Q32 -42 31 -10 Q0 -20 -31 -10 Z" fill="{roupa}"/>'
                      f'<path d="M28 -16 l14 -4 l-4 14 Z" fill="{roupa}"/>'
                      '<circle cx="-24" cy="-26" r="2.5" fill="#f0f0f0" stroke="none"/><circle cx="-14" cy="-30" r="2.5" fill="#f0f0f0" stroke="none"/>')
        if "Olho" in m["nome"]:
            partes.append('<path d="M-22 -10 L26 -20" stroke-width="2"/><ellipse cx="10" cy="0" rx="8" ry="7" fill="#1a1a1a"/>')
        partes.append('<circle cx="29" cy="12" r="4" fill="none" stroke="#e0b100" stroke-width="2.4"/>')
    partes.append(acessorios_cabeca(m))
    return "".join(partes)


def acessorios_cabeca(m):
    """Objetos que se veem na cara: óculos, cicatriz, pena atrás da orelha e brinco."""
    a = m["acessorios"]
    partes = []
    if "oculos" in a:
        partes.append('<circle cx="-10" cy="0" r="7.5" fill="#dff3ff" fill-opacity=".35" stroke-width="2"/>'
                      '<circle cx="10" cy="0" r="7.5" fill="#dff3ff" fill-opacity=".35" stroke-width="2"/>'
                      '<path d="M-2.5 0 h5 M-17.5 -1 l-9 -3 M17.5 -1 l9 -3" fill="none" stroke-width="2"/>')
    if "cicatriz" in a:
        partes.append('<path d="M14 6 l8 12 M15 11 l5 -2 M18 15 l4 -2" fill="none" stroke="#8a3a2a" stroke-width="1.8"/>')
    if "pena" in a:
        partes.append('<path d="M24 -14 Q44 -46 40 -60 Q30 -40 22 -12 Z" fill="#f6efe0"/><path d="M23 -13 L40 -58" fill="none" stroke-width="1.2"/>')
    if "brinco" in a and m["aspeto"] != "pirata":
        partes.append('<circle cx="-29" cy="12" r="3.5" fill="none" stroke="#e0b100" stroke-width="2.4"/>')
    return "".join(partes)


def corpo(m):
    """O corpo do mercador visto inteiro (para a cena do porto), em pé, com os pés em (0, 0)."""
    pele = pele_de(m)
    roupa = m["roupa"]
    escuro = tom(roupa, .7) if roupa != "#ffffff" else "#d8d0c0"
    longo = m["aspeto"] in ("arabe", "indiano") or m["mulher"]
    if longo:
        pernas = f'<path d="M-26 -8 Q-30 -60 -22 -88 L22 -88 Q30 -60 26 -8 Z" fill="{escuro}"/>'
    else:
        pernas = (f'<path d="M-14 -70 Q-16 -36 -14 -6" stroke="{TINTA}" stroke-width="15" fill="none"/>'
                  f'<path d="M-14 -70 Q-16 -36 -14 -6" stroke="{escuro}" stroke-width="11" fill="none"/>'
                  f'<path d="M14 -70 Q16 -36 15 -6" stroke="{TINTA}" stroke-width="15" fill="none"/>'
                  f'<path d="M14 -70 Q16 -36 15 -6" stroke="{escuro}" stroke-width="11" fill="none"/>')
    pes = '<ellipse cx="-16" cy="-3" rx="11" ry="5" fill="#4a3324"/><ellipse cx="17" cy="-3" rx="11" ry="5" fill="#4a3324"/>'
    tronco = (f'<path d="M-30 -84 Q-34 -126 -20 -132 L20 -132 Q34 -126 30 -84 Q0 -78 -30 -84 Z" fill="{roupa}"/>'
              f'<path d="M-30 -86 Q0 -80 30 -86" fill="none" stroke="{tom(roupa, .5) if roupa != "#ffffff" else "#b8a98a"}" stroke-width="5"/>')
    bracos = (f'<path d="M-24 -126 Q-44 -100 -30 -76" stroke="{TINTA}" stroke-width="15" fill="none"/>'
              f'<path d="M-24 -126 Q-44 -100 -30 -76" stroke="{roupa}" stroke-width="11" fill="none"/>'
              f'<path d="M24 -126 Q46 -108 40 -86" stroke="{TINTA}" stroke-width="15" fill="none"/>'
              f'<path d="M24 -126 Q46 -108 40 -86" stroke="{roupa}" stroke-width="11" fill="none"/>'
              f'<circle cx="-30" cy="-73" r="6" fill="{pele}"/><circle cx="40" cy="-83" r="6" fill="{pele}"/>')
    a = m["acessorios"]
    atras, frente = [], []
    if "cajado" in a:                          # cajado na mão esquerda
        atras.append('<path d="M-31 -150 L-35 -2" fill="none" stroke="#7a4a2a" stroke-width="5"/>')
    if "colar" in a:
        frente.append("".join(f'<circle cx="{x}" cy="{y}" r="2.6" fill="{c}" stroke-width="1"/>'
                              for x, y, c in ((-12, -129, "#e8c34a"), (-7, -125, "#c0392b"), (0, -123, "#e8c34a"),
                                              (7, -125, "#2a9d8f"), (12, -129, "#e8c34a"))))
    if "bolsa" in a:                           # bolsa de moedas presa ao cinto
        frente.append('<path d="M-22 -86 q-10 6 -8 18 q8 8 16 0 q2 -12 -8 -18 Z" fill="#a0703a"/><path d="M-26 -86 h8" stroke-width="2"/>'
                      '<circle cx="-22" cy="-74" r="2" fill="#e8c34a" stroke="none"/>')
    if "livro" in a:                           # livro de contas debaixo do braço
        frente.append('<g transform="rotate(-12 -40 -104)"><rect x="-50" y="-118" width="20" height="28" rx="2" fill="#7b2d26"/>'
                      '<path d="M-47 -112 h14 M-47 -106 h14" stroke="#e8c34a" stroke-width="1.5"/></g>')
    if "balanca" in a:                         # balança na mão direita
        frente.append('<path d="M40 -86 V-112 M22 -112 H58 M22 -112 L16 -96 M22 -112 L28 -96 M58 -112 L52 -96 M58 -112 L64 -96" '
                      'fill="none" stroke-width="2"/><path d="M14 -96 q8 7 16 0 Z M50 -96 q8 7 16 0 Z" fill="#e8c34a"/>')
    if "papagaio" in a:                        # papagaio no ombro direito
        frente.append('<g transform="translate(26 -140)"><ellipse cx="0" cy="-10" rx="8" ry="12" fill="#2f9e44"/>'
                      '<circle cx="2" cy="-24" r="7" fill="#e63946"/><path d="M8 -25 q6 2 2 7 Z" fill="#ffd23f"/>'
                      '<circle cx="3" cy="-26" r="1.5" fill="#1a1a1a" stroke="none"/><path d="M-4 0 l-4 14 l6 -6" fill="#1d6fb8"/></g>')
    if "macaco" in a:                          # macaquinho no ombro esquerdo
        frente.append('<g transform="translate(-30 -142)"><path d="M6 6 q16 4 10 20" fill="none" stroke="#7a4a2a" stroke-width="3"/>'
                      '<ellipse cx="0" cy="0" rx="9" ry="11" fill="#8b5e34"/><circle cx="0" cy="-15" r="8" fill="#8b5e34"/>'
                      '<circle cx="0" cy="-14" r="5" fill="#e0b48a" stroke="none"/><circle cx="-2" cy="-15" r="1.2" fill="#1a1a1a" stroke="none"/>'
                      '<circle cx="2" cy="-15" r="1.2" fill="#1a1a1a" stroke="none"/></g>')
    if "gato" in a:                            # um gato sentado aos pés
        frente.append('<g transform="translate(50 -2)"><ellipse cx="0" cy="-12" rx="11" ry="13" fill="#e2a55a"/>'
                      '<circle cx="0" cy="-30" r="9" fill="#e2a55a"/><path d="M-8 -36 l2 -9 l5 6 M8 -36 l-2 -9 l-5 6" fill="#e2a55a"/>'
                      '<path d="M10 -4 q14 2 8 -14" fill="none" stroke="#e2a55a" stroke-width="4"/>'
                      '<circle cx="-3" cy="-31" r="1.4" fill="#1a1a1a" stroke="none"/><circle cx="3" cy="-31" r="1.4" fill="#1a1a1a" stroke="none"/></g>')
    return ("".join(atras) + pes + pernas + bracos + tronco + "".join(frente)
            + f'<g transform="translate(0 -160) scale(.95)">{cabeca(m, "neutro")}</g>')


def retrato(m, humor):
    """Retrato grande do mercador para a conversa (o humor muda a expressão)."""
    roupa = m["roupa"]
    gola = tom(roupa, .6) if roupa != "#ffffff" else "#cfc4ae"
    fundo = {"europeu": ("#f4e2bd", "#e9cf9c"), "africano": ("#ffe3b3", "#f2c36b"), "arabe": ("#fbe7c6", "#ecc890"),
             "indiano": ("#ffe1c2", "#f6b98a"), "malaio": ("#e7f3d9", "#c3e0a8"), "chines": ("#fbe6d4", "#f0c4a0"),
             "pirata": ("#dfe7ea", "#b7c7cc")}[m["aspeto"]]
    conteudo = (f'<path d="M30 300 Q30 214 80 196 L180 196 Q230 214 230 300 Z" fill="{roupa}"/>'
                f'<path d="M98 196 L130 236 L162 196" fill="{gola}"/>'
                f'<path d="M112 160 L112 198 Q130 210 148 198 L148 160 Z" fill="{pele_de(m)}"/>'
                f'<g transform="translate(130 112) scale(2.5)" stroke-width=".9">{cabeca(m, humor)}</g>'
                + acessorios_retrato(m))
    return svg(f"r{m['id']}", 260, 300, fundo[0], fundo[1], conteudo, "retrato-svg", f"Retrato de {m['nome']}, com ar {humor}.")


def acessorios_retrato(m):
    """Objetos que aparecem no retrato: colar, papagaio, macaco e gato."""
    a = m["acessorios"]
    partes = []
    if "colar" in a:
        partes.append("".join(f'<circle cx="{130 + dx}" cy="{205 + dy}" r="5" fill="{c}"/>'
                              for dx, dy, c in ((-26, -2, "#e8c34a"), (-14, 8, "#c0392b"), (0, 12, "#e8c34a"),
                                                (14, 8, "#2a9d8f"), (26, -2, "#e8c34a"))))
    if "papagaio" in a:
        partes.append('<g transform="translate(206 196) scale(2)"><ellipse cx="0" cy="-10" rx="8" ry="12" fill="#2f9e44"/>'
                      '<circle cx="2" cy="-24" r="7" fill="#e63946"/><path d="M8 -25 q6 2 2 7 Z" fill="#ffd23f"/>'
                      '<circle cx="3" cy="-26" r="1.5" fill="#1a1a1a" stroke="none"/></g>')
    if "macaco" in a:
        partes.append('<g transform="translate(52 200) scale(1.9)"><ellipse cx="0" cy="0" rx="9" ry="11" fill="#8b5e34"/>'
                      '<circle cx="0" cy="-15" r="8" fill="#8b5e34"/><circle cx="0" cy="-14" r="5" fill="#e0b48a" stroke="none"/>'
                      '<circle cx="-2" cy="-15" r="1.2" fill="#1a1a1a" stroke="none"/><circle cx="2" cy="-15" r="1.2" fill="#1a1a1a" stroke="none"/></g>')
    if "gato" in a:
        partes.append('<g transform="translate(212 296) scale(1.6)"><ellipse cx="0" cy="-12" rx="11" ry="13" fill="#e2a55a"/>'
                      '<circle cx="0" cy="-30" r="9" fill="#e2a55a"/><path d="M-8 -36 l2 -9 l5 6 M8 -36 l-2 -9 l-5 6" fill="#e2a55a"/>'
                      '<circle cx="-3" cy="-31" r="1.4" fill="#1a1a1a" stroke="none"/><circle cx="3" cy="-31" r="1.4" fill="#1a1a1a" stroke="none"/></g>')
    return "".join(partes)


# ---------------------- CENÁRIOS DOS PORTOS ----------------------
# Paletas de cada estilo: céu (cima, baixo), água, terra, paredes, telhados, chão do cais
ESTILOS = {
    "lisboa":   {"ceu": ("#9fd3f5", "#fdf1d6"), "agua": "#4fa3b8", "terra": "#d8c08a", "paredes": ["#fbf6ea", "#f6d9a8", "#f2b8a0", "#fdf3c4"], "telhado": "#c1532e", "cais": "#a77b4f", "casas": "telha"},
    "algarve":  {"ceu": ("#8fd0f2", "#fff3d6"), "agua": "#3fa7b5", "terra": "#e2b36a", "paredes": ["#ffffff", "#fbf4e2"], "telhado": "#c45b32", "cais": "#c9a06a", "casas": "plano"},
    "londres":  {"ceu": ("#aab7c4", "#e6e2d8"), "agua": "#6f8a91", "terra": "#9aa77a", "paredes": ["#efe4cc", "#e2d4b4"], "telhado": "#4b4f5a", "cais": "#7d6a55", "casas": "enxaimel"},
    "flandres": {"ceu": ("#b9cfe0", "#f1ece0"), "agua": "#5f8f9c", "terra": "#a9b77c", "paredes": ["#b5523b", "#c2693f", "#9e4632"], "telhado": "#3f3f4a", "cais": "#8a7259", "casas": "empena"},
    "veneza":   {"ceu": ("#ffd1a1", "#fff0d8"), "agua": "#3d9aa3", "terra": "#e6c79a", "paredes": ["#e9a17c", "#f3d3a0", "#d98b6a", "#f6e4c2"], "telhado": "#b0482c", "cais": "#d8c3a0", "casas": "telha"},
    "grecia":   {"ceu": ("#8fd3ff", "#f2fbff"), "agua": "#2f8fb8", "terra": "#d9c7a0", "paredes": ["#ffffff", "#f6f2ea"], "telhado": "#ffffff", "cais": "#cdb58a", "casas": "cubo"},
    "madeira":  {"ceu": ("#9bd7f0", "#f4fbf2"), "agua": "#2f9bb0", "terra": "#4f9a4a", "paredes": ["#ffffff", "#fbf0d8"], "telhado": "#c1532e", "cais": "#8d7a62", "casas": "telha"},
    "caboverde": {"ceu": ("#7fd0f5", "#fff6dc"), "agua": "#22a6b8", "terra": "#c98b4f", "paredes": ["#fbe9c6", "#f6c58a", "#e9a76a"], "telhado": "#a14b2a", "cais": "#d7b98a", "casas": "plano"},
    "mina":     {"ceu": ("#8ad6f2", "#fff3d1"), "agua": "#2a9fae", "terra": "#d6a865", "paredes": ["#d8b48a"], "telhado": "#8a6a3a", "cais": "#e2c693", "casas": "cabana"},
    "congo":    {"ceu": ("#a9dbe9", "#fff0c9"), "agua": "#7a9a6c", "terra": "#9a7a42", "paredes": ["#c9a06a"], "telhado": "#a8843d", "cais": "#c9a26c", "casas": "cabana"},
    "suaili":   {"ceu": ("#7fd3ee", "#fff6de"), "agua": "#1fb0b5", "terra": "#e8d3a3", "paredes": ["#f8f1e2", "#efe2c6"], "telhado": "#efe2c6", "cais": "#e6d2a6", "casas": "plano"},
    "melinde":  {"ceu": ("#7fd3ee", "#fff2d4"), "agua": "#19aab3", "terra": "#e8d3a3", "paredes": ["#f8f1e2", "#efe2c6"], "telhado": "#efe2c6", "cais": "#e6d2a6", "casas": "plano"},
    "ormuz":    {"ceu": ("#f7c58f", "#fff1d6"), "agua": "#2e9fa8", "terra": "#e6c088", "paredes": ["#e9cf9f", "#dcb984"], "telhado": "#dcb984", "cais": "#d9b67e", "casas": "plano"},
    "calecute": {"ceu": ("#8fd8e8", "#fff3cf"), "agua": "#2a9a8f", "terra": "#7aa64e", "paredes": ["#e9c38a", "#d9a86a"], "telhado": "#9a6a2e", "cais": "#c8a06a", "casas": "telha"},
    "goa":      {"ceu": ("#8ed6ee", "#fff4d8"), "agua": "#2b9fa0", "terra": "#7fb05a", "paredes": ["#ffffff", "#f6e7b8", "#f2c4a0"], "telhado": "#c1532e", "cais": "#c9a26c", "casas": "telha"},
    "malaca":   {"ceu": ("#9bdde0", "#fdf6d8"), "agua": "#2a9a8c", "terra": "#5f9a4a", "paredes": ["#c9a06a", "#b58b55"], "telhado": "#8a6a3a", "cais": "#b9915e", "casas": "palafita"},
    "ternate":  {"ceu": ("#a4dcd2", "#fdf3d8"), "agua": "#1e9f96", "terra": "#3f8a45", "paredes": ["#c9a06a"], "telhado": "#8a6a3a", "cais": "#b9915e", "casas": "palafita"},
    "piratas":  {"ceu": ("#e9b88a", "#f6e2c2"), "agua": "#2c7f8a", "terra": "#8a7a6a", "paredes": ["#c9a06a"], "telhado": "#7a5a3a", "cais": "#9a7a52", "casas": "tenda"},
}


def casario(rng, estilo, x0, x1, base):
    """Fila de casas no fundo da cena, com tamanhos e cores sorteados (sempre iguais para o mesmo porto)."""
    e = ESTILOS[estilo]
    tipo = e["casas"]
    partes = []
    x = x0
    while x < x1:
        larg = rng.randint(42, 70)
        alt = rng.randint(40, 92)
        parede = rng.choice(e["paredes"])
        topo = base - alt
        if tipo in ("telha", "enxaimel"):
            partes.append(f'<rect x="{x}" y="{topo}" width="{larg}" height="{alt}" fill="{parede}"/>'
                          f'<path d="M{x - 4} {topo} L{x + larg / 2} {topo - larg * (.55 if tipo == "enxaimel" else .35)} L{x + larg + 4} {topo} Z" fill="{e["telhado"]}"/>')
            if tipo == "enxaimel":
                partes.append(f'<path d="M{x} {topo + alt * .45} H{x + larg} M{x + larg / 2} {topo} V{base} M{x} {topo} L{x + larg / 2} {topo + alt * .45}" '
                              'fill="none" stroke="#4a3324" stroke-width="3"/>')
        elif tipo == "empena":       # casas flamengas com empena em degraus
            d = larg / 6
            partes.append(f'<path d="M{x} {base} V{topo} h{d} v-{d} h{d} v-{d} h{d * 2} v{d} h{d} v{d} h{d} V{base} Z" fill="{parede}"/>')
        elif tipo == "plano":
            partes.append(f'<rect x="{x}" y="{topo}" width="{larg}" height="{alt}" fill="{parede}"/>'
                          f'<path d="M{x - 3} {topo} H{x + larg + 3}" stroke-width="4"/>')
        elif tipo == "cubo":
            partes.append(f'<rect x="{x}" y="{topo + 10}" width="{larg}" height="{alt - 10}" fill="{parede}"/>')
            if rng.random() < .3:
                partes.append(f'<path d="M{x + 8} {topo + 10} Q{x + larg / 2} {topo - 14} {x + larg - 8} {topo + 10} Z" fill="#2f6fb5"/>')
        elif tipo == "cabana":
            partes.append(f'<rect x="{x + 6}" y="{base - 34}" width="{larg - 12}" height="34" fill="{parede}"/>'
                          f'<path d="M{x - 4} {base - 30} Q{x + larg / 2} {base - 80} {x + larg + 4} {base - 30} Z" fill="{e["telhado"]}"/>')
            alt = 60
        elif tipo == "palafita":
            partes.append(f'<path d="M{x + 8} {base} V{base - 26} M{x + larg - 8} {base} V{base - 26}" stroke-width="4"/>'
                          f'<rect x="{x}" y="{base - 60}" width="{larg}" height="34" fill="{parede}"/>'
                          f'<path d="M{x - 8} {base - 58} L{x + larg / 2} {base - 96} L{x + larg + 8} {base - 58} Z" fill="{e["telhado"]}"/>')
        elif tipo == "tenda":
            partes.append(f'<path d="M{x} {base} L{x + larg / 2} {base - 60} L{x + larg} {base} Z" fill="{rng.choice(["#c9a06a", "#b5523b", "#7a8a5a"])}"/>'
                          f'<path d="M{x + larg / 2} {base} L{x + larg / 2} {base - 60}" fill="none"/>')
        if tipo not in ("cabana", "tenda", "palafita"):        # janelas e portas
            for jy in range(int(topo) + 12, int(base) - 20, 26):
                partes.append(f'<rect x="{x + larg * .2:.0f}" y="{jy}" width="9" height="12" fill="#5b4636" stroke="none"/>'
                              f'<rect x="{x + larg * .62:.0f}" y="{jy}" width="9" height="12" fill="#5b4636" stroke="none"/>')
        x += larg + rng.randint(-4, 6)
    return "".join(partes)


def marco(estilo):
    """O edifício ou a paisagem que distingue cada porto."""
    if estilo == "lisboa":       # castelo no alto e a Torre de Belém junto ao rio
        return ('<path d="M120 170 h120 v-30 h12 v-12 h-12 h96 v12 h-12 v30" fill="none"/>'
                '<path d="M80 200 Q200 120 380 190 Z" fill="#d8c08a"/><rect x="150" y="128" width="140" height="44" fill="#e8dcc0"/>'
                '<path d="M150 128 v-10 h14 v10 h14 v-10 h14 v10 h14 v-10 h14 v10 h14 v-10 h14 v10 h14 v-10 h14 v10 h14 v-10 h0" fill="#e8dcc0"/>'
                '<g class="torre"><rect x="700" y="210" width="50" height="100" fill="#f1e8d2"/>'
                '<rect x="712" y="160" width="26" height="52" fill="#f1e8d2"/><path d="M708 160 h34 l-6 -14 h-22 Z" fill="#e2d2ae"/>'
                '<path d="M700 210 h50 M716 228 h8 v14 h-8 Z M730 228 h8 v14 h-8 Z" fill="#5b4636"/></g>')
    if estilo == "algarve":
        return ('<path d="M0 260 Q60 200 140 230 L180 300 L0 300 Z" fill="#d79a4f"/>'
                '<path d="M600 250 Q660 200 760 220 L760 300 L600 300 Z" fill="#d79a4f"/>'
                '<rect x="640" y="186" width="70" height="40" fill="#efe2c6"/><path d="M640 186 v-10 h10 v10 h10 v-10 h10 v10 h10 v-10 h10 v10 h10 v-10 h10 v10" fill="#efe2c6"/>')
    if estilo == "londres":     # a Torre de Londres
        return ('<rect x="560" y="150" width="120" height="120" fill="#d9d0bd"/>'
                '<rect x="550" y="120" width="26" height="60" fill="#d9d0bd"/><rect x="664" y="120" width="26" height="60" fill="#d9d0bd"/>'
                '<path d="M550 120 q13 -18 26 0 M664 120 q13 -18 26 0" fill="#9aa1ad"/>'
                '<path d="M590 200 h16 v24 h-16 Z M634 200 h16 v24 h-16 Z" fill="#5b4636"/>')
    if estilo == "flandres":    # torre da catedral e a grua de madeira do porto
        return ('<rect x="560" y="120" width="44" height="160" fill="#c9b79a"/><path d="M556 120 L582 30 L608 120 Z" fill="#c9b79a"/>'
                '<path d="M575 150 h14 v26 h-14 Z" fill="#5b4636"/>'
                '<path d="M660 300 V180 L740 160" fill="none" stroke-width="6"/><circle cx="660" cy="250" r="28" fill="none" stroke-width="5"/>'
                '<path d="M740 160 V230" fill="none"/><rect x="730" y="230" width="20" height="16" fill="#a77b4f"/>')
    if estilo == "veneza":      # campanário e cúpulas de São Marcos
        return ('<rect x="520" y="70" width="40" height="210" fill="#c96f4a"/><path d="M516 70 L540 20 L564 70 Z" fill="#7aa58a"/>'
                '<rect x="526" y="80" width="28" height="22" fill="#f3e2c2"/>'
                '<path d="M590 280 V180 h150 V280" fill="#f3e2c2"/>'
                '<path d="M600 180 q20 -40 40 0 M650 180 q22 -50 44 0 M700 180 q18 -36 36 0" fill="#9cb8a4"/>'
                '<path d="M600 280 v-50 q14 -20 28 0 v50 M640 280 v-50 q14 -20 28 0 v50 M680 280 v-50 q14 -20 28 0 v50" fill="#e0c79a"/>')
    if estilo == "grecia":      # a colina com o Pártenon
        return ('<path d="M420 280 Q520 130 700 160 Q780 180 820 280 Z" fill="#cdb98f"/>'
                '<rect x="540" y="150" width="130" height="10" fill="#f2ecdd"/><path d="M536 150 L605 126 L674 150 Z" fill="#f2ecdd"/>'
                + "".join(f'<rect x="{x}" y="160" width="9" height="40" fill="#f2ecdd"/>' for x in range(546, 666, 17)) +
                '<rect x="538" y="200" width="134" height="8" fill="#f2ecdd"/>')
    if estilo == "madeira":     # montanhas verdes com socalcos
        return ('<path d="M0 260 Q120 60 260 180 Q340 90 460 200 Q560 70 760 230 L760 300 L0 300 Z" fill="#5fae5a"/>'
                '<path d="M60 230 Q140 210 220 230 M300 210 Q380 190 440 214 M520 200 Q600 180 700 214" fill="none" stroke="#3f7d3a"/>'
                '<rect x="330" y="214" width="34" height="50" fill="#ffffff"/><path d="M330 214 L347 180 L364 214 Z" fill="#ffffff"/>')
    if estilo == "caboverde":
        return ('<path d="M0 250 Q100 150 220 230 Q330 140 470 240 Q600 170 760 250 L760 300 L0 300 Z" fill="#b97a44"/>'
                + palmeira(120, 290, .8) + palmeira(620, 292, .9))
    if estilo == "mina":        # o castelo branco de São Jorge da Mina
        return ('<rect x="430" y="170" width="260" height="110" fill="#f6f1e4"/>'
                '<path d="M430 170 v-12 h16 v12 h16 v-12 h16 v12 h16 v-12 h16 v12 h16 v-12 h16 v12 h16 v-12 h16 v12 h16 v-12 h16 v12 h16 v-12 h16 v12 h16 v-12 h16 v12" fill="#f6f1e4"/>'
                '<rect x="520" y="120" width="60" height="60" fill="#f6f1e4"/><path d="M546 120 V96" fill="none"/><path d="M546 96 l22 6 l-22 6 Z" fill="#c0392b"/>'
                '<path d="M470 210 h14 v22 h-14 Z M640 210 h14 v22 h-14 Z" fill="#5b4636"/>'
                + palmeira(90, 290, .9) + palmeira(360, 292, .7))
    if estilo == "congo":       # palmeiras e o grande rio
        return palmeira(80, 290, 1.1) + palmeira(260, 292, .9) + palmeira(560, 290, 1) + palmeira(700, 292, .8)
    if estilo in ("suaili", "melinde"):   # mesquita de coral; em Melinde, o padrão de Vasco da Gama
        extra = ('<rect x="706" y="190" width="14" height="100" fill="#f1e8d2"/><rect x="698" y="182" width="30" height="12" fill="#f1e8d2"/>'
                 '<path d="M713 182 V162 M704 170 H722" fill="none" stroke-width="4" stroke="#c0392b"/>') if estilo == "melinde" else ""
        return ('<rect x="470" y="190" width="120" height="90" fill="#f8f1e2"/><path d="M490 190 q40 -60 80 0 Z" fill="#efe2c6"/>'
                '<rect x="600" y="120" width="22" height="160" fill="#f8f1e2"/><path d="M596 120 q15 -26 30 0 Z" fill="#efe2c6"/>'
                + palmeira(60, 290, .9) + palmeira(400, 292, .8) + extra)
    if estilo == "ormuz":       # fortaleza e torres de vento
        return ('<path d="M0 270 Q200 230 400 260 Q600 220 760 260 L760 300 L0 300 Z" fill="#e2b877"/>'
                '<rect x="440" y="150" width="240" height="130" fill="#d7b07a"/>'
                '<path d="M440 150 v-14 h20 v14 h20 v-14 h20 v14 h20 v-14 h20 v14 h20 v-14 h20 v14 h20 v-14 h20 v14 h20 v-14 h20 v14 h20 v-14 h20 v14" fill="#d7b07a"/>'
                '<rect x="140" y="160" width="26" height="70" fill="#e9cf9f"/><path d="M140 160 h26 v-10 h-26 Z M144 176 h6 v16 h-6 Z M156 176 h6 v16 h-6 Z" fill="#a98a5a"/>'
                '<path d="M520 150 q40 -60 80 0 Z" fill="#7fb6b8"/>')
    if estilo == "calecute":    # templo hindu (gopuram) entre palmeiras
        return ('<path d="M470 280 L490 110 L590 110 L610 280 Z" fill="#e2a65e"/>'
                + "".join(f'<path d="M{486 + i * 3} {250 - i * 30} H{594 - i * 3}" fill="none" stroke="#9a5a2e" stroke-width="3"/>' for i in range(5)) +
                '<path d="M500 110 q40 -30 80 0 Z" fill="#c76b3a"/><path d="M528 280 v-40 q12 -16 24 0 v40" fill="#5b4636"/>'
                + palmeira(70, 290, 1) + palmeira(360, 292, .9) + palmeira(680, 290, 1.05))
    if estilo == "goa":         # igreja branca e palmeiras
        return ('<rect x="470" y="150" width="140" height="130" fill="#ffffff"/>'
                '<rect x="460" y="110" width="34" height="170" fill="#ffffff"/><rect x="586" y="110" width="34" height="170" fill="#ffffff"/>'
                '<path d="M500 150 q40 -40 80 0 Z M470 112 q7 -12 14 0" fill="#ffffff"/><path d="M540 112 V86 M530 96 h20" fill="none" stroke-width="4"/>'
                '<path d="M526 280 v-46 q14 -18 28 0 v46" fill="#5b4636"/>'
                + palmeira(80, 290, 1) + palmeira(380, 292, .9) + palmeira(700, 290, 1.05))
    if estilo == "malaca":      # a fortaleza A Famosa e um junco chinês
        return ('<path d="M380 280 Q460 150 620 170 L700 280 Z" fill="#6fae5a"/>'
                '<rect x="470" y="140" width="120" height="70" fill="#e4dccb"/><rect x="510" y="96" width="40" height="50" fill="#e4dccb"/>'
                '<path d="M510 96 v-8 h10 v8 h10 v-8 h10 v8 h10 v-8" fill="#e4dccb"/>'
                + palmeira(70, 290, 1) + palmeira(300, 292, .8))
    if estilo == "ternate":     # o vulcão a fumegar e as árvores do cravinho
        return ('<path d="M260 280 L430 70 L470 70 L640 280 Z" fill="#5c7a4a"/><path d="M430 70 L470 70 L456 100 L444 96 Z" fill="#7a5a3a"/>'
                '<path class="fumo-vulcao" d="M450 66 q-20 -30 6 -50 q26 -20 4 -50" fill="none" stroke="#e8e2d8" stroke-width="16" opacity=".85"/>'
                + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#3f8a45"/>' for x, y, r in ((90, 240, 30), (150, 250, 24), (700, 244, 30), (640, 254, 22))))
    if estilo == "piratas":     # enseada rochosa e bandeira com caveira
        return ('<path d="M0 300 L0 120 Q80 60 160 140 Q200 100 260 170 L300 300 Z" fill="#7a6a5a"/>'
                '<path d="M560 300 Q600 120 720 90 Q760 120 760 300 Z" fill="#6a5a4a"/>'
                '<path d="M620 170 V110" fill="none" stroke-width="3"/><path d="M620 110 h40 v26 h-40 Z" fill="#1a1a1a"/>'
                '<circle cx="640" cy="121" r="6" fill="#f0f0f0" stroke="none"/>'
                + palmeira(330, 292, .9))
    return ""


def banca(x, toldo, produtos):
    """A banca do mercador: toldo às riscas, mesa e caixas com a mercadoria."""
    riscas = "".join(f'<path d="M{x - 70 + i * 28} 300 L{x - 58 + i * 28} 336 L{x - 44 + i * 28} 336 L{x - 56 + i * 28} 300 Z" fill="#fbf3dc" stroke="none"/>'
                     for i in range(5))
    caixas = "".join(f'<g transform="translate({x - 48 + i * 34} 408)"><rect x="-14" y="-18" width="28" height="22" fill="#c9965a"/>'
                     f'<text y="-1" font-size="16" text-anchor="middle" stroke="none">{PRODUTOS[p]["icone"]}</text></g>'
                     for i, p in enumerate(produtos[:3]))
    return (f'<path d="M{x - 66} 336 V430 M{x + 66} 336 V430" stroke-width="5" fill="none"/>'
            f'<path d="M{x - 76} 336 L{x - 70} 300 L{x + 70} 300 L{x + 76} 336 Z" fill="{toldo}"/>{riscas}'
            f'<path d="M{x - 76} 336 q19 12 38 0 q19 12 38 0 q19 12 38 0 q19 12 38 0" fill="{toldo}"/>'
            f'<rect x="{x - 72}" y="408" width="144" height="16" fill="#9a6b3b"/>{caixas}')


POSICOES_MERCADORES = {2: [150, 400], 3: [120, 320, 520], 4: [100, 270, 440, 610]}


def cena_porto(chave):
    """O cenário completo de um porto, com os mercadores e o navio CLICÁVEIS (links em SVG)."""
    porto = PORTOS[chave]
    e = ESTILOS[porto["estilo"]]
    rng = random.Random(chave)                  # gerador próprio: o mesmo porto é sempre igual
    camadas = [sol(880, 70, 30) if porto["estilo"] != "londres" else nuvem(860, 70, 1.6, "#d8dde3"),
               nuvem(rng.randint(80, 300), rng.randint(50, 90), 1.2), nuvem(rng.randint(420, 700), rng.randint(40, 80), .9),
               f'<path d="M0 230 Q250 {rng.randint(170, 210)} 500 225 T1000 220 L1000 310 L0 310 Z" fill="{e["terra"]}" stroke-opacity=".4"/>',
               marco(porto["estilo"]) if porto["estilo"] in ("madeira", "caboverde", "ormuz", "algarve", "grecia", "piratas", "ternate", "malaca") else "",
               casario(rng, porto["estilo"], 10, 760 if porto["estilo"] not in ("grecia", "ternate") else 420, 300),
               marco(porto["estilo"]) if porto["estilo"] not in ("madeira", "caboverde", "ormuz", "algarve", "grecia", "piratas", "ternate", "malaca") else "",
               # água com ondas animadas
               f'<rect x="-10" y="296" width="1020" height="240" fill="{e["agua"]}"/>',
               '<g class="ondas">' + "".join(f'<path d="M{x} {y} q12 -7 24 0 t24 0" fill="none" stroke="#ffffff" stroke-opacity=".6"/>'
                                             for x, y in ((40, 320), (300, 330), (560, 318), (800, 440), (880, 480), (930, 360), (760, 500))) + '</g>',
               caravela(rng.randint(250, 520), 330, .45, classe="barco-longe")]
    if chave == "lisboa":                       # o Paço Real: clicar para te apresentares ao Rei
        camadas.append('<a href="/rei" class="alvo" aria-label="Paço Real: apresentar-se ao Rei">'
                       '<rect x="380" y="196" width="170" height="100" fill="#f6efe0"/><path d="M372 196 L465 160 L558 196 Z" fill="#c1532e"/>'
                       '<path d="M465 160 V132" fill="none" stroke-width="3"/><path d="M465 132 l24 7 l-24 7 Z" fill="#2f5aa8" class="bandeira"/>'
                       + "".join(f'<path d="M{x} 222 h12 v20 h-12 Z" fill="#5b4636"/>' for x in range(396, 540, 30)) +
                       '<path d="M452 296 v-28 q13 -14 26 0 v28" fill="#7a4a2a"/>'
                       '<rect x="390" y="140" width="150" height="24" rx="12" fill="#fff8e6" class="etiqueta"/>'
                       '<text x="465" y="157" font-size="15" text-anchor="middle" fill="#3b2a1a" stroke="none" font-weight="700">👑 Paço Real</text></a>')
    # o cais (chão de madeira ou pedra) onde estão os mercadores
    camadas.append(f'<path d="M-10 400 L770 400 L790 540 L-10 540 Z" fill="{e["cais"]}"/>'
                   + "".join(f'<path d="M{x} 400 L{x + 6} 540" fill="none" stroke-opacity=".35"/>' for x in range(40, 770, 60))
                   + '<path d="M-10 400 H770" stroke-width="3"/>')
    # o navio: clicar para abrir o mapa e voltar a navegar
    camadas.append('<a href="/mapa" class="alvo" aria-label="O teu navio: voltar a navegar">'
                   + caravela(880, 420, 1.15) +
                   '<rect x="800" y="250" width="160" height="30" rx="15" fill="#fff8e6" class="etiqueta"/>'
                   '<text x="880" y="271" font-size="17" text-anchor="middle" fill="#3b2a1a" stroke="none" font-weight="700">⚓ Voltar a navegar</text></a>')
    mercadores = [m for m in MERCADORES if m["porto"] == chave]
    for m, x in zip(mercadores, POSICOES_MERCADORES[len(mercadores)]):
        camadas.append(f'<a href="/falar?m={m["id"]}" class="alvo mercador" aria-label="Falar com {html.escape(m["nome"])}">'
                       f'{banca(x, tom(m["roupa"], 1.1) if m["roupa"] != "#ffffff" else "#c9a06a", m["vende"])}'
                       f'<g transform="translate({x} 512)">{corpo(m)}</g>'
                       f'<rect x="{x - 82}" y="250" width="164" height="44" rx="14" fill="#fff8e6" class="etiqueta"/>'
                       f'<text x="{x}" y="270" font-size="15.5" text-anchor="middle" fill="#3b2a1a" stroke="none" font-weight="700">'
                       f'{html.escape(m["nome"])}</text>'
                       f'<text x="{x}" y="287" font-size="12" text-anchor="middle" fill="#6a4d33" stroke="none" font-style="italic">'
                       f'{html.escape(m["profissao"])}</text></a>')
    return svg(f"p{chave}", 1000, 520, e["ceu"][0], e["ceu"][1], "".join(camadas), "cena-svg",
               f"O porto de {porto['nome']}: {porto['texto']} Há mercadores no cais e o teu navio está atracado à direita.")


# ---------------------- O MAR (durante a viagem) ----------------------
CLIMAS = {
    "normal": ("#8fd3f5", "#e9f7ff", "#2f8fb0"), "tempestade": ("#3b4654", "#7c8794", "#2f4a5a"),
    "calmaria": ("#f6e7c8", "#fff8ea", "#7fb9c2"), "piratas": ("#9fc7dc", "#e6f1f5", "#2a7a94"),
    "ilha": ("#8fd8f0", "#f2fbff", "#22a0b8"), "golfinhos": ("#91d8f5", "#eef9ff", "#2393b8"),
    "monstro": ("#7f9aab", "#cfdde3", "#2b6f86"), "noite": ("#0f1c3a", "#3b4f7a", "#14324a"),
    "naufragio": ("#56606b", "#9aa3ab", "#2f4f5f"),
}


def cena_mar(clima):
    """O navio no meio do mar. O clima muda o céu, as ondas e o que aparece à volta."""
    cima, baixo, agua = CLIMAS[clima]
    partes = []
    if clima == "noite":
        partes.append('<circle cx="820" cy="80" r="34" fill="#f6f1d0" stroke="#d8d0a0"/>'
                      + "".join(f'<circle cx="{x}" cy="{y}" r="2" fill="#ffffff" stroke="none"/>'
                                for x, y in ((80, 50), (160, 110), (260, 40), (380, 90), (520, 30), (640, 120), (920, 160), (720, 40))))
    elif clima in ("tempestade", "naufragio"):
        partes.append(nuvem(200, 70, 2.4, "#4a5563") + nuvem(560, 50, 2.8, "#3f4a57") + nuvem(860, 80, 2.2, "#4a5563"))
        partes.append('<g class="chuva">' + "".join(f'<path d="M{x} {y} l-14 34" stroke="#c9d6e0" stroke-opacity=".6" fill="none"/>'
                                                   for x in range(20, 1000, 46) for y in (130, 210, 290)) + '</g>')
        if clima == "tempestade":
            partes.append('<path class="relampago" d="M640 90 L612 170 L640 166 L606 260 L676 150 L646 154 L672 90 Z" fill="#fff4a8" stroke="#e0c040"/>')
    else:
        partes.append(sol(840, 80, 32) + nuvem(180, 80, 1.3) + nuvem(520, 60, 1))
        partes.append('<path d="M300 120 q8 -8 16 0 q8 -8 16 0 M360 150 q6 -6 12 0 q6 -6 12 0" fill="none" stroke-width="2"/>')
    partes.append(f'<rect x="-10" y="250" width="1020" height="200" fill="{agua}"/>')
    if clima == "ilha":
        partes.append('<path d="M640 262 Q720 200 840 214 Q920 226 980 262 Z" fill="#e8d3a3"/>'
                      + palmeira(760, 232, .7) + palmeira(850, 236, .6))
    if clima == "piratas":
        partes.append(caravela(820, 290, .8, preta=True, classe="navio-pirata"))
    if clima == "monstro":
        partes.append('<path class="serpente" d="M640 300 q30 -70 60 0 q30 -60 60 0 q26 -50 52 0" fill="none" stroke="#3f7a5a" stroke-width="16"/>'
                      '<circle cx="636" cy="292" r="16" fill="#3f7a5a"/><circle cx="630" cy="286" r="3" fill="#fff4a8"/>')
    partes.append('<g class="ondas-mar">' + "".join(f'<path d="M{x} {y} q20 -12 40 0 t40 0 t40 0" fill="none" stroke="#ffffff" stroke-opacity=".55" stroke-width="2.5"/>'
                                                   for x, y in ((0, 280), (260, 300), (560, 274), (120, 340), (420, 360), (720, 330), (40, 400), (600, 410), (860, 380))) + '</g>')
    if clima == "golfinhos":
        partes.append('<g class="golfinho"><path d="M200 330 q40 -60 90 -10 q-30 -10 -50 10 l-14 10 Z" fill="#6c8ea3"/></g>'
                      '<g class="golfinho g2"><path d="M720 340 q40 -60 90 -10 q-30 -10 -50 10 l-14 10 Z" fill="#6c8ea3"/></g>')
    if clima == "naufragio":
        partes.append('<g transform="translate(500 330) rotate(18)"><path d="M-70 0 L70 0 Q62 26 30 30 L-38 30 Q-66 26 -70 0 Z" fill="#6b4a2a"/>'
                      '<path d="M-14 0 V-90" stroke-width="4"/><path d="M-44 -80 L16 -70 L10 -30 L-40 -40 Z" fill="#d8ccb0"/></g>'
                      '<rect x="300" y="380" width="40" height="10" fill="#8b5a2b" transform="rotate(-12 320 385)"/>'
                      '<circle cx="680" cy="400" r="12" fill="#8b5a2b"/>')
    else:
        partes.append(caravela(470, 300, 1.2, classe="navio-viagem"))
    descricoes = {"normal": "O teu navio navega em mar calmo.", "tempestade": "O navio enfrenta uma tempestade, com relâmpagos e chuva.",
                  "calmaria": "O mar está parado e as velas estão moles.", "piratas": "Um navio pirata de velas negras aproxima-se.",
                  "ilha": "Uma ilha com palmeiras aparece no horizonte.", "golfinhos": "Golfinhos saltam ao lado do navio.",
                  "monstro": "Uma forma de serpente gigante aparece nas ondas.", "noite": "O navio navega de noite, à luz da lua.",
                  "naufragio": "O navio está a afundar no meio da tempestade."}
    return svg(f"m{clima}", 1000, 450, cima, baixo, "".join(partes), f"mar-svg clima-{clima}", descricoes[clima])


# ---------------------- O PALÁCIO (cerimónia final) ----------------------
def cena_palacio():
    """A sala do trono do Paço Real, com o Rei D. Manuel I."""
    chao = "".join(f'<rect x="{x}" y="{y}" width="50" height="25" fill="{"#e9dcc0" if (x // 50 + y // 25) % 2 else "#b8946a"}" stroke="none"/>'
                   for x in range(0, 1000, 50) for y in (380, 405, 430, 455, 480, 505))
    estandarte = ('<path d="M0 0 h70 v120 l-35 -20 l-35 20 Z" fill="#b8202a"/>'
                  '<circle cx="35" cy="45" r="20" fill="none" stroke="#e8c34a" stroke-width="4"/>'
                  '<path d="M15 45 h40 M35 25 v40 M20 33 Q35 45 50 57" fill="none" stroke="#e8c34a" stroke-width="3"/>')
    rei = ('<path d="M440 380 Q430 270 470 250 L530 250 Q570 270 560 380 Z" fill="#b8202a"/>'
           '<path d="M450 380 Q446 300 470 262 L478 262 Q462 300 466 380 Z M550 380 Q554 300 530 262 L522 262 Q538 300 534 380 Z" fill="#f6f1e4"/>'
           '<path d="M470 262 L500 300 L530 262" fill="#e8c34a"/>'
           '<g transform="translate(500 212) scale(1.25)">'
           '<ellipse cx="0" cy="0" rx="26" ry="30" fill="#f2c9a5"/>'
           '<path d="M-22 6 Q-22 44 0 48 Q22 44 22 6 Q16 22 0 22 Q-16 22 -22 6 Z" fill="#8a5a3a"/>'
           '<circle cx="-9" cy="-2" r="3" fill="#1a1a1a" stroke="none"/><circle cx="9" cy="-2" r="3" fill="#1a1a1a" stroke="none"/>'
           '<path d="M-8 14 Q0 19 8 14" fill="none"/>'
           '<path d="M-26 -18 L-26 -40 L-14 -28 L0 -46 L14 -28 L26 -40 L26 -18 Z" fill="#e8c34a"/>'
           '<circle cx="0" cy="-28" r="3" fill="#c0392b"/></g>'
           '<path d="M556 300 l40 -80" stroke="#e8c34a" stroke-width="6" fill="none"/><circle cx="598" cy="216" r="10" fill="#e8c34a"/>')
    trono = ('<path d="M420 400 V200 Q500 140 580 200 V400 Z" fill="#7a3a1e"/><path d="M440 400 V214 Q500 168 560 214 V400 Z" fill="#9c2a2a"/>'
             '<rect x="400" y="380" width="200" height="30" fill="#7a3a1e"/>')
    conteudo = (chao + '<path d="M420 540 L460 380 L540 380 L580 540 Z" fill="#a8202a" stroke="none"/>'
                '<rect x="0" y="0" width="1000" height="380" fill="#efe2c6" stroke="none"/>'
                + "".join(f'<rect x="{x}" y="40" width="44" height="340" fill="#e2d2ae"/><rect x="{x - 8}" y="30" width="60" height="16" fill="#d6c299"/>'
                          for x in (60, 240, 716, 896)) +
                '<path d="M140 120 v120 h70 v-120 q-35 -40 -70 0 Z M790 120 v120 h70 v-120 q-35 -40 -70 0 Z" fill="#a9d6f0"/>'
                + f'<g transform="translate(300 60)">{estandarte}</g><g transform="translate(630 60)">{estandarte}</g>'
                + trono + rei)
    return svg("palacio", 1000, 540, "#efe2c6", "#e2cfa6", conteudo, "palacio-svg",
               "A sala do trono do Paço Real. O Rei D. Manuel I, de coroa e manto vermelho, está sentado no trono.")


# ---------------------- O MAPA ----------------------
def caminho_svg(pontos):
    """Lista de pontos (lon, lat) -> caminho SVG fechado."""
    return "M" + " L".join(f"{mx(lon)} {my(lat)}" for lon, lat in pontos) + " Z"


def mapa_base():
    """O mapa-múndi antigo (a parte que nunca muda): mar, terras, rosa dos ventos e monstros."""
    ondas = "".join(f'<path d="M{x} {y} q8 -5 16 0 t16 0" fill="none" stroke="#5a8f8a" stroke-opacity=".45" stroke-width="1.4"/>'
                    for x, y in ((60, 300), (120, 520), (230, 440), (330, 560), (520, 560), (640, 420), (700, 520), (820, 470),
                                 (900, 560), (200, 250), (470, 80), (950, 330), (860, 300), (580, 300)))
    terras = "".join(f'<path d="{caminho_svg(pts)}" fill="#ead6a6"/>' for pts in TERRAS.values())
    ilhas = "".join(f'<circle cx="{mx(lon)}" cy="{my(lat)}" r="3.2" fill="#ead6a6"/>' for lon, lat in ILHAS)
    rosa = ('<g transform="translate(905 520)" stroke-width="1.5"><circle r="44" fill="#f2e3bf"/><circle r="32" fill="none" stroke-opacity=".5"/>'
            '<path d="M0 -54 L8 -8 L0 0 L-8 -8 Z" fill="#a4262c"/><path d="M0 54 L8 8 L0 0 L-8 8 Z" fill="#6b4a2a"/>'
            '<path d="M-54 0 L-8 -8 L0 0 L-8 8 Z" fill="#6b4a2a"/><path d="M54 0 L8 -8 L0 0 L8 8 Z" fill="#6b4a2a"/>'
            '<text y="-58" font-size="14" text-anchor="middle" fill="#3b2a1a" stroke="none" font-family="Georgia, serif">N</text></g>')
    serpente = ('<g transform="translate(70 470)"><path d="M0 20 q20 -40 40 0 q20 -36 40 0 q18 -30 36 0" fill="none" stroke="#5f8f6a" stroke-width="10"/>'
                '<circle cx="-4" cy="16" r="10" fill="#5f8f6a"/><path d="M-12 12 l-10 -4" fill="none"/></g>')
    baleia = ('<g transform="translate(630 515)"><path d="M0 0 q30 -30 70 -10 q14 -16 20 -4 q-6 4 -12 12 q-30 30 -78 2 Z" fill="#7a9aaa"/>'
              '<path d="M30 -24 q-4 -14 4 -18 M34 -24 q6 -12 12 -10" fill="none"/><circle cx="14" cy="-6" r="2" fill="#1a1a1a" stroke="none"/></g>')
    nomes = ('<g font-family="Georgia, serif" font-style="italic" fill="#6b4a2a" stroke="none" text-anchor="middle">'
             '<text x="80" y="330" font-size="20">Mar Oceano</text><text x="620" y="380" font-size="22">Oceano Índico</text>'
             '<text x="240" y="580" font-size="16">Terra Incógnita</text><text x="370" y="170" font-size="13">Mar Mediterrâneo</text>'
             f'<text x="{mx(20)}" y="{my(10)}" font-size="18">ÁFRICA</text><text x="{mx(45)}" y="{my(48)}" font-size="18">EUROPA</text>'
             f'<text x="{mx(95)}" y="{my(28)}" font-size="18">ÁSIA</text><text x="{mx(116)}" y="{my(-10)}" font-size="13">Mares por descobrir</text></g>')
    return ('<rect width="1000" height="600" fill="#cfe2d6" stroke="none"/>' + ondas + terras + ilhas + nomes + rosa + serpente + baleia
            + '<rect x="6" y="6" width="988" height="588" fill="none" stroke-width="3"/><rect x="14" y="14" width="972" height="572" fill="none" stroke-width="1"/>')


def texto_pontos(pontos):
    """Lista de pontos (x, y) -> texto "x,y x,y ..." para uma <polyline>."""
    return " ".join(f"{x},{y}" for x, y in pontos)


def linha_rota(origem, destino, classe):
    """Uma rota desenhada no mapa, entre dois portos."""
    return f'<polyline class="{classe}" points="{rota(origem, destino)["texto"]}" fill="none"/>'


def pecas_do_porto(chave):
    """As peças do desenho de um porto no mapa: o ponto com o nome, a bandeira de 'já visitado' e o navio."""
    x, y = posicao(chave)
    esquerda = chave in ("lisboa", "londres", "goa", "calecute", "mina", "congo", "sofala")   # nome à esquerda do ponto
    texto = (f'<text x="{round(x - 9 if esquerda else x + 9, 1)}" y="{round(y + 4, 1)}" font-size="13" '
             f'text-anchor="{"end" if esquerda else "start"}" class="nome-porto" stroke="none">{html.escape(PORTOS[chave]["nome"])}</text>')
    return {"marca": f'<circle cx="{x}" cy="{y}" r="6"/>{texto}',
            "bandeira": f'<path d="M{x} {round(y - 6, 1)} V{round(y - 20, 1)} l9 3 l-9 3" fill="#a4262c" stroke-width="1.2"/>',
            "navio": f'<g class="navio-mapa">{caravela(x, round(y - 4, 1), .22)}</g>'}


def desenhar_mapa(jogo, destino=None, clicavel=True, nome_terra=None):
    """O mapa completo: a base + as rotas já feitas + os portos (clicáveis) + o navio."""
    partes = [MAPA_BASE]
    for a, b in zip(jogo.percurso, jogo.percurso[1:]):          # rotas já navegadas (a vermelho)
        if a != b:
            partes.append(linha_rota(a, b, "rota-feita"))
    if destino and destino != jogo.porto:                       # rota que se está a pensar fazer (tracejado azul)
        partes.append(linha_rota(jogo.porto, destino, "rota-nova"))
    for chave in jogo.portos_no_mapa():
        classes = ["porto"]
        if chave in jogo.visitados:
            classes.append("visitado")
        if chave == jogo.porto:
            classes.append("atual")
        if chave == destino:
            classes.append("escolhido")
        if PORTOS[chave].get("secreto"):
            classes.append("secreto")
        marca = PECAS_MAPA[chave]["marca"]
        if chave in jogo.visitados and chave != jogo.porto:
            marca += PECAS_MAPA[chave]["bandeira"]
        if clicavel and chave != jogo.porto:
            partes.append(f'<a href="/mapa?destino={chave}#info" class="{" ".join(classes)}" '
                          f'aria-label="{html.escape(PORTOS[chave]["nome"])}">{marca}</a>')
        else:
            partes.append(f'<g class="{" ".join(classes)}">{marca}</g>')
    if jogo.fase != "fim":                      # o teu navio, no porto onde estás
        partes.append(PECAS_MAPA[jogo.porto]["navio"])
    if nome_terra:                              # o Rei pôs o teu nome numa terra nova!
        partes.append(TERRA_NOVA[0] + html.escape(nome_terra) + TERRA_NOVA[1])
    return MOLDURA_MAPA[0] + "".join(partes) + MOLDURA_MAPA[1]


PECAS_MAPA = {chave: pecas_do_porto(chave) for chave in PORTOS}
for _r in ROTAS.values():
    _r["texto"] = texto_pontos(_r["pontos"])
TERRA_NOVA = (f'<text x="{mx(100)}" y="{my(-22)}" font-size="20" font-family="Georgia, serif" font-style="italic" '
              'fill="#a4262c" stroke="none" text-anchor="middle" class="terra-nova">Terra de ', '</text>')
# a "moldura" do mapa (céu, filtros e grão de papel), com um buraco no meio para o conteúdo
MOLDURA_MAPA = tuple(svg("mapa", 1000, 600, "#cfe2d6", "#cfe2d6", "§CONTEUDO§", "mapa-svg",
                         "Mapa-múndi antigo com os portos do comércio das especiarias. Clica num porto para veres a viagem.").split("§CONTEUDO§"))
MAPA_BASE = mapa_base()


# =====================================================================
# 6. PÁGINAS
# O paginas.html está dividido em BLOCOS (<!--@ nome -->): uns são páginas inteiras
# (inicio, porto, conversa, mapa...), outros são peças pequenas que se repetem
# (uma caixa do porão, uma linha de produto, uma escolha de um evento...).
# Estas funções escolhem os blocos e preenchem os campos $campo.
# =====================================================================
PASTA = Path(__file__).parent
FICHEIRO_HTML = PASTA / "paginas.html"
FICHEIRO_CSS = PASTA / "estilo.css"
TITULO = "Rota das Especiarias"

# Desenhos que nunca mudam: fazem-se uma vez quando o jogo arranca (assim as páginas abrem mais depressa)
CENAS_PORTOS = {}
CENAS_MAR = {}
RETRATOS = {}


def cena(chave):
    if chave not in CENAS_PORTOS:
        CENAS_PORTOS[chave] = cena_porto(chave)
    return CENAS_PORTOS[chave]


def mar(clima):
    if clima not in CENAS_MAR:
        CENAS_MAR[clima] = cena_mar(clima)
    return CENAS_MAR[clima]


def cara(mid, humor):
    if (mid, humor) not in RETRATOS:
        RETRATOS[(mid, humor)] = retrato(MERCADOR[mid], humor)
    return RETRATOS[(mid, humor)]


def carregar_blocos():
    """Lê o paginas.html e separa-o pelos marcadores. Devolve {nome do bloco: Template}.
    O ficheiro é lido em cada pedido: basta carregar em F5 depois de o alterares."""
    texto = FICHEIRO_HTML.read_text(encoding="utf-8")
    partes = re.split(r"<!--@ (\w+) -->", texto)
    return {partes[i]: Template(partes[i + 1].strip()) for i in range(1, len(partes), 2)}


def esc(texto):
    """Protege o texto antes de o pôr no HTML."""
    return html.escape(str(texto))


def montar(b, ecra, classe, **campos):
    """Mete a página 'ecra' dentro da página-base. 'classe' muda o fundo da página (CSS)."""
    return b["base"].substitute(titulo=TITULO, classe=classe, conteudo=b[ecra].substitute(campos))


def nome_produto(p):
    return PRODUTOS[p]["nome"]


def lista_carga(b, jogo):
    """As caixas do porão (cada produto com o seu ícone e quantidade)."""
    if not jogo.porao:
        return b["carga_vazia"].substitute()
    return "".join(b["carga_item"].substitute(icone=PRODUTOS[p]["icone"], nome=nome_produto(p), qtd=q,
                                              nota=b["nota_carga"].substitute(custo=jogo.custo_medio(p)) if jogo.custo_medio(p) else "")
                   for p, q in sorted(jogo.porao.items()))


def painel(b, jogo):
    """O painel do navio: data, tempo que falta, dinheiro, porão, estado do navio e encomendas."""
    encomendas = "".join(b["encomenda_item"].substitute(nome=esc(MERCADOR[mid]["nome"]), porto=PORTOS[MERCADOR[mid]["porto"]]["nome"],
                                                         qtd=e["qtd"], produto=nome_produto(e["produto"]).lower(),
                                                         icone=PRODUTOS[e["produto"]]["icone"])
                         for mid, e in jogo.encomendas.items())
    navio = "bom" if jogo.navio >= 60 else ("medio" if jogo.navio >= 30 else "mau")
    return b["painel"].substitute(
        data=data_do_dia(min(jogo.dia, DIAS_TOTAIS)), dias=jogo.dias_restantes(),
        tempo=round(min(jogo.dia, DIAS_TOTAIS) / DIAS_TOTAIS * 100),
        dinheiro=jogo.dinheiro, carga=jogo.carga_total(), capacidade=CAPACIDADE_PORAO,
        ocupado=round(jogo.carga_total() / CAPACIDADE_PORAO * 100), navio=jogo.navio, classe_navio=navio,
        lista_carga=lista_carga(b, jogo),
        encomendas=b["encomendas"].substitute(itens=encomendas) if encomendas else "")


def diario(b, jogo, ultimos=None):
    entradas = jogo.diario[-ultimos:] if ultimos else jogo.diario
    return "".join(b["diario_item"].substitute(data=data_do_dia(min(d, DIAS_TOTAIS)), texto=esc(t)) for d, t in reversed(entradas))


def pagina_inicio():
    b = carregar_blocos()
    return montar(b, "inicio", "ecra-inicio", cena=mar("normal"))


def pagina_como_jogar():
    b = carregar_blocos()
    return montar(b, "como_jogar", "ecra-papel", capacidade=CAPACIDADE_PORAO, amigo=AMIGO)


def pagina_carta(jogo):
    b = carregar_blocos()
    return montar(b, "carta", "ecra-carta", nome=esc(jogo.nome), data=data_do_dia(0), texto_inicial=esc(jogo.texto_inicial),
                  dinheiro=jogo.dinheiro, carga=lista_carga(b, jogo), capacidade=CAPACIDADE_PORAO)


def pagina_porto(jogo):
    b = carregar_blocos()
    porto = PORTOS[jogo.porto]
    chips = []
    for m in jogo.mercadores_aqui():
        a = jogo.amizade.get(m["id"], 0)
        estado = ""
        if m["id"] in jogo.zangados:
            estado = b["chip_zangado"].substitute()
        elif m["id"] in jogo.encomendas:
            estado = b["chip_encomenda"].substitute()
        chips.append(b["chip_mercador"].substitute(id=m["id"], nome=esc(m["nome"]), profissao=esc(m["profissao"]),
                                                   coracoes=coracoes(a), estado=estado,
                                                   amigo="amigo" if a >= AMIGO else ""))
    reparar = (b["reparar"].substitute(custo=(100 - jogo.navio) * CUSTO_REPARACAO, dias=DIAS_REPARACAO, navio=jogo.navio)
               if jogo.navio < 100 else b["reparar_ok"].substitute())
    return montar(b, "porto", f"ecra-porto estilo-{porto['estilo']}",
                  painel=painel(b, jogo), cena=cena(jogo.porto), nome=esc(porto["nome"]), regiao=esc(porto["regiao"]),
                  mensagem=b["mensagem"].substitute(texto=esc(jogo.mensagem)) if jogo.mensagem else "",
                  mercadores="".join(chips), reparar=reparar,
                  rei=b["botao_rei"].substitute() if jogo.porto == "lisboa" else "",
                  diario=diario(b, jogo, 6))


def nota_custo(b, jogo, produto, oferta):
    """A nota 'pagaste X por caixa': diz se vender ao preço do mercador dá lucro ou prejuízo."""
    custo = jogo.custo_medio(produto)
    if not custo:
        return b["nota_oferta"].substitute()
    diferenca = oferta - custo
    if diferenca > 0:
        return b["nota_lucro"].substitute(custo=custo, valor=diferenca)
    if diferenca < 0:
        return b["nota_prejuizo"].substitute(custo=custo, valor=-diferenca)
    return b["nota_empate"].substitute(custo=custo)


def coracoes(amizade):
    """Amizade em corações (0 a 5)."""
    cheios = min(5, amizade // 20)
    return "❤️" * cheios + "🤍" * (5 - cheios)


def pagina_conversa(jogo):
    b = carregar_blocos()
    c = jogo.conversa
    m = MERCADOR[c["m"]]
    a = jogo.amizade.get(m["id"], 0)
    conhecido = a > 0                          # a personalidade só se descobre depois do primeiro negócio
    personalidade = PERSONALIDADES[m["personalidade"]]["nome"] if conhecido else "???"
    if c["fechada"]:
        corpo = b["conversa_fechada"].substitute(nome=esc(m["nome"]))
    else:
        # o que ele compra: os produtos que procura e tudo o que eu tenho no porão
        linhas_compra = []
        for p in list(dict.fromkeys(m["quer"] + sorted(jogo.porao))):
            tenho = jogo.porao.get(p, 0)
            oferta = jogo.oferta(m["id"], p, True)
            precos = jogo.precos_niveis(m["id"], p, True)
            if tenho:
                acoes = b["acoes_vender"].substitute(produto=p, max=tenho, p0=precos[0], p1=precos[1], p2=precos[2])
            else:
                acoes = b["sem_produto"].substitute()
            linhas_compra.append(b["linha_produto"].substitute(
                icone=PRODUTOS[p]["icone"], nome=nome_produto(p), preco=oferta,
                etiqueta=b["etiqueta_procura"].substitute() if p in m["quer"] else b["etiqueta_outro"].substitute(),
                info=f"Tens {tenho}" if tenho else "Não tens", acoes=acoes, nota=nota_custo(b, jogo, p, oferta) if tenho else ""))
        linhas_venda = []
        for p in m["vende"]:
            stock = jogo.stock[m["id"]].get(p, 0)
            oferta = jogo.oferta(m["id"], p, False)
            precos = jogo.precos_niveis(m["id"], p, False)
            exame = c["examinados"].get(p)
            if exame == "falso":
                etiqueta = b["etiqueta_falso"].substitute()
            elif exame == "bom":
                etiqueta = b["etiqueta_bom"].substitute()
            else:
                etiqueta = b["botao_examinar"].substitute(produto=p)
            maximo = min(stock, jogo.espaco_livre(), jogo.dinheiro // max(1, precos[2]))
            acoes = (b["acoes_comprar"].substitute(produto=p, max=maximo, sugerido=min(stock, jogo.espaco_livre(), jogo.dinheiro // precos[0]) or 1,
                                                   p0=precos[0], p1=precos[1], p2=precos[2])
                     if stock and maximo > 0 else b["sem_compra"].substitute(
                         motivo="Esgotado" if not stock else ("Porão cheio" if jogo.espaco_livre() <= 0 else "Sem dinheiro")))
            linhas_venda.append(b["linha_produto"].substitute(icone=PRODUTOS[p]["icone"], nome=nome_produto(p), preco=oferta,
                                                              etiqueta=etiqueta, info=f"Tem {stock}", acoes=acoes, nota=""))
        contra = ""
        if c["contra"]:
            p = c["contra"]
            contra = b["contraproposta"].substitute(
                texto=esc(f"{'Comprar-te' if p['acao'] == 'vender' else 'Vender-te'} {p['qtd']} caixas de "
                          f"{nome_produto(p['produto']).lower()} a {p['preco']} cruzados cada ({p['qtd'] * p['preco']} no total)."))
        entrega = ""
        pedido = jogo.encomendas.get(m["id"])
        if pedido:
            tem = jogo.verdadeiras(pedido["produto"]) >= pedido["qtd"]
            entrega = b["encomenda_conversa"].substitute(
                qtd=pedido["qtd"], produto=nome_produto(pedido["produto"]).lower(), icone=PRODUTOS[pedido["produto"]]["icone"],
                botao=b["botao_entregar"].substitute(valor=2 * pedido["qtd"] * jogo.preco(pedido["produto"])) if tem
                else b["falta_encomenda"].substitute())
        corpo = b["conversa_negocio"].substitute(compra="".join(linhas_compra), venda="".join(linhas_venda),
                                                 contra=contra, entrega=entrega, nome=esc(m["nome"]))
    return montar(b, "conversa", f"ecra-conversa estilo-{PORTOS[jogo.porto]['estilo']}",
                  painel=painel(b, jogo), retrato=cara(m["id"], c["humor"]), nome=esc(m["nome"]), personalidade=personalidade,
                  profissao=esc(m["profissao"]), terra=esc(m["terra"]), idade=m["idade"], historia=esc(m["historia"]),
                  coracoes=coracoes(a), paciencia="⏳" * max(0, c["paciencia"]) or "💢",
                  fala=esc(c["fala"]), extra=b["fala_extra"].substitute(texto=esc(c["extra"])) if c["extra"] else "",
                  mensagem=b["mensagem"].substitute(texto=esc(jogo.mensagem)) if jogo.mensagem else "",
                  corpo=corpo, porto=esc(PORTOS[jogo.porto]["nome"]), humor=c["humor"])


def pagina_mapa(jogo, destino=None):
    b = carregar_blocos()
    if destino not in jogo.portos_no_mapa() or destino == jogo.porto:
        destino = None
    if destino:
        r = rota(jogo.porto, destino)
        chegada = jogo.dia + r["dias"] + DIAS_NO_PORTO
        if chegada >= DIAS_TOTAIS:
            aviso = b["aviso_mapa"].substitute(texto="Atenção: vais chegar depois do fim do prazo! "
                                               + ("Chegar atrasado a Lisboa custa-te 25% da fortuna." if destino == "lisboa"
                                                  else "O prazo acaba no mar e perdes metade da fortuna."))
        elif destino != "lisboa" and chegada + rota(destino, "lisboa")["dias"] + DIAS_NO_PORTO > DIAS_TOTAIS:
            aviso = b["aviso_mapa"].substitute(texto="Cuidado: daí já não há tempo para voltar a Lisboa antes do fim do prazo!")
        else:
            aviso = ""
        p = PORTOS[destino]
        info = b["mapa_info"].substitute(
            nome=esc(p["nome"]), regiao=esc(p["regiao"]), texto=esc(p["texto"]), dias=r["dias"],
            chegada=data_do_dia(min(chegada, DIAS_TOTAIS + 400)), destino=destino, aviso=aviso,
            visitado="Já lá estiveste" if destino in jogo.visitados else "Porto novo!",
            produz=", ".join(f"{PRODUTOS[x]['icone']} {nome_produto(x)}" for x in p["produz"]) if destino in jogo.visitados else "Ainda não sabes",
            procura=", ".join(f"{PRODUTOS[x]['icone']} {nome_produto(x)}" for x in p["procura"]) if destino in jogo.visitados else "Ainda não sabes")
    else:
        info = b["mapa_info_vazio"].substitute(volta=rota(jogo.porto, "lisboa")["dias"] if jogo.porto != "lisboa" else 0)
    return montar(b, "mapa", "ecra-mapa", painel=painel(b, jogo), mapa=desenhar_mapa(jogo, destino), info=info,
                  porto=esc(PORTOS[jogo.porto]["nome"]))


def pagina_viagem(jogo):
    b = carregar_blocos()
    v = jogo.viagem
    evento = jogo.evento_atual()
    destino = PORTOS[v["destino"]]["nome"]
    if evento and not v["resultado"]:
        escolhas = "".join(b["escolha_evento"].substitute(indice=i, texto=esc(e["texto"])) for i, e in enumerate(evento["escolhas"]))
        bloco = b["evento"].substitute(icone=evento["icone"], titulo=esc(evento["titulo"]), texto=esc(evento["texto"]), escolhas=escolhas)
    else:
        bloco = b["resultado_viagem"].substitute(
            icone=evento["icone"] if evento else "🧭", titulo=esc(evento["titulo"]) if evento else "Boa viagem",
            texto=esc(v["resultado"]), destino=esc(destino),
            chegada=data_do_dia(min(jogo.dia + v["dias"] + DIAS_NO_PORTO, DIAS_TOTAIS + 400)), dias=v["dias"])
    return montar(b, "viagem", f"ecra-viagem clima-{v['clima']}", painel=painel(b, jogo), cena=mar(v["clima"]),
                  origem=esc(PORTOS[v["origem"]]["nome"]), destino=esc(destino), dias=v["dias"], bloco=bloco)


def pagina_rei(jogo):
    b = carregar_blocos()
    return montar(b, "rei_confirmar", "ecra-papel", painel=painel(b, jogo), dias=jogo.dias_restantes(),
                  data=data_do_dia(jogo.dia))


FRASES_TITULOS = {
    "Mercador Mais Rico do Reino": "Os teus cofres estão cheios! O Rei manda pôr as tuas armas por cima da porta da Casa da Índia.",
    "Grande Explorador": "Conheceste meio mundo! O Rei manda os cartógrafos porem o teu nome numa terra nova do mapa.",
    "Embaixador dos Sete Mares": "Fizeste amigos em todos os portos. O Rei quer que sejas o seu embaixador junto dos reis do Oriente.",
    "Lenda dos Descobrimentos": "Riqueza, coragem e amizade: és uma lenda! Os cronistas vão escrever sobre a tua viagem.",
    "Corsário do Rei": "O Rei finge que não sabe dos teus amigos piratas... e dá-te uma carta de corso. Ao serviço de Portugal! 🏴‍☠️",
    "Regressou com Histórias para Contar": "Não trouxeste grande fortuna, mas as tuas histórias vão animar as tabernas de Lisboa durante anos.",
}
MEDALHAS = [("fortuna", "💰", "Fortuna"), ("descoberta", "🗺️", "Descoberta"), ("amizades", "🤝", "Amizades")]
NIVEIS_MEDALHA = ["Sem medalha", "Bronze", "Prata", "Ouro"]


def pagina_fim(jogo):
    b = carregar_blocos()
    f = jogo.final
    valores = {"fortuna": f"{f['fortuna']} cruzados", "descoberta": f"{f['portos']} portos visitados",
               "amizades": f"{f['amigos']} amigos e {f['missoes']} encomendas"}
    medalhas = "".join(b["medalha"].substitute(classe=f"nivel-{f['medalhas'][k]}", icone=icone, nome=nome, valor=valores[k],
                                               nivel=NIVEIS_MEDALHA[f["medalhas"][k]]) for k, icone, nome in MEDALHAS)
    aviso = ""
    if f["motivo"]:
        aviso = b["aviso_fim"].substitute(texto=esc(f"{f['motivo']} O Rei ficou desagradado: perdeste {jogo.ganho_penalizado} cruzados."))
    return montar(b, "fim", "ecra-fim", cena=cena_palacio(), nome=esc(jogo.nome), titulo=esc(f["titulo"]),
                  frase=esc(FRASES_TITULOS[f["titulo"]]), medalhas=medalhas, aviso=aviso, pontos=f["pontos"],
                  mapa=desenhar_mapa(jogo, clicavel=False, nome_terra=jogo.nome if f["titulo"] == "Grande Explorador" else None),
                  diario=diario(b, jogo), viagens=len(jogo.percurso) - 1, data=data_do_dia(min(jogo.dia, DIAS_TOTAIS)))


def pagina_derrota(jogo):
    b = carregar_blocos()
    naufragio = jogo.final["motivo"] == "naufragio"
    return montar(b, "derrota", "ecra-derrota", cena=mar("naufragio" if naufragio else "calmaria"),
                  titulo="O mar levou tudo..." if naufragio else "Falido!",
                  texto=("O navio afundou e ninguém apareceu para te salvar. Os teus amigos ficaram longe... "
                         "Da próxima vez, cuida do navio e faz mais amizades pelos portos!") if naufragio else
                  ("Ficaste sem dinheiro e sem mercadoria para vender. Nenhum mercador te fia nem um saco de pimenta. "
                   "Da próxima vez, guarda sempre umas moedas de reserva!"),
                  diario=diario(b, jogo), nome=esc(jogo.nome))


def pagina_moldura():
    """A 'moldura': a página que nunca muda, com a música de fundo e o jogo lá dentro (num <iframe>).
    Como o jogo muda de página a cada clique, a música tem de estar FORA do jogo para não recomeçar."""
    b = carregar_blocos()
    return b["moldura"].substitute(titulo=TITULO, barra=b["barra_musica"].substitute(fonte="/musica.wav"))


def pagina_do_jogo(jogo, caminho, consulta):
    """Escolhe a página certa conforme a fase do jogo."""
    if jogo.fase == "carta":
        return pagina_carta(jogo)
    if jogo.fase == "fim":
        return pagina_fim(jogo)
    if jogo.fase == "derrota":
        return pagina_derrota(jogo)
    if jogo.fase == "viagem":
        return pagina_viagem(jogo)
    if caminho == "/mapa" and jogo.fase == "porto":
        return pagina_mapa(jogo, consulta.get("destino", [None])[0])
    if caminho == "/rei" and jogo.fase == "porto" and jogo.porto == "lisboa":
        return pagina_rei(jogo)
    if jogo.fase == "conversa":
        return pagina_conversa(jogo)
    return pagina_porto(jogo)


# =====================================================================
# 7b. MÚSICA DE FUNDO
# Não há ficheiros de som: o PYTHON gera a música, amostra a amostra, e cria um ficheiro .wav
# em memória. A melodia é original, ao estilo do século XVI (modo dórico, compasso 6/8), com:
#   - uma corda dedilhada (alaúde), feita com o algoritmo Karplus-Strong: um ruído curto que
#     se repete e vai sendo "amaciado" soa como uma corda a vibrar;
#   - um bordão grave e contínuo, como o de uma gaita de foles;
#   - um pandeiro (ruído que se apaga depressa) a marcar o ritmo;
#   - na segunda volta, uma flauta (onda suave com vibrato) junta-se à melodia.
# =====================================================================
TAXA_SOM = 16000                # amostras por segundo
COLCHEIA = 0.2                  # duração de uma colcheia, em segundos
NOTAS = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}   # semitons a partir de Lá

# Melodia: (nota, duração em colcheias). Cada compasso tem 6 colcheias.
MELODIA = [
    ("D4", 2), ("F4", 1), ("A4", 2), ("G4", 1),   ("F4", 2), ("E4", 1), ("D4", 3),
    ("C4", 2), ("D4", 1), ("E4", 2), ("F4", 1),   ("E4", 3), ("A3", 3),
    ("D4", 2), ("F4", 1), ("A4", 2), ("C5", 1),   ("B4", 2), ("A4", 1), ("G4", 3),
    ("F4", 2), ("G4", 1), ("A4", 1), ("G4", 1), ("F4", 1),   ("E4", 3), ("D4", 3),
    ("A4", 2), ("C5", 1), ("D5", 2), ("C5", 1),   ("A4", 2), ("G4", 1), ("A4", 3),
    ("F4", 2), ("G4", 1), ("A4", 2), ("F4", 1),   ("G4", 3), ("E4", 3),
    ("A4", 2), ("C5", 1), ("D5", 2), ("E5", 1),   ("D5", 2), ("C5", 1), ("A4", 3),
    ("G4", 1), ("F4", 1), ("E4", 1), ("F4", 1), ("E4", 1), ("C4", 1),   ("D4", 6),
]
BAIXOS = ["D3", "D3", "C3", "A2", "D3", "G2", "F2", "D3", "D3", "A2", "F2", "C3", "D3", "A2", "C3", "D3"]   # um por compasso


def frequencia(nota):
    """'A4' -> 440 Hz. Cada oitava dobra a frequência; cada semitom multiplica por 2^(1/12)."""
    semitons = NOTAS[nota[0]] + 12 * (int(nota[1]) - 4)
    return 440 * 2 ** (semitons / 12)


def corda(som, inicio, freq, duracao, volume, rng):
    """Karplus-Strong: uma corda dedilhada, misturada na lista 'som' a partir da amostra 'inicio'."""
    periodo = max(2, int(TAXA_SOM / freq))
    tabela = [rng.uniform(-1, 1) for _ in range(periodo)]       # o "dedilhar": um ruído curto
    for i in range(int(duracao * TAXA_SOM)):
        if inicio + i >= len(som):
            break
        j = i % periodo
        valor = tabela[j]
        tabela[j] = 0.497 * (valor + tabela[(j + 1) % periodo])  # média com o vizinho: o som amacia
        som[inicio + i] += valor * volume


def flauta(som, inicio, freq, duracao, volume):
    """Uma flauta suave: onda sinusoidal com vibrato, que entra e sai devagar."""
    n = int(duracao * TAXA_SOM)
    for i in range(n):
        if inicio + i >= len(som):
            break
        t = i / TAXA_SOM
        envelope = min(1, t / 0.05, (n - i) / (0.08 * TAXA_SOM))
        som[inicio + i] += math.sin(2 * math.pi * freq * t + 0.4 * math.sin(2 * math.pi * 5 * t)) * volume * envelope


def pandeiro(som, inicio, volume, rng, duracao=0.12):
    """Uma pancada de pandeiro: ruído que se apaga muito depressa."""
    for i in range(int(duracao * TAXA_SOM)):
        if inicio + i < len(som):
            som[inicio + i] += rng.uniform(-1, 1) * volume * math.exp(-i / (0.025 * TAXA_SOM))


def compor_musica():
    """Compõe a música (duas voltas da melodia) e devolve os bytes de um ficheiro .wav."""
    rng = random.Random(1515)                      # sempre a mesma música
    voltas = 2
    colcheias = sum(d for _, d in MELODIA)
    total = int(voltas * colcheias * COLCHEIA * TAXA_SOM)
    som = [0.0] * total
    passo = int(COLCHEIA * TAXA_SOM)               # amostras numa colcheia
    for volta in range(voltas):
        base = volta * colcheias * passo
        # bordão: Ré grave contínuo, com um ligeiro tremor (como a gaita de foles)
        for i in range(colcheias * passo):
            t = i / TAXA_SOM
            som[base + i] += 0.05 * math.sin(2 * math.pi * frequencia("D2") * t) * (0.85 + 0.15 * math.sin(2 * math.pi * 0.5 * t))
        # baixo dedilhado (no 1.º e no 4.º tempo de cada compasso) e pandeiro
        for compasso, nota in enumerate(BAIXOS):
            inicio = base + compasso * 6 * passo
            corda(som, inicio, frequencia(nota), 1.1, 0.32, rng)
            corda(som, inicio + 3 * passo, frequencia(nota) * 1.5, 0.9, 0.2, rng)   # a quinta da nota
            pandeiro(som, inicio, 0.16, rng)
            pandeiro(som, inicio + 3 * passo, 0.08, rng)
            pandeiro(som, inicio + 5 * passo, 0.05, rng)
        # melodia (e, na segunda volta, a flauta junta-se)
        posicao = base
        for nota, duracao in MELODIA:
            corda(som, posicao, frequencia(nota), duracao * COLCHEIA + 0.25, 0.45, rng)
            if volta == 1:
                flauta(som, posicao, frequencia(nota) * 2, duracao * COLCHEIA, 0.07)
            posicao += duracao * passo
    # normalizar (o som mais forte fica a 80% do máximo) e converter para números inteiros de 16 bits
    maior = max(abs(x) for x in som) or 1
    amostras = array.array("h", (int(x / maior * 0.8 * 32767) for x in som))
    ficheiro = io.BytesIO()
    with wave.open(ficheiro, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TAXA_SOM)
        w.writeframes(amostras.tobytes())
    return ficheiro.getvalue()


MUSICA = []                                     # a música só é composta uma vez (na primeira vez que é pedida)


def musica_wav():
    if not MUSICA:
        MUSICA.append(compor_musica())
    return MUSICA[0]


# =====================================================================
# 8. SERVIDOR WEB
# Os cliques nos desenhos são LINKS (GET) e os botões são FORMULÁRIOS (POST).
# Depois de cada formulário, o servidor manda o browser voltar à página do jogo.
# =====================================================================
PORTA = 8002
SESSOES = {}                                  # cookie -> Jogo
NOME_COOKIE = "sid_rota"
TAMANHO_MAXIMO_POST = 2_000


class Manipulador(BaseHTTPRequestHandler):

    def _jogo(self):
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        sid = cookie[NOME_COOKIE].value if NOME_COOKIE in cookie else None
        return sid, SESSOES.get(sid)

    def _responder(self, texto, tipo="text/html; charset=utf-8", codigo=200):
        corpo = texto.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def _responder_bytes(self, corpo, tipo):
        """Envia dados que não são texto (a música)."""
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _redirecionar(self, destino="/jogo", novo_sid=None):
        self.send_response(303)
        self.send_header("Location", destino)
        if novo_sid:
            self.send_header("Set-Cookie", f"{NOME_COOKIE}={novo_sid}; Path=/; HttpOnly; SameSite=Lax")
        self.end_headers()

    def do_GET(self):
        url = urlparse(self.path)
        consulta = parse_qs(url.query)
        try:
            if url.path == "/estilo.css":
                return self._responder(FICHEIRO_CSS.read_text(encoding="utf-8"), "text/css; charset=utf-8")
            if url.path == "/favicon.ico":
                self.send_response(204)
                return self.end_headers()
            if url.path == "/musica.wav":
                return self._responder_bytes(musica_wav(), "audio/wav")
            if url.path == "/":                          # a moldura (música + jogo lá dentro)
                return self._responder(pagina_moldura())
            if url.path == "/como-jogar":
                return self._responder(pagina_como_jogar())
            _, jogo = self._jogo()
            if jogo is None:
                return self._responder(pagina_inicio()) if url.path == "/jogo" else self._redirecionar()
            if url.path == "/falar":                     # clicar num mercador (link no desenho)
                jogo.mensagem = ""
                jogo.abrir_conversa(consulta.get("m", [""])[0])
                return self._redirecionar()
            if url.path not in ("/jogo", "/mapa", "/rei"):
                return self._responder("Página não encontrada.", codigo=404)
            self._responder(pagina_do_jogo(jogo, url.path, consulta))
        except Exception as erro:
            traceback.print_exc()
            self._responder(f"Erro no servidor: {esc(erro)}", codigo=500)

    def do_POST(self):
        try:
            tamanho = min(int(self.headers.get("Content-Length", 0) or 0), TAMANHO_MAXIMO_POST)
            campos = parse_qs(self.rfile.read(tamanho).decode("utf-8"))
            pedir = lambda nome: campos.get(nome, [""])[0].strip()
            numero = lambda nome: int(pedir(nome)) if pedir(nome).lstrip("-").isdigit() else 0
            sid, jogo = self._jogo()
            if self.path == "/comecar":
                nome = pedir("nome")[:24] or "Mercador"
                sid = secrets.token_hex(16)
                SESSOES[sid] = Jogo(nome)
                return self._redirecionar("/jogo", sid)
            if jogo is None:
                return self._redirecionar()
            destino = "/jogo"
            acao = self.path
            if acao not in ("/negociar", "/contraproposta", "/examinar", "/entregar"):
                jogo.mensagem = ""
            if acao == "/zarpar" and jogo.fase == "carta":          # sair da carta do Rei para o porto
                jogo.fase = "porto"
                jogo.mensagem = "Estás no porto de Lisboa. Clica nos mercadores para negociar, ou no navio para partir."
            elif acao == "/negociar":
                jogo.mensagem = ""
                jogo.negociar(pedir("acao"), pedir("produto"), max(1, numero("qtd")), numero("nivel"))
            elif acao == "/contraproposta":
                jogo.mensagem = ""
                jogo.responder_contraproposta(pedir("resposta") == "sim")
            elif acao == "/examinar":
                jogo.mensagem = ""
                jogo.examinar(pedir("produto"))
            elif acao == "/entregar":
                jogo.mensagem = ""
                jogo.entregar_encomenda()
            elif acao == "/sair":
                jogo.sair_conversa()
            elif acao == "/reparar":
                jogo.reparar()
            elif acao == "/navegar":
                jogo.navegar(pedir("destino"))
            elif acao == "/evento":
                jogo.escolher_no_evento(numero("escolha"))
            elif acao == "/desembarcar":
                jogo.desembarcar()
            elif acao == "/rei" and jogo.fase == "porto" and jogo.porto == "lisboa":
                jogo.terminar()
            elif acao == "/novo":
                SESSOES.pop(sid, None)
            self._redirecionar(destino)
        except Exception as erro:
            traceback.print_exc()
            self._responder(f"Erro no servidor: {esc(erro)}", codigo=500)

    def log_message(self, formato, *argumentos):
        """Não enche o terminal com uma linha por cada pedido."""


# =====================================================================
# 9. ARRANQUE
# =====================================================================
def main():
    for ficheiro in (FICHEIRO_HTML, FICHEIRO_CSS):
        if not ficheiro.exists():
            print(f"ERRO: não encontrei o ficheiro {ficheiro.name}. Põe o rota_especiarias.py, o paginas.html e o "
                  "estilo.css na mesma pasta (e confirma que os nomes estão exatamente assim, sem números como '(1)').")
            return
    try:
        servidor = ThreadingHTTPServer(("127.0.0.1", PORTA), Manipulador)
    except OSError:
        print(f"ERRO: a porta {PORTA} já está ocupada. O jogo já está aberto noutro terminal? "
              "Fecha-o (Ctrl+C) ou muda o número da PORTA no código.")
        return
    print("A preparar os desenhos e a compor a música...")
    for chave in PORTOS:                       # desenha já os portos, para as páginas abrirem depressa
        cena(chave)
    musica_wav()
    url = f"http://127.0.0.1:{PORTA}"
    print(f"Rota das Especiarias a correr em {url}  (Ctrl+C para parar)")
    webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor terminado.")


if __name__ == "__main__":
    main()

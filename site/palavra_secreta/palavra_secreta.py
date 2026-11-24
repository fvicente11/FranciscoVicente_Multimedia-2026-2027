# -*- coding: utf-8 -*-
"""
palavra_secreta.py - TODO o código Python do jogo "Palavra Secreta" (um Wordle em português, por temas).

COMO JOGAR
    1. Põe estes 3 ficheiros na MESMA pasta:
         palavra_secreta.py   (este ficheiro: toda a lógica em Python)
         paginas.html         (todo o HTML)
         estilo.css           (todo o CSS)
    2. Abre a pasta no Visual Studio Code e corre este ficheiro
       (botão "Run Python File" ou, no terminal: python palavra_secreta.py).
    3. O browser abre sozinho em http://127.0.0.1:8001
       (para parar o jogo, carrega em Ctrl+C no terminal).
    Não é preciso instalar nada: só usa a biblioteca standard do Python.
    Usa a porta 8001, por isso pode estar a correr ao mesmo tempo que o "Banco ou Falência" (8000).

COMO ESTÁ ORGANIZADO ESTE FICHEIRO
    1. Importações
    2. Constantes do jogo     (tentativas, pontos, cores do teclado...)
    3. Dados                  (os 6 TEMAS, cada um com 30 palavras, 2 pistas e 1 curiosidade)
    4. Regras do jogo         (comparar letras, classes Partida, Estatisticas e Sessao)
    5. Páginas                (preenche os blocos de HTML que estão no paginas.html)
    5b. Ilustrações           (desenha em SVG o cenário de cada tema)
    6. Servidor web           (recebe os cliques do browser e responde)
    7. Arranque               (função main)

REGRA IMPORTANTE DESTE PROJETO
    Aqui NÃO há HTML nem CSS: todos os pedaços de HTML (cada letra da grelha, cada tecla,
    cada pista...) são blocos do paginas.html, e este ficheiro só os preenche com dados.
    A única exceção são os desenhos SVG dos cenários (secção 5b).
"""

# =====================================================================
# 1. IMPORTAÇÕES (só bibliotecas que já vêm com o Python)
# =====================================================================
import html                                   # escapar texto antes de o pôr no HTML
import math                                   # senos e cossenos (para a juba do leão)
import random                                 # sortear palavras e temas
import re                                     # separar os blocos dentro do paginas.html
import secrets                                # gerar o identificador de sessão de cada jogador
import traceback                              # mostrar erros no terminal
import unicodedata                            # tirar acentos às letras (MAÇÃ -> MACA)
import webbrowser                             # abrir o browser sozinho
from dataclasses import dataclass, field      # classes curtas e claras
from http.cookies import SimpleCookie         # ler a cookie que identifica o jogador
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer   # o servidor web
from pathlib import Path                      # caminhos de ficheiros
from string import Template                   # preencher os campos ($campo) do HTML
from urllib.parse import parse_qs             # ler os dados dos formulários


# =====================================================================
# 2. CONSTANTES DO JOGO (mexe aqui para mudar a dificuldade)
# =====================================================================
TENTATIVAS = 6                                # número de tentativas por palavra
PONTOS_POR_TENTATIVA = {1: 100, 2: 85, 3: 70, 4: 55, 5: 40, 6: 25}   # pontos ao acertar à 1.ª, 2.ª, ...
CUSTO_PISTA = 15                              # pontos que cada pista tira
PONTOS_MINIMOS = 10                           # quem acerta ganha sempre pelo menos isto
PISTAS_POR_PALAVRA = 2                        # cada palavra tem 2 pistas
TAMANHO_MIN, TAMANHO_MAX = 4, 7               # tamanho das palavras (em letras)
LINHAS_TECLADO = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]   # teclado do ecrã

# Estado de cada letra depois de uma tentativa (é também o nome da classe CSS)
CERTA = "certa"        # verde: letra certa no sítio certo
EXISTE = "existe"      # amarelo: a letra existe, mas noutro sítio
FALHA = "falha"        # cinzento: a letra não existe na palavra
# Quando a mesma letra aparece em várias tentativas, o teclado mostra o "melhor" estado
FORCA_ESTADO = {FALHA: 1, EXISTE: 2, CERTA: 3}
NOMES_ESTADO = {CERTA: "certa", EXISTE: "noutro sítio", FALHA: "não existe"}   # para leitores de ecrã


# =====================================================================
# 3. DADOS: OS TEMAS E AS PALAVRAS
# Cada palavra tem: a palavra (bem escrita, com acentos), 2 pistas (a 1.ª mais vaga,
# a 2.ª mais fácil) e uma curiosidade que aparece no fim.
# Para acrescentares uma palavra, copia uma linha p(...) e muda o texto.
# =====================================================================
def p(palavra, pista1, pista2, curiosidade):
    """Cria o dicionário de uma palavra (só para a lista de baixo ficar mais curta)."""
    return {"palavra": palavra, "pistas": [pista1, pista2], "curiosidade": curiosidade}


TEMAS = {
    # ------------------------------------------------------------- ANIMAIS
    "animais": {
        "nome": "Animais", "icone": "🦒",
        "descricao": "Do gato de casa à baleia-azul.",
        "palavras": [
            p("GATO", "É um dos animais de estimação mais comuns.", "Mia e adora perseguir novelos de lã.",
              "Os gatos passam cerca de dois terços do dia a dormir: entre 12 e 16 horas!"),
            p("LOBO", "Vive e caça em grupo, chamado alcateia.", "Uiva e aparece no conto do Capuchinho Vermelho.",
              "O uivo de um lobo pode ouvir-se a cerca de 10 km. Em Portugal vive o lobo-ibérico, uma espécie protegida."),
            p("URSO", "É um mamífero grande que pode hibernar no inverno.", "Há o polar, o pardo e o de peluche.",
              "O urso-polar parece branco, mas a pele dele é preta e os pelos são transparentes e ocos."),
            p("LEÃO", "Vive na savana africana.", "É conhecido como o rei da selva e tem juba.",
              "O rugido de um leão pode ouvir-se a 8 km de distância."),
            p("ZEBRA", "É parente do cavalo e vive em África.", "É famosa pelas riscas pretas e brancas.",
              "Não há duas zebras iguais: o padrão das riscas é único, como uma impressão digital."),
            p("TIGRE", "É o maior felino do mundo.", "Tem pelo cor de laranja com riscas pretas.",
              "O tigre não tem riscas só no pelo: se o raparem, as riscas continuam na pele!"),
            p("PANDA", "Vive nas florestas de montanha da China.", "É preto e branco e come bambu.",
              "O panda-gigante pode passar 12 horas por dia a comer bambu."),
            p("POLVO", "Vive no mar e é muito inteligente.", "Tem oito braços cheios de ventosas.",
              "O polvo tem três corações e sangue azul."),
            p("LINCE", "É um felino selvagem com tufos de pelo nas orelhas.", "Na versão ibérica, também vive em Portugal.",
              "O lince-ibérico é um dos felinos mais ameaçados do mundo e só existe na Península Ibérica."),
            p("ÁGUIA", "É uma ave de rapina.", "É famosa pela visão apurada e voa muito alto.",
              "Uma águia consegue ver um coelho a mais de 3 km de distância."),
            p("COALA", "Vive na Austrália e passa a vida nas árvores.", "Parece um ursinho cinzento e come eucalipto.",
              "O coala dorme até 20 horas por dia: as folhas de eucalipto dão-lhe muito pouca energia."),
            p("CAVALO", "Foi durante séculos o principal meio de transporte.", "Relincha, galopa e usa ferraduras.",
              "Os cavalos conseguem dormir de pé, porque as pernas deles têm uma espécie de 'trinco'."),
            p("GIRAFA", "Vive na savana e come folhas das copas das árvores.", "É o animal mais alto do mundo.",
              "A língua da girafa mede cerca de 50 cm e é escura, para não se queimar com o sol."),
            p("COELHO", "Tem orelhas compridas e salta.", "Adora cenouras, segundo os desenhos animados.",
              "Os dentes do coelho nunca param de crescer: gastam-se a roer."),
            p("RAPOSA", "Tem uma cauda farta e é conhecida por ser esperta.", "É ruiva e aparece em muitas fábulas a enganar os outros.",
              "Os cientistas pensam que a raposa usa o campo magnético da Terra para saltar em cima das presas."),
            p("CAMELO", "Aguenta muitos dias sem beber no deserto.", "Tem duas bossas nas costas.",
              "As bossas do camelo não guardam água, mas sim gordura, que serve de reserva de energia."),
            p("BALEIA", "É um mamífero que vive no oceano.", "É o maior animal do planeta e solta jatos de água.",
              "A baleia-azul é o maior animal que alguma vez existiu: o coração dela pesa tanto como uma mota."),
            p("CORUJA", "É uma ave noturna.", "Tem olhos enormes e é símbolo da sabedoria.",
              "A coruja não consegue mexer os olhos, mas roda a cabeça cerca de 270 graus."),
            p("ABELHA", "É um inseto que vive numa colmeia.", "Faz mel e pode picar.",
              "As abelhas dançam para dizer às outras onde estão as flores: chama-se a 'dança do abanar'."),
            p("LONTRA", "É um mamífero que nada muito bem, em rios ou no mar.", "Às vezes usa pedras para partir conchas, deitada de costas.",
              "As lontras-marinhas dão as mãos enquanto dormem, para a corrente não as separar."),
            p("GORILA", "É o maior dos macacos.", "Vive nas florestas de África e bate no peito.",
              "Os gorilas partilham cerca de 98% do ADN connosco."),
            p("PINGUIM", "É uma ave, mas não voa.", "Vive sobretudo em zonas geladas e parece usar fraque.",
              "Quase todos os pinguins vivem no hemisfério sul: no Polo Norte não há nenhum."),
            p("TUBARÃO", "É um peixe muito antigo.", "Tem várias filas de dentes e uma barbatana nas costas.",
              "Os tubarões existem há mais de 400 milhões de anos: são mais antigos do que as árvores!"),
            p("FORMIGA", "É um inseto pequenino que vive em colónias.", "Trabalha sem parar e carrega comida para o formigueiro.",
              "Uma formiga consegue carregar entre 10 e 50 vezes o seu próprio peso."),
            p("CANGURU", "É um símbolo da Austrália.", "Anda aos saltos e transporta a cria numa bolsa.",
              "Quando nasce, o canguru bebé tem o tamanho de um feijão e vai viver para a bolsa da mãe."),
            p("CARACOL", "É muito lento.", "Leva a casa às costas e tem corninhos.",
              "O caracol tem milhares de dentes minúsculos numa espécie de língua, chamada rádula."),
            p("MORCEGO", "É um mamífero noturno.", "Voa e dorme de cabeça para baixo.",
              "O morcego é o único mamífero que voa a sério e orienta-se no escuro pelo eco dos sons que faz."),
            p("CISNE", "É uma ave aquática elegante.", "Tem um pescoço comprido e aparece num bailado famoso.",
              "Muitos casais de cisnes ficam juntos a vida inteira."),
            p("CHITA", "É um felino com manchas pretas.", "É o animal terrestre mais rápido.",
              "A chita pode passar dos 100 km/h, mas só aguenta essa velocidade durante alguns segundos."),
            p("ESQUILO", "Vive nas árvores e tem uma cauda peluda.", "Junta bolotas e nozes para o inverno.",
              "Os esquilos enterram nozes e esquecem-se de muitas: assim acabam por plantar árvores novas."),
        ],
    },
    # ------------------------------------------------------------- COMIDA
    "comida": {
        "nome": "Comida", "icone": "🍕",
        "descricao": "Pratos, frutas e petiscos.",
        "palavras": [
            p("PIZZA", "É um prato italiano famoso em todo o mundo.", "Massa redonda com molho de tomate e queijo, cozida no forno.",
              "Diz-se que a pizza margherita foi criada em Nápoles, em 1889, em homenagem à rainha Margarida: tem as cores da bandeira italiana."),
            p("ARROZ", "É um cereal que alimenta metade do mundo.", "Acompanha muitos pratos e pode ser de pato ou de marisco.",
              "Portugal é o país da Europa que mais arroz come por pessoa."),
            p("BOLO", "É muito comum em festas.", "Leva farinha, ovos e açúcar, e às vezes velas por cima.",
              "O bolo-rei chegou a Portugal no século XIX, inspirado numa receita francesa, pela Confeitaria Nacional, em Lisboa."),
            p("SOPA", "Come-se muitas vezes no início da refeição.", "Come-se à colher e pode ser de legumes.",
              "A palavra 'sopa' vem de uma palavra antiga que queria dizer 'pão molhado em caldo'."),
            p("QUEIJO", "É feito a partir do leite.", "Pode ser fresco ou curado, e há um famoso da Serra da Estrela.",
              "O queijo da Serra da Estrela é feito com leite de ovelha e coalha com flor de cardo."),
            p("BATATA", "Cresce debaixo da terra.", "Pode ser cozida, assada ou frita.",
              "A batata vem dos Andes, na América do Sul, e só chegou à Europa no século XVI."),
            p("TOMATE", "É vermelho e muito usado em saladas.", "É a base do ketchup.",
              "Para a botânica, o tomate é um fruto e não um legume, porque tem sementes."),
            p("BANANA", "É uma fruta tropical.", "É amarela e descasca-se à mão.",
              "Para a botânica, a banana é uma baga. Em Portugal, cresce na ilha da Madeira."),
            p("CENOURA", "É uma raiz que se come.", "É cor de laranja e dizem que faz bem à vista.",
              "As primeiras cenouras eram roxas ou amarelas: as cor de laranja tornaram-se populares nos Países Baixos, no século XVII."),
            p("LARANJA", "É um citrino.", "Tem o nome da sua própria cor e faz-se sumo com ela.",
              "Em grego, turco ou romeno, a laranja chama-se quase 'portugal', porque foram os portugueses que a trouxeram da Ásia."),
            p("MAÇÃ", "É uma fruta que pode ser vermelha, verde ou amarela.", "Na história da Branca de Neve, estava envenenada.",
              "A maçã flutua na água porque cerca de um quarto dela é ar."),
            p("LIMÃO", "É um citrino muito ácido.", "É amarelo e usa-se para fazer limonada.",
              "Os marinheiros levavam limões nas viagens longas para evitar o escorbuto, uma doença causada pela falta de vitamina C."),
            p("MANGA", "É uma fruta tropical de polpa cor de laranja.", "O nome é igual ao de uma parte da camisola.",
              "A manga é a fruta nacional da Índia, onde se cultiva há milhares de anos."),
            p("AZEITE", "É feito a partir de um fruto.", "Vem da azeitona e tempera a comida.",
              "Na Grécia Antiga, o azeite servia para iluminar candeeiros e para os atletas olímpicos untarem o corpo."),
            p("FEIJÃO", "É uma leguminosa.", "Pode ser preto, branco ou encarnado e é a base da feijoada.",
              "O feijão mais comum veio das Américas e é muito rico em proteínas."),
            p("CEBOLA", "É um bolbo usado para dar sabor aos cozinhados.", "Faz chorar quem a corta.",
              "A cebola faz chorar porque, ao ser cortada, liberta um gás que irrita os olhos."),
            p("ALHO", "Tem um cheiro forte e vem em dentes.", "Diz a lenda que afasta vampiros.",
              "Conta-se que os construtores das pirâmides do Egito comiam alho para terem mais força."),
            p("MILHO", "É um cereal com grãos amarelos.", "É com ele que se fazem as pipocas.",
              "O grão de milho rebenta e vira pipoca porque a água lá dentro se transforma em vapor quando aquece."),
            p("IOGURTE", "É um produto feito com leite.", "Come-se à colher e pode ser natural ou de aromas.",
              "O iogurte é feito por bactérias 'boas' que transformam o leite. A palavra vem do turco."),
            p("CAFÉ", "É uma bebida feita com grãos torrados.", "Em Lisboa pede-se uma bica.",
              "Conta a lenda que o café foi descoberto por um pastor da Etiópia, que viu as cabras muito agitadas depois de comerem os frutos."),
            p("BROA", "É um tipo de pão.", "É feita de milho e típica do norte de Portugal.",
              "A broa de Avintes, perto do Porto, é escura e coze lentamente no forno durante várias horas."),
            p("PASTEL", "É um doce ou salgado de massa.", "O mais famoso é de nata e vem de Belém.",
              "O pastel de nata nasceu no Mosteiro dos Jerónimos. A receita dos Pastéis de Belém é secreta desde 1837."),
            p("MORANGO", "É uma fruta vermelha da primavera.", "Tem sementes por fora e come-se com natas.",
              "As 'sementes' do morango são, na verdade, os verdadeiros frutos: cada morango tem cerca de 200."),
            p("ABACATE", "É um fruto verde por fora, com um caroço grande.", "É o ingrediente principal do guacamole.",
              "A palavra 'abacate' vem da língua dos astecas, que lhe chamavam 'ahuacatl'."),
            p("MASSA", "Faz-se com farinha e água (e às vezes ovos).", "Há esparguete, macarrão e lasanha.",
              "É um mito que Marco Polo trouxe a massa da China: em Itália já se comia massa antes da viagem dele."),
            p("AMEIXA", "É uma fruta com caroço.", "Também se come seca e há uma famosa de Elvas.",
              "A ameixa d'Elvas tem Denominação de Origem Protegida: só pode ter este nome se for feita nessa região."),
            p("PIMENTO", "É um legume que pode ser verde, amarelo ou vermelho.", "É oco por dentro e cheio de sementes.",
              "O pimento vermelho é um pimento verde que amadureceu, e tem mais vitamina C do que uma laranja."),
            p("COUVE", "É um legume de folhas verdes.", "É o ingrediente principal do caldo verde.",
              "O caldo verde nasceu no Minho e faz-se com couve-galega cortada em tiras muito finas."),
            p("GELADO", "É uma sobremesa muito fria.", "Come-se num cone ou num copo, sobretudo no verão.",
              "Conta-se que os imperadores romanos mandavam buscar neve às montanhas para a misturar com fruta e mel."),
            p("FIGO", "É uma fruta doce do fim do verão.", "Pode ser preto ou verde e também se come seco.",
              "O figo é, na verdade, uma flor virada para dentro, que é polinizada por pequenas vespas."),
        ],
    },
    # ------------------------------------------------------------- DESPORTO
    "desporto": {
        "nome": "Desporto", "icone": "⚽",
        "descricao": "Modalidades, estádios e campeões.",
        "palavras": [
            p("FUTEBOL", "É o desporto mais popular do mundo.", "Joga-se com os pés, onze contra onze.",
              "A seleção portuguesa ganhou o Euro 2016, em França, com um golo do Éder no prolongamento da final."),
            p("TÉNIS", "Joga-se num campo dividido por uma rede.", "Usa-se uma raquete e uma bola amarela.",
              "Wimbledon é o torneio de ténis mais antigo do mundo (1877) e os jogadores têm de se vestir de branco."),
            p("GOLFE", "Joga-se num campo enorme de relva.", "O objetivo é meter a bola num buraco com poucas tacadas.",
              "Em 1971, o astronauta Alan Shepard deu tacadas de golfe na Lua, na missão Apollo 14."),
            p("BOXE", "É um desporto de combate.", "Lutam dois atletas num ringue, com luvas.",
              "As luvas passaram a ser obrigatórias no boxe com as regras do Marquês de Queensberry, de 1867."),
            p("JUDO", "É uma arte marcial japonesa.", "Usa-se quimono e cinto, e o objetivo é derrubar o adversário.",
              "O judo foi criado no Japão em 1882 por Jigoro Kano. 'Judo' quer dizer 'caminho suave'."),
            p("SURF", "Pratica-se no mar.", "Desliza-se nas ondas em cima de uma prancha.",
              "Na Nazaré já foram surfadas algumas das maiores ondas do mundo, com mais de 20 metros de altura."),
            p("REMO", "Pratica-se num barco.", "Os atletas puxam umas pás compridas para avançar na água.",
              "No remo, os atletas avançam de costas para a meta: só a veem depois de a cruzarem!"),
            p("XADREZ", "É um desporto da mente.", "Tem rei, rainha, torres e peões num tabuleiro.",
              "Há mais jogos de xadrez possíveis do que átomos no universo observável."),
            p("RÂGUEBI", "A bola é oval.", "Para marcar ensaio, a bola tem de ser pousada atrás da linha.",
              "Diz a lenda que o râguebi nasceu em 1823, quando um aluno da escola de Rugby, em Inglaterra, pegou na bola com as mãos num jogo de futebol."),
            p("ANDEBOL", "Joga-se com as mãos, sete contra sete.", "A bola é lançada para uma baliza e não se pode entrar na área.",
              "No andebol, os jogadores de campo não podem tocar na bola com as pernas abaixo do joelho."),
            p("NATAÇÃO", "Pratica-se numa piscina.", "Há estilos como livre, costas, bruços e mariposa.",
              "O nadador Michael Phelps é o atleta com mais medalhas olímpicas de sempre: 28."),
            p("KARATÉ", "É uma arte marcial japonesa.", "Usa socos e pontapés, e os cintos têm cores.",
              "'Karaté' quer dizer 'mão vazia' em japonês, porque se luta sem armas. Nasceu na ilha de Okinawa."),
            p("ESGRIMA", "É um desporto de combate muito antigo.", "Luta-se com espada, florete ou sabre.",
              "A esgrima é um dos poucos desportos que esteve em todos os Jogos Olímpicos modernos, desde 1896."),
            p("HÓQUEI", "Joga-se com um stick.", "Em Portugal é muito famoso o de patins.",
              "Portugal é uma das seleções mais vitoriosas do hóquei em patins, com mais de 15 títulos mundiais."),
            p("CORRIDA", "É a forma mais simples de competir.", "Pode ser de 100 metros ou uma maratona.",
              "Usain Bolt correu os 100 metros em 9,58 segundos, em 2009. É o recorde mundial."),
            p("GOLO", "É o que todos os adeptos querem ver.", "Acontece quando a bola entra na baliza.",
              "Cristiano Ronaldo é o jogador com mais golos marcados por uma seleção nacional em toda a história."),
            p("BALIZA", "Há uma em cada ponta do campo.", "É defendida pelo guarda-redes.",
              "Uma baliza de futebol mede 7,32 metros de largura e 2,44 metros de altura."),
            p("ÁRBITRO", "Está em campo, mas não joga.", "Usa apito e mostra cartões.",
              "Os cartões amarelo e vermelho foram inventados pelo árbitro Ken Aston, inspirado nos semáforos, e estrearam no Mundial de 1970."),
            p("RAQUETE", "É um objeto usado em vários desportos.", "Tem cordas esticadas e usa-se no ténis.",
              "Antes de haver raquetes, o ténis jogava-se com a palma da mão: chamava-se 'jogo da palma'."),
            p("ESTÁDIO", "É um edifício enorme.", "É onde se jogam os grandes jogos, com bancadas cheias.",
              "'Estádio' vem do grego 'stadion', a distância (cerca de 190 m) da corrida mais antiga dos Jogos Olímpicos."),
            p("MEDALHA", "É o prémio dos melhores.", "Pode ser de ouro, prata ou bronze.",
              "As medalhas de 'ouro' olímpicas são feitas sobretudo de prata, com um banho de ouro por cima."),
            p("PÓDIO", "É onde sobem os vencedores.", "Tem três degraus: o mais alto é para o primeiro.",
              "O pódio de três degraus começou a ser usado nos Jogos Olímpicos de 1932."),
            p("TAÇA", "É um troféu.", "O capitão levanta-a quando a equipa ganha.",
              "A Taça do Mundo de futebol é de ouro maciço e pesa cerca de 6 kg."),
            p("DARDO", "É uma prova de lançamento do atletismo.", "É uma espécie de lança que se atira o mais longe possível.",
              "O recorde mundial do lançamento do dardo é de 98,48 metros, de Jan Železný, desde 1996."),
            p("SKATE", "Pratica-se na rua ou num parque.", "É uma prancha com quatro rodas.",
              "O skate foi inventado por surfistas da Califórnia para 'surfar' na rua e estreou nos Jogos Olímpicos de Tóquio 2020."),
            p("ESQUI", "Pratica-se na neve.", "Desliza-se montanha abaixo com duas pranchas compridas.",
              "Os esquis foram inventados há milhares de anos, para caçar e viajar na neve."),
            p("TRIATLO", "É uma prova muito exigente.", "Junta natação, ciclismo e corrida.",
              "No triatlo Ironman nada-se 3,8 km, pedala-se 180 km e corre-se uma maratona (42,2 km), tudo seguido."),
            p("CANOA", "É um barco estreito.", "Rema-se com uma pá, em rios ou lagos.",
              "O canoísta português Fernando Pimenta ganhou a prata em Londres 2012 e o bronze em Tóquio 2020."),
            p("APITO", "É pequeno, mas faz muito barulho.", "O árbitro usa-o para parar o jogo.",
              "Antes de usarem apito (por volta de 1878), os árbitros de futebol agitavam um lenço."),
            p("BILHAR", "Joga-se numa mesa com um pano verde.", "Usa-se um taco para meter bolas nos buracos.",
              "As bolas de bilhar eram de marfim. A procura de um substituto levou à invenção de um dos primeiros plásticos: o celuloide."),
        ],
    },
    # ------------------------------------------------------------- PAÍSES
    "paises": {
        "nome": "Países", "icone": "🌍",
        "descricao": "Uma volta ao mundo em palavras.",
        "palavras": [
            p("CHILE", "Fica na América do Sul.", "É muito comprido e estreito, entre os Andes e o Pacífico.",
              "O Chile tem cerca de 4300 km de comprimento, mas em média só uns 180 km de largura."),
            p("ITÁLIA", "Fica no sul da Europa.", "Tem a forma de uma bota e é a terra da pizza.",
              "A Itália é o país com mais locais classificados como Património Mundial pela UNESCO."),
            p("JAPÃO", "Fica na Ásia, num conjunto de ilhas.", "É o país do sol nascente e dos samurais.",
              "O Japão é formado por mais de 14 mil ilhas."),
            p("CHINA", "Fica na Ásia e é enorme.", "Tem uma muralha famosa e os pandas.",
              "Ao contrário do que se diz, a Grande Muralha da China não se vê do espaço a olho nu."),
            p("ÍNDIA", "Fica no sul da Ásia.", "Tem o Taj Mahal e já fez parte da rota de Vasco da Gama.",
              "Desde 2023, a Índia é o país com mais habitantes do mundo: passou a China."),
            p("BRASIL", "Fica na América do Sul e fala-se português.", "Tem a Amazónia e o Carnaval do Rio.",
              "O Brasil é o maior país do mundo onde se fala português e tem mais de 200 milhões de habitantes."),
            p("FRANÇA", "Fica na Europa e faz fronteira com Espanha.", "A capital é Paris, com a Torre Eiffel.",
              "A França é o país mais visitado do mundo."),
            p("ESPANHA", "É o nosso único vizinho por terra.", "A capital é Madrid.",
              "A Espanha é o único país europeu com fronteira terrestre com África, nas cidades de Ceuta e Melilla."),
            p("GRÉCIA", "Fica no sul da Europa, com muitas ilhas.", "A capital é Atenas, onde fica a Acrópole.",
              "A Grécia é o berço dos Jogos Olímpicos e da democracia."),
            p("EGITO", "Fica no norte de África.", "Tem as pirâmides e o rio Nilo.",
              "A Grande Pirâmide de Gizé é a única das Sete Maravilhas do Mundo Antigo que ainda existe."),
            p("MÉXICO", "Fica na América do Norte.", "É a terra dos tacos e dos mariachis.",
              "A Cidade do México foi construída por cima de um lago e afunda alguns centímetros todos os anos."),
            p("CANADÁ", "Fica na América do Norte.", "Tem uma folha de ácer na bandeira.",
              "O Canadá tem a costa mais comprida do mundo: mais de 200 mil km."),
            p("RÚSSIA", "Fica entre a Europa e a Ásia.", "É o maior país do mundo e a capital é Moscovo.",
              "A Rússia é tão grande que tem 11 fusos horários."),
            p("PERU", "Fica na América do Sul.", "Tem Machu Picchu e o mesmo nome de uma ave.",
              "Machu Picchu é uma cidade inca construída no alto das montanhas, no século XV."),
            p("CUBA", "É uma ilha das Caraíbas.", "A capital é Havana.",
              "Cuba é a maior ilha das Caraíbas."),
            p("NEPAL", "Fica na Ásia, entre a Índia e a China.", "É lá que fica o monte Evereste.",
              "O Nepal é o único país do mundo cuja bandeira não é retangular: são dois triângulos."),
            p("QUÉNIA", "Fica na África Oriental.", "É famoso pelos safaris e pelos grandes maratonistas.",
              "O queniano Eliud Kipchoge foi o primeiro a correr uma maratona em menos de 2 horas (numa prova especial, em 2019)."),
            p("ANGOLA", "Fica em África e fala-se português.", "A capital é Luanda.",
              "As quedas de Kalandula, em Angola, estão entre as maiores cascatas de África."),
            p("SUÉCIA", "Fica no norte da Europa.", "A capital é Estocolmo.",
              "Os Prémios Nobel foram criados pelo sueco Alfred Nobel, o inventor da dinamite."),
            p("NORUEGA", "Fica no norte da Europa.", "É famosa pelos fiordes e pela capital, Oslo.",
              "No norte da Noruega, no verão, o sol não se põe durante semanas: é o 'sol da meia-noite'."),
            p("IRLANDA", "É uma ilha a oeste da Grã-Bretanha.", "O símbolo é o trevo e a capital é Dublin.",
              "O símbolo oficial da Irlanda não é o trevo, mas sim uma harpa."),
            p("POLÓNIA", "Fica no centro da Europa.", "A capital é Varsóvia.",
              "Marie Curie nasceu em Varsóvia e foi a primeira pessoa a ganhar dois Prémios Nobel."),
            p("TURQUIA", "Fica entre a Europa e a Ásia.", "A sua maior cidade é Istambul.",
              "Istambul fica em dois continentes ao mesmo tempo: Europa e Ásia."),
            p("BÉLGICA", "É um país pequeno no centro da Europa.", "É famoso pelo chocolate e a capital é Bruxelas.",
              "O Tintim e os Estrunfes foram criados por autores belgas."),
            p("SUÍÇA", "Fica nos Alpes.", "É famosa pelos relógios, pelo chocolate e pelos queijos.",
              "A Suíça tem quatro línguas oficiais: alemão, francês, italiano e romanche."),
            p("TIMOR", "Fica na Ásia e fala-se português.", "O nome completo acaba em 'Leste'.",
              "Timor-Leste foi o primeiro país novo do século XXI: tornou-se independente em 2002."),
            p("MÓNACO", "É um país minúsculo junto ao Mediterrâneo.", "É famoso pelo casino e pelo Grande Prémio de Fórmula 1.",
              "O Mónaco é o segundo país mais pequeno do mundo: tem cerca de 2 km²."),
            p("MALTA", "É um pequeno país-ilha no Mediterrâneo.", "O nome também quer dizer 'grupo de amigos' em português.",
              "O maltês é a única língua oficial da União Europeia de origem semítica, e escreve-se com o alfabeto latino."),
            p("CROÁCIA", "Fica nos Balcãs, junto ao mar Adriático.", "Tem uma bandeira com um xadrez vermelho e branco.",
              "A gravata vem da Croácia: os soldados croatas usavam lenços ao pescoço, e os franceses chamaram-lhes 'cravate'."),
            p("JAMAICA", "É uma ilha das Caraíbas.", "É a terra de Usain Bolt e do reggae.",
              "A Jamaica é a terra de Bob Marley, o músico mais famoso do reggae."),
        ],
    },
    # ------------------------------------------------------------- HISTÓRIA
    "historia": {
        "nome": "História", "icone": "📜",
        "descricao": "Reis, castelos e Descobrimentos.",
        "palavras": [
            p("ROMA", "Foi a capital de um grande império.", "Diz-se que 'todos os caminhos vão dar' a esta cidade.",
              "Segundo a lenda, Roma foi fundada em 753 a.C. por Rómulo e Remo, dois gémeos criados por uma loba."),
            p("CASTELO", "É uma construção com torres e muralhas.", "Os reis viviam ou defendiam-se lá dentro.",
              "O Castelo de Guimarães é chamado o 'berço da nação', por estar ligado a D. Afonso Henriques."),
            p("CRUZADA", "Foi uma expedição militar da Idade Média.", "Os cavaleiros cristãos partiam para Jerusalém.",
              "Em 1147, cruzados a caminho da Terra Santa ajudaram D. Afonso Henriques a conquistar Lisboa."),
            p("PIRATA", "Atacava navios no mar.", "Tem uma pala no olho e procura tesouros.",
              "Uma teoria diz que os piratas usavam pala para terem sempre um olho habituado ao escuro dos porões."),
            p("FARAÓ", "Era o rei do Antigo Egito.", "Tutankhamon era um.",
              "Tutankhamon tornou-se faraó com cerca de 9 anos. O seu túmulo, cheio de tesouros, foi descoberto em 1922."),
            p("MÚMIA", "Encontra-se em túmulos do Antigo Egito.", "É um corpo embrulhado em ligaduras.",
              "Para fazerem uma múmia, os egípcios tiravam o cérebro pelo nariz com ganchos compridos."),
            p("ESPADA", "É uma arma antiga.", "Os cavaleiros usavam-na com uma lâmina comprida.",
              "Na Idade Média, uma boa espada era tão cara que passava de pais para filhos como herança."),
            p("ESCUDO", "Os cavaleiros levavam-no no braço.", "Servia para se protegerem e também foi a nossa moeda.",
              "O escudo foi a moeda de Portugal até 2002, quando chegou o euro."),
            p("IMPÉRIO", "É um conjunto de territórios governados por um só poder.", "O romano foi um dos maiores.",
              "O Império Português durou quase 600 anos: da conquista de Ceuta (1415) à entrega de Macau (1999)."),
            p("RAINHA", "É uma mulher que reina.", "D. Maria I foi uma delas.",
              "D. Maria I foi a primeira mulher a reinar em Portugal por direito próprio, a partir de 1777."),
            p("PAPIRO", "Era usado no Antigo Egito.", "É uma planta com que se fazia uma espécie de papel.",
              "A palavra 'papel' vem de 'papiro', a planta do rio Nilo com que os egípcios faziam folhas para escrever."),
            p("TRONO", "É um assento muito especial.", "É onde se senta o rei.",
              "Entre 1580 e 1640, o trono de Portugal foi ocupado pelos reis de Espanha. A independência voltou a 1 de dezembro de 1640."),
            p("COROA", "É um símbolo dos reis.", "Usa-se na cabeça e tem joias.",
              "Em 1646, D. João IV ofereceu a coroa a Nossa Senhora da Conceição. Desde aí, os reis portugueses deixaram de a usar na cabeça."),
            p("MAPA", "Era essencial para os navegadores.", "Mostra terras, mares e caminhos.",
              "O Planisfério de Cantino, de 1502, é um dos mapas mais antigos a mostrar as descobertas portuguesas, incluindo o Brasil."),
            p("BÚSSOLA", "É um instrumento de orientação.", "Tem uma agulha que aponta sempre para norte.",
              "A bússola foi inventada na China e foi muito usada pelos navegadores portugueses nos Descobrimentos."),
            p("CANHÃO", "É uma arma de fogo grande.", "Disparava balas de ferro nos navios e castelos.",
              "Os canhões a bordo dos navios ajudaram os portugueses a dominar as rotas do oceano Índico no século XVI."),
            p("MURALHA", "É uma parede enorme de defesa.", "A da China é a mais famosa.",
              "Somando todos os troços, a Grande Muralha da China tem mais de 21 mil km."),
            p("TEMPLO", "É um edifício religioso antigo.", "Em Évora há um romano, com colunas.",
              "O templo romano de Évora é chamado 'Templo de Diana', mas não há provas de que fosse dedicado a esta deusa."),
            p("ELMO", "Era usado pelos guerreiros.", "É um capacete de metal.",
              "Os elmos dos vikings não tinham chifres: essa ideia foi inventada no século XIX, para óperas e ilustrações."),
            p("MOEDA", "Serve para comprar coisas.", "É dinheiro feito de metal.",
              "As primeiras moedas foram feitas na Lídia (atual Turquia), há cerca de 2600 anos."),
            p("GALEÃO", "É um navio grande dos séculos XVI e XVII.", "Tinha várias velas e canhões, e levava tesouros.",
              "Muitos galeões afundaram carregados de ouro e prata. Ainda hoje há quem procure esses tesouros no fundo do mar."),
            p("SAMURAI", "Era um guerreiro de um país asiático.", "Usava catana e seguia um código de honra no Japão.",
              "Os portugueses chegaram ao Japão em 1543 e levaram as primeiras armas de fogo. Em japonês, pão diz-se 'pan'!"),
            p("CRAVO", "É uma flor.", "É o símbolo do 25 de Abril.",
              "No 25 de Abril de 1974, Celeste Caeiro deu cravos aos soldados, que os puseram nas espingardas: daí o nome 'Revolução dos Cravos'."),
            p("ESCRIBA", "Era uma profissão muito importante no Antigo Egito.", "Era a pessoa que escrevia os textos à mão.",
              "No Egito, os escribas estavam entre os poucos que sabiam ler e escrever hieróglifos: a aprendizagem durava anos."),
            p("COLISEU", "É um anfiteatro famoso.", "Fica em Roma, e lá lutavam gladiadores.",
              "O Coliseu de Roma recebia cerca de 50 mil espectadores e tinha um toldo enorme para os proteger do sol."),
            p("TRATADO", "É um acordo entre países.", "O de Tordesilhas dividiu o mundo entre Portugal e Espanha.",
              "O Tratado de Windsor, entre Portugal e Inglaterra (1386), é a aliança mais antiga do mundo ainda em vigor."),
            p("LEGIÃO", "Era uma unidade do exército.", "Era formada por milhares de soldados romanos.",
              "Uma legião romana tinha cerca de 5000 soldados, que caminhavam uns 30 km por dia com o equipamento às costas."),
            p("FEUDO", "Tem a ver com a Idade Média.", "Eram terras dadas por um senhor a um vassalo.",
              "No feudalismo, os servos estavam presos à terra: se o senhor a vendesse, eles iam com ela."),
            p("INFANTE", "É o título dos filhos dos reis que não são herdeiros.", "D. Henrique, o Navegador, tinha este título.",
              "O Infante D. Henrique ficou conhecido como 'o Navegador', mas quase não fez viagens: organizava-as a partir de terra."),
            p("MONARCA", "É quem governa sozinho um reino.", "Pode ser rei ou rainha.",
              "O último monarca de Portugal foi D. Manuel II. A monarquia acabou a 5 de outubro de 1910."),
        ],
    },
    # ------------------------------------------------------------- MÚSICA
    "musica": {
        "nome": "Música", "icone": "🎸",
        "descricao": "Instrumentos, géneros e palcos.",
        "palavras": [
            p("PIANO", "É um instrumento de teclas.", "Tem 88 teclas brancas e pretas.",
              "O nome completo é 'pianoforte', porque consegue tocar suave (piano) e forte. Foi inventado em Itália, por volta de 1700."),
            p("BANDA", "É um grupo de pessoas.", "Tocam juntas, com guitarra, baixo e bateria.",
              "Os Beatles são a banda que mais discos vendeu em toda a história."),
            p("ROCK", "É um género musical.", "Tem guitarras elétricas e Elvis Presley foi o seu rei.",
              "O rock nasceu nos Estados Unidos nos anos 50, a misturar blues, country e gospel."),
            p("FADO", "É um género musical português.", "Amália Rodrigues era a sua rainha.",
              "Desde 2011, o fado é Património Cultural Imaterial da Humanidade, classificado pela UNESCO."),
            p("JAZZ", "É um género musical americano.", "Usa muito o saxofone e a improvisação.",
              "O jazz nasceu em Nova Orleães, nos Estados Unidos, no início do século XX."),
            p("VIOLINO", "É um instrumento de cordas.", "Toca-se com um arco, apoiado no ombro.",
              "Os violinos feitos por Antonio Stradivari, há mais de 300 anos, valem hoje milhões de euros."),
            p("VIOLA", "É um instrumento de cordas.", "Em Portugal é o nome que se dá à guitarra clássica.",
              "Em Portugal, a 'guitarra portuguesa' é outro instrumento: tem 12 cordas e acompanha o fado."),
            p("FLAUTA", "É um instrumento de sopro.", "Tem buracos para os dedos e há uma de bisel na escola.",
              "A flauta mais antiga que se conhece foi feita de osso há mais de 35 mil anos."),
            p("TAMBOR", "É um instrumento de percussão.", "Toca-se batendo com baquetas.",
              "Em África, há tambores que imitam a voz e eram usados para enviar mensagens entre aldeias."),
            p("HARPA", "É um instrumento de cordas muito antigo.", "Tem forma triangular e toca-se com os dedos.",
              "A harpa de concerto tem 47 cordas e 7 pedais."),
            p("BATERIA", "É um conjunto de instrumentos.", "Tem bombo, tarola e pratos.",
              "A bateria nasceu no início do século XX, com o jazz, quando a invenção do pedal do bombo deixou uma só pessoa tocar tudo."),
            p("ÓPERA", "É um espetáculo de teatro.", "As personagens cantam em vez de falar.",
              "'Ópera' quer dizer 'obra' em italiano. Este género nasceu em Itália, por volta de 1600."),
            p("CORO", "É um grupo de cantores.", "Cantam juntos, muitas vezes em igrejas.",
              "O cante alentejano, cantado em coro e sem instrumentos, é Património da Humanidade desde 2014."),
            p("TENOR", "É um tipo de voz.", "Pavarotti era um dos mais famosos.",
              "Em 1990, os 'Três Tenores' (Pavarotti, Domingo e Carreras) cantaram juntos em Roma, na véspera da final do Mundial."),
            p("ACORDE", "Tem a ver com harmonia.", "São várias notas tocadas ao mesmo tempo.",
              "Há centenas de canções pop que usam apenas os mesmos quatro acordes."),
            p("MELODIA", "É a parte de uma música que fica no ouvido.", "É uma sequência de notas que se pode trautear.",
              "A melodia dos 'Parabéns' foi criada em 1893 por duas irmãs americanas, para uma canção chamada 'Good Morning to All'."),
            p("RITMO", "Tem a ver com o tempo da música.", "É o que nos faz bater o pé.",
              "O ritmo mede-se em batidas por minuto (BPM). Muitas músicas de dança andam pelos 120 BPM."),
            p("CANÇÃO", "É uma música com letra.", "Portugal ganhou a Eurovisão com uma.",
              "Portugal ganhou o Festival Eurovisão da Canção em 2017, com 'Amar pelos Dois', cantada por Salvador Sobral."),
            p("MAESTRO", "Está à frente da orquestra.", "Dirige os músicos com uma batuta.",
              "Antigamente, os maestros marcavam o ritmo a bater com um bastão no chão. O compositor Lully feriu o pé assim, em 1687."),
            p("PAUTA", "Serve para escrever música.", "Tem cinco linhas onde se põem as notas.",
              "Os nomes das notas (dó, ré, mi...) vêm das primeiras sílabas de um hino em latim, do século XI."),
            p("REGGAE", "É um género musical das Caraíbas.", "Bob Marley é o artista mais famoso deste género.",
              "Em 2018, a UNESCO classificou o reggae da Jamaica como Património Cultural Imaterial da Humanidade."),
            p("BLUES", "É um género musical americano.", "O nome vem de uma palavra inglesa que quer dizer tristeza.",
              "Os blues nasceram entre os afro-americanos do sul dos Estados Unidos e influenciaram o jazz e o rock."),
            p("PALCO", "Fica num teatro ou num concerto.", "É onde os artistas atuam.",
              "No teatro, desejar 'boa sorte' dá azar: os atores preferem dizer 'parte uma perna'!"),
            p("DISCO", "É redondo.", "Antigamente era onde se gravava a música.",
              "Um 'disco de ouro' ou de 'platina' é um prémio para os álbuns que vendem muitas cópias."),
            p("GAITA", "É um instrumento de sopro.", "A de foles também é tradicional em Trás-os-Montes.",
              "A gaita de foles não é só da Escócia: também é tradicional em Trás-os-Montes e na Galiza."),
            p("ÓRGÃO", "É um instrumento de teclas enorme.", "Tem tubos e costuma estar nas igrejas.",
              "A Basílica de Mafra tem seis órgãos feitos para tocarem todos ao mesmo tempo: é caso único no mundo."),
            p("VALSA", "É uma dança.", "Dança-se a pares, em três tempos, e é famosa em Viena.",
              "'O Danúbio Azul', de Johann Strauss, é uma das valsas mais famosas e toca todos os anos no concerto de Ano Novo de Viena."),
            p("SAMBA", "É uma dança e um ritmo.", "É a música do Carnaval do Brasil.",
              "O samba de roda da Bahia é Património Cultural Imaterial da Humanidade desde 2005."),
            p("HINO", "É uma música solene.", "Cada país tem o seu, e o nosso é 'A Portuguesa'.",
              "'A Portuguesa' foi composta em 1890 e tornou-se o hino nacional em 1911, depois da implantação da República."),
            p("VINIL", "É um material.", "É de que são feitos os discos que tocam no gira-discos.",
              "Os discos de vinil voltaram à moda: em alguns países, já se vendem mais discos de vinil do que CDs."),
        ],
    },
}

SURPRESA = {"nome": "Surpresa", "icone": "🎲", "descricao": "Um tema sorteado à sorte."}


# =====================================================================
# 4. REGRAS DO JOGO
# =====================================================================
def sem_acentos(texto):
    """Põe o texto em MAIÚSCULAS e tira acentos e cedilhas: 'Maçã' -> 'MACA'.
    O unicodedata separa cada letra do seu acento (NFD) e depois deitamos fora os acentos."""
    decomposto = unicodedata.normalize("NFD", texto.upper())
    return "".join(c for c in decomposto if unicodedata.category(c) != "Mn")


def so_letras(texto):
    """Fica só com as letras de A a Z (sem acentos). Serve para limpar o que o jogador escreve."""
    return "".join(c for c in sem_acentos(texto) if "A" <= c <= "Z")


def avaliar(tentativa, segredo):
    """Compara a tentativa com a palavra secreta (ambas sem acentos) e devolve a cor de cada letra.

    Faz-se em DUAS passagens, como no Wordle original, para as letras repetidas ficarem certas:
      1.ª passagem: marca as letras no sítio certo (verde) e conta as letras do segredo que sobram;
      2.ª passagem: uma letra fica amarela só se ainda sobrar essa letra no segredo.
    Exemplo: segredo GATO, tentativa OSSO -> só o último O fica verde; o primeiro O fica cinzento,
    porque a palavra secreta só tem um O."""
    estados = [FALHA] * len(tentativa)
    sobram = {}                                  # letras do segredo que não ficaram verdes
    for i, (letra, certa) in enumerate(zip(tentativa, segredo)):
        if letra == certa:
            estados[i] = CERTA
        else:
            sobram[certa] = sobram.get(certa, 0) + 1
    for i, letra in enumerate(tentativa):
        if estados[i] != CERTA and sobram.get(letra, 0) > 0:
            estados[i] = EXISTE
            sobram[letra] -= 1
    return estados


def pontos_ganhos(numero_tentativa, pistas_usadas):
    """Pontos ao acertar: mais pontos com menos tentativas e menos pistas."""
    return max(PONTOS_MINIMOS, PONTOS_POR_TENTATIVA[numero_tentativa] - CUSTO_PISTA * pistas_usadas)


@dataclass
class Partida:
    """Um jogo (uma palavra)."""
    tema: str                                    # chave do tema ("animais", "comida", ...)
    dados: dict                                  # a palavra, as pistas e a curiosidade
    surpresa: bool = False                       # True se o tema foi sorteado
    tentativas: list = field(default_factory=list)   # lista de (letras, estados)
    rascunho: str = ""                           # letras escritas na linha atual (ainda não enviadas)
    pistas_usadas: int = 0
    estado: str = "a jogar"                      # "a jogar", "ganhou" ou "perdeu"
    pontos: int = 0
    aviso: str = ""                              # mensagem para o jogador (por exemplo: tamanho errado)
    animar: bool = False                         # True logo a seguir a uma tentativa (as letras "viram")
    contada: bool = False                        # True depois de ir para as estatísticas

    @property
    def segredo(self):
        """A palavra secreta sem acentos (é com esta que se compara)."""
        return sem_acentos(self.dados["palavra"])

    @property
    def tamanho(self):
        return len(self.segredo)

    @property
    def terminou(self):
        return self.estado != "a jogar"

    def escrever(self, texto, acao):
        """Trata um clique no formulário do jogo.
        'texto' é o que está na caixa de texto; 'acao' diz que botão foi carregado:
        "letra:X" (tecla do ecrã), "apagar" ou "tentar" (botão Tentar ou tecla Enter)."""
        if self.terminou:
            return
        self.aviso = ""
        self.animar = False
        letras = so_letras(texto)
        if acao.startswith("letra:"):
            letras = (letras + so_letras(acao[6:]))[:self.tamanho]
            self.rascunho = letras
        elif acao == "apagar":
            self.rascunho = letras[:self.tamanho][:-1]
        else:
            self.tentar(texto)

    def tentar(self, texto):
        """Envia uma tentativa. Se o tamanho estiver errado, mostra um aviso e não gasta tentativa."""
        letras = so_letras(texto)
        limpo = sem_acentos(texto).replace(" ", "")
        self.rascunho = letras[:self.tamanho]
        if not limpo:
            self.aviso = "Escreve uma palavra primeiro. 🙂"
        elif len(letras) != len(limpo):
            self.aviso = "Usa só letras (sem números nem símbolos). Não gastaste nenhuma tentativa."
        elif len(letras) != self.tamanho:
            self.aviso = (f"A palavra secreta tem {self.tamanho} letras e escreveste {len(letras)}. "
                          "Não faz mal: não gastaste nenhuma tentativa!")
        else:
            estados = avaliar(letras, self.segredo)
            self.tentativas.append((letras, estados))
            self.rascunho = ""
            self.animar = True
            if letras == self.segredo:
                self.estado = "ganhou"
                self.pontos = pontos_ganhos(len(self.tentativas), self.pistas_usadas)
            elif len(self.tentativas) == TENTATIVAS:
                self.estado = "perdeu"

    def pedir_pista(self):
        """Revela a pista seguinte (se ainda houver)."""
        if not self.terminou and self.pistas_usadas < PISTAS_POR_PALAVRA:
            self.pistas_usadas += 1
            self.aviso = ""
            self.animar = False

    def desistir(self):
        """O jogador desiste: conta como derrota e mostra a palavra."""
        if not self.terminou:
            self.estado = "perdeu"
            self.animar = False

    def estado_das_teclas(self):
        """Cor de cada letra no teclado: a melhor cor que essa letra já teve."""
        teclas = {}
        for letras, estados in self.tentativas:
            for letra, estado in zip(letras, estados):
                if FORCA_ESTADO[estado] > FORCA_ESTADO.get(teclas.get(letra), 0):
                    teclas[letra] = estado
        return teclas

    def pontos_possiveis(self):
        """Quantos pontos o jogador ganha se acertar na próxima tentativa."""
        return pontos_ganhos(min(len(self.tentativas) + 1, TENTATIVAS), self.pistas_usadas)


@dataclass
class Estatisticas:
    """Estatísticas da sessão (enquanto o servidor estiver ligado)."""
    jogos: int = 0
    vitorias: int = 0
    sequencia: int = 0                           # vitórias seguidas, neste momento
    melhor_sequencia: int = 0
    pontos: int = 0
    distribuicao: list = field(default_factory=lambda: [0] * TENTATIVAS)   # vitórias à 1.ª, 2.ª, ... tentativa
    por_tema: dict = field(default_factory=dict)  # tema -> [jogos, vitórias, tentativas nas vitórias]

    def registar(self, partida):
        """Junta o resultado de uma partida às estatísticas (só uma vez por partida)."""
        if partida.contada or not partida.terminou:
            return
        partida.contada = True
        tema = self.por_tema.setdefault(partida.tema, [0, 0, 0])
        self.jogos += 1
        tema[0] += 1
        if partida.estado == "ganhou":
            self.vitorias += 1
            self.sequencia += 1
            self.melhor_sequencia = max(self.melhor_sequencia, self.sequencia)
            self.pontos += partida.pontos
            self.distribuicao[len(partida.tentativas) - 1] += 1
            tema[1] += 1
            tema[2] += len(partida.tentativas)
        else:
            self.sequencia = 0

    def media_tentativas(self):
        """Média de tentativas nas palavras acertadas (texto, com uma casa decimal)."""
        if not self.vitorias:
            return "–"
        total = sum((i + 1) * n for i, n in enumerate(self.distribuicao))
        return f"{total / self.vitorias:.1f}".replace(".", ",")


@dataclass
class Sessao:
    """Tudo o que pertence a um jogador: a partida atual, as estatísticas e as palavras já jogadas."""
    partida: Partida = None
    estatisticas: Estatisticas = field(default_factory=Estatisticas)
    usadas: dict = field(default_factory=dict)   # tema -> conjunto de palavras já jogadas
    recomecou_tema: bool = False                 # True quando já se jogaram as 30 palavras de um tema

    def nova_partida(self, escolha):
        """Começa uma partida nova. 'escolha' é a chave de um tema ou "surpresa"."""
        surpresa = escolha == "surpresa"
        tema = random.choice(list(TEMAS)) if surpresa else escolha
        usadas = self.usadas.setdefault(tema, set())
        livres = [d for d in TEMAS[tema]["palavras"] if d["palavra"] not in usadas]
        self.recomecou_tema = not livres
        if not livres:                           # já se jogaram todas: recomeça o tema do zero
            usadas.clear()
            livres = TEMAS[tema]["palavras"]
        dados = random.choice(livres)
        usadas.add(dados["palavra"])
        self.partida = Partida(tema, dados, surpresa)

    def depois_da_jogada(self):
        """Se a partida acabou, guarda o resultado nas estatísticas."""
        if self.partida and self.partida.terminou:
            self.estatisticas.registar(self.partida)


def verificar_dados():
    """Confirma que todas as palavras têm entre 4 e 7 letras, 2 pistas e não há repetidas.
    Corre quando o jogo arranca: se te enganares a acrescentar uma palavra, avisa logo."""
    for chave, tema in TEMAS.items():
        vistas = set()
        for dados in tema["palavras"]:
            palavra = sem_acentos(dados["palavra"])
            assert palavra.isalpha() and palavra == so_letras(palavra), f"{chave}: '{dados['palavra']}' tem símbolos"
            assert TAMANHO_MIN <= len(palavra) <= TAMANHO_MAX, f"{chave}: '{dados['palavra']}' tem {len(palavra)} letras"
            assert len(dados["pistas"]) == PISTAS_POR_PALAVRA, f"{chave}: '{dados['palavra']}' precisa de 2 pistas"
            assert palavra not in vistas, f"{chave}: '{dados['palavra']}' está repetida"
            vistas.add(palavra)


# =====================================================================
# 5. PÁGINAS
# O paginas.html está dividido em BLOCOS (<!--@ nome -->). Alguns são páginas inteiras
# (inicio, jogo, fim...) e outros são peças pequenas que se repetem (celula, tecla, pista...).
# Estas funções escolhem os blocos certos e preenchem os campos $campo.
# =====================================================================
PASTA = Path(__file__).parent                 # pasta onde estão os 3 ficheiros do jogo
FICHEIRO_HTML = PASTA / "paginas.html"        # todo o HTML
FICHEIRO_CSS = PASTA / "estilo.css"           # todo o CSS
TITULO = "Palavra Secreta"


def carregar_blocos():
    """Lê o paginas.html e separa-o pelos marcadores. Devolve {nome do bloco: Template}.
    O ficheiro é lido em cada pedido, por isso basta carregar em F5 depois de o alterares."""
    texto = FICHEIRO_HTML.read_text(encoding="utf-8")
    partes = re.split(r"<!--@ (\w+) -->", texto)      # [cabeçalho, nome1, corpo1, nome2, corpo2, ...]
    return {partes[i]: Template(partes[i + 1].strip()) for i in range(1, len(partes), 2)}


def esc(texto):
    """Protege o texto antes de o pôr no HTML (por exemplo, '<' passa a '&lt;')."""
    return html.escape(str(texto))


def montar(blocos, ecra, tema="inicio", **campos):
    """Preenche a página 'ecra' e mete-a dentro da página-base (cabeçalho e rodapé).
    'tema' escolhe as cores da página (classe CSS no <body>)."""
    corpo = blocos[ecra].substitute(campos)
    return blocos["base"].substitute(titulo=TITULO, classe_tema=f"tema-{tema}", conteudo=corpo)


def nome_do_tema(partida):
    """Nome do tema para mostrar (com a indicação 'Surpresa' se foi sorteado)."""
    tema = TEMAS[partida.tema]
    if partida.surpresa:
        return f"{SURPRESA['icone']} Surpresa: {tema['icone']} {tema['nome']}"
    return f"{tema['icone']} {tema['nome']}"


def plural(n, palavra):
    """'1 tentativa', '2 tentativas'..."""
    return f"{n} {palavra}" if n == 1 else f"{n} {palavra}s"


def celula(blocos, letra="", estado="vazia", indice=0, extra=""):
    """Um quadradinho da grelha."""
    rotulo = f"{letra}, {NOMES_ESTADO[estado]}" if estado in NOMES_ESTADO else (letra or "vazio")
    return blocos["celula"].substitute(letra=esc(letra), estado=estado + extra, i=indice, rotulo=esc(rotulo))


def grelha(blocos, partida, a_jogar=True):
    """A grelha toda: linhas já tentadas (coloridas), a linha atual (rascunho) e linhas vazias.
    A última tentativa leva a classe 'nova' (as letras viram) e, se acertou, 'ganhou' (as letras saltam)."""
    linhas = []
    total = len(partida.tentativas)
    for n, (letras, estados) in enumerate(partida.tentativas, start=1):
        if letras == partida.segredo:           # na linha certa, mostra a palavra bem escrita (com acentos)
            letras = partida.dados["palavra"]
        celulas = "".join(celula(blocos, l, e, i) for i, (l, e) in enumerate(zip(letras, estados)))
        classe = "tentada"
        if n == total and partida.animar:
            classe += " nova"
        if n == total and partida.estado == "ganhou":
            classe += " ganhou"
        linhas.append(blocos["linha"].substitute(classe=classe, celulas=celulas, tamanho=partida.tamanho,
                                                 rotulo=f"Tentativa {n}"))
    if a_jogar and not partida.terminou:        # linha atual, com as letras já escritas
        rascunho = partida.rascunho
        celulas = "".join(celula(blocos, rascunho[i] if i < len(rascunho) else "",
                                 "escrita" if i < len(rascunho) else "vazia", i,
                                 " pop" if i == len(rascunho) - 1 else "")
                          for i in range(partida.tamanho))
        classe = "atual abanar" if partida.aviso else "atual"
        linhas.append(blocos["linha"].substitute(classe=classe, celulas=celulas, tamanho=partida.tamanho,
                                                 rotulo=f"Tentativa {total + 1} (a escrever)"))
    vazias = TENTATIVAS - len(linhas)
    for n in range(vazias):                      # linhas ainda por usar
        celulas = "".join(celula(blocos) for _ in range(partida.tamanho))
        linhas.append(blocos["linha"].substitute(classe="vazia", celulas=celulas, tamanho=partida.tamanho,
                                                 rotulo="Tentativa por usar"))
    return "".join(linhas)


def teclado(blocos, partida):
    """O teclado do ecrã: cada tecla é um botão que envia a letra, com a cor que essa letra já teve."""
    cores = partida.estado_das_teclas()
    linhas = []
    for n, letras in enumerate(LINHAS_TECLADO):
        teclas = "".join(blocos["tecla"].substitute(letra=l, estado=cores.get(l, "nova"),
                                                    rotulo=esc(f"{l}, {NOMES_ESTADO[cores[l]]}" if l in cores else l))
                         for l in letras)
        if n == len(LINHAS_TECLADO) - 1:         # a última linha tem as teclas Apagar e Tentar
            teclas = blocos["tecla_tentar"].substitute() + teclas + blocos["tecla_apagar"].substitute()
        linhas.append(blocos["teclado_linha"].substitute(teclas=teclas))
    return "".join(linhas)


def pistas(blocos, partida):
    """As pistas já reveladas e o botão para pedir a próxima."""
    reveladas = "".join(blocos["pista"].substitute(numero=i + 1, texto=esc(partida.dados["pistas"][i]))
                        for i in range(partida.pistas_usadas))
    if partida.pistas_usadas < PISTAS_POR_PALAVRA:
        botao = blocos["pista_botao"].substitute(custo=CUSTO_PISTA,
                                                 restam=PISTAS_POR_PALAVRA - partida.pistas_usadas)
    else:
        botao = blocos["pista_esgotada"].substitute()
    return reveladas, botao


def pagina_inicio(sessao):
    """Ecrã inicial: escolher o tema."""
    blocos = carregar_blocos()
    cartoes = "".join(blocos["cartao_tema"].substitute(chave=chave, icone=t["icone"], nome=esc(t["nome"]),
                                                       descricao=esc(t["descricao"]))
                      for chave, t in list(TEMAS.items()) + [("surpresa", SURPRESA)])
    continuar = ""
    if sessao.partida and not sessao.partida.terminou:
        continuar = blocos["continuar"].substitute(tema=esc(nome_do_tema(sessao.partida)),
                                                   feitas=plural(len(sessao.partida.tentativas), "tentativa"))
    e = sessao.estatisticas
    resumo = ""
    if e.jogos:
        resumo = blocos["resumo"].substitute(jogos=e.jogos, vitorias=e.vitorias, pontos=e.pontos,
                                             sequencia=e.sequencia)
    return montar(blocos, "inicio", cartoes=cartoes, continuar=continuar, resumo=resumo)


def pagina_como_jogar():
    """Página com as regras."""
    blocos = carregar_blocos()
    return montar(blocos, "como_jogar", tentativas=TENTATIVAS, custo=CUSTO_PISTA,
                  minimo=TAMANHO_MIN, maximo=TAMANHO_MAX)


def pagina_jogo(sessao):
    """Página de jogo: cenário e pistas à esquerda, grelha e teclado à direita."""
    blocos = carregar_blocos()
    partida = sessao.partida
    reveladas, botao = pistas(blocos, partida)
    aviso = blocos["aviso"].substitute(texto=esc(partida.aviso)) if partida.aviso else ""
    if sessao.recomecou_tema and not partida.tentativas:
        aviso += blocos["aviso_info"].substitute(
            texto="Já jogaste as 30 palavras deste tema! Recomeçámos a lista do início.")
    pagina = montar(blocos, "jogo", tema=partida.tema,
                    cenario=desenhar_cenario(partida.tema),
                    nome_tema=esc(nome_do_tema(partida)),
                    tamanho=partida.tamanho,
                    numero=len(partida.tentativas) + 1, tentativas=TENTATIVAS,
                    pontos_possiveis=partida.pontos_possiveis(),
                    aviso=aviso, grelha=grelha(blocos, partida), teclado=teclado(blocos, partida),
                    rascunho=esc(partida.rascunho),
                    pistas=reveladas, botao_pista=botao)
    partida.animar = False                      # a animação só acontece uma vez
    return pagina


def estatisticas(blocos, e):
    """O quadro de estatísticas: números, barras das tentativas e resultados por tema."""
    maior = max(e.distribuicao) or 1
    barras = "".join(blocos["barra"].substitute(numero=i + 1, valor=n, largura=max(8, round(n / maior * 100)),
                                                classe="cheia" if n else "")
                     for i, n in enumerate(e.distribuicao))
    temas = "".join(blocos["tema_stat"].substitute(icone=TEMAS[chave]["icone"], nome=esc(TEMAS[chave]["nome"]),
                                                   jogos=valores[0], vitorias=valores[1],
                                                   media=(f"{valores[2] / valores[1]:.1f}".replace(".", ",")
                                                          if valores[1] else "–"))
                    for chave, valores in e.por_tema.items())
    percentagem = round(e.vitorias / e.jogos * 100) if e.jogos else 0
    return blocos["estatisticas"].substitute(jogos=e.jogos, percentagem=percentagem, sequencia=e.sequencia,
                                             melhor=e.melhor_sequencia, media=e.media_tentativas(),
                                             pontos=e.pontos, barras=barras, temas=temas)


def pagina_fim(sessao):
    """Ecrã final: ganhou ou perdeu, a palavra, os pontos, a curiosidade e as estatísticas."""
    blocos = carregar_blocos()
    partida = sessao.partida
    ganhou = partida.estado == "ganhou"
    palavra = partida.dados["palavra"]
    # a palavra em quadradinhos: verdes se ganhou, cinzentos se perdeu
    estado = CERTA if ganhou else "revelada"
    letras = "".join(celula(blocos, l, estado, i) for i, l in enumerate(palavra))
    if ganhou:
        n = len(partida.tentativas)
        titulo = "Acertaste! 🎉" if n > 1 else "À primeira! Incrível! 🤩"
        frase = (f"Descobriste a palavra em {plural(n, 'tentativa')}"
                 + (f" e usaste {plural(partida.pistas_usadas, 'pista')}." if partida.pistas_usadas else ", sem pistas!"))
        resultado = blocos["pontos"].substitute(pontos=partida.pontos)
    else:
        titulo = "Não foi desta... 😅"
        frase = "Desististe, mas fica a saber qual era:" if len(partida.tentativas) < TENTATIVAS \
            else f"Gastaste as {TENTATIVAS} tentativas. A palavra secreta era:"
        resultado = ""
    pagina = montar(blocos, "fim", tema=partida.tema,
                    cenario=desenhar_cenario(partida.tema, festa=ganhou),
                    classe="ganhou" if ganhou else "perdeu",
                    nome_tema=esc(nome_do_tema(partida)),
                    titulo=esc(titulo), frase=esc(frase), letras=letras, resultado=resultado,
                    curiosidade=esc(partida.dados["curiosidade"]),
                    grelha=grelha(blocos, partida, a_jogar=False),
                    estatisticas=estatisticas(blocos, sessao.estatisticas),
                    escolha=partida.tema)
    partida.animar = False
    return pagina


# =====================================================================
# 5b. ILUSTRAÇÕES (SVG)
# Cada tema tem um cenário desenhado com formas simples de SVG.
# Para não parecer "feito por computador":
#   - tudo tem um contorno escuro, como se fosse desenhado a caneta (cor TINTA);
#   - os braços e as pernas são linhas grossas e curvas (função membro);
#   - um filtro ("lapis") entorta ligeiramente os traços e outro ("papel") dá um grão suave.
# O desenho tem 320 x 300 unidades. No telemóvel aparece cortado, como uma faixa.
# =====================================================================
TINTA = "#3b2f2a"                             # cor dos contornos
LARGURA, ALTURA = 320, 300


def defs(cima, baixo):
    """Degradê do fundo e os dois filtros do 'desenho à mão'."""
    return ('<defs><linearGradient id="fundo" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{cima}"/><stop offset="1" stop-color="{baixo}"/></linearGradient>'
            '<filter id="lapis" x="-5%" y="-5%" width="110%" height="110%">'
            '<feTurbulence type="fractalNoise" baseFrequency=".04" numOctaves="2" seed="4" result="ruido"/>'
            '<feDisplacementMap in="SourceGraphic" in2="ruido" scale="2.4" xChannelSelector="R" yChannelSelector="G"/></filter>'
            '<filter id="papel" x="0" y="0" width="100%" height="100%">'
            '<feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2" seed="9"/>'
            '<feColorMatrix values="0 0 0 0 .35  0 0 0 0 .28  0 0 0 0 .2  .3 0 0 0 -.08"/></filter></defs>'
            f'<rect width="{LARGURA}" height="{ALTURA}" fill="url(#fundo)"/>')


def membro(caminho, cor, largura):
    """Braço ou perna: uma linha grossa e curva com contorno (primeiro a escura, por cima a de cor)."""
    return (f'<path d="{caminho}" stroke="{TINTA}" stroke-width="{largura + 4}" fill="none" stroke-linecap="round"/>'
            f'<path d="{caminho}" stroke="{cor}" stroke-width="{largura}" fill="none" stroke-linecap="round"/>')


def nuvem(x, y, escala=1.0):
    """Uma nuvem fofa."""
    return (f'<g transform="translate({x} {y}) scale({escala})" fill="#ffffff" stroke="{TINTA}" stroke-opacity=".35" stroke-width="1.5">'
            '<path d="M-30 10 Q-34 -4 -20 -6 Q-16 -22 2 -18 Q14 -28 24 -12 Q38 -12 34 4 Q34 12 24 12 L-24 12 Q-32 12 -30 10 Z"/></g>')


def sol(x, y, raio):
    """Um sol com brilho à volta."""
    return (f'<circle cx="{x}" cy="{y}" r="{raio + 9}" fill="#ffe680" opacity=".45" stroke="none"/>'
            f'<circle cx="{x}" cy="{y}" r="{raio}" fill="#ffd23f" stroke="#e0a800" stroke-width="2"/>')


def relva(xs, y, cor="#3f8f45"):
    """Tufos de relva."""
    return "".join(f'<path d="M{x} {y} l3 -7 l2 6 l3 -8 l2 8" stroke="{cor}" stroke-width="1.4" fill="none" opacity=".7"/>'
                   for x in xs)


# ---------------------- ANIMAIS: um jardim zoológico ----------------------
def girafa():
    """Girafa atrás da vedação: corpo, pescoço comprido, cabeça e manchas."""
    pernas = "".join(membro(f"M{x} 186 Q{x + d} 212 {x + d} 246", "#f2b84b", 7)
                     for x, d in ((204, -2), (214, 2), (238, -1), (248, 3)))
    manchas = "".join(f'<path d="M{x} {y} q5 -4 9 0 q2 6 -4 8 q-7 0 -5 -8 Z" fill="#b8692a" stroke="none"/>'
                      for x, y in ((206, 172), (222, 168), (238, 174), (216, 182), (250, 166), (254, 140), (258, 118), (262, 98)))
    return (pernas +
            '<path d="M240 168 Q252 150 256 120 Q258 100 262 84 L276 86 Q272 106 270 124 Q266 154 258 176 Z" fill="#f2b84b"/>'
            '<ellipse cx="226" cy="176" rx="34" ry="18" fill="#f2b84b"/>'
            '<path d="M193 172 q-10 6 -9 20" stroke-width="2.4" fill="none"/>'
            + manchas +
            '<path d="M262 76 Q276 66 290 74 Q296 80 290 86 Q278 92 266 88 Q258 84 262 76 Z" fill="#f2b84b"/>'
            '<path d="M268 70 l-2 -10 M276 69 l1 -10" stroke-width="2.4"/>'
            '<circle cx="266" cy="59" r="3" fill="#8a5a33"/><circle cx="277" cy="58" r="3" fill="#8a5a33"/>'
            '<path d="M262 76 q-8 -4 -10 2 q4 4 10 2" fill="#e8a63c"/>'
            '<circle cx="279" cy="76" r="2.2" fill="#3b2f2a" stroke="none"/>'
            '<path d="M288 82 q-3 2 -6 1" fill="none" stroke-width="1.6"/>')


def leao():
    """Leão sentado à frente da vedação, com uma juba farta."""
    # a juba: 10 tufos à volta da cabeça (posições calculadas num círculo)
    raios = "".join(f'<ellipse cx="{94 + 21 * math.cos(a * math.tau / 10):.1f}" '
                    f'cy="{228 + 21 * math.sin(a * math.tau / 10):.1f}" rx="10" ry="9" fill="#c8742c"/>'
                    for a in range(10))
    return ('<ellipse cx="114" cy="262" rx="30" ry="18" fill="#e8a24a"/>'
            '<path d="M140 262 q22 -4 20 -24 q6 -2 6 4" fill="none" stroke-width="3"/>'
            '<circle cx="167" cy="238" r="5" fill="#c8742c"/>'
            + membro("M100 266 Q98 276 96 284", "#e8a24a", 9) + membro("M122 268 Q124 278 126 284", "#e8a24a", 9) +
            raios +
            '<circle cx="94" cy="228" r="16" fill="#f0b45a"/>'
            '<circle cx="82" cy="214" r="5" fill="#f0b45a"/><circle cx="106" cy="214" r="5" fill="#f0b45a"/>'
            '<circle cx="88" cy="226" r="2.2" fill="#3b2f2a" stroke="none"/><circle cx="100" cy="226" r="2.2" fill="#3b2f2a" stroke="none"/>'
            '<path d="M91 232 h6 l-3 4 Z" fill="#7a4a2a"/>'
            '<path d="M94 236 q-4 4 -7 2 M94 236 q4 4 7 2" fill="none" stroke-width="1.4"/>')


def cenario_animais():
    vedacao = "".join(f'<rect x="{x}" y="200" width="9" height="56" rx="2" fill="#c58b52"/>'
                      f'<path d="M{x} 200 l4.5 -7 l4.5 7" fill="#c58b52"/>' for x in range(6, 320, 38))
    return (defs("#bfe6ff", "#effaff") + sol(272, 48, 20) + nuvem(70, 44) + nuvem(180, 30, .7) +
            '<path d="M0 196 Q60 160 130 186 T260 178 T320 184 L320 300 L0 300 Z" fill="#b6e09a" stroke-opacity=".3"/>'
            '<path d="M0 232 Q80 218 160 228 T320 224 L320 300 L0 300 Z" fill="#8fcf6e"/>'
            # árvore
            '<path d="M30 230 Q34 190 32 132 L46 132 Q44 190 50 230 Z" fill="#8a5a33"/>'
            '<circle cx="22" cy="132" r="24" fill="#5fae4a"/><circle cx="58" cy="128" r="26" fill="#6dbb55"/>'
            '<circle cx="40" cy="104" r="28" fill="#74c25c"/>'
            + girafa() +
            vedacao + '<rect x="0" y="210" width="320" height="8" rx="3" fill="#d79a5e"/>'
            '<rect x="0" y="236" width="320" height="8" rx="3" fill="#d79a5e"/>'
            + leao() + relva((20, 60, 180, 230, 292), 292))


# ---------------------- COMIDA: uma mesa na cozinha ----------------------
def cenario_comida():
    azulejos = "".join(f'<rect x="{x}" y="{y}" width="30" height="30" fill="{"#ffffff" if (x // 30 + y // 30) % 2 else "#d8ecf7"}" '
                       f'stroke="#c7dbe6" stroke-width="1"/>'
                       for x in range(0, 330, 30) for y in range(120, 210, 30))
    fumo = "".join(f'<path class="fumo" d="M{x} 150 q-8 -12 0 -24 q8 -12 0 -24" fill="none" stroke="#ffffff" '
                   f'stroke-width="5" stroke-linecap="round" opacity=".85"/>' for x in (92, 112, 132))
    return (defs("#fff3e0", "#ffe2c2") +
            '<g stroke="none">' + azulejos + '</g>'
            # prateleira com frascos
            '<rect x="20" y="78" width="130" height="8" rx="2" fill="#b0703a"/>'
            '<rect x="30" y="52" width="24" height="26" rx="4" fill="#ffd6a5"/><rect x="28" y="46" width="28" height="8" rx="2" fill="#e05a47"/>'
            '<rect x="66" y="44" width="22" height="34" rx="4" fill="#cfe8a9"/><rect x="64" y="38" width="26" height="8" rx="2" fill="#4c9a5b"/>'
            '<rect x="100" y="56" width="30" height="22" rx="4" fill="#ffe08a"/><rect x="98" y="50" width="34" height="8" rx="2" fill="#2f7fc1"/>'
            # janela com cortinas
            '<rect x="200" y="30" width="96" height="72" rx="4" fill="#bfe6ff"/>'
            '<path d="M248 30 V102 M200 66 H296" stroke-width="3" fill="none"/>'
            '<path d="M196 26 Q214 60 204 106 L194 106 Z" fill="#ff8a65"/><path d="M300 26 Q282 60 292 106 L302 106 Z" fill="#ff8a65"/>'
            + fumo +
            # mesa
            '<path d="M0 214 L320 214 L320 300 L0 300 Z" fill="#d9894a"/>'
            '<path d="M0 214 L320 214 L320 226 L0 226 Z" fill="#c2733a"/>'
            '<path d="M60 240 Q160 236 270 242 M20 268 Q150 262 300 270" fill="none" stroke-opacity=".35" stroke-width="1.4"/>'
            # tacho
            '<path d="M66 164 L158 164 L152 214 Q112 222 72 214 Z" fill="#d6503a"/>'
            '<ellipse cx="112" cy="164" rx="48" ry="9" fill="#b83e2b"/>'
            '<path d="M66 172 q-16 0 -16 10 q0 6 10 6" fill="none" stroke-width="4"/>'
            '<path d="M158 172 q16 0 16 10 q0 6 -10 6" fill="none" stroke-width="4"/>'
            '<path d="M80 186 Q112 192 144 186" fill="none" stroke="#ffffff" stroke-opacity=".5" stroke-width="3"/>'
            # pão
            '<path d="M206 214 Q200 186 236 180 Q276 176 290 196 Q296 212 282 216 Z" fill="#e2a456"/>'
            '<path d="M226 190 l8 12 M246 186 l8 12 M266 188 l7 11" fill="none" stroke="#9c6428" stroke-width="2.2"/>'
            # fruta
            '<circle cx="180" cy="208" r="13" fill="#e63946"/><path d="M180 196 q2 -8 8 -9" fill="none" stroke-width="2"/>'
            '<path d="M182 192 q8 -6 12 0 q-6 4 -12 0" fill="#5fae4a"/>'
            '<circle cx="201" cy="222" r="11" fill="#ff9f1c"/><circle cx="199" cy="218" r="1.5" fill="#c46a00" stroke="none"/>'
            '<path d="M222 236 Q252 252 286 232 Q284 242 270 248 Q246 256 224 242 Z" fill="#ffd93d"/>'
            '<path d="M286 232 l4 -3" stroke-width="2.4"/>')


# ---------------------- DESPORTO: um jogo de futebol num estádio ----------------------
def jogador_futebol():
    """Um jogador a rematar: uma perna apoiada e a outra esticada para a bola."""
    pele, camisola, calcao = "#e9b48a", "#e63946", "#ffffff"
    return (membro("M118 222 Q112 248 104 276", pele, 9) +                  # perna de apoio
            membro("M128 222 Q148 236 170 240", pele, 9) +                  # perna do remate
            '<path d="M98 274 l16 2 q2 6 -4 8 l-14 -2 Z" fill="#1d2b3a"/>'   # chuteira de apoio
            '<path d="M168 234 l10 4 q2 6 -4 8 l-9 -3 Z" fill="#1d2b3a"/>'    # chuteira do remate
            '<path d="M108 212 L136 212 L138 228 L106 230 Z" fill="' + calcao + '"/>'
            + membro("M112 176 Q96 186 90 204", camisola, 9) +              # braço de trás (manga)
            membro("M134 176 Q152 170 160 156", camisola, 9) +              # braço da frente (manga)
            '<circle cx="88" cy="208" r="5" fill="' + pele + '"/><circle cx="162" cy="152" r="5" fill="' + pele + '"/>'
            '<path d="M108 172 Q122 166 138 172 L136 214 L108 214 Z" fill="' + camisola + '"/>'
            '<text x="122" y="200" font-size="16" font-weight="700" text-anchor="middle" fill="#ffffff" stroke="none" '
            'font-family="system-ui, sans-serif">7</text>'
            '<path d="M117 160 L127 160 L126 170 L118 170 Z" fill="' + pele + '"/>'
            '<circle cx="123" cy="148" r="14" fill="' + pele + '"/>'
            '<path d="M109 146 Q110 130 126 132 Q138 134 137 146 Q130 138 118 140 Z" fill="#3b2f2a"/>'
            '<circle cx="129" cy="149" r="1.8" fill="#3b2f2a" stroke="none"/>'
            '<path d="M128 156 q4 1 6 -2" fill="none" stroke-width="1.6"/>')


def cenario_desporto():
    publico = random.Random(7)                   # gerador próprio, para o público ser sempre igual
    cores = ["#e63946", "#ffd23f", "#2f8fe0", "#ffffff", "#ff7a59", "#3cc7a6"]
    adeptos = "".join(f'<circle cx="{x + publico.randint(-2, 2)}" cy="{y}" r="4" fill="{publico.choice(cores)}"/>'
                      for y in (76, 90, 104, 118) for x in range(6, 320, 11))
    riscas = "".join(f'<rect x="{x}" y="140" width="40" height="160" fill="#63b961"/>' for x in range(0, 320, 80))
    rede = "".join(f'<path d="M{x} 132 V196" />' for x in range(236, 300, 8)) + \
        "".join(f'<path d="M232 {y} H300" />' for y in range(138, 198, 8))
    return (defs("#bfe3ff", "#eef8ff") + nuvem(60, 30, .8) + nuvem(250, 24, .6) +
            '<path d="M0 64 L320 64 L320 140 L0 140 Z" fill="#7d95b3"/>'
            '<path d="M-4 58 L324 58 L324 66 L-4 66 Z" fill="#5b6f8a"/>'
            '<g stroke="none">' + adeptos + '</g>'
            '<path d="M0 140 L320 140 L320 300 L0 300 Z" fill="#6cc36a"/>'
            '<g stroke="none">' + riscas + '</g>'
            '<path d="M0 140 H320" stroke="#ffffff" stroke-width="3"/>'
            '<path d="M196 300 Q206 214 216 140" fill="none" stroke="#ffffff" stroke-width="3" stroke-opacity=".8"/>'
            '<g stroke="#ffffff" stroke-opacity=".7" stroke-width="1.2">' + rede + '</g>'
            '<path d="M228 196 V128 H304 V196" fill="none" stroke="#ffffff" stroke-width="6"/>'
            '<path d="M228 196 V128 H304 V196" fill="none" stroke-width="1.4"/>'
            + jogador_futebol() +
            # bola com riscos de movimento
            '<path d="M196 230 h-14 M198 240 h-18 M196 250 h-12" stroke="#ffffff" stroke-width="3" stroke-linecap="round"/>'
            '<circle cx="210" cy="240" r="11" fill="#ffffff"/>'
            '<path d="M210 234 l5 4 -2 6 -6 0 -2 -6 Z" fill="#1d2b3a"/>'
            + relva((30, 70, 150, 250, 296), 292, "#3f8f45"))


# ---------------------- PAÍSES: um globo e um avião ----------------------
def cenario_paises():
    return (defs("#a9dcff", "#eaf7ff") + sol(46, 46, 16) + nuvem(250, 54, .9) + nuvem(150, 30, .6) +
            # monumentos ao longe (Torre Eiffel, pirâmide e um farol)
            '<g fill="#a9c7dc" stroke-opacity=".4">'
            '<path d="M30 236 Q42 206 45 150 L51 150 Q54 206 66 236 L57 236 Q48 216 39 236 Z"/>'
            '<path d="M38 210 H58 M43 182 H53" fill="none"/><path d="M48 150 V140" fill="none"/>'
            '<path d="M240 236 L276 192 L312 236 Z"/>'
            '<path d="M8 236 L12 192 L20 192 L24 236 Z"/><rect x="10" y="184" width="12" height="8"/></g>'
            '<path d="M0 232 Q90 222 170 230 T320 228 L320 300 L0 300 Z" fill="#cfe8c2"/>'
            # suporte do globo
            '<path d="M160 240 L160 266" stroke-width="6"/>'
            '<path d="M128 280 Q160 262 192 280 Z" fill="#c9a227"/>'
            '<path d="M92 158 A68 68 0 0 0 228 158" fill="none" stroke="#c9a227" stroke-width="7"/>'
            '<path d="M92 158 A68 68 0 0 0 228 158" fill="none" stroke-width="1.4"/>'
            # globo: oceano, continentes e linhas
            '<circle cx="160" cy="158" r="58" fill="#4aa3e8"/>'
            '<path d="M120 118 Q136 106 150 116 Q160 126 148 136 Q156 150 140 158 Q128 150 126 138 Q112 132 120 118 Z" fill="#7cc96b"/>'
            '<path d="M152 160 Q170 152 178 166 Q184 186 170 204 Q160 198 158 182 Q148 172 152 160 Z" fill="#7cc96b"/>'
            '<path d="M172 112 Q192 106 206 122 Q212 140 198 146 Q186 138 182 128 Q170 124 172 112 Z" fill="#7cc96b"/>'
            '<path d="M196 168 Q208 166 210 178 Q202 186 194 180 Z" fill="#7cc96b"/>'
            '<g fill="none" stroke="#ffffff" stroke-opacity=".45" stroke-width="1.2">'
            '<ellipse cx="160" cy="158" rx="58" ry="20"/><ellipse cx="160" cy="158" rx="24" ry="58"/>'
            '<path d="M102 158 H218"/></g>'
            '<path d="M128 122 Q140 110 156 108" fill="none" stroke="#ffffff" stroke-opacity=".7" stroke-width="4" stroke-linecap="round"/>'
            # avião com rasto
            '<path d="M18 104 Q60 70 110 76" fill="none" stroke="#ffffff" stroke-width="3" stroke-dasharray="6 7" stroke-linecap="round"/>'
            '<g transform="translate(118 72) rotate(-12)">'
            '<path d="M0 0 Q4 -6 30 -6 Q44 -6 48 0 Q44 6 30 6 L4 6 Q0 4 0 0 Z" fill="#ffffff"/>'
            '<path d="M18 0 L8 -20 L16 -20 L30 -2 Z" fill="#e63946"/><path d="M18 2 L10 18 L18 18 L30 4 Z" fill="#e63946"/>'
            '<path d="M2 -2 L-4 -14 L4 -14 L10 -4 Z" fill="#e63946"/>'
            '<circle cx="34" cy="-1" r="1.6" fill="#2f8fe0"/><circle cx="28" cy="-1" r="1.6" fill="#2f8fe0"/><circle cx="22" cy="-1" r="1.6" fill="#2f8fe0"/>'
            '</g>' + relva((90, 214, 300), 292))


# ---------------------- HISTÓRIA: livros, pergaminho e uma caravela ----------------------
def cenario_historia():
    ondas = "".join(f'<path d="M{x} {y} q10 -6 20 0 t20 0" fill="none" stroke="#ffffff" stroke-width="2" stroke-opacity=".7"/>'
                    for x, y in ((180, 246), (240, 258), (200, 276), (270, 284), (150, 290)))
    return (defs("#f8ecd2", "#ecd5a8") +
            # rosa dos ventos
            '<g transform="translate(56 58)" stroke-width="1.4">'
            '<circle r="30" fill="#f6e3bb"/><circle r="22" fill="none" stroke-opacity=".5"/>'
            '<path d="M0 -36 L6 -6 L0 0 L-6 -6 Z" fill="#c0392b"/><path d="M0 36 L6 6 L0 0 L-6 6 Z" fill="#8b5a2b"/>'
            '<path d="M-36 0 L-6 -6 L0 0 L-6 6 Z" fill="#8b5a2b"/><path d="M36 0 L6 -6 L0 0 L6 6 Z" fill="#8b5a2b"/>'
            '<text y="-40" font-size="11" text-anchor="middle" fill="#3b2f2a" stroke="none" font-family="Georgia, serif">N</text></g>'
            # mar (à direita)
            '<path d="M168 238 Q220 228 266 236 T320 232 L320 300 L168 300 Z" fill="#7fb6c9"/>' + ondas +
            # caravela (velas latinas, triangulares, com a cruz da Ordem de Cristo)
            '<path d="M196 230 L300 230 Q292 254 262 256 L224 256 Q202 252 196 230 Z" fill="#8b5a2b"/>'
            '<path d="M204 238 H292" stroke-opacity=".5" fill="none"/>'
            '<path d="M232 230 V112 M268 230 V130" stroke-width="3"/>'
            '<path d="M232 116 Q262 160 232 222 L210 222 Q228 170 232 116 Z" fill="#fbf3dc"/>'
            '<path d="M268 134 Q298 172 268 224 L250 224 Q266 178 268 134 Z" fill="#fbf3dc"/>'
            '<path d="M233 162 h6 v8 h8 v6 h-8 v8 h-6 v-8 h-8 v-6 h8 Z" fill="#c0392b" stroke="none"/>'
            '<path d="M271 176 h5 v6 h6 v5 h-6 v6 h-5 v-6 h-6 v-5 h6 Z" fill="#c0392b" stroke="none"/>'
            '<path d="M232 112 l14 4 -14 4" fill="#c0392b"/>'
            # secretária com livros antigos e um pergaminho (à esquerda)
            '<path d="M0 262 H186 V300 H0 Z" fill="#b07a45"/><path d="M0 262 H186" stroke-width="2.4" fill="none"/>'
            '<rect x="16" y="244" width="96" height="18" rx="2" fill="#8c2f39"/>'
            '<rect x="24" y="226" width="84" height="18" rx="2" fill="#2f5d8c"/>'
            '<rect x="20" y="208" width="80" height="18" rx="2" fill="#4f7a3a"/>'
            '<path d="M30 253 H100 M36 235 H96 M32 217 H88" stroke="#e6c35c" stroke-width="2" fill="none"/>'
            '<path d="M122 246 L172 242 L173 260 L123 263 Z" fill="#fbf0d4"/>'
            '<ellipse cx="122" cy="254" rx="5" ry="11" fill="#ead9ae"/><ellipse cx="173" cy="251" rx="5" ry="11" fill="#ead9ae"/>'
            '<path d="M132 250 L164 247 M132 256 L160 254" stroke-opacity=".45" fill="none"/>'
            # pena e tinteiro
            '<path d="M70 206 Q60 172 84 150 Q80 182 74 206 Z" fill="#ffffff"/>'
            '<path d="M84 150 L70 208" fill="none" stroke-width="1.4"/>'
            '<path d="M62 206 L82 206 L80 194 L64 194 Z" fill="#3b2f2a"/>')


# ---------------------- MÚSICA: um palco com guitarra ----------------------
def nota_musical(x, y, cor, dupla=False):
    """Uma nota musical (♪ ou ♫) desenhada com formas."""
    if dupla:
        return (f'<g class="nota"><ellipse cx="{x}" cy="{y}" rx="7" ry="5" fill="{cor}" transform="rotate(-20 {x} {y})"/>'
                f'<ellipse cx="{x + 22}" cy="{y - 6}" rx="7" ry="5" fill="{cor}" transform="rotate(-20 {x + 22} {y - 6})"/>'
                f'<path d="M{x + 6} {y - 2} V{y - 30} L{x + 28} {y - 36} V{y - 8}" fill="none" stroke-width="2.6"/></g>')
    return (f'<g class="nota"><ellipse cx="{x}" cy="{y}" rx="7" ry="5" fill="{cor}" transform="rotate(-20 {x} {y})"/>'
            f'<path d="M{x + 6} {y - 2} V{y - 30} Q{x + 18} {y - 22} {x + 14} {y - 12}" fill="none" stroke-width="2.6"/></g>')


def cenario_musica():
    tabuas = "".join(f'<path d="M{x} 236 L{x * 1.2 - 32:.0f} 300" stroke-opacity=".3" fill="none"/>' for x in range(20, 320, 40))
    return (defs("#efdcff", "#ffdcec") +
            # holofotes
            '<path d="M70 0 L20 236 L130 236 Z" fill="#ffffff" opacity=".35" stroke="none"/>'
            '<path d="M250 0 L190 236 L300 236 Z" fill="#ffffff" opacity=".35" stroke="none"/>'
            # cortinas
            '<path d="M0 0 L54 0 Q40 90 50 236 L0 236 Z" fill="#b0306a"/>'
            '<path d="M320 0 L266 0 Q280 90 270 236 L320 236 Z" fill="#b0306a"/>'
            '<path d="M18 10 Q12 120 20 230 M36 6 Q28 120 36 232 M302 10 Q308 120 300 230 M284 6 Q292 120 284 232" '
            'fill="none" stroke="#7d1f4a" stroke-width="2"/>'
            '<path d="M0 0 H320 V22 Q240 34 160 24 Q80 34 0 22 Z" fill="#8f2457"/>'
            # palco
            '<path d="M0 236 H320 V300 H0 Z" fill="#c98a5a"/>' + tabuas +
            '<path d="M0 236 H320" stroke-width="2.4"/>'
            # coluna de som
            '<rect x="62" y="176" width="46" height="60" rx="4" fill="#3d3550"/>'
            '<circle cx="85" cy="194" r="9" fill="#6b6280"/><circle cx="85" cy="220" r="12" fill="#6b6280"/>'
            '<circle cx="85" cy="220" r="4" fill="#3d3550"/>'
            # guitarra no suporte
            '<path d="M150 236 L160 206 L170 236" fill="none" stroke-width="3"/>'
            '<path d="M160 218 Q132 220 134 196 Q136 182 148 178 Q140 166 150 156 Q160 150 170 156 Q180 166 172 178 '
            'Q184 182 186 196 Q188 220 160 218 Z" fill="#e07a2f"/>'
            '<circle cx="160" cy="180" r="7" fill="#5b2c0f"/>'
            '<rect x="155" y="80" width="10" height="84" rx="2" fill="#8a5a33"/>'
            '<path d="M153 64 L167 64 L169 84 L151 84 Z" fill="#5b3a1f"/>'
            '<path d="M157 82 V204 M160 82 V204 M163 82 V204" stroke="#f3e2c0" stroke-width=".8" fill="none"/>'
            '<rect x="150" y="200" width="20" height="5" rx="1" fill="#3b2f2a"/>'
            # microfone
            '<path d="M236 236 L244 228 L252 236 M244 228 V140" fill="none" stroke-width="3"/>'
            '<path d="M244 140 L226 124" stroke-width="3"/>'
            '<ellipse cx="222" cy="120" rx="8" ry="10" fill="#5c5470" transform="rotate(-40 222 120)"/>'
            + nota_musical(110, 120, "#7a2e8f") + nota_musical(196, 96, "#d6336c", dupla=True)
            + nota_musical(262, 176, "#7a2e8f") + nota_musical(84, 72, "#d6336c"))


CENARIOS = {"animais": cenario_animais, "comida": cenario_comida, "desporto": cenario_desporto,
            "paises": cenario_paises, "historia": cenario_historia, "musica": cenario_musica}

DESCRICOES_CENARIOS = {
    "animais": "Um jardim zoológico com uma girafa atrás da vedação, uma árvore e um leão sentado.",
    "comida": "Uma cozinha com um tacho a fumegar, pão, fruta e frascos na prateleira.",
    "desporto": "Um jogador de futebol a rematar a bola para a baliza, num estádio cheio.",
    "paises": "Um globo terrestre, um avião a voar e monumentos ao longe.",
    "historia": "Livros antigos, um pergaminho, uma rosa dos ventos e uma caravela no mar.",
    "musica": "Um palco com cortinas, uma guitarra, um microfone e notas musicais a flutuar.",
}


def confettis():
    """Papelinhos coloridos para quando o jogador acerta."""
    cores = ["#ff7a59", "#3cc7a6", "#2f8fe0", "#ffc93c", "#b46cf0", "#e63946"]
    posicoes = [(24, 30), (64, 80), (104, 22), (150, 60), (196, 34), (240, 86), (286, 28), (40, 130),
                (130, 110), (220, 130), (300, 110), (170, 16)]
    # o <g class="voa"> é animado pelo CSS; o <rect> lá dentro mantém a sua rotação
    return "".join(f'<g class="voa v{i % 4}"><rect x="{x}" y="{y}" width="9" height="4" rx="1" '
                   f'fill="{cores[i % len(cores)]}" transform="rotate({i * 37} {x} {y})"/></g>'
                   for i, (x, y) in enumerate(posicoes))


def desenhar_cenario(tema, festa=False):
    """O SVG completo do cenário do tema (com confettis se o jogador acertou)."""
    desenho = CENARIOS[tema]()
    corte = desenho.index("</defs>") + len("</defs>")
    # o fundo (degradê) fica de fora; o resto passa pelo filtro "lapis" e leva contorno de tinta
    fundo = desenho[:corte] + desenho[corte:].split("/>", 1)[0] + "/>"
    resto = desenho[len(fundo):]
    descricao = DESCRICOES_CENARIOS[tema] + (" Há confettis a voar: acertaste!" if festa else "")
    return (f'<svg class="cenario-svg" viewBox="0 0 {LARGURA} {ALTURA}" preserveAspectRatio="xMidYMid slice" '
            f'role="img" aria-labelledby="cenario-titulo"><title id="cenario-titulo">{esc(descricao)}</title>'
            f'{fundo}<g filter="url(#lapis)" stroke="{TINTA}" stroke-width="1.8" stroke-linejoin="round" '
            f'stroke-linecap="round">{resto}</g>'
            + (confettis() if festa else "") +
            f'<rect width="{LARGURA}" height="{ALTURA}" filter="url(#papel)"/></svg>')


# =====================================================================
# 6. SERVIDOR WEB
# Pequeno servidor feito só com a biblioteca standard (http.server).
# Cada clique do jogador é um formulário enviado ao servidor (POST); o servidor
# atualiza a partida e manda o browser voltar à página do jogo (GET).
# =====================================================================
PORTA = 8001                                  # o jogo abre em http://127.0.0.1:8001
SESSOES = {}                                  # cookie 'sid' -> Sessao (cada visitante tem a sua, em memória)
TAMANHO_MAXIMO_POST = 2_000                   # limite de segurança para os dados de um formulário
NOME_COOKIE = "sid_palavra"                   # nome diferente do outro jogo, para não se misturarem


class Manipulador(BaseHTTPRequestHandler):
    """Trata cada pedido do browser. GET = mostrar páginas, POST = ações do jogador."""

    def _sessao(self):
        """Devolve a sessão deste jogador e o novo identificador (se foi preciso criar uma)."""
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        sid = cookie[NOME_COOKIE].value if NOME_COOKIE in cookie else None
        if sid in SESSOES:
            return SESSOES[sid], None
        sid = secrets.token_hex(16)
        SESSOES[sid] = Sessao()
        return SESSOES[sid], sid

    def _cabecalho_cookie(self, novo_sid):
        if novo_sid:
            self.send_header("Set-Cookie", f"{NOME_COOKIE}={novo_sid}; Path=/; HttpOnly; SameSite=Lax")

    def _responder(self, texto, tipo="text/html; charset=utf-8", codigo=200, novo_sid=None):
        """Envia uma resposta de texto (HTML ou CSS) ao browser."""
        corpo = texto.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")       # F5 mostra sempre a versão mais recente
        self._cabecalho_cookie(novo_sid)
        self.end_headers()
        self.wfile.write(corpo)

    def _redirecionar(self, destino="/", novo_sid=None):
        """Manda o browser para outra página (assim, carregar em F5 não reenvia o formulário)."""
        self.send_response(303)
        self.send_header("Location", destino)
        self._cabecalho_cookie(novo_sid)
        self.end_headers()

    def do_GET(self):
        """O browser pede uma página (GET)."""
        caminho = self.path.split("?")[0]
        try:
            if caminho == "/estilo.css":
                return self._responder(FICHEIRO_CSS.read_text(encoding="utf-8"), "text/css; charset=utf-8")
            if caminho == "/favicon.ico":
                self.send_response(204)                      # sem conteúdo (o ícone já vem no HTML)
                return self.end_headers()
            sessao, novo_sid = self._sessao()
            if caminho == "/":
                partida = sessao.partida
                if partida is None:
                    pagina = pagina_inicio(sessao)
                elif partida.terminou:
                    pagina = pagina_fim(sessao)
                else:
                    pagina = pagina_jogo(sessao)
            elif caminho == "/inicio":
                pagina = pagina_inicio(sessao)
            elif caminho == "/como-jogar":
                pagina = pagina_como_jogar()
            else:
                return self._responder("Página não encontrada.", codigo=404)
            self._responder(pagina, novo_sid=novo_sid)
        except Exception as erro:                            # mostra o erro no terminal e no browser
            traceback.print_exc()
            self._responder(f"Erro no servidor: {esc(erro)}", codigo=500)

    def do_POST(self):
        """O jogador carregou num botão (POST)."""
        try:
            tamanho = min(int(self.headers.get("Content-Length", 0) or 0), TAMANHO_MAXIMO_POST)
            campos = parse_qs(self.rfile.read(tamanho).decode("utf-8"))
            pedir = lambda nome: campos.get(nome, [""])[0].strip()      # lê um campo do formulário
            sessao, novo_sid = self._sessao()
            partida = sessao.partida

            # Depois da ação, o browser volta à página do jogo. O "#jogo" (ou "#pistas") faz a página
            # voltar logo à grelha: no telemóvel não é preciso fazer scroll depois de cada letra.
            destino = "/"
            if self.path == "/tema":                         # escolher um tema (ou "jogar outra vez")
                escolha = pedir("tema")
                if escolha in TEMAS or escolha == "surpresa":
                    sessao.nova_partida(escolha)
            elif partida is not None and self.path == "/jogada":
                partida.escrever(pedir("palavra")[:40], pedir("acao") or "tentar")
                destino = "/#jogo"
            elif partida is not None and self.path == "/pista":
                partida.pedir_pista()
                destino = "/#pistas"
            elif partida is not None and self.path == "/desistir":
                partida.desistir()
            sessao.depois_da_jogada()
            if sessao.partida is not None and sessao.partida.terminou:
                destino = "/"                                # no fim, mostra o resultado desde o início
            self._redirecionar(destino, novo_sid)
        except Exception as erro:
            traceback.print_exc()
            self._responder(f"Erro no servidor: {esc(erro)}", codigo=500)

    def log_message(self, formato, *argumentos):
        """Não enche o terminal com uma linha por cada pedido."""


# =====================================================================
# 7. ARRANQUE
# =====================================================================
def main():
    """Verifica os ficheiros e os dados, arranca o servidor e abre o browser."""
    for ficheiro in (FICHEIRO_HTML, FICHEIRO_CSS):
        if not ficheiro.exists():
            print(f"ERRO: não encontrei o ficheiro {ficheiro.name}. "
                  "Põe o palavra_secreta.py, o paginas.html e o estilo.css na mesma pasta "
                  "(e confirma que os nomes estão exatamente assim, sem números como '(1)').")
            return
    verificar_dados()
    try:
        servidor = ThreadingHTTPServer(("127.0.0.1", PORTA), Manipulador)
    except OSError:
        print(f"ERRO: a porta {PORTA} já está ocupada. O jogo já está aberto noutro terminal? "
              "Fecha-o (Ctrl+C) ou muda o número da PORTA no código.")
        return
    url = f"http://127.0.0.1:{PORTA}"
    print(f"Palavra Secreta a correr em {url}  (Ctrl+C para parar)")
    webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor terminado.")


# Só arranca o jogo quando este ficheiro é executado diretamente
if __name__ == "__main__":
    main()

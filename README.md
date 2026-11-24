# FVMultimedia-2026-2027
Projeto Multimédia de Programacao com Inteligencia Artificial

Nome da Aplicação / Dashboard Web: "Sala de Jogos"

Disciplina: Oficina de Multimédia - 12.º Ano - CRSI, turno 2

Ano Letivo: 2026/2027   

Autor: Francisco Vicente

Turma: Oficina de Multimédia Turno 2  

Link da Aplicação Web: link (a adicionar) 
2. Visão Geral do Projeto


Descrição: O site "sala de jogos" é uma pequena interface de 3 jogos bastante interativos. Algo simples, no entanto jogos com alguma profundidade, exigência de raciocínio e desafiadores da visão estratégica de cada um.  

Proposta Escolhida: Proposta 1
Embora nao se encaixe perfeitamente na proposta 1, é aquele que mais se aproxima.

3. Estrutura do Código e Funcionalidades Integradas

Ao longo dos 3 jogos fui capaz de utilizar bastante do codigo e das funcionalidades aprendidas em aula. No geral, utilizei variaveis, int e float, atribuição multipla, case sensitive, prints e f-strings, utilizei bastante as listas e indices, tuplos, utilizei tambem variaas das funcoes extras que o professor nos deu no classroom, utilizei tambem sets, dicionários. Para além disso, integrei if, elif e else, and, or, pontuação com score =+1, e muitas mais mas estes foram os principais utilizados que trabalhámos em aula.

A maneira como o código está dividido é, de maneira geral, a seguinte:
1. Importações	
2. Constantes	
3. Dados	
4. Regras do jogo	
5. Páginas	
5b. Desenhos SVG	
6. Servidor web	
7. Arranque


  Dentro do jogo "Banco ou Falência"
   
Dados: cerca de 40 decisões (divididas pelas 4 fases da vida) e 44 eventos aleatórios.
Regras: a classe Jogador (dinheiro, idade, esperança de vida...) e a classe Jogo (turnos, efeitos das escolhas, os 5 finais).
5b: a personagem que muda com a riqueza, a idade e a saúde. É a maior parte do ficheiro.

  Dentro do jogo "Palavra Secreta"

Dados: 6 temas com 30 palavras cada, e para cada palavra 2 pistas e 1 curiosidade.
Regras: a função avaliar() (decide as cores das letras), e as classes Partida, Estatisticas e Sessao.
5b: os 6 cenários dos temas (o zoológico, a cozinha, o estádio...).

  Dentro do jogo "Rota das Especiarias"

Dados: produtos, 19 portos, 76 mercadores, 6 personalidades com as falas, e os eventos no mar.
Mapa e rotas: os contornos dos continentes e o algoritmo que calcula o caminho mais curto no mar (Dijkstra) e os dias de viagem.
Regras: a classe Jogo (negociar, comprar e vender, navegar, eventos, naufrágio, fim do jogo).
Desenhos SVG: os portos, os mercadores, o mar, o palácio e o mapa.
Páginas.
Música de fundo: o Python compõe a música e cria o ficheiro de som.
Servidor web e arranque.



4. Registo de Utilização da IA 

Para os prompts que coloquei na inteligência artificial, mais precisamente o Claude code, várias vezes pedia lhe para me criar prompts específicos para certas funções, de forma a maximizar e otimizar o seu uso. No entanto, colocarei tudo o que questionei, ordenei, e de todas as formas que colaborei com a IA.


prompts iniciais para a criação incial dos jogos o do código em pyhton, html e css:
Prompt para o "Banco ou Falência":

  "bem, ja sabes o que quero, portanto faz me um prompt para eu pedir o código, em python e todo comentado, disto:
jogo banco ou falencia. um jogador comeca com 18 anos, herdou/ganhou 100.000€ e agora tem de tomar certas decisoes de vida para, ao chegar as 65, reforma, conseguir liberdade financeira ou ter uma reforma pobre. cada descisao pode adicionar lhe anos de vida, adicionar dinheiro e futuros rendimentos, tambem perder dinheiro. tambem podem acontecer eventos aleatórios que tiram dinheiro, adicionem, ou obriguem o jogador a tomar decisoes. antes de me enviares o prompt dá me um resumo de tudo"

Prompt para o jogo "Palavra Secreta":

  "ok. cria me um prompt para eu te pedir o jogo: 
wordle em portugues, por temas. o tema é escolhido inicialmente pelo jogador, e cada tema tem um banco de por exemplo, 30 palavras. é escolhida 1 ao acaso e depois joga se o jogo. quero isso das cores com as letras para ajudar o jogador a perceber que letras funcionam, um botao para dicas, e no fim, quando/se o jogador acertar, queria que desses uma curiosidade cobre o nome que foi escolhido. tema de cores dependendo do tema que for escolhido. por exmplo, se for animais talvez um zoologico ou algo do genero, se for história uns livros, uns barcos, se for desporto alguem a fazer desporto, tu percebes. relembrar, que o jogo tem de ser em python puro e quero o python o html e o css em ficheiros separados"

prompt gerado:

  Quero que me cries um jogo para o meu site de 3 jogos (projeto escolar de Multimédia). O primeiro jogo, o "Banco ou Falência", já está feito; este é o segundo.
O JOGO: "Palavra Secreta", um Wordle em português, por temas.
REGRAS TÉCNICAS (obrigatórias):
- Python puro: só a biblioteca standard (http.server, string.Template, random, etc.). Não uses pip, Flask, Pygame, imagens externas, CDNs nem bibliotecas de JavaScript.
- Exatamente 3 ficheiros separados: palavra_secreta.py, paginas.html e estilo.css. O Python não pode ter HTML nem CSS escritos lá dentro (só pequenos pedaços de SVG gerados pelo Python, se for preciso).
- Sem JavaScript (ou o mínimo possível). Cada jogada é um formulário enviado ao servidor.
- Usa a mesma estrutura do Banco ou Falência: servidor http.server em 127.0.0.1, o browser abre sozinho, o paginas.html dividido em blocos com marcadores <!--@ nome --> e campos $campo, e uma sessão por cookie.
- Usa a porta 8001, para poder correr ao mesmo tempo que o primeiro jogo (que usa a 8000).
- Comentários no código em português de Portugal, claros, para eu conseguir explicar o código numa apresentação.
- Se faltar o paginas.html ou o estilo.css, o programa deve mostrar uma mensagem de erro clara.
COMO SE JOGA:
1. Ecrã inicial: o jogador escolhe um tema, cada um com ícone e nome. Temas: Animais, Comida, Desporto, Países, História e Música, mais a opção "Surpresa", que sorteia um tema.
2. Cada tema tem um banco de 30 palavras em português, entre 4 e 7 letras. É escolhida uma ao acaso, sem repetir palavras já jogadas na mesma sessão.
3. A grelha mostra o número de letras da palavra e o jogador tem 6 tentativas.
4. Depois de cada tentativa, as letras ficam coloridas:
   - verde: letra certa no sítio certo
   - amarelo: a letra existe, mas noutro sítio
   - cinzento: a letra não existe na palavra
   (Trata corretamente as letras repetidas, como no Wordle original.)
5. Um teclado no ecrã (botões) que vai ficando colorido conforme as letras já testadas. Também deve dar para escrever a palavra numa caixa de texto e carregar em "Tentar".
6. Acentos e cedilhas: o jogador não precisa de os escrever ("MACA" conta como "MAÇÃ"), mas no fim a palavra aparece bem escrita.
7. Aceita qualquer combinação de letras com o tamanho certo (não é preciso dicionário). Se o tamanho estiver errado, mostra um aviso simpático e não gasta tentativa.
8. Botão "💡 Pista": cada palavra tem 2 pistas, reveladas uma de cada vez. Usar pistas tira pontos.
9. Pontuação: mais pontos por acertar em menos tentativas e sem pistas.
10. No fim:
    - Se acertar: mensagem de parabéns, a palavra, os pontos e uma CURIOSIDADE interessante sobre essa palavra (cada palavra tem a sua curiosidade).
    - Se perder: mostra qual era a palavra e também a curiosidade.
    - Botões "Jogar outra vez (mesmo tema)" e "Mudar de tema".
    - Estatísticas da sessão: jogos, vitórias, sequência de vitórias e média de tentativas, também por tema.
11. Uma página "Como jogar" com as regras e um exemplo das cores.
ASPETO VISUAL (muito importante):
- Estilo luminoso e fresco, a combinar com o primeiro jogo.
- O tema de cores e o cenário mudam conforme o tema escolhido, com uma ilustração em SVG desenhada pelo Python (sem imagens externas), com ar desenhado à mão e não artificial. Por exemplo:
  - Animais: um zoológico (vedação, árvores, uma girafa ou um leão), em tons verdes e terra.
  - Comida: uma cozinha ou mesa (tacho, pão, fruta), em tons quentes de laranja e vermelho.
  - Desporto: alguém a jogar à bola num campo ou estádio, em verde relva e azul.
  - Países: um globo, aviões ou monumentos, em tons de azul e céu.
  - História: livros antigos, um pergaminho e uma caravela, em tons sépia e pergaminho.
  - Música: notas musicais, uma guitarra e um palco, em roxo e rosa.
- As cores das letras (verde, amarelo, cinzento) devem ver-se bem em todos os temas, com bom contraste.
- Animações simples em CSS: as letras a "virar" quando aparecem as cores e um pequeno salto quando ganha. Respeitar prefers-reduced-motion.
- Tem de funcionar bem no computador e no telemóvel.
O QUE QUERO QUE ME ENTREGUES:
1. Os 3 ficheiros completos, prontos a correr.
2. Uma lista curta do que fizeste e como está organizado o código.
3. Como correr o jogo no VS Code.
4. Deixa-me ver e jogar o jogo."


Prompt para o jogo: "Rota das especiarias":

  "entao pronto quero que o terceiro jogo seja o da ilha das especiarias. cria me um prompt para eu te pedir o jogo com as seguintes caracteristicas:
quero um jogo da rota das especiarias. o rei da envia me uma carta a dizer que tenho 2 anos para voltar a lisboa e mostrar o resultado de todo o meu trabalho de bom mercador. comecamos com recursos aleatorios. pode ser dinheiro, especiarias, ou um mix dos dois. comecamos no porto de lisboa o ecrã seja a aparencia do porto, com diverentes mercadores clicáveis que, ao clicar, abrimos uma conversa com ele, onde podemos vender lhed o que eles estão a pedir, ou propor lhes algo que temos. (Para além dos mercadores, quero tambem a opcao de voltar a navegar). os mercadores nao devem aceitar nem rejeitar sempre. deve ser flexivel a negociação de modo a que o jogo tenha a sua piada. o mapa deve conter portos famosos de todo o mundo da altura. os da india, os de portugal, talvez uns em inglaterra, na grecia e ao longo da costa africana. os mercadores tem personalidades e podem ser, por exemplio, vigaristas que nos vendem produto falso, no entanto tambem podem ser honestos, etc. queria tambem que acontecessem eventos aleatórios, como o meu barco afundar durante uma viagem e eu encontrar uns amigos, ou simplesmente perder a mercadoria.  quero que o tempo do jogo seja 2 anos, e que as viagens tirem dias. viagens mais perto como lisboa cabo verde tiram menos dias, mas por exemplo lisboa a goa dura mais dias.  quero que dê, mais ou menos, para fazer 7-9 viagens, entre umas mais curtas e outras mais longas. no fim, tendo em conta a qualidade do meu trabalho, posso receber honras do rei. Muito dinheiro : "Mercador Mais Rico do Reino", Muitos portos :"Grande Explorador" (o Rei põe o meu nome num mapa), Muitas amizades : "Embaixador dos Sete Mares", Tudo equilibrado : "Lenda dos Descobrimentos", Aliado dos piratas : "Corsário do Rei" 🏴‍☠️, Voltei com pouco :"Regressou com Histórias para Contar". acima de tudo quero que seja um jogo bastante visual e nada como o do banco ou falencia onde tenho um fundo branco e botoes pra clicar."


  Prompt gerado:
"Quero que me cries o terceiro jogo para o meu site de jogos (projeto escolar de Multimédia). Os dois primeiros, "Banco ou Falência" e "Palavra Secreta", já estão feitos.
O JOGO: "Rota das Especiarias", um jogo de comércio e exploração nos Descobrimentos.
REGRAS TÉCNICAS (obrigatórias):
- Python puro: só a biblioteca standard (http.server, string.Template, random, etc.). Não uses pip, Flask, Pygame, imagens externas, CDNs nem bibliotecas de JavaScript.
- SEM JAVASCRIPT NENHUM (o professor não deixa). Toda a interação é feita com links e formulários enviados ao servidor, e as animações são em CSS.
- Exatamente 3 ficheiros separados: rota_especiarias.py, paginas.html e estilo.css. O Python não pode ter HTML nem CSS escritos lá dentro: os pedaços de HTML ficam em blocos no paginas.html. A única exceção são os desenhos SVG gerados pelo Python.
- Usa a mesma estrutura dos outros jogos: servidor http.server em 127.0.0.1, o browser abre sozinho, o paginas.html dividido em blocos com marcadores <!--@ nome --> e campos $campo, e uma sessão por cookie.
- Usa a porta 8002, para poder correr ao mesmo tempo que os outros jogos (8000 e 8001).
- Comentários no código em português de Portugal, claros, para eu conseguir explicar o código numa apresentação.
- Se faltar o paginas.html ou o estilo.css, ou se a porta estiver ocupada, o programa deve mostrar uma mensagem de erro clara.
HISTÓRIA E OBJETIVO:
1. O jogo começa com uma CARTA DO REI D. Manuel I, num pergaminho com selo de lacre: "Tens 2 anos para voltares a Lisboa e mostrares o resultado de todo o teu trabalho de bom mercador." O jogo começa em 1515, para os portos serem historicamente corretos (Goa e Malaca já são portuguesas).
2. Recursos iniciais ALEATÓRIOS: só dinheiro, só especiarias ou um pouco de cada. A carta diz com o que começas.
3. Começamos no porto de Lisboa.
4. O jogo dura 2 anos (cerca de 730 dias). As viagens gastam dias conforme a distância: viagens curtas (Lisboa–Cabo Verde) gastam poucos dias, viagens longas (Lisboa–Goa) gastam muitos. Calibra os dias para que um jogo normal dê mais ou menos 7 a 9 viagens, entre curtas e longas, e confirma isso com simulações. Negociar num porto também pode gastar algum tempo.
5. É obrigatório estar em Lisboa quando acabar o prazo. Se o prazo acabar e estiveres longe, o Rei fica desagradado e perdes parte do que tens. Mostra sempre a data atual (por exemplo, "14 de março de 1516") e os dias que faltam.
O PORTO (ecrã principal):
- Cada porto é uma CENA DESENHADA em SVG, com ar desenhado à mão: casas, cais, barcos, céu e água com as cores típicas da região (Lisboa com casario e a Torre de Belém, Goa com palmeiras e templos, Veneza com canais, a costa africana com feitorias...).
- Na cena há 2 a 4 MERCADORES desenhados e clicáveis. Ao clicar num, abre-se uma conversa com ele.
- Na cena há também o cais, com a opção "Voltar a navegar", que abre o mapa.
- Um painel discreto mostra: data e dias restantes, dinheiro, o porão do navio (com espaço limitado) e o estado do navio.
AS CONVERSAS E A NEGOCIAÇÃO (a parte mais importante):
- O ecrã de conversa mostra o retrato do mercador em SVG (com expressão que muda: contente, desconfiado, zangado...), balões de fala e as opções.
- Cada mercador PEDE certos produtos e TEM produtos para vender.
- Opções: vender-lhe o que ele pede, propor-lhe algo que eu tenho, comprar-lhe produtos, regatear (pedir mais ou oferecer menos) e ir embora.
- A negociação é FLEXÍVEL: os mercadores não aceitam nem rejeitam sempre. A resposta depende da personalidade, do humor, de quão justa é a proposta e da amizade que tem comigo. Podem fazer contrapropostas, e cada um tem uma "paciência": se eu exagerar muitas vezes, acaba a conversa.
- PERSONALIDADES (com falas próprias e com humor): honesto, vigarista (pode vender produto falso, por exemplo "canela" que afinal é casca de árvore, e só descubro quando a tentar vender; deve haver pistas, como um preço demasiado bom ou falas suspeitas), teimoso, generoso, desconfiado, fala-barato...
- AMIZADES: os mercadores lembram-se de mim. Se negociar bem e de forma justa, a amizade sobe e dão-me descontos, dicas sobre preços noutros portos ou pequenas missões ("traz-me seda de Malaca e pago o dobro"). Se os enganar, a amizade desce.
- Os preços mudam de porto para porto, com lógica: as especiarias são baratas na Índia e caras na Europa, o ouro vem de África, etc.
- Produtos: pimenta, canela, cravinho, noz-moscada, gengibre, seda, porcelana, ouro, marfim, açúcar, vinho, tecidos, etc.
O MAPA:
- Um mapa-múndi antigo desenhado em SVG (pergaminho, rosa dos ventos, monstros marinhos), com os PORTOS CLICÁVEIS.
- Portos famosos da época: em Portugal (Lisboa, Lagos), na Europa (Londres, Antuérpia, Veneza, Atenas), nas ilhas atlânticas (Funchal, Cabo Verde), ao longo da costa africana (São Jorge da Mina, Congo, Sofala, Moçambique, Melinde), na Arábia e Pérsia (Ormuz) e na Ásia (Calecute, Goa, Malaca).
- Ao escolher um porto, mostra os dias de viagem e a data de chegada antes de confirmar. A rota já feita fica desenhada no mapa.
- Pode haver 1 ou 2 portos secretos, que só aparecem se alguém me contar onde ficam (por exemplo, um esconderijo de piratas).
A VIAGEM E OS EVENTOS ALEATÓRIOS:
- Durante a viagem aparece um ecrã com o navio no mar (animação CSS das ondas e do barco).
- Eventos aleatórios com ilustração e escolhas, por exemplo:
  - tempestade (o navio fica danificado ou perco mercadoria);
  - naufrágio: o barco afunda, mas posso ser salvo por amigos que fiz (quanto mais amizades, maior a hipótese) ou perder quase tudo;
  - piratas: pagar, fugir, lutar ou propor uma ALIANÇA (o caminho para o título "Corsário do Rei");
  - calmaria (a viagem demora mais dias), uma ilha desconhecida, um náufrago que se junta à tripulação, uma mercadoria que se estraga, um golfinho que dá sorte...
- Os eventos não devem ser sempre os mesmos e devem fazer sentido com a zona do mapa.
- Tem de dar para reparar o navio nos portos (a pagar).
O FIM DO JOGO:
- Quando acabam os 2 anos (ou se eu decidir terminar estando em Lisboa), há uma cerimónia no palácio, com o Rei desenhado em SVG.
- O Rei avalia o meu trabalho com três medalhas: Fortuna (dinheiro e valor da carga), Descoberta (portos visitados) e Amizades (mercadores amigos e missões cumpridas).
- HONRAS DO REI (um título conforme o resultado):
  - Muito dinheiro: "Mercador Mais Rico do Reino"
  - Muitos portos: "Grande Explorador" (o Rei põe o meu nome num mapa)
  - Muitas amizades: "Embaixador dos Sete Mares"
  - Tudo equilibrado: "Lenda dos Descobrimentos"
  - Aliado dos piratas: "Corsário do Rei" 🏴‍☠️
  - Voltei com pouco: "Regressou com Histórias para Contar"
- O ecrã final mostra também o mapa com a minha rota completa, um "diário de bordo" com os momentos mais importantes, a pontuação e um botão "Nova viagem" (com recursos iniciais diferentes).
- Também deve dar para perder antes do tempo (naufrágio sem salvação, ou ficar sem dinheiro nem carga), com um final próprio.
ASPETO VISUAL (MUITO IMPORTANTE):
- O jogo tem de ser MUITO VISUAL e NADA parecido com o Banco ou Falência: nada de fundo branco com botões. O jogador clica NOS DESENHOS (mercadores, cais, portos no mapa).
- Estilo de mapa antigo e Descobrimentos: pergaminho, tinta, cores quentes, mar azul-turquesa, letras com ar antigo (fontes do sistema, sem fontes externas).
- Cada porto com o seu cenário e as suas cores; mercadores com roupas da sua região.
- Animações simples em CSS: ondas, barco a balançar, bandeiras ao vento, transições entre ecrãs. Respeitar prefers-reduced-motion.
- Tem de funcionar bem no computador e no telemóvel.
- Uma página "Como jogar" com as regras.
O QUE QUERO QUE ME ENTREGUES:
1. Os 3 ficheiros completos, prontos a correr.
2. Uma lista curta do que fizeste e como está organizado o código.
3. Como correr o jogo no VS Code.
4. Deixa-me ver e jogar o jogo."

   Para a criacao do site com os tres widgets, coloquei o seguinte prompt:

   "entao agora preciso que me cries o site com os 3 widgets que correspondem aos 3 jogos. quero um design tambem claro, fresco os 3 widgets com o nome de cada jogo e uma oequena descricao de cada um"


  
1. Prompt para conversão Web/HTML
  
2. Prompt para ampliação e construção de funcionalidades

   No jogo do "Banco ou falência" tive se intervir para adicionar algumas funcionalidades:
   No inicio, o jogo era quase como um questionário e queria que fosse mais visual, adicionando um personagem de lado que, consoante o nivel de riqueza, sofre alterações:

"Quero que faças a seguinte mudança:
MUDANÇA – PERSONAGEM À ESQUERDA QUE REFLETE A VIDA DO JOGADOR
- Durante o jogo (páginas decisao, resultado e fim), a página passa a ter duas colunas:
  à esquerda, uma personagem grande; à direita, o conteúdo de agora (painel, perguntas,
  resultados). A coluna da personagem fica fixa ao fazer scroll (position: sticky).
  Em telemóvel, a personagem passa para cima, mais pequena. O ecrã inicial fica como está.
- A personagem é desenhada em SVG inline, gerado por uma função Python nova
  (por exemplo desenhar_personagem(jogador)) que monta o SVG por camadas
  (fundo, corpo, roupa, acessórios, cenário). Num ficheiro separado do HTML, como o painel.
- O aspeto depende do estado do jogador, com cerca de 5 níveis de riqueza, calculados
  a partir do dinheiro (e talvez do saldo anual). Põe os limites como constantes no topo
  do ficheiro, para eu poder afiná-los:
    1. Falido (dinheiro negativo): roupa rasgada e com remendos, descalço ou de chinelos,
       cara triste, fundo cinzento com uma caixa de cartão ou um banco de jardim.
    2. Pobre: roupa velha e simples, ar cansado, fundo de rua modesta.
    3. Classe média: roupa casual limpa, sorriso, fundo com um apartamento normal.
    4. Rico: fato ou roupa elegante, relógio, carro bonito atrás, casa grande.
    5. Muito rico: fato de luxo, óculos de sol, joias, carro desportivo e mansão
       (com piscina ou palmeiras), talvez moedas ou notas a voar.
- Outros fatores que também mudam a personagem:
    - Idade: o cabelo fica grisalho e aparecem rugas com a idade
      (jovem → adulto → meia-idade → sénior).
    - Saúde (esperança de vida): baixa = cara pálida, olheiras, ar doente;
      alta = cara corada, ar em forma.
    - Sexo escolhido: pequenas diferenças (cabelo, roupa). "Outro" tem um visual neutro.
    - Na página "resultado": a expressão reage ao que acabou de acontecer
      (feliz se "Correu bem", preocupada se "Correu mal").
    - No ecrã final: a personagem mostra o final (por exemplo, a celebrar na liberdade
      financeira, de bengala e triste na reforma pobre, ou uma lápide/anjo se morreu
      antes da reforma).
- Debaixo da personagem, uma pequena legenda com o nível atual
  (ex.: "💰 Nível: Rico") e uma frase curta que muda com o estado.
- Estilo de desenho: simples, plano e simpático (estilo cartoon/flat), com formas SVG
  básicas (círculos, retângulos, caminhos simples). Bonito, mas sem código gigante.
- Animações suaves só com CSS (a personagem a "respirar", o carro ou a mansão a aparecer
  com fade-in quando sobe de nível), respeitando prefers-reduced-motion.
- Acessibilidade: o SVG tem role="img" e um <title>/aria-label que descreve
  a personagem (ex.: "A Maria, 42 anos, rica, com um carro e uma casa grande").


  No jogo "rota das especiarias" na sua primeira versão os portos tinham apenas 1 ou 2 comerciantes, algo que nao me agradava. Para além disso quando estava para vender alguma coisa num porto, nao me lembrava que preço tinha pago pelo produto inicialmente então achei por bem adicionar essa ferramenta no jogo.

  "ok mas quero que mudes algumas coisas dentro do jogo. quando estou para vender alguma coisa que comprei, quero qeu tenha uma nota a dizer por quanto comprei porque chega aum ponto onde nao sei a quanto comprei e estou a vender atoa. para além disso, quero que adiciones mais mercadores dentro de cada porto e adicona mais detalhes a cada vendedor em vez de ser so ele e o nome quase. adiciona tambem a musica e da me os 3 ficheiros."

   
4. Dificuldades e erros corrigidos com a IA
   No jogo do "Banco ou falência" muitas vezes os resultados visuais que a inteligencia artifical me gerava eram demasiados artificiais e nada naturais portanto, através de alguns prompts tentei combater isso:
   "gostei bastante, no entanto ha algo a melhorar. gostei de como ficou o personagem no entanto gostava que ficasse menos IA, acho que está muito artificial. Gostei do tema de cores tambem. quero que me des os ficheiros atualizados e que me deixes ver como está o jogo e jogá-lo."
    O segundo prompts serviu para combater a repetitividade de certos acontecimentos aleatórios.

   "gostei, mas agora quero que haja mais acontecimentos aleatórios, como as crises financeiras. quando testei o jogo senti que acontecia quase sempre as mesmas coisas, e queria tambem que as 16 fases não fossem sempre todas iguais, para haver mais diversidade. da me os ficheiros ja atualizados com estas mudancas e deixa me jogar o jogo"  
    
6. Otimização de Layout: O que sugeriste à IA para alterar no design - cores, 
margens, fontes, botões?

    na primeira edição do jodo "Banco ou Falência" o jogo estava com um visual bastate escuro e fiz os possiveis para torná-lo mais claro, com uma aparência mais "fresca", digamos assim:

   "Quero que me faças esta mudança:
   MUDANÇA – CORES MAIS LUMINOSAS E FRESCAS
- Hoje o tema é azul-escuro. Quero um tema claro, luminoso e fresco: fundo claro
  (branco/creme ou um gradiente suave de céu, menta ou pêssego), cartões brancos com
  sombras leves e cores de destaque alegres (por exemplo verde-menta, coral, azul-céu
  e amarelo-sol).
- Muda sobretudo as variáveis em :root, para eu poder ajustar as cores num só sítio.
  Muda também color-scheme e theme-color.
- Garante bom contraste de texto (legibilidade, WCAG AA). Os verdes, vermelhos e dourados
  dos chips, do gráfico e dos finais têm de continuar fáceis de distinguir num fundo claro.
- Revê todas as cores escritas diretamente no CSS (rgba, #hex) que só faziam sentido no
  tema escuro."
 
8. Estrutura de Ficheiros do Repositório 

Listagem simples dos ficheiros presentes na pasta:
 descircao 

1. index.html – página principal do Dashboard / Web App:

    site.html – página principal do site: mostra os 3 jogos em widgets, cada um com o nome, uma pequena descrição e o botão "Jogar". 

2. app.py - Ficheiro principal da aplicação. :

    abrir_site.py – ficheiro principal da aplicação: liga os servidores dos 3 jogos ao mesmo tempo (cada um na sua porta: 8000, 8001 e 8002) e abre o site no browser, em http://127.0.0.1:8080.  

3. style.css (Se necessário) - Folha de estilos para o layout Web 

    site.css – folha de estilos do site: cores, widgets e animações dos desenhos 

6. README.md - Este relatório de projeto. 

7. Assets - Imagens, nuvens de palavras geradas, recursos utilizados, etc. 

8. Reflexão Crítica e Aprendizagem 
Desenvolve um pequeno texto refletivo sobre o projeto que inclua: 
O que correu melhor durante o desenvolvimento. Qual foi a maior dificuldade. Como é 
que a Inteligência Artificial mudou a tua forma de programar?

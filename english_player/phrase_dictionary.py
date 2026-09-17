from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


WORD_RE = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?", re.UNICODE)


@dataclass(frozen=True)
class PhraseEntry:
    canonical: str
    translation: str
    meaning_pt: str
    example_en: str
    example_pt: str
    kind: str = "phrasal verb"
    separable: bool = False


@dataclass(frozen=True)
class PhraseMatch:
    entry: PhraseEntry
    start: int
    end: int
    matched_text: str
    word_indices: tuple[int, ...]


# canonical | tradução | significado | exemplo EN | exemplo PT | tipo | separável (0/1)
_DATA = r"""
ask out|convidar para sair|Convidar alguém para um encontro.|He asked her out for dinner.|Ele a convidou para jantar.|phrasal verb|1
back up|fazer backup / apoiar|Criar uma cópia de segurança ou dar apoio.|Back up your files before updating.|Faça backup dos arquivos antes de atualizar.|phrasal verb|1
break down|quebrar / parar de funcionar|Parar de funcionar; também pode significar perder o controle emocional.|My car broke down yesterday.|Meu carro quebrou ontem.|phrasal verb|0
break up|terminar / separar|Encerrar um relacionamento ou separar algo em partes.|They broke up last month.|Eles terminaram no mês passado.|phrasal verb|0
bring back|trazer de volta|Levar algo ou alguém de volta; também fazer lembrar.|This song brings back memories.|Esta música traz lembranças de volta.|phrasal verb|1
bring up|mencionar / criar|Introduzir um assunto numa conversa; também criar uma criança.|She brought up an important point.|Ela mencionou um ponto importante.|phrasal verb|1
call back|ligar de volta|Retornar uma ligação.|I'll call you back later.|Vou ligar para você mais tarde.|phrasal verb|1
call off|cancelar|Cancelar algo planejado.|They called off the meeting.|Eles cancelaram a reunião.|phrasal verb|1
calm down|acalmar-se|Ficar mais calmo ou fazer alguém se acalmar.|Calm down and tell me what happened.|Acalme-se e me diga o que aconteceu.|phrasal verb|0
carry on|continuar|Continuar fazendo algo.|Please carry on with your work.|Por favor, continue seu trabalho.|phrasal verb|0
catch up|colocar-se em dia / alcançar|Chegar ao mesmo nível ou atualizar-se sobre algo.|I need to catch up on my studies.|Preciso colocar meus estudos em dia.|phrasal verb|0
check in|fazer check-in|Registrar chegada em hotel, aeroporto ou evento.|We need to check in at the hotel.|Precisamos fazer check-in no hotel.|phrasal verb|0
check out|dar uma olhada / fazer check-out|Examinar algo ou registrar a saída de hotel.|Check out this new app.|Dê uma olhada neste aplicativo novo.|phrasal verb|0
clean up|limpar / arrumar|Deixar um lugar ou objeto limpo e organizado.|We need to clean up the kitchen.|Precisamos limpar a cozinha.|phrasal verb|1
come back|voltar|Retornar a um lugar ou situação.|Come back tomorrow.|Volte amanhã.|phrasal verb|0
come in|entrar|Entrar em um lugar.|Come in and sit down.|Entre e sente-se.|phrasal verb|0
come on|vamos / qual é|Usado para incentivar, apressar ou demonstrar incredulidade.|Come on, we're going to be late!|Vamos, vamos nos atrasar!|expressão|0
come over|vir até aqui / visitar|Visitar a casa ou o local de alguém.|Do you want to come over tonight?|Você quer vir aqui hoje à noite?|phrasal verb|0
come up|surgir|Aparecer ou ser mencionado inesperadamente.|Something came up at work.|Surgiu uma coisa no trabalho.|phrasal verb|0
come up with|ter uma ideia / criar|Pensar em uma solução, ideia ou plano.|We need to come up with a better plan.|Precisamos pensar em um plano melhor.|phrasal verb|0
cut off|cortar / interromper|Interromper fornecimento, comunicação ou passagem.|The storm cut off the power.|A tempestade interrompeu a energia.|phrasal verb|1
deal with|lidar com|Enfrentar, administrar ou tratar de uma situação.|I can deal with this problem.|Eu consigo lidar com este problema.|phrasal verb|0
drop off|deixar / entregar|Levar alguém ou algo a um local e deixar lá.|Can you drop me off at the station?|Você pode me deixar na estação?|phrasal verb|1
eat out|comer fora|Fazer uma refeição em restaurante ou fora de casa.|Let's eat out tonight.|Vamos comer fora hoje à noite.|phrasal verb|0
end up|acabar / terminar|Chegar a um resultado ou situação, geralmente não planejada.|We ended up staying home.|Acabamos ficando em casa.|phrasal verb|0
fall apart|desmoronar / se desfazer|Quebrar em partes ou perder estabilidade.|The old chair is falling apart.|A cadeira velha está se desfazendo.|phrasal verb|0
figure out|descobrir / entender|Conseguir compreender ou encontrar a solução de algo.|I can't figure out how this works.|Não consigo descobrir como isso funciona.|phrasal verb|1
fill out|preencher|Completar um formulário com informações.|Fill out the application online.|Preencha a inscrição online.|phrasal verb|1
find out|descobrir|Obter uma informação que antes não era conhecida.|I found out the truth yesterday.|Descobri a verdade ontem.|phrasal verb|1
get along|dar-se bem|Ter uma boa relação com alguém.|Do you get along with your coworkers?|Você se dá bem com seus colegas?|phrasal verb|0
get away|escapar / afastar-se|Escapar de algo ou afastar-se por um tempo.|We need to get away for the weekend.|Precisamos sair por aí no fim de semana.|phrasal verb|0
get away with|sair impune|Fazer algo errado sem sofrer a consequência esperada.|He thought he could get away with it.|Ele achou que poderia sair impune.|phrasal verb|0
get back|voltar / recuperar|Retornar ou recuperar alguma coisa.|What time did you get back?|Que horas você voltou?|phrasal verb|0
get in|entrar|Entrar em um lugar ou veículo.|Get in the car.|Entre no carro.|phrasal verb|0
get off|descer / sair|Sair de transporte ou retirar-se de algo.|We get off at the next stop.|Nós descemos na próxima parada.|phrasal verb|0
get on|subir / embarcar|Entrar em transporte ou continuar uma atividade.|Get on the bus.|Entre no ônibus.|phrasal verb|0
get out|sair|Sair de um lugar.|We need to get out now.|Precisamos sair agora.|phrasal verb|0
get over|superar / recuperar-se|Recuperar-se de doença, problema ou término.|It took her months to get over it.|Ela levou meses para superar isso.|phrasal verb|0
get rid of|livrar-se de|Eliminar algo indesejado.|I need to get rid of these old boxes.|Preciso me livrar destas caixas velhas.|phrasal verb|0
give back|devolver|Devolver algo ao dono.|Give the book back tomorrow.|Devolva o livro amanhã.|phrasal verb|1
give in|ceder|Parar de resistir e aceitar algo.|He finally gave in.|Ele finalmente cedeu.|phrasal verb|0
give up|desistir|Parar de tentar ou abandonar um hábito.|Don't give up now.|Não desista agora.|phrasal verb|1
go ahead|vá em frente / prossiga|Dar permissão ou incentivar alguém a continuar.|Go ahead, I'm listening.|Pode continuar, estou ouvindo.|expressão|0
go away|ir embora|Deixar um lugar.|Go away and leave me alone.|Vá embora e me deixe em paz.|phrasal verb|0
go back|voltar|Retornar a um lugar, estado ou assunto anterior.|I want to go back home.|Quero voltar para casa.|phrasal verb|0
go on|continuar / acontecer|Continuar; também pode se referir ao que está acontecendo.|Please go on.|Por favor, continue.|phrasal verb|0
grow up|crescer|Passar da infância para a vida adulta.|I grew up in a small town.|Eu cresci em uma cidade pequena.|phrasal verb|0
hang on|espere / aguente|Pedir para alguém esperar por um momento.|Hang on a second.|Espere um segundo.|expressão|0
hang out|passar tempo / sair|Passar tempo informalmente com outras pessoas.|We hang out after class.|Nós passamos um tempo juntos depois da aula.|phrasal verb|0
hang up|desligar|Encerrar uma ligação telefônica.|Don't hang up.|Não desligue.|phrasal verb|0
hold on|espere / aguarde|Pedir para alguém esperar.|Hold on, I'll be right back.|Espere, já volto.|expressão|0
keep up|acompanhar / manter|Manter o mesmo ritmo ou nível.|I can't keep up with him.|Não consigo acompanhar ele.|phrasal verb|0
let down|decepcionar|Fazer alguém se sentir decepcionado.|I don't want to let you down.|Não quero decepcionar você.|phrasal verb|1
look after|cuidar de|Ser responsável pelo cuidado de alguém ou algo.|Can you look after my dog?|Você pode cuidar do meu cachorro?|phrasal verb|0
look for|procurar|Tentar encontrar algo ou alguém.|I'm looking for my keys.|Estou procurando minhas chaves.|phrasal verb|0
look forward to|aguardar com expectativa|Sentir entusiasmo por algo que acontecerá no futuro.|I'm looking forward to the trip.|Estou ansioso pela viagem.|phrasal verb|0
look into|investigar|Examinar um problema ou situação com atenção.|We'll look into the issue.|Vamos investigar o problema.|phrasal verb|0
look out|cuidado|Aviso para prestar atenção a um perigo.|Look out! There's a car coming.|Cuidado! Está vindo um carro.|expressão|0
look up|procurar / consultar|Buscar uma informação em uma fonte.|Look the word up in the dictionary.|Procure a palavra no dicionário.|phrasal verb|1
make up|inventar / fazer as pazes|Inventar algo ou reconciliar-se após uma discussão.|He made up an excuse.|Ele inventou uma desculpa.|phrasal verb|1
pick up|pegar / buscar / aprender|Pegar algo, buscar alguém ou aprender informalmente.|I'll pick you up at eight.|Vou buscar você às oito.|phrasal verb|1
point out|apontar / destacar|Chamar atenção para uma informação.|She pointed out the mistake.|Ela apontou o erro.|phrasal verb|1
put away|guardar|Colocar algo no lugar onde é armazenado.|Put your clothes away.|Guarde suas roupas.|phrasal verb|1
put off|adiar|Transferir algo para uma data posterior.|We had to put off the meeting.|Tivemos que adiar a reunião.|phrasal verb|1
put on|vestir / colocar|Colocar roupa, acessório ou aparelho.|Put on your jacket.|Vista sua jaqueta.|phrasal verb|1
put out|apagar / extinguir|Apagar fogo, cigarro ou luz.|Please put out the candle.|Por favor, apague a vela.|phrasal verb|1
put up with|aguentar / tolerar|Aceitar uma situação desagradável por algum tempo.|I can't put up with this noise.|Não consigo aguentar este barulho.|phrasal verb|0
run into|encontrar por acaso|Encontrar alguém inesperadamente; também pode significar colidir.|I ran into an old friend.|Encontrei um velho amigo por acaso.|phrasal verb|0
run out|acabar / ficar sem|Esgotar um recurso.|We're running out of time.|Estamos ficando sem tempo.|phrasal verb|0
set up|configurar / montar|Preparar, organizar ou instalar algo.|I need to set up the computer.|Preciso configurar o computador.|phrasal verb|1
show up|aparecer / comparecer|Chegar a um lugar, muitas vezes inesperadamente.|He didn't show up for class.|Ele não apareceu na aula.|phrasal verb|0
shut down|desligar / encerrar|Desligar uma máquina ou encerrar uma operação.|Shut down the computer.|Desligue o computador.|phrasal verb|1
shut up|cale-se|Mandar alguém parar de falar; pode soar rude.|He told them to shut up.|Ele mandou eles calarem a boca.|expressão|0
take after|puxar a / parecer com|Ser parecido com um familiar em aparência ou personalidade.|She takes after her mother.|Ela puxou à mãe.|phrasal verb|0
take away|levar embora / retirar|Remover algo ou levar para outro lugar.|Take these boxes away.|Leve estas caixas embora.|phrasal verb|1
take back|devolver / retirar o que disse|Devolver algo ou admitir que algo dito estava errado.|I take back what I said.|Retiro o que eu disse.|phrasal verb|1
take off|tirar / decolar|Remover roupa ou, para aeronaves, deixar o chão.|Take off your shoes.|Tire seus sapatos.|phrasal verb|1
take on|assumir|Aceitar responsabilidade, trabalho ou desafio.|She took on a new project.|Ela assumiu um novo projeto.|phrasal verb|0
take out|tirar / levar para sair|Remover algo ou levar alguém a um encontro.|Take the trash out.|Leve o lixo para fora.|phrasal verb|1
take over|assumir o controle|Passar a controlar ou administrar algo.|She took over the company.|Ela assumiu o controle da empresa.|phrasal verb|0
throw away|jogar fora|Descartar algo.|Don't throw it away.|Não jogue isso fora.|phrasal verb|1
try on|experimentar|Vestir algo para verificar se serve ou fica bem.|Can I try this shirt on?|Posso experimentar esta camisa?|phrasal verb|1
turn down|recusar / abaixar|Recusar uma oferta ou reduzir volume/intensidade.|She turned down the offer.|Ela recusou a oferta.|phrasal verb|1
turn off|desligar|Desligar um aparelho, luz ou sistema.|Turn the TV off.|Desligue a TV.|phrasal verb|1
turn on|ligar|Ligar um aparelho, luz ou sistema.|Turn on the lights.|Ligue as luzes.|phrasal verb|1
turn up|aumentar / aparecer|Aumentar volume/intensidade ou aparecer.|Turn up the volume.|Aumente o volume.|phrasal verb|1
wake up|acordar|Parar de dormir.|I wake up at seven.|Eu acordo às sete.|phrasal verb|1
work out|dar certo / resolver / malhar|Resolver algo, ter bom resultado ou fazer exercício.|Everything worked out in the end.|No fim, tudo deu certo.|phrasal verb|0
by the way|a propósito|Usado para introduzir um comentário ou assunto adicional.|By the way, did you call her?|A propósito, você ligou para ela?|expressão|0
at least|pelo menos|Indica um mínimo ou um aspecto positivo em uma situação.|At least we tried.|Pelo menos nós tentamos.|expressão|0
right away|imediatamente|Sem demora.|I'll do it right away.|Vou fazer isso imediatamente.|expressão|0
right now|agora mesmo|Neste exato momento.|I need it right now.|Preciso disso agora mesmo.|expressão|0
in fact|na verdade / de fato|Introduz informação que reforça ou corrige a anterior.|In fact, I already knew.|Na verdade, eu já sabia.|expressão|0
of course|claro / é claro|Expressa algo evidente ou uma concordância forte.|Of course I can help.|Claro que posso ajudar.|expressão|0
no way|de jeito nenhum|Expressa recusa forte ou surpresa.|No way! I don't believe you.|De jeito nenhum! Não acredito em você.|expressão|0
take care|se cuida / cuide-se|Despedida desejando cuidado e bem-estar.|Take care. See you tomorrow.|Se cuida. Até amanhã.|expressão|0
never mind|deixa pra lá|Indica que algo não precisa mais ser considerado.|Never mind, I found it.|Deixa pra lá, eu encontrei.|expressão|0
make sure|certificar-se|Confirmar que algo está correto ou foi feito.|Make sure the door is locked.|Certifique-se de que a porta está trancada.|expressão|0
kind of|meio que / tipo|Suaviza ou torna uma afirmação menos precisa.|I'm kind of tired.|Estou meio cansado.|expressão|0
sort of|meio que / mais ou menos|Indica aproximação ou incerteza.|It's sort of complicated.|É meio complicado.|expressão|0
a lot of|muito / muitos|Indica grande quantidade.|We have a lot of work.|Temos muito trabalho.|expressão|0
a little bit|um pouquinho|Indica pequena quantidade ou intensidade.|I'm a little bit nervous.|Estou um pouquinho nervoso.|expressão|0
as soon as|assim que|Indica que algo acontecerá imediatamente depois de outra coisa.|Call me as soon as you arrive.|Ligue para mim assim que chegar.|expressão|0
as far as i know|até onde eu sei|Limita uma afirmação ao conhecimento atual da pessoa.|As far as I know, the meeting is tomorrow.|Até onde eu sei, a reunião é amanhã.|expressão|0
in case|caso / por precaução|Indica condição possível ou medida preventiva.|Take an umbrella in case it rains.|Leve um guarda-chuva caso chova.|expressão|0
on purpose|de propósito|Intencionalmente.|He did it on purpose.|Ele fez isso de propósito.|expressão|0
for a while|por um tempo|Durante um período não muito definido.|Let's wait here for a while.|Vamos esperar aqui por um tempo.|expressão|0
once in a while|de vez em quando|Ocasionalmente.|I eat pizza once in a while.|Eu como pizza de vez em quando.|expressão|0
all of a sudden|de repente|Subitamente, sem aviso.|All of a sudden, the lights went out.|De repente, as luzes apagaram.|expressão|0
at the moment|no momento|Na situação ou tempo atual.|I'm busy at the moment.|Estou ocupado no momento.|expressão|0
sooner or later|mais cedo ou mais tarde|Em algum momento no futuro.|Sooner or later, you'll understand.|Mais cedo ou mais tarde, você vai entender.|expressão|0
first of all|antes de tudo / primeiro|Introduz o primeiro ponto de uma explicação.|First of all, thank you for coming.|Antes de tudo, obrigado por vir.|expressão|0
after all|afinal|Introduz uma razão ou reconsideração.|He deserves a chance, after all.|Afinal, ele merece uma chance.|expressão|0
so far|até agora|Até o momento presente.|So far, everything is fine.|Até agora, está tudo bem.|expressão|0
from now on|de agora em diante|A partir deste momento.|From now on, I'll be more careful.|De agora em diante, serei mais cuidadoso.|expressão|0
in the end|no fim / no final|Refere-se ao resultado final de uma situação.|In the end, we agreed.|No fim, nós concordamos.|expressão|0
on the other hand|por outro lado|Introduz um ponto de vista contrastante.|On the other hand, it is very reliable.|Por outro lado, é muito confiável.|expressão|0
in other words|em outras palavras|Reformula uma ideia de forma diferente.|In other words, we need more time.|Em outras palavras, precisamos de mais tempo.|expressão|0
to be honest|para ser sincero|Introduz uma opinião ou afirmação franca.|To be honest, I don't agree.|Para ser sincero, eu não concordo.|expressão|0
i mean|quer dizer / digo|Usado para esclarecer ou corrigir o que foi dito.|I mean, that's not what I wanted.|Quero dizer, não era isso que eu queria.|expressão|0
you know|sabe / você sabe|Marcador de conversa usado para buscar compreensão ou ganhar tempo.|It's difficult, you know?|É difícil, sabe?|expressão|0
what's going on|o que está acontecendo|Pergunta sobre uma situação atual.|What's going on here?|O que está acontecendo aqui?|expressão|0
what do you mean|o que você quer dizer|Pede esclarecimento sobre o que alguém disse.|What do you mean by that?|O que você quer dizer com isso?|expressão|0
no problem|sem problema|Indica que algo não causa dificuldade ou responde a agradecimento.|No problem, I can help.|Sem problema, eu posso ajudar.|expressão|0
have no idea|não fazer ideia|Não saber absolutamente nada sobre algo.|I have no idea what happened.|Não faço ideia do que aconteceu.|expressão|0
used to|costumava|Fala de hábito ou situação do passado que não ocorre mais.|I used to live here.|Eu costumava morar aqui.|estrutura|0
have to|ter que|Indica necessidade ou obrigação.|I have to leave now.|Tenho que sair agora.|estrutura|0
would rather|preferiria|Expressa preferência entre alternativas.|I'd rather stay home.|Eu preferiria ficar em casa.|estrutura|0
had better|é melhor / deveria|Dá um conselho forte ou alerta.|You'd better call her.|É melhor você ligar para ela.|estrutura|0
as long as|desde que / contanto que|Expressa uma condição.|You can go as long as you finish your work.|Você pode ir desde que termine seu trabalho.|expressão|0
even though|embora / apesar de|Introduz contraste entre duas ideias.|Even though it was late, we stayed.|Embora estivesse tarde, nós ficamos.|conector|0
even if|mesmo se|Apresenta uma condição que não altera o resultado.|I'll go even if it rains.|Eu vou mesmo se chover.|conector|0
instead of|em vez de|Indica substituição de uma opção por outra.|Let's walk instead of taking a taxi.|Vamos caminhar em vez de pegar um táxi.|conector|0
because of|por causa de|Apresenta a causa de algo.|The game was canceled because of the rain.|O jogo foi cancelado por causa da chuva.|conector|0
according to|de acordo com|Atribui uma informação a uma fonte.|According to the report, sales increased.|De acordo com o relatório, as vendas aumentaram.|conector|0
""".strip()


def _load_entries() -> list[PhraseEntry]:
    out = []
    for raw in _DATA.splitlines():
        parts = raw.split("|")
        if len(parts) != 7:
            continue
        canonical, translation, meaning, ex_en, ex_pt, kind, separable = parts
        out.append(PhraseEntry(
            canonical=canonical.strip(),
            translation=translation.strip(),
            meaning_pt=meaning.strip(),
            example_en=ex_en.strip(),
            example_pt=ex_pt.strip(),
            kind=kind.strip(),
            separable=separable.strip() == "1",
        ))
    return out


ENTRIES = _load_entries()
BY_CANONICAL = {entry.canonical: entry for entry in ENTRIES}
FIRST_WORDS = {key.split()[0] for key in BY_CANONICAL}

IRREGULAR_BASE = {
    "am":"be","is":"be","are":"be","was":"be","were":"be","been":"be",
    "has":"have","had":"have","did":"do","done":"do","went":"go","gone":"go",
    "came":"come","gave":"give","given":"give","got":"get","gotten":"get",
    "grew":"grow","grown":"grow","made":"make","ran":"run","sat":"sit",
    "stood":"stand","took":"take","taken":"take","threw":"throw","thrown":"throw",
    "woke":"wake","woken":"wake","brought":"bring","broke":"break","broken":"break",
    "caught":"catch","fell":"fall","fallen":"fall","found":"find","held":"hold",
    "kept":"keep","put":"put","set":"set","shut":"shut",
}


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower().replace("’", "'").strip()
    return re.sub(r"[^a-z0-9']+", "", value)


def words(text: str) -> list[str]:
    return WORD_RE.findall(text or "")


def base_verb(word: str) -> str:
    w = normalize(word)
    if w in IRREGULAR_BASE:
        return IRREGULAR_BASE[w]
    if len(w) > 5 and w.endswith("ing"):
        stem = w[:-3]
        if len(stem) >= 2 and stem[-1] == stem[-2]:
            stem = stem[:-1]
        return stem + "e" if stem + "e" in FIRST_WORDS else stem
    if len(w) > 4 and w.endswith("ied"):
        return w[:-3] + "y"
    if len(w) > 4 and w.endswith("ed"):
        stem = w[:-2]
        if len(stem) >= 2 and stem[-1] == stem[-2]:
            stem = stem[:-1]
        return stem + "e" if stem + "e" in FIRST_WORDS else stem
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith("es"):
        if w[:-2] in FIRST_WORDS:
            return w[:-2]
        if w[:-1] in FIRST_WORDS:
            return w[:-1]
    if len(w) > 3 and w.endswith("s"):
        return w[:-1]
    return w


def _candidate_keys(tokens: list[str]) -> list[str]:
    norm = [normalize(token) for token in tokens]
    if not norm:
        return []
    exact = " ".join(norm)
    based = " ".join([base_verb(norm[0])] + norm[1:])
    return list(dict.fromkeys((exact, based)))


def _contiguous_match(sentence_words: list[str], clicked_index: int) -> PhraseMatch | None:
    n = len(sentence_words)
    for length in range(min(6, n), 1, -1):
        for start in range(max(0, clicked_index-length+1), min(clicked_index, n-length)+1):
            end = start + length
            chunk = sentence_words[start:end]
            for key in _candidate_keys(chunk):
                entry = BY_CANONICAL.get(key)
                if entry:
                    return PhraseMatch(entry, start, end, " ".join(chunk), tuple(range(start, end)))
    return None


def _separable_match(sentence_words: list[str], clicked_index: int) -> PhraseMatch | None:
    norm = [normalize(w) for w in sentence_words]
    for entry in ENTRIES:
        if not entry.separable:
            continue
        parts = entry.canonical.split()
        if len(parts) != 2:
            continue
        verb, particle = parts
        for i in range(len(norm)):
            if base_verb(norm[i]) != verb:
                continue
            for j in range(i+1, min(len(norm), i+6)):
                if norm[j] == particle and i <= clicked_index <= j:
                    return PhraseMatch(entry, i, j+1, " ".join(sentence_words[i:j+1]), (i, j))
    return None


def find_phrase(sentence: str, clicked_index: int) -> PhraseMatch | None:
    sentence_words = words(sentence)
    if not sentence_words or not 0 <= clicked_index < len(sentence_words):
        return None
    return (
        _contiguous_match(sentence_words, clicked_index)
        or _separable_match(sentence_words, clicked_index)
    )


def find_all_phrases(sentence: str) -> list[PhraseMatch]:
    sentence_words = words(sentence)
    candidates = []
    seen = set()
    for idx in range(len(sentence_words)):
        match = find_phrase(sentence, idx)
        if not match:
            continue
        key = (match.entry.canonical, match.start, match.end)
        if key not in seen:
            seen.add(key)
            candidates.append(match)

    candidates.sort(key=lambda m: (m.start, -(m.end-m.start)))
    output = []
    occupied = set()
    for match in candidates:
        span = set(range(match.start, match.end))
        if span & occupied:
            continue
        output.append(match)
        occupied |= span
    return output

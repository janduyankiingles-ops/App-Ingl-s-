# English Video Player — V2.7.2

Aplicativo desktop em Python/PySide6 para estudar inglês com vídeos, séries, filmes, músicas e conteúdo real.







## V2.7.2 — Contraste refinado

A V2.7.2 mantém a arquitetura visual da V2.7, mas melhora a leitura das superfícies: fundo geral cinza-claro, cards brancos, bordas mais nítidas, campos editáveis com fundo próprio, separação mais forte na tela Texto e maior contraste entre painel, editor e resultado. Não há alteração funcional.

## V2.7.1 — Contraste e profundidade

A V2.7.1 mantém a arquitetura visual da V2.7.0 e corrige o aspecto excessivamente branco/lavado. O fundo geral passa a ser cinza-claro, cards permanecem brancos, campos editáveis recebem fundo próprio e bordas mais visíveis, tabelas e grupos ganham separação mais nítida e a tela Texto passa a distinguir claramente card, editor e painel interno.

## V2.7.0 — Redesign inspirado em learning apps

A V2.7.0 abandona a estética de dashboard técnico e adota uma experiência clara e guiada: tema claro, cinco destinos principais, trilha diária visual com nós circulares, próxima atividade destacada, prática separada da progressão principal e telas-resumo para Progresso e Configurações. Atividades futuras da trilha ficam visualmente secundárias e o usuário pode acessar qualquer habilidade livremente pela área Praticar. As ferramentas avançadas continuam disponíveis sem ocupar o primeiro nível da interface.

## V2.6.0 — Experiência guiada

A V2.6.0 reorganiza o aplicativo em cinco destinos principais: Aprender, Praticar, Meu conteúdo, Progresso e Configurações. A tela Aprender apresenta uma trilha diária, recomenda o próximo passo e oferece três formas simples de estudar: vídeo, texto ou música. As telas técnicas continuam existindo, mas são abertas a partir de cartões orientados por tarefa e exibem um botão Voltar para retornar ao hub correspondente. A inspiração é o princípio de learning path do Duolingo: reduzir escolhas simultâneas e indicar claramente o próximo passo.

## V2.5.0 — Interface simplificada

A V2.5.0 reorganiza a experiência sem remover funcionalidades: navegação agrupada e expansível, menos opções simultâneas, controles avançados de vídeo recolhidos em “Mais opções”, títulos repetidos removidos, ações renomeadas com verbos claros e dicionário da área Texto mostrado apenas quando necessário. A lógica funcional permanece a mesma da V2.4.0/V2.3.2.

## V2.4.0 — Redesign profissional

A V2.4.0 moderniza toda a interface sem alterar a lógica de estudo. O novo design usa uma identidade visual única, sidebar limpa, superfícies consistentes, botões por hierarquia de ação, tabelas mais legíveis, player integrado e menos decoração visual. A sincronização funcional permanece a mesma da V2.3.2.

## Versão atual

**V2.2.2 — Compatibilidade do núcleo legado**

A V2.2.2 amplia a compatibilidade com o núcleo histórico do aplicativo, restaurando as APIs legadas de caminhos usadas por main_window.py e settings.py, e mantém as melhorias de estabilidade da V2.2:

- backup manual e backup automático diário do banco local;
- restauração validada com cópia de segurança antes de substituir os dados atuais;
- backup automático antes de preparar uma atualização;
- verificação de integridade do SQLite;
- correção de vínculos de Frases Inteligentes quando uma mídia é movida;
- validação mais rígida do manifesto do atualizador;
- instalador com rollback para atualizações futuras;
- repositório autocontido com os módulos-base que antes existiam apenas na instalação original;
- testes automáticos de integridade do repositório e dos componentes críticos.

## Recursos principais

- sincronização automática entre Vocabulário, Revisão, Quiz, Hoje e Progresso;
- reanálise de Frases quando o vocabulário conhecido muda;
- métricas integradas de Texto, Frases e Música no Progresso;
- estatísticas consistentes entre Séries e Filmes;
- estudo de textos para concursos;
- tradução local EN → PT de textos;
- análise de conectores, referências, gramática e vocabulário de TI/bancário;
- questões geradas a partir do próprio texto;
- biblioteca persistente de textos estudados;
- player com múltiplas faixas de áudio;
- geração de legenda inglesa com Faster-Whisper;
- tradução EN → PT local;
- biblioteca de vídeos;
- Séries, temporadas e episódios;
- Filmes com progresso e retomada;
- Música e videoclipes, karaoke e completar letra;
- vocabulário contextual e inteligente;
- repetição espaçada;
- listening/ditado e Quiz;
- progresso e página Hoje;
- chunks, collocations e gramática contextual;
- Frases Inteligentes / sentence mining;
- treino ativo de frases;
- Imersão Adaptativa;
- Sessão Inteligente com Revisão, Escuta, Quiz e Frases.

Recursos de microfone/fala não fazem parte do roadmap principal. O Shadowing legado permanece disponível, mas não é prioridade.

## Instalação de desenvolvimento

Requer Python 3.11+.

~~~bash
python -m pip install -r requirements.txt
python main.py
~~~

Os dados locais ficam, por padrão, em %LOCALAPPDATA%/EnglishVideoPlayer no Windows. A biblioteca de mídia gerenciada fica em Videos/EnglishVideoPlayer, salvo quando o usuário escolhe outra pasta.

## Atualizador

update_manifest.json é consumido pelo atualizador interno. Os arquivos de cada versão devem apontar para URLs imutáveis presas ao SHA exato do commit-fonte. O fluxo de publicação é:

1. publicar todos os arquivos da versão;
2. congelar o commit-fonte;
3. calcular SHA-256 a partir desse commit;
4. publicar update_manifest.json em um commit posterior e exclusivo.

O manifesto deve ser sempre o último passo da publicação.

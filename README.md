# English Video Player

Aplicativo desktop em Python/PySide6 para estudar inglês com vídeos, séries, filmes, músicas e conteúdo real.

## Versão atual

**V2.2.1 — Correção de compatibilidade**

A V2.2.1 corrige a compatibilidade com o núcleo histórico do aplicativo e mantém as melhorias de estabilidade da V2.2:

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

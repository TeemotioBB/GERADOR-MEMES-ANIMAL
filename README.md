# Cretino Factory

Aplicação web para produzir, em massa, posts estáticos e vídeos MP4 de 8 segundos no estilo de páginas de frases com cachorro.

O sistema permite:

- trocar a imagem base quando quiser;
- gerar frases automaticamente com a API da OpenAI;
- editar o prompt, tema, tom, intensidade e exemplos;
- ajustar posição do texto, margens, tamanho, entrelinhas e marca-d'água;
- visualizar uma prévia aproximada no navegador;
- gerar uma prévia exata no servidor;
- criar um lote com JPG + MP4 estático para cada frase;
- baixar tudo em um ZIP com `frases.csv` e `manifest.json`.

A versão atual **não adiciona música**. O vídeo é uma imagem totalmente parada durante a duração configurada, sem zoom ou animação.

## Estrutura

```text
app/
  ai.py                 geração de frases pela IA
  renderer.py           composição do JPG e criação do MP4
  jobs.py               fila simples de processamento em segundo plano
  main.py               API FastAPI e páginas
  prompts/
    default_prompt.txt  prompt editável
  static/
    app.js
    styles.css
    sample-dog.jpg      imagem padrão, que pode ser substituída no painel
  templates/
    index.html
Dockerfile
railway.json
requirements.txt
.env.example
```

## Executar localmente

Pré-requisitos: Python 3.12+ e FFmpeg.

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Exporte as variáveis do arquivo `.env` no seu terminal ou use uma ferramenta como `python-dotenv`. Depois:

```bash
uvicorn app.main:app --reload
```

Abra `http://localhost:8000`.

Também é possível usar Docker:

```bash
docker build -t cretino-factory .
docker run --rm -p 8000:8000 \
  -e OPENAI_API_KEY="sua-chave" \
  -e APP_USERNAME="admin" \
  -e APP_PASSWORD="uma-senha-forte" \
  cretino-factory
```

## Subir no GitHub

Crie um repositório vazio e execute dentro desta pasta:

```bash
git init
git add .
git commit -m "Primeira versão do Cretino Factory"
git branch -M main
git remote add origin URL_DO_SEU_REPOSITORIO
git push -u origin main
```

O `.gitignore` impede o envio do arquivo `.env`. Nunca publique sua chave da API no GitHub.

## Hospedar no Railway

1. No Railway, crie um novo projeto.
2. Escolha **Deploy from GitHub repo**.
3. Selecione o repositório criado.
4. O Railway detectará automaticamente o `Dockerfile` da raiz.
5. Na área **Variables**, adicione:

```text
OPENAI_API_KEY=sua-chave-da-openai
OPENAI_MODEL=gpt-5-mini
APP_USERNAME=admin
APP_PASSWORD=uma-senha-forte
MAX_BATCH_SIZE=50
JOB_TTL_HOURS=24
STORAGE_DIR=/tmp/cretino-factory
```

6. Em **Networking**, gere um domínio público.
7. Acesse o domínio. O navegador solicitará o usuário e a senha definidos acima.

O servidor usa a variável `PORT` fornecida automaticamente pelo Railway.

## Onde colocar a chave da IA

A forma recomendada é usar `OPENAI_API_KEY` nas variáveis do Railway. Assim a chave não aparece no navegador nem fica salva no repositório.

O painel também possui um campo de chave temporária. Ele serve para testes e a chave não é gravada pela aplicação. Mesmo assim, use esse campo somente em um domínio seu, protegido por HTTPS e senha.

## Modelo da IA

O modelo padrão vem de `OPENAI_MODEL`. O painel permite trocar o nome do modelo para cada geração sem alterar o código.

A integração usa a Responses API e solicita um JSON neste formato:

```json
{
  "phrases": [
    "Primeira frase",
    "Segunda frase"
  ]
}
```

A geração é dividida em blocos de até 25 frases, remove repetições e rejeita respostas inválidas.

## Visual padrão

Os valores iniciais foram configurados para se aproximarem da referência enviada:

- fonte serifada semelhante a Times/Georgia;
- texto preto centralizado;
- grande área vazia na parte superior;
- margem lateral de 9%;
- área do texto começando em 13,5% da altura;
- entrelinhas de 1,22;
- marca-d'água na região inferior esquerda.

O servidor usa **Liberation Serif**, instalada no Docker. A prévia do navegador usa Georgia/Times, então pode existir uma pequena diferença até você clicar em **Gerar prévia exata**.

## Exemplo de saída

O arquivo `docs/exemplo-saida.jpg` foi renderizado pelo próprio sistema com a imagem padrão e os valores iniciais.

## Arquivo gerado

O ZIP final contém:

```text
imagens/post_001.jpg
imagens/post_002.jpg
videos/post_001.mp4
videos/post_002.mp4
frases.csv
manifest.json
```

Cada vídeo é codificado em H.264, 30 FPS, `yuv420p`, com `faststart`, para ampla compatibilidade com Instagram e celulares.

## Armazenamento e limites

Os trabalhos são gravados temporariamente em `STORAGE_DIR` e apagados após o período configurado em `JOB_TTL_HOURS`.

O armazenamento padrão do Railway é efêmero. Isso é adequado para gerar e baixar o ZIP logo em seguida. Para guardar os lotes permanentemente, conecte um Railway Volume, S3, Cloudflare R2 ou outro armazenamento.

Para evitar consumo excessivo de memória e CPU, o lote padrão é limitado a 50 frases. Esse valor pode ser alterado por `MAX_BATCH_SIZE` até 200, mas lotes menores são mais seguros em planos básicos.

## Testes

```bash
pytest -q
```

## Próxima versão: música

A música pode ser acrescentada posteriormente de duas formas:

1. biblioteca própria de arquivos autorizados, com etiquetas de emoção e tema;
2. sugestão de música pela IA, deixando a faixa para ser anexada na plataforma de postagem.

A estrutura atual já separa renderização de imagem e vídeo, facilitando a inclusão de uma segunda entrada de áudio no FFmpeg.

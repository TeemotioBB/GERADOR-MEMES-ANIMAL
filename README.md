# Cretino Factory — Grok/xAI

Aplicação web para gerar frases com o Grok e produzir, em massa, posts estáticos e vídeos MP4 de 8 segundos.

A versão atual:

- usa a API da xAI/Grok para criar as frases;
- permite editar prompt, tema, tom, intensidade e exemplos;
- permite trocar a imagem base quando quiser;
- gera JPG e MP4 totalmente estático, sem zoom ou animação;
- gera vários posts de uma vez e entrega tudo em ZIP;
- ainda não adiciona música.

## Estrutura sem pastas

Todos os arquivos ficam na primeira página/raiz do GitHub:

```text
ai.py
app.js
auth.py
config.py
default_prompt.txt
Dockerfile
index.html
jobs.py
main.py
models.py
railway.json
renderer.py
requirements.txt
sample-dog.jpg
styles.css
.env.example
.gitignore
.dockerignore
README.md
```

## Variáveis do Railway

Na área **Variables** do Railway, adicione:

```env
XAI_API_KEY=sua-chave-da-xai
XAI_MODEL=grok-4.5
XAI_BASE_URL=https://api.x.ai/v1
XAI_REASONING_EFFORT=low

APP_USERNAME=admin
APP_PASSWORD=uma-senha-forte
MAX_BATCH_SIZE=50
JOB_TTL_HOURS=24
STORAGE_DIR=/tmp/cretino-factory
```

Não envie sua chave para o GitHub. A chave deve ficar nas variáveis privadas do Railway.

## Como criar a chave da xAI

1. Crie sua conta no console da xAI.
2. Adicione créditos à conta.
3. Gere uma API key.
4. Copie a chave para `XAI_API_KEY` no Railway.

## Modelo

O modelo padrão é definido por:

```env
XAI_MODEL=grok-4.5
```

O campo **Modelo do Grok** no painel pode substituir esse valor em uma geração específica.

O sistema usa o pacote Python `openai` apenas como cliente compatível com a API da xAI. O endpoint configurado é:

```text
https://api.x.ai/v1
```

A geração utiliza a Responses API com Structured Outputs/Pydantic, evitando JSON inválido.

## Raciocínio

Para geração rápida de frases, o padrão é:

```env
XAI_REASONING_EFFORT=low
```

Valores aceitos:

```text
low
medium
high
```

## Atualizar o GitHub

1. Extraia o ZIP.
2. Abra seu repositório no GitHub.
3. Clique em **Add file → Upload files**.
4. Selecione todos os arquivos extraídos.
5. Substitua os arquivos com o mesmo nome.
6. Clique em **Commit changes**.
7. Aguarde o Railway fazer o novo deploy.

## Executar localmente

Pré-requisitos: Python 3.12+ e FFmpeg.

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Defina `XAI_API_KEY` e execute:

```bash
uvicorn main:app --reload
```

Abra:

```text
http://localhost:8000
```

## Docker

```bash
docker build -t cretino-factory .

docker run --rm -p 8000:8000 \
  -e XAI_API_KEY="sua-chave-da-xai" \
  -e XAI_MODEL="grok-4.5" \
  -e APP_USERNAME="admin" \
  -e APP_PASSWORD="uma-senha-forte" \
  cretino-factory
```

## Testes

```bash
pytest -q
```

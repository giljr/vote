## Comandos úteis:

### 1️⃣ Preparar o ambiente (toda vez que abrir o projeto)
```bash
cd ~/projetos/python/flask/votr/votr-modern
source venv/bin/activate      # ativa o ambiente virtual — aparece (venv) no prompt
export FLASK_APP=votr.py      # diz ao Flask qual é o arquivo principal
code .                        # (opcional) abre o projeto no VS Code
```
### 2️⃣ Rodar o app
```bash
flask run                     # sobe em http://127.0.0.1:5000
```
# ou, se a 5000 estiver ocupada:
```bash
flask run --port 5050         # sobe em http://127.0.0.1:5050
Para parar: Ctrl+C no terminal onde está rodando.
```

### 3️⃣ Liberar uma porta presa (quando dá "Address already in use")
```bash
bashlsof -i :5000                 # descobre o PID do processo na porta (ou :5050)
kill <PID>                    # encerra o processo
lsof -i :5000                 # confere se liberou (sem saída = livre)
Atalho que dispensa procurar PID: pkill -f "flask run" mata todos de uma vez.
```

### 4️⃣ Encerrar o trabalho
```bash
deactivate                    # sai do ambiente virtual
```

### 5️⃣ Utilitários que apareceram no seu histórico
```bash
clear        # limpa a tela (o LS maiúsculo que você digitou não existe — Linux diferencia maiúsculas)
ls           # lista arquivos
history      # mostra os comandos já digitados
```

### 6️⃣ Claude Code (instalação — só uma vez)
```bash
bashcurl -fsSL https://claude.ai/install.sh | bash   # instala
claude --version                                  # confirma a instalação
claude 
```
# inicia na pasta do projeto
Duas dicas baseadas no que vi no seu histórico:
```bash
Primeiro, você repetiu o ciclo deactivate → source venv/bin/activate → export várias vezes. Crie o arquivo .flaskenv na raiz do projeto com FLASK_APP=votr.py e FLASK_DEBUG=1 — aí o export nunca mais será necessário, só source venv/bin/activate e flask run.
```
```bash
Segundo, você matou vários PIDs em sequência (9441, 9241, 9242...). Isso acontece porque o modo debug do Flask cria um processo filho para o auto-reload. O pkill -f "flask run" resolve os dois de uma vez — vale adotar como padrão.
```
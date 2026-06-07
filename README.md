
# 🚀 Windows 11 + WSL2 + OpenAI + Python

> Primeiros passos com Inteligência Artificial utilizando **Windows 11**, **WSL2**, **Ubuntu**, **VS Code** e a **API da OpenAI**.

![Python](https://img.shields.io/badge/Python-3.x-blue) ![WSL2](https://img.shields.io/badge/WSL2-Ubuntu%2024.04-orange) ![VSCode](https://img.shields.io/badge/VS_Code-Ready-blue) ![OpenAI](https://img.shields.io/badge/OpenAI-API-green)

---

## 📖 Sobre

Este projeto acompanha o artigo:

**Windows 11 + WSL2 + OpenAI: Primeiros Passos com Python e VS Code ([Episódio 2](https://medium.com/jungletronics/windows-11-wsl2-openai-primeiros-passos-com-python-e-vs-code-epis%C3%B3dio-2-7818719f4342))**

Nele você aprenderá a:
```
✅ Configurar o VS Code para trabalhar com WSL2
✅ Criar ambientes virtuais Python
✅ Armazenar credenciais com `.env`
✅ Utilizar a API da OpenAI com Python
✅ Executar seus primeiros prompts de IA
```
---

Another project: **Most Python Beginners Learn Matrices the Hard Way - Use Pandas Instead** [Pandas Project](https://medium.com/p/19f41a0cc492/
) Create, combine, and manipulate matrices effortlessly while building a professional WSL2 + VS Code development setup. 

---

## 🛠 Tecnologias

* Windows 11
* WSL2
* Ubuntu 24.04 LTS
* Python
* VS Code
* OpenAI API
* python-dotenv

---

## 📂 Estrutura

```text
python/
│  |_ machine-learning (first lessons about openAI)
|       ├── main_0.py
|       ├── main_1.py
|       ├── .env
|       ├── .gitignore
|  |_ pandas
|       ├── 01_matrix.ipynb
|       ├── 02 soon...
└── README.md
```

---

## ⚙️ Criando o Ambiente

### Criar projeto

```bash
mkdir -p ~/projetos/python
cd ~/projetos/python
```

### Criar ambiente virtual
Melhor prática: usar ambiente virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Instalar dependências

```bash
pip install openai python-dotenv
```

---

## 🔐 Configurar a Chave da OpenAI

Crie o arquivo:

```bash
nano .env
```

Conteúdo:

```env
OPENAI_API_KEY=sua-chave-aqui
```

⚠️ Nunca envie o arquivo `.env` para o GitHub.

Adicione ao `.gitignore`:

```gitignore
.env
*.env
```

---

## 🤖 Exemplo 0 — Responses API

```python
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()

response = client.responses.create(
    model="gpt-4o",
    input="Why Python is great?"
)

print(response.output_text)
```

Executar:

```bash
python main_0.py
```

---

## 💬 Exemplo 1 — Chat Completions

```python
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {
            "role": "user",
            "content": "Why is Python great?"
        }
    ]
)

print(response.choices[0].message.content)
```

Executar:

```bash
python main_1.py
```

---

## 🧠 Entendendo o objeto `messages`

```python
messages=[
    {
        "role": "system",
        "content": "You are a Python teacher."
    },
    {
        "role": "user",
        "content": "Why is Python great?"
    }
]
```

### Roles

| Role      | Descrição                        |
| --------- | -------------------------------- |
| system    | Define o comportamento do modelo |
| user      | Pergunta do usuário              |
| assistant | Respostas anteriores do modelo   |

---

## 🎯 Objetivo da Série

Transformar um computador Windows 11 em uma workstation moderna para desenvolvimento de aplicações de IA utilizando:

* Python | Rails
* OpenAI | Gemini | Claude ...
* VS Code
* Ubuntu
* WSL2

---

## 📚 Lista de Artigos da Série Completa

Leia os tutoriais completos no Medium:

01# [Como Transformar o Windows 11 em uma Workstation Rails com WSL2 e Docker e IA](https://medium.com/jungletronics/como-transformar-o-windows-11-em-uma-workstation-rails-com-wsl2-e-docker-08bd29a50f4f)

02# [Windows 11 + WSL2 + OpenAI: Primeiros Passos com Python e VS Code](https://medium.com/jungletronics/windows-11-wsl2-openai-primeiros-passos-com-python-e-vs-code-epis%C3%B3dio-2-7818719f4342)

03# [Most Python Beginners Learn Matrices the Hard Way - Use Pandas Instead](https://medium.com/p/19f41a0cc492/)

04# soon... :)

---

## 🔜 Próximos Episódios

* Geração de código com IA
* Automação de tarefas
* Modelos multimodais
* Integração com APIs
* Docker + PostgreSQL
* Projetos reais em Python e Rails

---

## 👨‍💻 Autor

**Gilberto Junior (J3)**

Arduino Hobbyist • Python Enthusiast • AI Explorer • Computer Engineer

⭐ Se este projeto foi útil, considere deixar uma estrela no repositório.


# 🚀 Windows 11 + WSL2 + OpenAI + Python
> First steps with Artificial Intelligence using Windows 11, WSL2, Ubuntu, VS Code, and the OpenAI API, and Django.

> Primeiros passos com Inteligência Artificial utilizando **Windows 11**, **WSL2**, **Ubuntu**, **VS Code** e a **API da OpenAI**.

![Python](https://img.shields.io/badge/Python-3.x-blue)
![WSL2](https://img.shields.io/badge/WSL2-Ubuntu%2024.04-orange)
![OpenAI](https://img.shields.io/badge/OpenAI-API-green)
![VSCode](https://img.shields.io/badge/VS_Code-Ready-blue)
![Django](https://img.shields.io/badge/Django-6.0-darkgreen)

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
* Django

---

## 📂 Estrutura

```text
python/
├── machine-learning (first lessons about openAI)
|       ├── main_0.py
|       ├── main_1.py
|       ├── .env
|       ├── .gitignore
├── pandas
|       ├── 01_matrix.ipynb
|       ├── 02 soon...
├── django
│   ├── 0
│   ├── 1
│   ├── 2
│   |    ...
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

### WSL 

01# [Como Transformar o Windows 11 em uma Workstation Rails com WSL2 e Docker e IA](https://medium.com/jungletronics/como-transformar-o-windows-11-em-uma-workstation-rails-com-wsl2-e-docker-08bd29a50f4f)

02# [Windows 11 + WSL2 + OpenAI: Primeiros Passos com Python e VS Code](https://medium.com/jungletronics/windows-11-wsl2-openai-primeiros-passos-com-python-e-vs-code-epis%C3%B3dio-2-7818719f4342)

03# [Most Python Beginners Learn Matrices the Hard Way - Use Pandas Instead](https://medium.com/p/19f41a0cc492/)

04# soon... :)

### IA

01# 📖 [The Claude Code Skills Journey](https://medium.com/jungletronics/the-claude-code-skills-journey-096bd803bc90)
Documenting discoveries, experiments, and lessons learned while pushing the boundaries of AI-assisted software development

02# ⚡ [From SKILL.md to Superpower: Deploying a Claude Skill](https://medium.com/jungletronics/from-skill-md-to-superpower-deploying-a-claude-skill-7b75982e93ba)
Build your first custom Skill and turn Claude into a specialized tool for Ruby security audits

### DJANGO

01# 🐍 [Django from Zero to Pro — Episode 0](https://medium.com/jungletronics/django-from-zero-to-pro-setup-in-minutes-clean-modern-structure-17922233e957)
Build a Clean Django Development Environment in Minutes

02# [Django MVC EXPOSED (You’ve Been Learning It Wrong) — Episode 1](https://medium.com/jungletronics/episode-1-django-mvc-exposed-youve-been-learning-it-wrong-8aa038600928)
The Simple Framework That Powers Instagram, YouTube, and Netflix (and Why Everyone Misunderstands It)

03# [Stop Being Confused by Django’s Structure — Episode 3](https://medium.com/jungletronics/stop-being-confused-by-djangos-structure-3c1607a7fee7)
Master the Django file structure before building real applications — no more guessing what each file does — # Episode 3

04# [Dockerize Django Like a Pro — The Production Setup Every Developer Should Know — Episode 4](https://medium.com/jungletronics/dockerize-django-like-a-pro-the-production-setup-every-developer-should-know-episode-4-948c480f4cdc)
Stop running Django the old way. Learn the clean, production-style Docker workflow used by modern teams — simple, reproducible, and ready for real-world deployment

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

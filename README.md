# MeuHexa

O MeuHexa é uma aplicação web temática da Copa do Mundo desenvolvida como projeto interdisciplinar do 1º período do curso de Engenharia de Software do IFPB. O sistema integra as disciplinas de Programação Web 1, Introdução à Programação e Introdução à Engenharia de Software.

A plataforma oferece uma experiência gamificada em torno do futebol mundial, combinando um álbum digital de figurinhas colecionáveis, um minigame no estilo Akinator que tenta adivinhar jogadores históricos pensados pelo usuário, e um mecanismo de aprendizado contínuo pelo qual o próprio usuário contribui para o crescimento da base de dados do sistema.

## Funcionalidades

- **Álbum de figurinhas** - abra pacotes, cole figurinhas e troque repetidas por bônus
- **AkinaCopa** - minigame que tenta adivinhar em qual jogador você está pensando, usando perguntas progressivas (escopo de jogadores limitado para as copas modernas: 2002–2022)
- **Histórico de partidas** - cada jogo é registrado automaticamente
- **Sugestão de jogadores** - quando o motor erra, o usuário pode sugerir o jogador para expandir a base

## Tecnologias

- Python 3.11+ / Flask
- Pandas (motor do AkinaCopa)
- HTML + CSS + JavaScript (vanilla)
- Jinja2 (templates)
- CSV (persistência de dados)

## Instalação

```bash
# Clone o repositório
git clone https://github.com/ericfabricio7/meuhexa-projeto.git
cd meuhexa-projeto

# Crie e ative o ambiente virtual
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # Linux/Mac

# Instale as dependências
pip install -r requirements.txt
```

## Executando

```bash
python main.py
```

Acesse em `http://localhost:5000`

## Estrutura do Projeto

```
meuhexa-projeto/
├── main.py                        # Entry point Flask
├── app/
│   └── copa/
│       ├── routes.py              # Todas as rotas (álbum + minigame)
│       ├── akinator_motor.py      # Lógica do AkinaCopa
│       └── utils.py               # Utilitários (carregar figurinhas)
├── data/
│   ├── akinacopa-dataset - Jogadores.csv
│   ├── akinacopa-dataset - Participações Copa.csv
│   ├── akinacopa-dataset - Perguntas.csv
│   ├── akinacopa-dataset - Histórico Aprendizado.csv
│   └── sugestoes_jogadores.csv    # criado automaticamente
├── templates/
│   ├── base.html
│   ├── index.html
│   └── minigame.html
└── static/
    ├── css/styles.css
    └── img/
```

## Branches

| Branch | Propósito |
|---|---|
| `master` | Produção estável |
| `dev` | Integração de features |
| `feature/*` | Desenvolvimento de novas funcionalidades |
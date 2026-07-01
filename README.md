# MeuHexa

O MeuHexa é uma aplicação web temática da Copa do Mundo desenvolvida como projeto interdisciplinar do 1º período do curso de Engenharia de Software do IFPB. O sistema integra as disciplinas de Programação Web 1, Introdução à Programação e Introdução à Engenharia de Software.

A plataforma oferece uma experiência gamificada em torno do futebol mundial, combinando um álbum digital de figurinhas colecionáveis, um minigame no estilo Akinator que tenta adivinhar jogadores históricos pensados pelo usuário, e um mecanismo de aprendizado contínuo pelo qual o próprio usuário contribui para o crescimento da base de dados do sistema.

## Diagrama de Casos de Uso

[Ver DiagramaUC-MeuHexa.svg](./DiagramaUC-MeuHexa.svg)

## Funcionalidades

- **Cadastro e autenticação** - criação de conta, login, gerenciamento de perfil (foto, seleção favorita, senha)
- **Álbum de figurinhas** - abra pacotes e cole figurinhas
- **AkinaCopa** - minigame que tenta adivinhar em qual jogador você está pensando, usando perguntas progressivas (escopo de jogadores limitado para as copas modernas da seleção brasileira: 2002–2022)
- **Histórico de partidas** - cada jogo é registrado automaticamente em CSV
- **Contribuição de dataset** - quando o motor erra e o jogador não está na base, o usuário cadastrado pode enviar os dados do jogador; a contribuição fica pendente para aprovação futura

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
├── main.py                              # Entry point Flask
├── requirements.txt
├── DiagramaUC-MeuHexa.svg               # Diagrama de casos de uso
├── app/
│   └── copa/
│       ├── routes.py                    # Todas as rotas HTTP + helpers de CSV
│       ├── akinator_motor.py            # Motor do AkinaCopa (pandas)
│       └── utils.py                     # Carregamento de figurinhas
│
├── data/
│   ├── akinacopa-dataset - Jogadores.csv   
│   ├── akinacopa-dataset - Participações Copa.csv
│   ├── akinacopa-dataset - Perguntas.csv
│   ├── akinacopa-dataset - Seleção.csv
│   ├── akinacopa-dataset - Técnicos.csv
│   ├── akinacopa-dataset - Histórico Aprendizado.csv  # gerado em runtime
│   ├── figurinhas.csv                   # Catálogo do álbum
│   ├── usuarios.csv                     # Contas cadastradas
│   └── pending.csv                      # Contribuições aguardando aprovação
│
├── templates/
│   ├── base.html                        # Layout base (nav, header)
│   ├── index.html                       # Homepage + álbum
│   ├── minigame.html                    # AkinaCopa
│   ├── cadastro.html                    # Login e cadastro
│   └── perfil.html                      # Perfil do usuário
│
└── static/
    ├── css/styles.css
    └── img/
        ├── img-figurinhas/              # Fotos dos jogadores (usadas no palpite)
        └── perfil/                      # Fotos de perfil enviadas pelos usuários
```

## Branches

| Branch | Propósito |
|---|---|
| `master` | Produção estável |
| `dev` | Integração de features |
| `feature/*` | Desenvolvimento de novas funcionalidades |

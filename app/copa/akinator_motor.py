"""
Motor do AkinaCopa — lógica do jogo extraída do notebook.
Carrega os dados uma vez (cache) e expõe funções para as rotas Flask.
"""

import os
import csv
import uuid
from datetime import datetime

import pandas as pd

# Caminhos
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

def _path(nome):
    return os.path.join(_BASE, 'data', nome)

# Configuração 
COPAS_MODERNAS = [2002, 2006, 2010, 2014, 2018, 2022]
MAX_RODADAS    = 22
MARGEM_PALPITE = 1.5
RODADA_MIN     = 4

MAPA_RESPOSTAS = {"1": 1.0, "2": 0.75, "3": None, "4": 0.25, "5": 0.0}

RARITY = {2002: "rar-lendaria", 2006: "rar-epica", 2010: "rar-epica",
          2014: "rar-rara",     2018: "rar-rara",  2022: "rar-epica"}

# Cache de dados (carregado na primeira chamada)
_matriz    = None
_perguntas = None

# Constantes de exclusão
_COPAS_ANO  = ['copa_2022','copa_2018','copa_2014','copa_2010',
               'copa_2006','copa_2002','copa_1994']
_ERA_ANTIGA = ['antes_1970','anos_70_80','era_pele']
_CLUBES_BR  = ['RJ','SP','Flamengo','Botafogo','Fluminense',
               'São Paulo','Palmeiras','Corinthians','Santos',
               'Cruzeiro','Atlético Mineiro','Grêmio','Internacional']
_PAISES     = ['pais_Inglaterra','pais_Espanha','pais_Italia',
               'pais_Franca','pais_Alemanha','pais_Portugal']

EXCLUSOES_CONTEXTUAIS = {
    'Atacante':      {'excluir_se_sim': ['Goleiro','Defensor','Meio-campista','Zagueiro',
                                          'Lateral','Volante','Meia-atacante']},
    'Goleiro':       {'excluir_se_sim': ['Atacante','Defensor','Meio-campista','Zagueiro',
                                          'Lateral','Ponta','Centroavante','Volante','Meia-atacante',
                                          'lado_esquerdo','lado_direito',
                                          'gols_positivo','gols_artilheiro','artilheiro']},
    'Defensor':      {'excluir_se_sim': ['Atacante','Goleiro','Meio-campista',
                                          'Ponta','Centroavante','Meia-atacante']},
    'Meio-campista': {'excluir_se_sim': ['Atacante','Goleiro','Defensor',
                                          'Zagueiro','Lateral','Ponta','Centroavante']},
    'Zagueiro':      {'excluir_se_sim': ['Lateral','Ponta','Centroavante','Volante',
                                          'Meia-atacante','Goleiro',
                                          'lado_esquerdo','lado_direito']},
    'Lateral':       {'excluir_se_sim': ['Zagueiro','Ponta','Centroavante','Goleiro','Atacante']},
    'Ponta':         {'excluir_se_sim': ['Zagueiro','Lateral','Centroavante','Volante',
                                          'Goleiro','Atacante']},
    'Centroavante':  {'excluir_se_sim': ['Zagueiro','Lateral','Ponta','Volante',
                                          'Meia-atacante','Goleiro',
                                          'lado_esquerdo','lado_direito','Atacante']},
    'Volante':       {'excluir_se_sim': ['Zagueiro','Lateral','Ponta','Centroavante',
                                          'Goleiro','lado_esquerdo','lado_direito']},
    'Meia-atacante': {'excluir_se_sim': ['Zagueiro','Lateral','Centroavante','Volante',
                                          'Goleiro','lado_esquerdo','lado_direito']},
    'lado_esquerdo': {'excluir_se_sim': ['lado_direito']},
    'lado_direito':  {'excluir_se_sim': ['lado_esquerdo']},
    'seculo_21': {
        'excluir_se_sim': _ERA_ANTIGA,
        'excluir_se_nao': _COPAS_ANO + _PAISES,
    },
    'antes_1970': {'excluir_se_nao': ['era_pele']},
    'era_pele':   {'excluir_se_nao': ['antes_1970']},
    **{f'copa_{a}': {'excluir_se_sim': [c for c in _COPAS_ANO if c != f'copa_{a}']
                                       + _ERA_ANTIGA + ['seculo_21']}
       for a in [2022,2018,2014,2010,2006,2002,1994]},
    'campeao':        {'excluir_se_nao': ['campeao_invicto']},
    'capitao':        {'excluir_se_sim': ['titular']},
    'gols_positivo':  {'excluir_se_nao': ['gols_artilheiro']},
    'gols_artilheiro':{'excluir_se_sim': ['gols_positivo']},
    'artilheiro':     {'excluir_se_sim': ['gols_positivo','gols_artilheiro']},
    'veterano':       {'excluir_se_nao': ['super_veterano']},
    'super_veterano': {'excluir_se_sim': ['veterano']},
    'exterior': {
        'excluir_se_sim': _CLUBES_BR,
        'excluir_se_nao': _PAISES,
    },
    **{p: {'excluir_se_sim': ['exterior'] + [x for x in _PAISES if x != p] + _CLUBES_BR}
       for p in _PAISES},
    **{c: {'excluir_se_sim': ['exterior'] + _PAISES}
       for c in ['Flamengo','Botafogo','Fluminense','São Paulo',
                 'Palmeiras','Corinthians','Santos',
                 'Cruzeiro','Atlético Mineiro','Grêmio','Internacional']},
    'RJ': {'excluir_se_sim': ['exterior'] + _PAISES
                              + ['SP','São Paulo','Palmeiras','Corinthians','Santos',
                                 'Cruzeiro','Atlético Mineiro','Grêmio','Internacional']},
    'SP': {'excluir_se_sim': ['exterior'] + _PAISES
                              + ['RJ','Flamengo','Botafogo','Fluminense',
                                 'Cruzeiro','Atlético Mineiro','Grêmio','Internacional']},
}

# Funções core (extraídas do notebook) 

def _construir_matriz(fj, fp):
    df_j = pd.read_csv(fj)
    df_p = pd.read_csv(fp)
    df   = pd.merge(df_p, df_j, on='id_jogador')
    df   = df[df['ano_copa'].isin(COPAS_MODERNAS)].copy()

    for pos in ['Atacante','Goleiro','Defensor','Meio-campista']:
        df[pos] = (df['linha_campo'] == pos).astype(int)
    for pos in ['Zagueiro','Lateral','Ponta','Volante','Meia-atacante','Centroavante']:
        df[pos] = (df['posicao_especifica'] == pos).astype(int)

    df['antes_1970'] = (df['ano_copa'] < 1970).astype(int)
    df['anos_70_80'] = ((df['ano_copa'] >= 1974) & (df['ano_copa'] <= 1990)).astype(int)
    df['seculo_21']  = (df['ano_copa'] >= 2002).astype(int)
    df['era_pele']   = df['ano_copa'].isin([1958,1962,1966,1970]).astype(int)
    for ano in [1994,2002,2006,2010,2014,2018,2022]:
        df[f'copa_{ano}'] = (df['ano_copa'] == ano).astype(int)

    df['campeao']        = df['ano_copa'].isin([1958,1962,1970,1994,2002]).astype(int)
    df['capitao']        = (df['capitao'] == 'Sim').astype(int)
    cnt = df.groupby('id_jogador')['ano_copa'].nunique()
    df['veterano']       = df['id_jogador'].map(cnt).gt(1).astype(int)
    df['super_veterano'] = df['id_jogador'].map(cnt).ge(3).astype(int)
    df['finalista']      = 0
    df['campeao_invicto']= 0

    clubes_rj = ['Flamengo','Vasco da Gama','Botafogo','Fluminense']
    clubes_sp = ['São Paulo','Palmeiras','Corinthians','Santos','Portuguesa']
    df['RJ'] = df['clube_no_ano'].str.contains('|'.join(clubes_rj), na=False).astype(int)
    df['SP'] = df['clube_no_ano'].str.contains('|'.join(clubes_sp), na=False).astype(int)
    df['exterior'] = (df['clube_pais'] != 'Brasil').astype(int)

    for clube in ['Flamengo','Vasco da Gama','Botafogo','Fluminense',
                  'São Paulo','Palmeiras','Corinthians','Santos']:
        df[clube] = df['clube_no_ano'].str.contains(clube, na=False).astype(int)

    df['Cruzeiro']         = df['clube_no_ano'].str.contains('Cruzeiro', na=False).astype(int)
    df['Atlético Mineiro'] = df['clube_no_ano'].str.contains('Atlético Mineiro', na=False).astype(int)
    df['Grêmio']           = df['clube_no_ano'].str.contains('Grêmio', na=False).astype(int)
    df['Internacional']    = df['clube_no_ano'].str.contains(r'\bInternacional\b', na=False).astype(int)

    df['pais_Franca']    = (df['clube_pais'] == 'França').astype(int)
    df['pais_Alemanha']  = (df['clube_pais'] == 'Alemanha').astype(int)
    df['pais_Portugal']  = (df['clube_pais'] == 'Portugal').astype(int)
    df['titular']        = (df['titular'] == 'Sim').astype(int)
    df['gols_positivo']  = (df['gols_na_copa'] > 0).astype(int)
    df['gols_artilheiro']= (df['gols_na_copa'] >= 3).astype(int)
    df['lado_esquerdo']  = (df['lado_campo'] == 'Esquerdo').astype(int)
    df['lado_direito']   = (df['lado_campo'] == 'Direito').astype(int)
    df['pais_Inglaterra']= (df['clube_pais'] == 'Inglaterra').astype(int)
    df['pais_Espanha']   = (df['clube_pais'] == 'Espanha').astype(int)
    df['pais_Italia']    = (df['clube_pais'] == 'Itália').astype(int)
    df['expulso']        = (df['expulso_ou_suspenso'] == 'Sim').astype(int)
    df['artilheiro']     = (df['artilheiro_destaque'] == 'Sim').astype(int)
    df['sub23']          = (df['faixa_etaria'] == 'Sub-23').astype(int)
    df['altura_alto']    = (df['altura_categoria'] == 'Alto').astype(int)
    return df


def _filtrar_perguntas(df_p, df_m):
    cols = set(df_m.columns)
    validas = []
    for _, row in df_p.iterrows():
        partes = [p.strip() for p in str(row['chave_atributo']).split(',')]
        ps = [p for p in partes if p in cols]
        if ps and any(0 < df_m[p].mean() < 1.0 for p in ps):
            validas.append(row)
    return pd.DataFrame(validas).reset_index(drop=True)


def _resolver_chave(chave, df, cols):
    partes = [p.strip() for p in chave.split(',')]
    validas = [p for p in partes if p in cols]
    if not validas:
        return None
    s = df[validas[0]].copy()
    for p in validas[1:]:
        s = s | df[p]
    return s.astype(int)


def _melhor_pergunta(df, pq, cols):
    if len(df) <= 1:
        return None
    min_e = df['total_erros'].min()
    top   = df[df['total_erros'] <= min_e + 0.5]
    cands = top if len(top) <= 5 else df[df['total_erros'] <= df['total_erros'].quantile(0.25) + 0.001]
    if len(cands) <= 1:
        cands = df
    melhor, menor = None, float('inf')
    for _, row in pq.iterrows():
        s = _resolver_chave(row['chave_atributo'], cands, cols)
        if s is None:
            continue
        d = abs(s.mean() - 0.5)
        if d < menor:
            menor, melhor = d, row
    return melhor


def _aplicar_exclusoes(pq, chave, peso):
    if pq.empty:
        return pq
    regras = EXCLUSOES_CONTEXTUAIS.get(chave, {})
    excluir = set()
    if peso >= 0.75:
        excluir.update(regras.get('excluir_se_sim', []))
    elif peso <= 0.25:
        excluir.update(regras.get('excluir_se_nao', []))
    if not excluir:
        return pq
    def deve(c):
        return bool({p.strip() for p in c.split(',')} & excluir)
    resultado = pq[~pq['chave_atributo'].apply(deve)]
    if resultado.empty:
        return pq.iloc[0:0]  # garante colunas preservadas mesmo com df vazio
    return resultado


# Cache 

def _carregar():
    global _matriz, _perguntas
    if _matriz is None:
        fj = _path('akinacopa-dataset - Jogadores.csv')
        fp = _path('akinacopa-dataset - Participações Copa.csv')
        fq = _path('akinacopa-dataset - Perguntas.csv')
        _matriz    = _construir_matriz(fj, fp)
        _perguntas = _filtrar_perguntas(pd.read_csv(fq), _matriz)


# API pública

def novo_jogo():
    """Retorna o estado inicial da sessão."""
    _carregar()
    return {
        'erros': {},
        'queue': _perguntas['id_pergunta'].tolist(),
        'rodada': 1,
    }


def _reconstruir_df(erros):
    df = _matriz.copy()
    df['total_erros'] = 0.0
    for id_str, val in erros.items():
        mask = df['id_participacao'] == int(id_str)
        df.loc[mask, 'total_erros'] = float(val)
    return df


def _row_para_dict(row):
    ano = int(row['ano_copa'])
    return {
        'id':      int(row['id_participacao']),
        'nome':    str(row['nome']),
        'apelido': str(row['apelido']),
        'ano':     ano,
        'fato':    str(row['caracteristica_geral']),
        'erro':    round(float(row['total_erros']), 2),
        'rarity':  RARITY.get(ano, 'rar-rara'),
        'imagem':  str(row.get('imagem', '') or ''),
    }


def calcular_estado(ak):
    """
    Dado o estado da sessão, retorna o próximo estado para o frontend:
    {'fase', 'rodada', 'total', 'pergunta', 'palpite', 'top3'}
    """
    _carregar()
    df = _reconstruir_df(ak['erros'])
    pq = _perguntas[_perguntas['id_pergunta'].isin(ak['queue'])].copy()

    df_ord = df.sort_values('total_erros')
    err1   = df_ord.iloc[0]['total_erros']
    err2   = df_ord.iloc[1]['total_erros'] if len(df_ord) > 1 else float('inf')
    margem = err2 - err1
    rodada = ak['rodada']

    top3 = [_row_para_dict(r) for _, r in df_ord.head(3).iterrows()]

    # Palpite intermediário
    if rodada >= RODADA_MIN and margem >= MARGEM_PALPITE:
        return {
            'fase':     'palpite_mid',
            'rodada':   rodada,
            'total':    MAX_RODADAS,
            'palpite':  _row_para_dict(df_ord.iloc[0]),
            'top3':     top3,
            'pergunta': None,
        }

    # Fim de jogo
    if rodada > MAX_RODADAS or pq.empty:
        return {
            'fase':     'palpite_final',
            'rodada':   rodada,
            'total':    MAX_RODADAS,
            'palpite':  _row_para_dict(df_ord.iloc[0]),
            'top3':     top3,
            'pergunta': None,
        }

    # Próxima pergunta
    cols = set(df.columns)
    perg = _melhor_pergunta(df, pq, cols)
    if perg is None:
        return {
            'fase':     'palpite_final',
            'rodada':   rodada,
            'total':    MAX_RODADAS,
            'palpite':  _row_para_dict(df_ord.iloc[0]),
            'top3':     top3,
            'pergunta': None,
        }

    return {
        'fase':    'pergunta',
        'rodada':  rodada,
        'total':   MAX_RODADAS,
        'pergunta': {'id': int(perg['id_pergunta']), 'texto': perg['texto_pergunta']},
        'palpite':  None,
        'top3':     None,
    }


def processar_resposta(ak, id_pergunta, resposta_str):
    """Aplica a resposta e retorna (novo_ak, estado)."""
    _carregar()
    pq   = _perguntas[_perguntas['id_pergunta'].isin(ak['queue'])].copy()
    perg = pq[pq['id_pergunta'] == id_pergunta]
    if perg.empty:
        return ak, calcular_estado(ak)

    chave = perg.iloc[0]['chave_atributo']
    peso  = MAPA_RESPOSTAS.get(str(resposta_str))

    novo_queue = [q for q in ak['queue'] if q != id_pergunta]
    novos_erros = dict(ak['erros'])

    if peso is not None:
        df   = _reconstruir_df(novos_erros)
        cols = set(df.columns)
        s    = _resolver_chave(chave, df, cols)
        if s is not None:
            df['total_erros'] += abs(s - peso)
            for _, row in df.iterrows():
                v = float(row['total_erros'])
                if v > 0:
                    novos_erros[str(int(row['id_participacao']))] = v

        pq_rest = _perguntas[_perguntas['id_pergunta'].isin(novo_queue)].copy()
        pq_rest = _aplicar_exclusoes(pq_rest, chave, peso)
        novo_queue = pq_rest['id_pergunta'].tolist()

    novo_ak = {**ak, 'erros': novos_erros, 'queue': novo_queue, 'rodada': ak['rodada'] + 1}
    return novo_ak, calcular_estado(novo_ak)


def confirmar_palpite(ak, confirmado, palpite_id, fase_palpite='mid'):
    """
    Lida com a resposta ao palpite (mid ou final).
    confirmado: True = acertou / False = errou / None = continuar
    fase_palpite: 'mid' ou 'final' — quando 'final' e errou, encerra o jogo.
    """
    _carregar()
    if confirmado is True:
        df_ord = _reconstruir_df(ak['erros']).sort_values('total_erros')
        top3   = [_row_para_dict(r) for _, r in df_ord.head(3).iterrows()]
        return ak, {
            'fase': 'fim', 'acertou': True,
            'rodada': ak['rodada'], 'total': MAX_RODADAS,
            'palpite': _row_para_dict(df_ord.iloc[0]),
            'top3': top3, 'pergunta': None,
        }

    if confirmado is False and palpite_id is not None:
        novos_erros = dict(ak['erros'])
        k = str(palpite_id)
        novos_erros[k] = novos_erros.get(k, 0.0) + 5.0
        ak = {**ak, 'erros': novos_erros}

    # Palpite final errado → encerra o jogo imediatamente
    if confirmado is False and fase_palpite == 'final':
        df     = _reconstruir_df(ak['erros'])
        df_ord = df.sort_values('total_erros')
        top3   = [_row_para_dict(r) for _, r in df_ord.head(3).iterrows()]

        # Exibe o palpite que o motor fez (antes da penalidade), não o novo top-1
        mask = df['id_participacao'] == int(palpite_id) if palpite_id is not None else None
        if mask is not None and mask.any():
            palpite_exibido = _row_para_dict(df[mask].iloc[0])
        else:
            palpite_exibido = _row_para_dict(df_ord.iloc[0])

        return ak, {
            'fase': 'fim', 'acertou': False,
            'rodada': ak['rodada'], 'total': MAX_RODADAS,
            'palpite': palpite_exibido,
            'top3': top3, 'pergunta': None,
        }

    return ak, calcular_estado(ak)


# Persistência em CSV

_CABECALHO_HISTORICO  = [
    'id_sessao', 'data_hora', 'apelido_palpite',
    'ano_copa', 'resultado', 'n_rodadas',
]
_CABECALHO_SUGESTOES  = [
    'id_sugestao', 'data_hora', 'nome', 'apelido',
    'ano_copa', 'posicao', 'clube', 'titular', 'gols', 'observacoes',
]


def salvar_historico(acertou: bool, palpite: dict, n_rodadas: int) -> None:
    """Grava o resultado da partida no CSV de Histórico Aprendizado."""
    caminho = _path('akinacopa-dataset - Histórico Aprendizado.csv')
    existe  = os.path.isfile(caminho) and os.path.getsize(caminho) > 0

    linha = {
        'id_sessao':      str(uuid.uuid4())[:8],
        'data_hora':      datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'apelido_palpite': palpite.get('apelido', ''),
        'ano_copa':       palpite.get('ano', ''),
        'resultado':      'acerto' if acertou else 'erro',
        'n_rodadas':      n_rodadas,
    }

    print(f'[histórico] salvando em: {caminho}')
    try:
        with open(caminho, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=_CABECALHO_HISTORICO)
            if not existe:
                writer.writeheader()
            writer.writerow(linha)
        print(f'[histórico] gravado com sucesso')
    except OSError as e:
        print(f'[AVISO] Falha ao salvar histórico: {e}')


def verificar_jogador(nome: str, ano: int) -> dict:
    """
    Verifica se um jogador existe na base para a Copa informada.

    Retorna dict com:
      encontrado : bool
      id_participacao : int | None
      apelido : str | None
    """
    _carregar()
    if not nome or not ano:
        return {'encontrado': False, 'id_participacao': None, 'apelido': None}

    nome_lower = nome.strip().lower()
    ano = int(ano)

    # Busca por nome OU apelido (case-insensitive, contém)
    mascara = (
        (_matriz['nome'].str.lower().str.contains(nome_lower, regex=False, na=False) |
         _matriz['apelido'].str.lower().str.contains(nome_lower, regex=False, na=False))
        & (_matriz['ano_copa'] == ano)
    )
    resultado = _matriz[mascara]

    if resultado.empty:
        return {'encontrado': False, 'id_participacao': None, 'apelido': None}

    linha = resultado.iloc[0]
    return {
        'encontrado':      True,
        'id_participacao': int(linha['id_participacao']),
        'apelido':         str(linha['apelido']),
    }


def salvar_sugestao(dados: dict) -> tuple[bool, str]:
    """
    Valida e grava uma sugestão de jogador em sugestoes_jogadores.csv.

    Retorna (sucesso, mensagem).
    """
    obrigatorios = ['nome', 'apelido', 'ano_copa', 'posicao']
    for campo in obrigatorios:
        if not dados.get(campo, '').strip():
            return False, f'O campo "{campo}" é obrigatório.'

    try:
        ano = int(dados['ano_copa'])
        if ano not in COPAS_MODERNAS:
            return False, 'Copa inválida. Escolha entre 2002, 2006, 2010, 2014, 2018 ou 2022.'
    except (ValueError, TypeError):
        return False, 'Ano da Copa inválido.'

    caminho = _path('sugestoes_jogadores.csv')
    existe  = os.path.isfile(caminho) and os.path.getsize(caminho) > 0

    linha = {
        'id_sugestao': str(uuid.uuid4())[:8],
        'data_hora':   datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'nome':        dados.get('nome', '').strip(),
        'apelido':     dados.get('apelido', '').strip(),
        'ano_copa':    ano,
        'posicao':     dados.get('posicao', '').strip(),
        'clube':       dados.get('clube', '').strip(),
        'titular':     dados.get('titular', '').strip(),
        'gols':        dados.get('gols', '0').strip(),
        'observacoes': dados.get('observacoes', '').strip(),
    }

    try:
        with open(caminho, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=_CABECALHO_SUGESTOES)
            if not existe:
                writer.writeheader()
            writer.writerow(linha)
        return True, 'Sugestão registrada! Avaliaremos para incluir na base.'
    except OSError as e:
        return False, f'Não foi possível salvar a sugestão: {e}'

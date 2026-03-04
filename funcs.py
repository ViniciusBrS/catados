import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from supabase import create_client, Client
from collections import Counter
import googlemaps

# =========================
# Supabase connection
# =========================
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if not url or not key:
        st.error("Configure SUPABASE_URL e SUPABASE_KEY em .streamlit/secrets.toml")
        st.stop()
    return create_client(url, key)

supabase = get_supabase()

# =========================
# Helpers (DB)
# =========================
def sb_select(table: str, columns="*", order: str | None = None, filtro = None,asc: bool = True):
    q = supabase.table(table).select(columns)
    if filtro:
        q = q.eq(filtro[0], filtro[1])
    if order:
        q = q.order(order, desc=not asc)
    res = q.execute()
    return res.data or []

def sb_insert(table: str, payload: dict):
    res = supabase.table(table).insert(payload).execute()
    return res.data

def sb_update(table: str, payload: dict, where: dict):
    q = supabase.table(table).update(payload)
    for k, v in where.items():
        q = q.eq(k, v)
    res = q.execute()
    return res.data

def sb_delete(table: str, where: dict):
    q = supabase.table(table).delete()
    for k, v in where.items():
        q = q.eq(k, v)
    res = q.execute()
    return res.data

def to_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows) if rows else pd.DataFrame()

def safe_int(x, default=0):
    try:
        if x is None or x == "":
            return default
        return int(x)
    except Exception:
        return default

def clamp_0_100(v: int) -> int:
    return max(0, min(100, v))

def getGeocode(endereco):
    gmaps = googlemaps.Client(key=st.secrets.get("MAPS_API_KEY", ""))
    geocode_result = gmaps.geocode(endereco)
    return geocode_result[0].get("geometry").get("location").get("lat"), geocode_result[0].get("geometry").get("location").get("lng")

# =========================
# Cached loads
# =========================
# @st.cache_data
def load_stats_jogadores():
    return sb_select(
        "vw_jogadores_estatisticas",
        columns="id,nome_completo,numero_camisa, posicao, partidas, gols, assistencias",
        order="nome_completo",
        asc=True
    )

def load_count_jogadores():
    return sb_select(
        "vw_partidas_count_jogadores",
        columns="id,data_partida,adversario, qtd_jogadores",
        order="data_partida",
        asc=True
    )

# @st.cache_data
def load_jogadores():
    return sb_select(
        "jogadores",
        columns="id,nome_completo,apelido,data_nascimento,posicao,numero_camisa,ativo,criado_em,atualizado_em,posicoes",
        order="nome_completo",
        asc=True
    )

# @st.cache_data
def load_partidas():
    return sb_select(
        "partidas",
        columns="id,data_partida,hora_partida,adversario,mandante,competicao,rodada,gols_pro,gols_contra,local_nome,endereco_linha,bairro,cidade,estado,cep,observacoes,criado_em,atualizado_em, latitude, longitude",
        order="data_partida",
        asc=False
    )

# @st.cache_data
def load_presencas(partida_id: str):
    return supabase.table("presencas_partida") \
        .select("id_partida,id_jogador,status,criado_em,jogadores(id,nome_completo,ativo)") \
        .eq("id_partida", partida_id).execute().data or []

# @st.cache_data
def load_gols(partida_id: str):
    return supabase.table("gols_partida") \
        .select(
            "id,id_partida,id_autor,id_assistente,criado_em,"
            "autor:jogadores!gols_partida_id_autor_fkey(id,nome_completo),"
            "assistente:jogadores!gols_partida_id_assistente_fkey(id,nome_completo)"
        ) \
        .eq("id_partida", partida_id).execute().data or []

# @st.cache_data
def load_habilidades(id_jogador: str):
    res = supabase.table("habilidades_jogador") \
        .select("id_jogador,velocidade,finalizacao,passe,drible,defesa,fisico,overall") \
        .eq("id_jogador", id_jogador).execute()
    data = res.data or []
    return data[0] if data else None

def clear_caches():
    load_jogadores.clear()
    load_partidas.clear()
    load_presencas.clear()
    load_gols.clear()
    load_habilidades.clear()

# =========================
# Position + OVR calc (0..100)
# =========================
def normalizar_posicao(posicoes: list | None) -> str:
    dict_norm = {"GK":"GK",
             "SW":"DF","CB":"DF","SB":"DF",
             "DMF":"MF","WB":"MF","CMF":"MF","SMF":"MF","OMF":"MF",
             "WG":"FW","ST":"FW","CF":"FW"}
    
    if "GK" in posicoes:
        return "GK"
    
    cnts = Counter([dict_norm.get(k) for k in posicoes])

    if (cnts.get("DF") or 0) >= (cnts.get("MF") or 0):
        return "DF"

    if (cnts.get("FW") or 0) >= (cnts.get("MF") or 0):
        return "FW"
    
    if (cnts.get("MF") or 0) > (cnts.get("FW") or 0):
        return "MF"
   
    return "MF"

def normalizar_posicao_old(posicao: str | None) -> str:
    if not posicao:
        return "MF"
    p = posicao.strip().lower()

    if p in ["gk", "gol", "goleiro", "keeper"] or "goleir" in p:
        return "GK"

    if p in ["df", "def", "defesa", "z", "zag"] or any(x in p for x in ["zague", "lateral", "defensor"]):
        return "DF"

    if p in ["mf", "mei", "meio"] or any(x in p for x in ["volant", "meia", "meio"]):
        return "MF"

    if p in ["fw", "ata", "atacante", "ponta", "centroavante", "st"] or any(x in p for x in ["atac", "ponta", "avante", "centro"]):
        return "FW"

    return "MF"

def calcular_overall_por_posicao(posicoes: list | None, skills: dict) -> int:
    """
    Skills em 0..100 -> OVR 0..100 (média ponderada por posição)
    """
    cat = normalizar_posicao(posicoes)

    pesos_por_cat = {
        "GK": {  # proxy (sem stats de goleiro específicos)
            "defesa": 2.3,
            "fisico": 1.4,
            "passe": 0.8,
            "velocidade": 0.6,
            "drible": 0,
            "finalizacao": 0,
        },
        "DF": {
            "defesa": 2,
            "fisico": 1.5,
            "passe": 0.8,
            "velocidade": 0.6,
            "drible": 0.1,
            "finalizacao": 0,
        },
        "MF": {
            "passe": 1.5,
            "drible": 1.1,
            "fisico": 1.0,
            "defesa": 0.9,
            "velocidade": 0.9,
            "finalizacao": 0.8,
        },
        "FW": {
            "finalizacao": 1.6,
            "velocidade": 1.5,
            "drible": 1.5,
            "passe": 0.6,
            "fisico": 0.8,
            "defesa": 0,
        },
    }

    pesos = pesos_por_cat.get(cat, pesos_por_cat["MF"])
    total_peso = sum(pesos.values())

    nota = 0.0
    for k, w in pesos.items():
        nota += float(skills.get(k, 50)) * w

    ovr = round(nota / total_peso)
    return clamp_0_100(ovr)

# =========================
# Habilidades upsert (com overall na própria tabela)
# =========================
def upsert_habilidades(id_jogador: str, payload: dict):
    try:
        sb_insert("habilidades_jogador", {"id_jogador": id_jogador, **payload})
    except Exception:
        sb_update("habilidades_jogador", payload, {"id_jogador": id_jogador})


# =========================
# Cria tabela de posicoes
# =========================
def render_pes_positions_grid(can_play: dict):
    rows = [
        ["GK", None],
        ["SW", "CB"],
        ["SB", None],
        ["DMF", "WB"],
        ["CMF", "SMF"],
        ["OMF", None],
        ["WG", "ST"],
        ["CF", None],
    ]

    defenders = {"SW", "CB", "SB"}
    midfield  = {"WB","DMF", "CMF", "SMF", "OMF"}
    attackers = {"WG", "ST", "CF"}

    def group_class(pos: str) -> str:
        if pos in defenders: return "grp-def"
        if pos in midfield:  return "grp-mid"
        if pos in attackers: return "grp-att"
        return "grp-gk"

    # st.markdown(
    #     """
    #     <style>
    #       .pes-wrap{
    #         display:inline-block;
    #         background:#bfc4c9;
    #         border:2px solid #5b6169;
    #         padding:8px;
    #         box-shadow: inset 0 0 0 1px #8b9198;
    #       }

    #       .pes-grid{
    #         display:grid;
    #         grid-template-columns: 58px 58px;
    #         gap:6px 6px;
    #       }

    #       .pes-cell{
    #         position:relative;
    #         width:58px; height:28px;
    #         display:flex;
    #         align-items:center;
    #         justify-content:center;
    #         font-weight:800;
    #         font-family: Arial, sans-serif;
    #         font-size:14px;
    #         letter-spacing:0.5px;
    #         border:1px solid #2a2f36;
    #         box-sizing:border-box;
    #         text-transform:uppercase;
    #         user-select:none;

    #         /* fundo escuro padrão para TODAS */
    #         background:#1b1f24;
    #         color:#8e959e;
    #       }

    #       /* NÃO JOGA */
    #       .off{
    #         filter: brightness(0.85);
    #         opacity: 0.9;
    #       }

    #       /* JOGA */
    #       .on{
    #         filter: brightness(1.55);
    #         color:#eef3f9;
    #       }

    #       /* acabamento interno HUD */
    #       .pes-cell::before{
    #         content:"";
    #         position:absolute;
    #         inset:1px;
    #         border:1px solid rgba(255,255,255,0.07);
    #         pointer-events:none;
    #       }

    #       /* faixa inferior por grupo */
    #       .pes-cell::after{
    #         content:"";
    #         position:absolute;
    #         left:0; right:0; bottom:0;
    #         height:4px;
    #         opacity:0.95;
    #       }

    #       .grp-att::after{ background:#c53a3a; }
    #       .grp-mid::after{ background:#2fa85f; }
    #       .grp-def::after{ background:#2f76c7; }
    #       .grp-gk::after { background:#b89f6a; }

    #       .pes-empty{
    #         width:58px; height:28px;
    #         border:1px solid transparent;
    #         background:transparent;
    #       }
    #     </style>
    #     """,
    #     unsafe_allow_html=True
    # )


    st.markdown(
        """
        <style>
        .pes-wrap{
            display:inline-block;
            background:#bfc4c9;
            border:3px solid #5b6169;              /* 2px → 3px */
            padding:12px;                          /* 8px → 12px */
            box-shadow: inset 0 0 0 2px #8b9198;   /* ajustado proporcionalmente */
        }

        .pes-grid{
            display:grid;
            grid-template-columns: 87px 87px;      /* 58px → 87px */
            gap:9px 9px;                           /* 6px → 9px */
        }

        .pes-cell{
            position:relative;
            width:87px; 
            height:42px;                           /* 28px → 42px */
            display:flex;
            align-items:center;
            justify-content:center;
            font-weight:800;
            font-family: Arial, sans-serif;
            font-size:21px;                        /* 14px → 21px */
            letter-spacing:0.75px;                 /* 0.5px → 0.75px */
            border:2px solid #2a2f36;              /* 1px → 2px */
            box-sizing:border-box;
            text-transform:uppercase;
            user-select:none;

            background:#1b1f24;
            color:#8e959e;
        }

        .off{
            filter: brightness(0.85);
            opacity: 0.9;
        }

        .on{
            filter: brightness(1.55);
            color:#eef3f9;
        }

        .pes-cell::before{
            content:"";
            position:absolute;
            inset:2px;                             /* proporcional */
            border:2px solid rgba(255,255,255,0.07);
            pointer-events:none;
        }

        .pes-cell::after{
            content:"";
            position:absolute;
            left:0; right:0; bottom:0;
            height:6px;                            /* 4px → 6px */
            opacity:0.95;
        }

        .grp-att::after{ background:#c53a3a; }
        .grp-mid::after{ background:#2fa85f; }
        .grp-def::after{ background:#2f76c7; }
        .grp-gk::after { background:#b89f6a; }

        .pes-empty{
            width:87px;
            height:42px;
            border:1px solid transparent;
            background:transparent;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    def cell_html(label):
        if label is None:
            return '<div class="pes-empty"></div>'

        plays = can_play.get(label, False)
        state_class = "on" if plays else "off"
        grp = group_class(label)

        return f'<div class="pes-cell {state_class} {grp}">{label}</div>'

    html_cells = []
    for r in rows:
        for label in r:
            html_cells.append(cell_html(label))

    st.markdown(
        f"""
        <div class="pes-wrap">
          <div class="pes-grid">
            {''.join(html_cells)}
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================
# Radar Plotly (0..100)
# =========================
def plot_radar_pes_hex_hud(skills: dict, titulo: str = "Habilidades"):
    categorias = ["Velocidade", "Finalização", "Drible", "Passe", "Defesa", "Físico"]
    chaves = ["velocidade", "finalizacao",  "drible", "passe", "defesa", "fisico"]

    valores = [clamp_0_100(int(skills.get(k, 50))) for k in chaves]
    valores_fechado = valores + [valores[0]]
    categorias_fechado = categorias + [categorias[0]]

    # Paleta “PES-like”
    #bg_paper = "#0f1318"      # fundo geral mais escuro
    bg_paper = "#fbfdff"      # fundo geral mais escuro
    #panel_bg = "#232a31"      # painel HUD
    #panel_bd = "#3a424c"      # borda do painel
    bg_polar = "rgba(0,0,0,0)"  # transparente pra aparecer o painel

    grid_col = "#58606a"      # grade hex
    axis_col = "#aeb6c2"      # contorno externo
    #text_col = "#d6dde8"      # textos
    text_col = "#2b2d30"      # textos

    neon = "#ff6f7d"          # linha principal
    neon_glow = "rgba(255, 111, 125, 0.22)"  # glow
    fill_col = "rgba(255, 111, 125, 0.08)"   # preenchimento bem discreto

    fig = go.Figure()

    # Painel HUD (retângulo no fundo)
    # fig.update_layout(
    #     shapes=[
    #         dict(
    #             type="rect",
    #             xref="paper", yref="paper",
    #             x0=0.05, y0=0.08, x1=0.95, y1=0.92,
    #             fillcolor=panel_bg,
    #             line=dict(color=panel_bd, width=2),
    #             layer="below"
    #         )
    #     ]
    # )

    # ---- Grade hexagonal (anéis) ----
    niveis = [20, 40, 60, 80, 100]
    for lvl in niveis:
        fig.add_trace(go.Scatterpolar(
            r=[lvl]*len(categorias) + [lvl],
            theta=categorias_fechado,
            mode="lines",
            line=dict(color=grid_col, width=1),
            hoverinfo="skip",
            showlegend=False
        ))

    # ---- “Raios” ----
    for cat in categorias:
        fig.add_trace(go.Scatterpolar(
            r=[0, 100],
            theta=[cat, cat],
            mode="lines",
            line=dict(color=grid_col, width=1),
            hoverinfo="skip",
            showlegend=False
        ))

    # ---- Contorno externo hexagonal mais forte ----
    fig.add_trace(go.Scatterpolar(
        r=[100]*len(categorias) + [100],
        theta=categorias_fechado,
        mode="lines",
        line=dict(color=axis_col, width=2),
        hoverinfo="skip",
        showlegend=False
    ))

    # ---- Glow do jogador ----
    fig.add_trace(go.Scatterpolar(
        r=valores_fechado,
        theta=categorias_fechado,
        mode="lines",
        line=dict(color=neon_glow, width=10),
        hoverinfo="skip",
        showlegend=False
    ))

    # ---- Linha principal do jogador (SEM marcadores) ----
    fig.add_trace(go.Scatterpolar(
        r=valores_fechado,
        theta=categorias_fechado,
        mode="lines",
        line=dict(color=neon, width=3),
        fill="toself",
        fillcolor=fill_col,
        hoverinfo="skip",
        showlegend=False
    ))

    fig.update_layout(
        title=dict(text=titulo, x=0.5, xanchor="center", font=dict(color=text_col)),
        paper_bgcolor=bg_paper,
        plot_bgcolor=bg_paper,
        margin=dict(l=50, r=50, t=70, b=50),
        polar=dict(
            bgcolor=bg_polar,

            # desliga grade circular padrão
            radialaxis=dict(
                range=[0, 100],
                showticklabels=False,
                showgrid=False,
                showline=False,
                ticks=""
            ),
            angularaxis=dict(
                rotation=30,  # Finalização no topo
                direction="counterclockwise",
                tickfont=dict(color=text_col, size=15),
                showgrid=False,
                showline=False
            ),
        ),
    )

    return fig

def plot_radar_plotly(skills: dict, titulo: str):
    categorias = ["Velocidade", "Finalização", "Passe", "Drible", "Defesa", "Físico"]
    chaves = ["velocidade", "finalizacao", "passe", "drible", "defesa", "fisico"]

    valores = [clamp_0_100(int(skills.get(k, 50))) for k in chaves]
    valores_fechado = valores + [valores[0]]
    categorias_fechado = categorias + [categorias[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=valores_fechado,
        theta=categorias_fechado,
        fill="tonext",
        name="Habilidades"
    ))

    fig.update_layout(
        title=titulo,
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tick0=0,
                dtick=20
            )
        ),
        showlegend=False,
        margin=dict(l=30, r=30, t=70, b=30),
    )

    return fig

def Xplot_radar_plotly(skills: dict, titulo: str):
    categorias = ["Velocidade", "Finalização", "Passe", "Drible", "Defesa", "Físico"]
    chaves = ["velocidade", "finalizacao", "passe", "drible", "defesa", "fisico"]

    valores = [clamp_0_100(int(skills.get(k, 50))) for k in chaves]
    valores_fechado = valores + [valores[0]]
    categorias_fechado = categorias + [categorias[0]]

    azul = "rgb(31,119,180)"
    fill_azul = "rgba(31,119,180,0.35)"

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=valores_fechado,
        theta=categorias_fechado,
        mode="lines+markers",
        line=dict(color=azul, width=3),
        marker=dict(size=7, color=azul),
        fill="toself",
        fillcolor=fill_azul,
        name=""
    ))



    fig.update_layout(
        title=dict(text=titulo, x=0.5, xanchor="center"),
        showlegend=False,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=40, r=40, t=60, b=40),
        polar=dict(
            bgcolor="white",
            radialaxis=dict(
                range=[0, 100],
                tickmode="linear",
                tick0=0,
                dtick=20,
                showline=True,
                linecolor="black",   # contorno externo mais escuro
                linewidth=1.5,
                gridcolor="lightgray",
                gridwidth=1,
                ticks="",
                tickfont=dict(size=10),
                angle=0,             # posiciona os números na direção da direita
            ),
            angularaxis=dict(
                direction="counterclockwise",
                rotation=0,           # começa em "Velocidade" na direita
                showline=True,
                linecolor="black",    # contorno externo mais escuro
                linewidth=1.5,
                gridcolor="lightgray",
                gridwidth=1,
                tickfont=dict(size=11),
            ),
        ),
    )

    return fig

#     fig.update_layout(
#   polar=dict(
#     angularaxis=dict(
#       rotation=90, # Rotates 90 degrees counter-clockwise
#       direction="clockwise" # Optional: set direction
#     )
#   )
# )


# =========================
# UI helpers
# =========================


def df_pick_id(df: pd.DataFrame, label_col: str, vkey: str = None, id_col: str = "id", label="Selecione", lbl_visibility='visible'):
    if df.empty:
        return None, None
    options = [(row[id_col], row[label_col]) for _, row in df.iterrows()]
    selected = st.selectbox(label,options, format_func=lambda x: x[1], key=vkey,  label_visibility=lbl_visibility)

    return selected[0], selected[1]


# ==========================================================
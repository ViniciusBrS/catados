import streamlit as st
import pandas as pd
import funcs as f

st.set_page_config(page_title="⚽ Catados F.C", layout="wide")

st.title("Elenco 2026")

df_stats = f.to_df(f.load_stats_jogadores())
dfj = f.to_df(f.load_jogadores())

if dfj.empty:
    st.info("Cadastre o primeiro jogador no formulário acima.")
else:
    st.subheader("Selecione o jogador")
    cc0, cc1, cc2, cc3 = st.columns(4)
    with cc0:
        dfj["label"] = dfj.apply(lambda r: f'{r["nome_completo"]} ({r["numero_camisa"] or "-"})', axis=1)
        jogador_id, jogador_label = f.df_pick_id(dfj, label_col="label", id_col="id", label="")

    if not jogador_id:
        st.stop()

    hab = f.load_habilidades(jogador_id)  
    st.session_state["hab"] = hab if hab is not None else {"velocidade": 50,"finalizacao": 50,"passe": 50,"drible": 50,"defesa": 50,"fisico": 50,"overall": 50}

    j_row = dfj[dfj["id"] == jogador_id].iloc[0].to_dict()
    posicao_jogador = j_row.get("posicao")
    posicoes_jogador = j_row.get("posicoes") or []

    pos_default = {
    "GK": False,
    "SW": False, "CB": False,
    "SB": False,
    "DMF": False, "WB": False,
    "CMF": False, "SMF": False,
    "OMF": False,
    "WG": False, "ST": False,
    "CF": False,
    }

    pos_can_play = {k: True if k in posicoes_jogador else v for k,v in pos_default.items()}


    # ---- Estatísticas (presença, gols, assists)
    pres_total = f.supabase.table("presencas_partida") \
        .select("status", count="exact") \
        .eq("id_jogador", jogador_id) \
        .execute()
    total_registros_presenca = pres_total.count or 0

    pres_ok = f.supabase.table("presencas_partida") \
        .select("status", count="exact") \
        .eq("id_jogador", jogador_id) \
        .eq("status", "presente") \
        .execute()
    jogos_presente = pres_ok.count or 0

    gols_autor = f.supabase.table("gols_partida") \
        .select("id", count="exact") \
        .eq("id_autor", jogador_id).execute()
    total_gols = gols_autor.count or 0

    assists = f.supabase.table("gols_partida") \
        .select("id", count="exact") \
        .eq("id_assistente", jogador_id).execute()
    total_assists = assists.count or 0

    perc_presenca = (jogos_presente / total_registros_presenca * 100) if total_registros_presenca else 0.0

    # ---- Habilidades
    # hab = f.load_habilidades(jogador_id)
    # if not hab:
    #     hab = {
    #         "velocidade": 50,
    #         "finalizacao": 50,
    #         "passe": 50,
    #         "drible": 50,
    #         "defesa": 50,
    #         "fisico": 50,
    #         "overall": 50
    #     }

    ovr_atual = f.clamp_0_100(int(st.session_state["hab"].get("overall", 50)))
    pos_cat = f.normalizar_posicao(posicao_jogador)

    #st.subheader(jogador_label)
    c0, c1, c2, c3, c4 = st.columns(5)
    c0.metric("OVR", ovr_atual)
    c1.metric("Gols", total_gols)
    c2.metric("Assistências", total_assists)
    c3.metric("Jogos presente", jogos_presente)
    c4.metric("% presença", f"{perc_presenca:.1f}%")

    st.caption(f"Posição (normalizada): **{pos_cat}** | Ajuste os sliders (0–100) e salve para recalcular o OVR.")

    st.divider()
    colRadar, colHab, colPos = st.columns([1, 1, 1], gap="large")

    with colRadar:
        st.subheader("Radar de habilidades")

        #fig = f.plot_radar_plotly(hab, f"{jogador_label} | OVR {ovr_atual}")
        fig = f.plot_radar_pes_hex_hud(st.session_state["hab"], f"{jogador_label} | OVR {ovr_atual}")
        
        st.plotly_chart(fig, width='stretch')

    with colHab:
        st.subheader("Editar habilidades (0–100)")
        with st.form("form_skills"):
            velocidade = st.slider("Velocidade", 0, 100, f.clamp_0_100(int(st.session_state["hab"].get("velocidade", 50))))
            finalizacao = st.slider("Finalização", 0, 100, f.clamp_0_100(int(st.session_state["hab"].get("finalizacao", 50))))
            passe = st.slider("Passe", 0, 100, f.clamp_0_100(int(st.session_state["hab"].get("passe", 50))))
            drible = st.slider("Drible", 0, 100, f.clamp_0_100(int(st.session_state["hab"].get("drible", 50))))
            defesa = st.slider("Defesa", 0, 100, f.clamp_0_100(int(st.session_state["hab"].get("defesa", 50))))
            fisico = st.slider("Físico", 0, 100, f.clamp_0_100(int(st.session_state["hab"].get("fisico", 50))))

            salvar = st.form_submit_button("Salvar habilidades e recalcular OVR")
            if salvar:
                if st.session_state['adm']:
                    payload = {
                        "velocidade": f.clamp_0_100(velocidade),
                        "finalizacao": f.clamp_0_100(finalizacao),
                        "passe": f.clamp_0_100(passe),
                        "drible": f.clamp_0_100(drible),
                        "defesa": f.clamp_0_100(defesa),
                        "fisico": f.clamp_0_100(fisico),
                    }
                    ovr = f.calcular_overall_por_posicao(posicao_jogador, payload)
                    payload["overall"] = ovr

                    f.upsert_habilidades(jogador_id, payload)
                    st.session_state["hab"] = f.load_habilidades(jogador_id)
                    st.success(f"Habilidades salvas! OVR ({pos_cat}) atualizado para {ovr}.")
                    st.rerun()
                else:
                    st.toast("Liberado apenas para ADM!", icon="❌")

    with colPos:
        st.subheader("Posições")
        f.render_pes_positions_grid(pos_can_play)

st.divider()

st.subheader("Elenco completo")
df_lista = df_stats
df_lista.columns = ['Nome','Número da Camisa','Posição','Partidas','Gols','Assistencias']             
st.dataframe(df_lista, hide_index=True,width='stretch', selection_mode='single-cell', on_select='rerun')

st.divider()

colA, colB = st.columns([1, 1], gap="large")
with colA:
    st.subheader("Cadastrar jogador")
    with st.form("form_add_jogador", clear_on_submit=True):
        nome = st.text_input("Nome completo*", placeholder="Ex: João da Silva")
        apelido = st.text_input("Apelido", placeholder="Ex: Jão")
        #posicao = st.text_input("Posição", placeholder="Ex: Goleiro / Zagueiro / Volante / Atacante")
        posicao = st.selectbox("Posição", options=['Goleiro','Zagueiro','Lateral','Volante','Meia','Atacante'])
        numero_camisa = st.number_input("Número da camisa", min_value=0, max_value=99, value=0, step=1)
        ativo = st.checkbox("Ativo", value=True)

        submitted = st.form_submit_button("Salvar")
        if submitted:
            if st.session_state['adm']:
                if not nome.strip():
                    st.error("Nome completo é obrigatório.")
                else:
                    f.sb_insert("jogadores", {
                        "nome_completo": nome.strip(),
                        "apelido": apelido.strip() if apelido else None,
                        "posicao": posicao.strip() if posicao else None,
                        "numero_camisa": f.safe_int(numero_camisa, 0),
                        "ativo": ativo
                    })
                    # f.clear_caches()
                    st.success("Jogador cadastrado!")
                    st.rerun()
            else:
                st.toast("Liberado apenas para ADM!", icon="❌")

with colB:
    st.subheader("Editar jogador")
    if dfj.empty:
        st.info("Nenhum jogador cadastrado ainda.")
    else:
        dfj["label"] = dfj.apply(
            lambda r: f'{r["nome_completo"]} ({r["posicao"] or "-"}) #{int(r["numero_camisa"]) if pd.notna(r["numero_camisa"]) else "-"}',
            axis=1
        )
        jogador_id, _ = f.df_pick_id(dfj, label_col="label", id_col="id", label="Selecione o jogador")

        if jogador_id:
            row = dfj[dfj["id"] == jogador_id].iloc[0]
            lista_posicao = ['Goleiro','Zagueiro','Lateral','Volante','Meia','Atacante']

            nome_e = st.text_input("Nome completo", value=row["nome_completo"])
            apelido_e = st.text_input("Apelido", value=row["apelido"] if pd.notna(row["apelido"]) else "")
            #posicao_e = st.text_input("Posição", value=row["posicao"] if pd.notna(row["posicao"]) else "")
            posicao_e = st.selectbox("Posição", options= lista_posicao, index = lista_posicao.index(row["posicao"]))
            numero_e = st.number_input(
                "Número da camisa", min_value=0, max_value=99,
                value=int(row["numero_camisa"]) if pd.notna(row["numero_camisa"]) else 0, step=1
            )
            ativo_e = st.checkbox("Ativo", value=bool(row["ativo"]))

            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("Atualizar", width='stretch'):
                    if st.session_state['adm']:
                        if not nome_e.strip():
                            st.error("Nome completo é obrigatório.")
                        else:
                            f.sb_update("jogadores", {
                                "nome_completo": nome_e.strip(),
                                "apelido": apelido_e.strip() if apelido_e else None,
                                "posicao": posicao_e.strip() if posicao_e else None,
                                "numero_camisa": f.safe_int(numero_e, 0),
                                "ativo": ativo_e
                            }, {"id": jogador_id})
                            # f.clear_caches()
                            st.success("Jogador atualizado!")
                            st.rerun()
                    else:
                        st.toast("Liberado apenas para ADM!", icon="❌")

            with c2:
                if st.button("Desativar", width='stretch'):
                    if st.session_state['adm']:
                        f.sb_update("jogadores", {"ativo": False}, {"id": jogador_id})
                        # f.clear_caches()
                        st.success("Jogador desativado!")
                        st.rerun()
                    else:
                        st.toast("Liberado apenas para ADM!", icon="❌")

            with c3:
                if st.button("Excluir", type="primary", width='stretch'):
                    if st.session_state['adm']:
                        f.sb_delete("jogadores", {"id": jogador_id})
                        # f.clear_caches()
                        st.success("Jogador excluído!")
                        st.rerun()
                    else:
                        st.toast("Liberado apenas para ADM!", icon="❌")




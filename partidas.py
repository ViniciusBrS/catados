import time
from datetime import datetime
import pandas as pd
import streamlit as st
import plotly.express as px
import folium
from streamlit_folium import st_folium
import funcs as f

st.set_page_config(page_title="⚽ Catados F.C", layout="wide")

st.title("Controle das partidas")

dfp = f.to_df(f.load_partidas())
dfcj = f.to_df(f.load_count_jogadores())
dfcj['data_partida'] = pd.to_datetime(dfcj['data_partida'])


# if dfp.empty:
#     st.info("Cadastre a primeira partida no formulário acima.")
#     st.stop()

# df_tbl_p = dfp.drop(columns=["label","id","mandante","competicao","rodada","criado_em","observacoes","atualizado_em"], errors="ignore")
# df_tbl_p['Endereço'] = df_tbl_p[["endereco_linha", "cidade", 'estado']].apply(", ".join, axis=1)
# df_tbl_p.rename(columns={'data_partida':'Data','hora_partida':'Hora', 'adversario':'Adversário', 'gols_pro':'Gols Pró',
#                     'gols_contra':'Gols Contra', 'local_nome':'Local'},inplace=True)
# df_tbl_p.drop(columns=['endereco_linha','bairro','cidade','cep','estado'], inplace=True)
# st.dataframe(df_tbl_p, hide_index=True, width='stretch')


mapa = folium.Map(location=(dfp['latitude'].mean(), dfp['longitude'].mean()), zoom_start=12)
for i in dfp.itertuples():
    folium.Marker(
    location=[i.latitude, i.longitude],
    tooltip=f"""Adversário: <b>{i.adversario}</b>
                <br/>Data: {datetime.strptime(i.data_partida, '%Y-%m-%d').strftime('%d/%m/%Y')}
                <br/>Resultado: Catados {i.gols_pro} x {i.adversario} {i.gols_contra}
                <br/>Local: {i.local_nome}
            """,      
    icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(mapa)

with st.expander("Mostrar mapa das partidas"):
    st.subheader("Clique nos marcadores para visualizar os detalhes da partida")
    container = st.container()
    with container:
        st_mapa = st_folium(mapa, height=500,use_container_width=True)

st.divider()


fig = px.bar(dfcj, x='data_partida', y='qtd_jogadores', 
             hover_data=['adversario'],
             labels={"data_partida": "Data", "qtd_jogadores": "Qtde. jogadores"},
             title='Quantidade de jogadores por partida')

# Barras neon azul/ciano
fig.update_traces(
    marker_color='#00c2ff',      # azul/ciano moderno
    marker_line_color='#6c2cff', # roxo neon
    marker_line_width=2
)


# Layout estilo videogame
fig.update_layout(
    plot_bgcolor='#f7f9fc',
    paper_bgcolor='#ffffff',
    font=dict(color='#1f2937'),
    title_font=dict(size=22)
)

# Eixo X
fig.update_xaxes(
    #range=["2026-01-01", "2026-12-31"],
    #dtick="M1",
    tickvals = dfcj['data_partida'].tolist(),
    tickformat="%d/%m/%Y",
    gridcolor='rgba(0,0,0,0.08)',
    zeroline=False,
    fixedrange=True
)

# Eixo Y (inteiros)
fig.update_yaxes(
    dtick=1,
     gridcolor='rgba(0,0,0,0.08)',
    zeroline=False,
    fixedrange=True
)

st.plotly_chart(fig, width='stretch', config={"displayModeBar": False, 'scrollZoom': False})

st.divider()

st.subheader("Partida: Presenças e Gols")


dfp["label"] = dfp.apply(
    lambda r: f'{datetime.strptime(r["data_partida"], '%Y-%m-%d').strftime('%d/%m/%Y')} vs {r["adversario"]} ({int(r["gols_pro"])}x{int(r["gols_contra"])})',
    axis=1
)
partida_id, partida_label = f.df_pick_id(dfp, label_col="label", id_col="id", label="Selecione a partida")
if not partida_id:
    st.stop()

partida_row = dfp[dfp["id"] == partida_id].iloc[0].to_dict()

dfj = f.to_df(f.load_jogadores())
if dfj.empty:
    st.info("Cadastre jogadores primeiro.")
    st.stop()

presencas = f.load_presencas(partida_id)
gols = f.load_gols(partida_id)

gols_eventos = len(gols)
gols_pro_salvo = int(partida_row.get("gols_pro") or 0)
#gols_contra_salvo = int(partida_row.get("gols_contra") or 0)

#st.subheader(partida_label)
#c1, c2, c3, c4 = st.columns(4)
#c1.metric("Gols pró (eventos)", gols_eventos)
#c2.metric("Gols pró (placar salvo)", gols_pro_salvo, delta=(gols_eventos - gols_pro_salvo))
#c3.metric("Gols contra (placar salvo)", gols_contra_salvo)
#c4.write("")

if gols_eventos != gols_pro_salvo:
    #st.warning("Diferença entre gols pró em eventos e o placar salvo.")
    st.badge("Existem gols marcados sem atribuição!", icon="⚠️", color="orange")
    # if st.button("Sincronizar placar salvo (gols_pro) com eventos"):
    #     if st.session_state['adm']:
    #         f.sb_update("partidas", {"gols_pro": gols_eventos}, {"id": partida_id})
            
    #         st.success("gols_pro atualizado com base nos eventos!")
    #         time.sleep(1)
    #         st.rerun()
    #     else:
    #         st.toast("Liberado apenas para ADM!", icon="❌")

tab1, tab2 = st.tabs(["⚽ Gols e Assistências","✅ Presenças"])

# ---- Gols e assistências ----
with tab1:
    st.markdown("### Registrar gols")

    dfj["label"] = dfj.apply(lambda r: f'{r["nome_completo"]} ({r["posicao"] or "-"})', axis=1)

    col1, col2, col3 = st.columns([1, 1, 1], gap="large")

    with col1:
        autor = st.selectbox(
            "Autor do gol",
            [(r["id"], r["label"]) for _, r in dfj.query("ativo==True").iterrows()],
            format_func=lambda x: x[1]
        )
        autor_id = autor[0]

    with col2:
        assist_opts = [(None, "Sem assistência")] + [(r["id"], r["label"]) for _, r in dfj.query("ativo==True").iterrows()]
        assist = st.selectbox("Assistente (opcional)", assist_opts, format_func=lambda x: x[1])
        assist_id = assist[0]

    with col3:
        st.write("")
        st.write("")
        if st.button("Adicionar gol", width='stretch'):
            if st.session_state['adm']:
                if autor_id != assist_id:
                    f.sb_insert("gols_partida", {"id_partida": partida_id, "id_autor": autor_id, "id_assistente": assist_id})
                    st.success("Gol registrado!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.toast("O autor do gol e da assistencia devem ser jogadores diferentes!", icon="❌")
            else:
                st.toast("Liberado apenas para ADM!", icon="❌")

    st.divider()

    col1_gol, col2_gol = st.columns([1, 1,], gap="large")

    gols = f.load_gols(partida_id)
    if gols:
        with col1_gol:
            st.markdown("### Gols cadastrados na partida")
            
            rows = []
            for g in gols:
                rows.append({
                    "Gol": (g.get("autor") or {}).get("nome_completo") or "-",
                    "Assistência": (g.get("assistente") or {}).get("nome_completo") or "-",
                })
            df_gols = pd.DataFrame(rows)
            st.dataframe(df_gols, width='stretch', hide_index=True)
            


        with col2_gol:
                st.markdown("### Remover gol")
                opts = [(g["id"], f'{(g.get("autor") or {}).get("nome_completo","-")} (assist: {(g.get("assistente") or {}).get("nome_completo","Sem assistência" )})') for g in gols]
                gol_sel = st.selectbox("Selecione o gol", opts, format_func=lambda x: x[1])
                if st.button("Remover gol", width='stretch'):
                    if st.session_state['adm']:
                        f.sb_delete("gols_partida", {"id": gol_sel[0]})
                        st.success("Gol removido!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.toast("Liberado apenas para ADM!", icon="❌")
    else:
        st.info("Sem gols registrados ainda.")

# ---- Presença----
with tab2:
    st.markdown("### Marcar presença")

    pres_map = {p["id_jogador"]: p["status"] for p in presencas}

    # só ativos por padrão
    dfj_ativos = dfj[dfj["ativo"] == True].copy() if "ativo" in dfj.columns else dfj.copy()
    dfj_ativos["label"] = dfj_ativos.apply(lambda r: f'{r["nome_completo"]} ({r["posicao"] or "-"})', axis=1)

    default_presentes = [jid for jid in dfj_ativos["id"] if pres_map.get(jid) == "presente"]

    selected_ids = st.multiselect(
        "Jogadores presentes (marque os que foram)",
        options=list(dfj_ativos["id"]),
        default=default_presentes,
        format_func=lambda pid: dfj_ativos.loc[dfj_ativos["id"] == pid, "label"].values[0]
    )

    st.caption("Ao salvar: selecionados = **presente**. Não selecionados (ativos) = **ausente**.")

    if st.button("Salvar presenças (lote)", width='stretch'):
        if st.session_state['adm']:
            ativos_ids = list(dfj_ativos["id"])
            for jid in ativos_ids:
                status = "presente" if jid in selected_ids else "ausente"
                try:
                    f.sb_insert("presencas_partida", {"id_partida": partida_id, "id_jogador": jid, "status": status})
                except Exception:
                    f.sb_update("presencas_partida", {"status": status}, {"id_partida": partida_id, "id_jogador": jid})
            
            st.success("Presenças atualizadas!")
            time.sleep(1)
            st.rerun()
        else:
            st.toast("Liberado apenas para ADM!", icon="❌")

    # st.divider()
    # st.markdown("### Presentes na partida")
    # presencas = f.load_presencas(partida_id)
    # if presencas:
    #     rows = []
    #     for p in presencas:
    #         rows.append({
    #             "jogador": (p.get("jogadores") or {}).get("nome_completo"),
    #             "status": p["status"],
    #             "criado_em": p["criado_em"]
    #         })
    #     st.dataframe(pd.DataFrame(rows).sort_values(by=["status", "jogador"], ignore_index=True), width='stretch')
    # else:
    #     st.info("Sem presenças registradas ainda.")   

st.divider()

colA, colB = st.columns([1, 1], gap="large")

with colA:
    st.subheader("Cadastrar partida")
    with st.form("form_add_partida", clear_on_submit=True):
        data_partida = st.date_input("Data da partida*")
        hora_partida = st.time_input("Hora (opcional)")
        adversario = st.text_input("Adversário*", placeholder="Ex: Time do Bairro")
        mandante = st.checkbox("Mandante (jogo em casa)", value=False)
        competicao = st.text_input("Competição", placeholder="Ex: Amistoso / Liga")
        rodada = st.text_input("Rodada", placeholder="Ex: Rodada 2")

        gols_pro = st.number_input("Gols pró", min_value=0, max_value=15, value=0, step=1)
        gols_contra = st.number_input("Gols contra", min_value=0, max_value=15, value=0, step=1)

        st.markdown("**Endereço / Local**")
        local_nome = st.text_input("Nome do local", placeholder="Ex: Campo do Vila")
        endereco_linha = st.text_input("Endereço (rua/av + número)*", placeholder="Ex: Rua X, 123")
        bairro = st.text_input("Bairro", placeholder="Ex: Centro")
        cidade = st.text_input("Cidade", placeholder="Ex: São Paulo")
        estado = st.text_input("Estado", placeholder="Ex: SP")
        cep = st.text_input("CEP", placeholder="Ex: 00000-000")

        observacoes = st.text_area("Observações")

        submitted = st.form_submit_button("Salvar")
        if submitted:
            if st.session_state['adm']:
                if not adversario.strip():
                    st.error("Adversário é obrigatório.")
                elif not endereco_linha.strip():
                    st.error("Endereço é obrigatório.")
                else:
                    lst_end = [endereco_linha, bairro, cidade, cep, estado]
                    endereco_comp = ", ".join([p.strip() for p in lst_end if p and p.strip()])
                        
                    lat, long = f.getGeocode(endereco_comp+", brazil")

                    f.sb_insert("partidas", {
                        "data_partida": str(data_partida),
                        "hora_partida": str(hora_partida) if hora_partida else None,
                        "adversario": adversario.strip(),
                        "mandante": mandante,
                        "competicao": competicao.strip() if competicao else None,
                        "rodada": rodada.strip() if rodada else None,
                        "gols_pro": f.safe_int(gols_pro, 0),
                        "gols_contra": f.safe_int(gols_contra, 0),
                        "local_nome": local_nome.strip() if local_nome else None,
                        "endereco_linha": endereco_linha.strip(),
                        "bairro": bairro.strip() if bairro else None,
                        "cidade": cidade.strip() if cidade else None,
                        "estado": estado.strip() if estado else None,
                        "cep": cep.strip() if cep else None,
                        "latitude": lat or None,
                        "longitude": long or None,
                        "observacoes": observacoes.strip() if observacoes else None
                    })
                    
                    st.success("Partida cadastrada!")
                    time.sleep(1)
                    st.rerun()
            else:
                st.toast("Liberado apenas para ADM!", icon="❌")

with colB:
    st.subheader("Editar / Excluir partida")

    with st.container(border=True):
        if dfp.empty:
            st.info("Nenhuma partida cadastrada ainda.")
            st.stop()
        
        dfp["label"] = dfp.apply(
            lambda r: f'{r["data_partida"]} vs {r["adversario"]} ({int(r["gols_pro"])}x{int(r["gols_contra"])})',
            axis=1
        )
        partida_id, _ = f.df_pick_id(dfp, label_col="label", id_col="id", label="Selecione a partida", vkey="slct_partida_crud")

        if partida_id:
            row = dfp[dfp["id"] == partida_id].iloc[0]

            adversario_e = st.text_input("Adversário", value=row["adversario"])
            mandante_e = st.checkbox("Mandante", value=bool(row["mandante"]))
            competicao_e = st.text_input("Competição", value=row["competicao"] if pd.notna(row["competicao"]) else "")
            rodada_e = st.text_input("Rodada", value=row["rodada"] if pd.notna(row["rodada"]) else "")

            gols_pro_e = st.number_input("Gols pró (placar salvo)", min_value=0, max_value=50, value=int(row["gols_pro"]), step=1)
            gols_contra_e = st.number_input("Gols contra (placar salvo)", min_value=0, max_value=50, value=int(row["gols_contra"]), step=1)

            local_nome_e = st.text_input("Nome do local", value=row["local_nome"] if pd.notna(row["local_nome"]) else "")
            endereco_linha_e = st.text_input("Endereço*", value=row["endereco_linha"])
            bairro_e = st.text_input("Bairro", value=row["bairro"] if pd.notna(row["bairro"]) else "")
            cidade_e = st.text_input("Cidade", value=row["cidade"] if pd.notna(row["cidade"]) else "")
            estado_e = st.text_input("Estado", value=row["estado"] if pd.notna(row["estado"]) else "")
            cep_e = st.text_input("CEP", value=row["cep"] if pd.notna(row["cep"]) else "")

            observacoes_e = st.text_area("Observações", value=row["observacoes"] if pd.notna(row["observacoes"]) else "")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("Atualizar", width='stretch'):
                    if st.session_state['adm']:
                        if not adversario_e.strip():
                            st.error("Adversário é obrigatório.")
                            st.stop()
                        if not endereco_linha_e.strip():
                            st.error("Endereço é obrigatório.")
                            st.stop()

                        lst_end_e = [endereco_linha_e, bairro_e, cidade_e, cep_e, estado_e]
                        endereco_comp_e = ", ".join([p.strip() for p in lst_end_e if p and p.strip()])
                            
                        lat_e, long_e = f.getGeocode(endereco_comp_e+", brazil")

                        f.sb_update("partidas", {
                            "adversario": adversario_e.strip(),
                            "mandante": mandante_e,
                            "competicao": competicao_e.strip() if competicao_e else None,
                            "rodada": rodada_e.strip() if rodada_e else None,
                            "gols_pro": f.safe_int(gols_pro_e, 0),
                            "gols_contra": f.safe_int(gols_contra_e, 0),
                            "local_nome": local_nome_e.strip() if local_nome_e else None,
                            "endereco_linha": endereco_linha_e.strip(),
                            "bairro": bairro_e.strip() if bairro_e else None,
                            "cidade": cidade_e.strip() if cidade_e else None,
                            "estado": estado_e.strip() if estado_e else None,
                            "cep": cep_e.strip() if cep_e else None,
                            "latitude": lat_e or None,
                            "longitude": long_e or None,
                            "observacoes": observacoes_e.strip() if observacoes_e else None
                        }, {"id": partida_id})
                        
                        st.success("Partida atualizada!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.toast("Liberado apenas para ADM!", icon="❌")
            
            with c2:
                if st.button("Excluir", width='stretch'):
                    if st.session_state['adm']:
                        f.sb_delete("partidas", {"id": partida_id})
                        st.success("Partida excluída!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.toast("Liberado apenas para ADM!", icon="❌")



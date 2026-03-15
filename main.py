import streamlit as st
import funcs as f

@st.dialog("Acesso administrativo")
def modal_login_adm():
    with st.form("form_login_adm"):
        txsenha = st.text_input("Digite a senha ADM:", type="password")
        entrou = st.form_submit_button("Entrar", use_container_width=True)

        if entrou:
            senha_ok = txsenha == st.secrets.get("SENHA_ADM", "")
            st.session_state["adm"] = senha_ok

            if senha_ok:
                st.toast("ADM LIBERADO COM SUCESSO!!", icon="✅")
                st.rerun()
            else:
                st.toast("SENHA INVÁLIDA!!", icon="❌")

if 'adm' not in st.session_state:
    st.session_state['adm'] = False
  
# with st.sidebar:
#     if not st.session_state['adm']:
#         txsenha = st.text_input("Digite a senha ADM:", type='password')
#         if st.button("Entrar"):
#             st.session_state['adm'] = txsenha == st.secrets.get('SENHA_ADM','')

#             if st.session_state['adm']:
#                 st.toast("ADM LIBERADO COM SUCESSO!!", icon="✅")
#             else:
#                 st.toast("SENHA INVÁLIDA!!", icon="❌")

st.title('⚽ Catados F.C')

c1, c2, c3, c4= st.columns(4)

with c1:
    if st.button("Partidas",type='primary',icon=":material/calendar_check:", use_container_width=True):
        st.switch_page("partidas.py")

with c2:
    if st.button("Elenco", type='primary',icon=":material/groups:", use_container_width=True):
        st.switch_page("elenco.py")


with c4:
    if not st.session_state["adm"]:
        if st.button("Abrir login ADM"):
            modal_login_adm()
    else:
        st.write("ADM liberado ✅")


# Define as páginas apontando para arquivos ou funções
pg_partidas = st.Page("partidas.py", title="Partidas", icon=":material/calendar_check:")
pg_elenco = st.Page("elenco.py", title="Elenco", icon=":material/groups:")

# Cria a navegação
pg = st.navigation([pg_partidas, pg_elenco])

# Executa a página selecionada
pg.run()
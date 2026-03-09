import streamlit as st
import funcs as f

if 'adm' not in st.session_state:
    st.session_state['adm'] = False
  
with st.sidebar:
    if not st.session_state['adm']:
        txsenha = st.text_input("Digite a senha ADM:", type='password')
        if st.button("Entrar"):
            st.session_state['adm'] = txsenha == st.secrets.get('SENHA_ADM','')

            if st.session_state['adm']:
                st.toast("ADM LIBERADO COM SUCESSO!!", icon="✅")
            else:
                st.toast("SENHA INVÁLIDA!!", icon="❌")

st.title('⚽ Catados F.C')

# Define as páginas apontando para arquivos ou funções
pg_partidas = st.Page("partidas.py", title="Partidas", icon=":material/calendar_check:")
pg_elenco = st.Page("elenco.py", title="Elenco", icon=":material/groups:")

# Cria a navegação
pg = st.navigation([pg_partidas, pg_elenco])

# Executa a página selecionada
pg.run()
import datetime

import streamlit as st

from strands_data_analyst.data_analyst_session import DataAnalystSession

st.set_page_config(
    page_title="Data Analyst Agent",
    page_icon="📈",
    layout="wide")

if "data_analyst" not in st.session_state:
    import pathlib
    st.session_state.data_analyst = DataAnalystSession(
        static_path=(pathlib.Path(__file__).parent / "static").resolve()
    )
agent = st.session_state.data_analyst


chat_column, doc_column = st.columns(2, border=True)

with chat_column:
    chat_container = st.container()

with doc_column:
    doc_container = st.empty()

if agent.data_analyst.document:
    with doc_container:
        st.markdown(agent.data_analyst.document)


SKIP_MSG_TYPES = {'code', 'dataframe'}

def display_message(msg):
    if msg is None or msg['type'] in SKIP_MSG_TYPES:
        return

    if msg['type'] == 'document':
        with doc_container:
            st.markdown(msg['content'])
    else:
        with chat_container:
            if msg['role'] == 'user':
                with st.chat_message('user'):
                    st.markdown(msg['content'])
            elif msg['role'] == 'assistant':
                with st.chat_message('assistant'):
                    if msg['type'] == 'image':
                        st.image(msg['content'].path, msg['content'].caption)
                    elif  msg['type'] == 'text':
                        st.markdown(msg['content'])


if 'selected_database' in st.session_state:
    db_id = st.session_state.selected_database
    if db_id and agent.is_new_db(db_id):
        with st.spinner(f"Loading {db_id}..."):
            agent.set_db(db_id)


for msg in agent.history:
    display_message(msg)


with st.sidebar:
    st.header("User Input")
    if agent.data_analyst.db_id is not None:
        if prompt := st.chat_input("Enter your input here."):
            for msg in agent.query(prompt):
                display_message(msg)
        
        if agent.history:
            if st.button("Generate Report"):
                msg = agent.generate_report()
                display_message(msg)

        if st.button("Automated Data Exploration"):
            for msg in agent.automated_data_exploration():
                display_message(msg)

        if agent.data_analyst.document:
            if st.button("Export Report to PDF"):
                pdf_out = agent.export_to_pdf()
                db_id = agent.data_analyst.db_id
                date_str = datetime.date.today().strftime("%Y%m%d")
                st.download_button("Download PDF ", pdf_out, f"report_{db_id}_{date_str}.pdf")
    
    st.selectbox(
        label="Select a Database",
        options=agent.get_databases(),
        index=None,
        key="selected_database")

    if st.button("Reset"):
        agent.data_analyst.reset()
        agent.history = []
        doc_container.empty()
        st.rerun()

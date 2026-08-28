import streamlit as st
from langgraph_backend import chatbot
from langchain_core.messages import HumanMessage

# session state -> dict

CONFIG = {'configurable': {'thread_id': 'thread_1'}}

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])

user_message = st.chat_input('Type here')

if(user_message):

    # first add the message to the history
    st.session_state['message_history'].append({'role': 'user', 'content': user_message},)
    with st.chat_message('user'):
        st.text(user_message)

    response = chatbot.invoke({'message': [HumanMessage(content=user_message)]}, config=CONFIG)
    ai_message = response['message'][-1].content
    # .first add the message to the history
    st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})
    with st.chat_message('assistant'):
        st.text(ai_message)
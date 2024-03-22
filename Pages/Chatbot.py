import vertexai
import streamlit as st
from utils import DataStore
from loguru import logger
from vertexai.language_models import ChatModel

PARAMETERS = {
    "candidate_count": 1,
    "max_output_tokens": 1024,
    "temperature": 0.9,
    "top_p": 1
}    
PROMPT_TEMPLATE = "Refer to the following context to answer this query: {query}\n\nContext: {context}"

def chat_with_bot():

    st.subheader("DocuBot is all set, Ask your questions!")    

    if "project_id" not in st.session_state:        
        vertexai.init(project = "inductive-world-416413")         
        st.session_state["project_id"] = "inductive-world-416413"

    if "chat_model" not in st.session_state:
        st.session_state["datastore"] = DataStore()
        st.session_state["chat_model"] = ChatModel.from_pretrained("chat-bison@002")
        st.session_state["chat"] = st.session_state["chat_model"].start_chat(context = "")
    
    if "messages" not in st.session_state:                        
        st.session_state["messages"] = []

    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])     

    # Accept user input
    if prompt := st.chat_input("Query"):
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)

        chat_model_1 = ChatModel.from_pretrained("chat-bison@002")
        chat_1 = chat_model_1.start_chat(context = "")
        prompt_1 = "Based on this conversation history {chat_history} and the current query {query}, find out what the user is trying to ask"
        input_1 = prompt_1.format(chat_history = st.session_state["messages"], query = prompt)
        response_1 = chat_1.send_message(input_1).text
                
        # Process user query    
        similar_chunks = st.session_state["datastore"].retrieve(response_1)
        context = '\n'.join(similar_chunks)        

        # Generate response and store
        input_2 = PROMPT_TEMPLATE.format(query = prompt, context = context)
        response = st.session_state["chat"].send_message(input_2).text

        # Update chat history
        st.session_state["messages"].append({"role": "user", "content": prompt})
        st.session_state["messages"].append({"role": "assistant", "content": response})                
        st.rerun()

if __name__ == "__main__":
    chat_with_bot()

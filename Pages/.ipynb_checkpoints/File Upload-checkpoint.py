from urllib import request
import streamlit as st
from utils import *
from datetime import datetime
import PyPDF2
import pdb


st.set_page_config(layout="wide")

st.title("DocuBot")
st.write("An Information Retrieval Chatbot with Document Ingestion")

file_names = []
uploaded_files = st.file_uploader("Upload one or more documents", accept_multiple_files=True)

if uploaded_files:
    st.write(uploaded_files)    
    all_uploaded_file_names = st.session_state.get("uploaded_files", set())    
    for file in uploaded_files:
        file_names.append(file.name)    
    newly_uploaded_files = set(file_names) - set(all_uploaded_file_names)
    data_store = DataStore()
    for file in uploaded_files:
        if file.name not in newly_uploaded_files:
            continue
        # Read the uploaded file as bytes
        bytes_data = file.getvalue()        
        # Convert the bytes to a PDF object
        pdf_reader = PyPDF2.PdfReader(file)        
        # Get the number of pages in the PDF
        num_pages = len(pdf_reader.pages)
        # Iterate over the pages and display the text content
        for page_num in range(num_pages):
            page_object = pdf_reader.pages[page_num]
            text = page_object.extract_text()
            data_store.ingest(text)
        
    st.session_state["uploaded_files"] = st.session_state.get("uploaded_files", set())
    st.session_state["uploaded_files"].update(newly_uploaded_files)
    
chat_model = ChatModel.from_pretrained("chat-bison@002")
parameters = {
    "candidate_count": 1,
    "max_output_tokens": 1024,
    "temperature": 0.9,
    "top_p": 1
}    
prompt_template = "Refer to the following context to answer this query: {query}\n\nContext: {context}"

chat = chat_model.start_chat(context="")

st.subheader("DocuBot is all set, Ask your questions!")    

chat_history = []    
#chat_history = st.text_area("Chat History:", value="", height=200, max_chars=None)

query = st.text_input("User Query:")

if st.button("Send"):
    if query.lower() == "quit":
        st.text("Chat ended.")
    else:
        # First API call to send the chat history and get the updated context
        model_input_1 = prompt_template.format(query="", context=chat_history)
        response_1 = chat.send_message(model_input_1)
        updated_context = response_1.text.strip()

        # Second API call to send the query with the updated context
        similar_chunks = data_store.retrieve(query)
        updated_context += '\n'.join(similar_chunks)
        model_input_2 = prompt_template.format(query=query, context=updated_context)
        response_2 = chat.send_message(model_input_2)
        st.write(response_2.text.strip())
        chat_history.append(query)

        # Display chat history
        #st.text_area("Chat History:", value=chat_history, height=200, max_chars=None, key="chat_history")
        
        
        

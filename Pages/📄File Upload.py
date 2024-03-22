from urllib import request
import streamlit as st
from utils import *
import PyPDF2
import pdb

st.set_page_config(layout="wide")

def upload_documents():

    st.write("<h1 style='text-align: center;'>Document Upload</h1>", unsafe_allow_html=True)
    st.write("")
    st.write("")
    st.write("Have a large document that you want to retreive information from? Upload them here and head to the chatbot to get your queries answered!")    

    file_names = []
    data_store = DataStore()

    st.write("Please Note: We are currently accepting pdf files only")
    uploaded_files = st.file_uploader("Upload here", accept_multiple_files=True)        
    all_uploaded_file_names = st.session_state.get("uploaded_files", set())    

    for file in uploaded_files:
        file_names.append(file.name)

    newly_uploaded_file_names = set(file_names) - set(all_uploaded_file_names)
    
    if uploaded_files:
        message_placeholder = st.empty()  # Create an empty placeholder for the message
        message_placeholder.write("Your files are being uploaded, please wait...")  # Display message while files are uploading

    for file in uploaded_files:
        if file.name not in newly_uploaded_file_names:
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
    st.session_state["uploaded_files"].update(newly_uploaded_file_names)
    
    if newly_uploaded_file_names:
        message_placeholder.empty()
        st.write("")
        st.write("<h3 style='text-align: center;'>Your files have been uploaded, DocuBot is ready to answer your questions now!</h3>", unsafe_allow_html = True)
                    
if __name__ == "__main__":
    upload_documents()    

import psycopg2
import pgvector
import vertexai
import tiktoken
import numpy as np
from loguru import logger
from psycopg2 import pool
from pypdf import PdfReader
from itertools import chain
from pydantic import BaseModel
from psycopg2.extras import execute_values
from llama_index.core.schema import Document
from pgvector.psycopg2 import register_vector
from vertexai.language_models import ChatModel
from vertexai.language_models import TextEmbeddingModel
from llama_index.core.text_splitter import SentenceSplitter

def read_pdf(file_path):    
    text = ""    
    with open(file_path, "rb") as file:
        reader = PdfReader(file)
        for page in reader.pages:            
            text += page.extract_text()
    
    return text

def chatbot_setup():
    
    chat_model = ChatModel.from_pretrained("chat-bison@002")
    parameters = {
        "candidate_count": 1,
        "max_output_tokens": 1024,
        "temperature": 0.9,
        "top_p": 1
    }
    
    prompt_template = "Refer to the following context to answer this query: {query}\n\nContext: {context}"
    return chat_model

def split_input_to_chunks(input_text: str) -> list[str]:
    """
    Split a sentence into chunks
    Input:
        text : Text to be split
    Output:
        chunks: Segments of text after splitting
    """

    # Parsing text with a preference for complete sentences
    text_splitter = SentenceSplitter(
        separator = " ",
        chunk_size = 300,
        chunk_overlap = 20,
        paragraph_separator = "\n\n",
        secondary_chunking_regex = "[^,.;。]+[,.;。]?",
        tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo").encode,
    )
    
    txt_doc = Document(text = input_text)    
    # Split the text into chunks
    chunks = text_splitter([txt_doc])

    return [chunk.text for chunk in chunks]

class TextEmbedding(BaseModel):
    text : str
    embedding : list[float]

def text_embedding(text) -> list[float]:    
    """
    Generate embeddings for given text
    Input:
        text : Input text   
    Output:
        vector: Emdedding of the input text
    """
    
    model = TextEmbeddingModel.from_pretrained("textembedding-gecko@001")
    embeddings = model.get_embeddings([text])
    
    for embedding in embeddings:
        vector = embedding.values             
        
    return vector

def get_text_embedding_pairs(text : str) -> list[TextEmbedding]:
    """
    Get all the chunks and corresponding embeddings for a given text
    Input:
        text : Text whose chunk and embedding is needed
    Output:
        chunk_embedding_pairs: chunk and embedding of given text
    """    
    
    chunks : list[str] = split_input_to_chunks(text) 
    chunk_embedding_pairs : list[TextEmbedding] = []
    logger.info(f'Number of chunks generated: {len(chunks)}')
    
    for curr_chunk in chunks:        
        curr_embedding = text_embedding(curr_chunk)
        chunk_embedding_pairs.append(TextEmbedding(text = curr_chunk, embedding = curr_embedding))    
    
    return chunk_embedding_pairs

vertexai.init(project = vertexai.init(project = "inductive-world-416413"))

DB_PARAMS = {
    'dbname' : "vectordb",
    'user' : "user",
    'password' : "pwd",
    'host' : "localhost",
    'port' : "5432"
}

class DataStore:
    
    DATABASE_SCHEMA = {
        "text_chunk" : "varchar",
        "embedding" : "vector(768)"
    }
    
    TABLE_NAME = "my_table"
    
    def __init__(self, db_params : dict = DB_PARAMS):
        self.db_params = db_params        
        self.conn_pool = self._get_connection_pool()        
        self._create_table()
    
    def _get_connection_pool(self):
        return psycopg2.pool.SimpleConnectionPool(1, 10, **self.db_params)

    def _create_table(self) -> None:
        col_defs = [f'{col_name} {col_type}' for col_name, col_type in self.DATABASE_SCHEMA.items()]        
        cols = ", ".join(col_defs)        
        table_creation_query = f"""
            CREATE EXTENSION IF NOT EXISTS vector;            
            CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
            id SERIAL PRIMARY KEY,
            {cols}
            );
            """   
        logger.info(table_creation_query)
        try:
            connection = self.conn_pool.getconn()
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute(table_creation_query)
        except Exception as e:
            logger.error(f"Error in create table query: {e}")
            raise
        finally:
            self.conn_pool.putconn(connection)
    
    def ingest(self, text: str) -> None:
        text_embedding_pairs : list[TextChunk] = get_text_embedding_pairs(text)
        data_list = [(curr.text, curr.embedding) for curr in text_embedding_pairs]
        print(data_list[0][0])
        col_names = ",".join(list(self.DATABASE_SCHEMA.keys()))
        table_update_query = f"""
            INSERT INTO {self.TABLE_NAME} 
            ( {col_names} )
            VALUES %s
            """                    
        try:            
            connection = self.conn_pool.getconn()
            with connection:
                with connection.cursor() as cursor:
                    execute_values(cursor, table_update_query, data_list)
                    logger.info("Updated table with embedding pairs")
        except Exception as e:
            logger.error(f"Error in update table query : {e}")
            raise
        finally:
            self.conn_pool.putconn(connection)

    def retrieve(self, query: str) -> str:
        query_embedding : list[float] = text_embedding(query)
        retrieval_query = f"""
            SELECT text_chunk FROM {self.TABLE_NAME}
            ORDER BY embedding <-> %s LIMIT 1
            """
        retrieved_chunk = ""
        try:            
            connection = self.conn_pool.getconn()
            register_vector(connection)
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute(retrieval_query, (np.array(query_embedding, dtype = np.float64), ))
                    retrieved_chunk = list(chain.from_iterable(cursor.fetchall()))
                    logger.info(f"Retreived {len(retrieved_chunk)} chunk for the given embedding")            
        except Exception as e:
            logger.error(f"Error in retrieval query : {e}")
            raise  
        finally:
            self.conn_pool.putconn(connection)
        return retrieved_chunk
import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.embeddings.spacy_embeddings import SpacyEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.tools.retriever import create_retriever_tool
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
import os

# Load environment variables from the .env file
load_dotenv()

# Retrieve the OpenAI API key from environment variables
api_key = os.getenv("OPENAI_API_KEY")

# Setting an environment variable to resolve any potential issues with duplicate libraries
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Initialize SpaCy embeddings with the specified model
embeddings = SpacyEmbeddings(model_name="en_core_web_sm")

def pdf_read(pdf_doc):
    """
    Reads text from a list of uploaded PDF documents.

    Args:
        pdf_doc (list): A list of PDF files uploaded by the user.

    Returns:
        str: A string containing the extracted text from all the PDF pages.
    """
    text = ""
    for pdf in pdf_doc:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def get_chunks(text):
    """
    Splits the input text into manageable chunks for processing.

    Args:
        text (str): The full text to be split.

    Returns:
        list: A list of text chunks.
    """
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_text(text)
    return chunks

def vector_store(text_chunks):
    """
    Creates a FAISS vector store from the text chunks and saves it locally.

    Args:
        text_chunks (list): A list of text chunks to be converted into vector embeddings.

    Returns:
        None
    """
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss_db")

def get_conversational_chain(tools, ques):
    """
    Executes a conversational chain using the provided tools and question.

    Args:
        tools: The tools to be used by the agent for retrieving information.
        ques (str): The user's question to be answered.

    Returns:
        None
    """
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0, api_key=api_key)
    
    # Create a chat prompt template for the conversation
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a helpful assistant. Answer the question as detailed as possible from the provided context. 
                If the answer is not in the provided context, just say, "answer is not available in the context", 
                and don't provide a wrong answer.""",
            ),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )
    
    # Create the tool calling agent with the provided LLM, tools, and prompt
    tool = [tools]
    agent = create_tool_calling_agent(llm, tool, prompt)

    # Execute the agent and get the response
    agent_executor = AgentExecutor(agent=agent, tools=tool, verbose=True)
    response = agent_executor.invoke({"input": ques})
    
    # Display the response in the Streamlit app
    st.write("Reply: ", response['output'])

def user_input(user_question):
    """
    Handles user input and invokes the conversational chain.

    Args:
        user_question (str): The question asked by the user.

    Returns:
        None
    """
    # Load the existing FAISS vector store
    new_db = FAISS.load_local("faiss_db", embeddings, allow_dangerous_deserialization=True)
    
    # Create a retriever tool for querying the vector store
    retriever = new_db.as_retriever()
    retrieval_chain = create_retriever_tool(retriever, "pdf_extractor", "This tool is to give answers to queries from the PDF.")
    
    # Execute the conversational chain with the user question
    get_conversational_chain(retrieval_chain, user_question)

def main():
    """
    The main function that sets up the Streamlit app and handles user interactions.

    Returns:
        None
    """
    st.set_page_config("Chat PDF")
    st.header("RAG based Chat with PDF")

    # Capture the user's question
    user_question = st.text_input("Ask a Question from the PDF Files")

    # Process the user's question if provided
    if user_question:
        user_input(user_question)

    # Sidebar for uploading PDFs and processing them
    with st.sidebar:
        st.title("Menu:")
        pdf_doc = st.file_uploader("Upload your PDF Files and Click on the Submit & Process Button", accept_multiple_files=True)
        if st.button("Submit & Process"):
            with st.spinner("Processing..."):
                # Read and process the uploaded PDF files
                raw_text = pdf_read(pdf_doc)
                text_chunks = get_chunks(raw_text)
                vector_store(text_chunks)
                st.success("Done")

if __name__ == "__main__":
    main()

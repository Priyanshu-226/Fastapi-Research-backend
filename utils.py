from langchain.text_splitter import CharacterTextSplitter
from langchain.document_loaders import PyPDFLoader, TextLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.llms import OpenAI

def process_document(path: str):
    ext = path.split(".")[-1]
    if ext == "pdf":
        loader = PyPDFLoader(path)
    elif ext == "txt":
        loader = TextLoader(path)
    else:
        raise Exception("Unsupported file type")
    documents = loader.load()
    splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = splitter.split_documents(documents)
    embeddings = OpenAIEmbeddings()
    db = FAISS.from_documents(docs, embeddings)
    db.save_local("embeddings/vector_store")

def get_answer(question: str):
    embeddings = OpenAIEmbeddings()
    db = FAISS.load_local("embeddings/vector_store", embeddings)
    docs = db.similarity_search(question)
    llm = OpenAI(temperature=0)
    chain = load_qa_chain(llm, chain_type="stuff")
    response = chain.run(input_documents=docs, question=question)
    return response
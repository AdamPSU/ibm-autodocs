import os
import tempfile
from dotenv import load_dotenv
from typing import List, Dict
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pathlib import Path
from git import Repo  # GitPython

# Load environment variables from .env file
load_dotenv()

test_code = """
def add(a, b):
    return a + b
"""

# Initialize the OpenAI client
llm = AzureChatOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT")
)

SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".cpp", ".c", ".cs", ".rb", ".go", ".rs",
    ".php", ".html", ".css", ".scss", ".swift", ".kt", ".m", ".sh", ".bat",
    ".ps1", ".lua", ".pl", ".r", ".jl", ".sql", ".xml", ".json", ".yml", ".yaml"
}

# Define PromptTemplates using LangChain's PromptTemplate class
SYSTEM_COMMENT_TEMPLATE = PromptTemplate(
    input_variables=["code"],
    template="Add helpful comments to the following code without changing it:\n\n{code}"
)

FILE_SUMMARY_TEMPLATE = PromptTemplate(
    input_variables=["code"],
    template="Summarize the following file:\n\n{code}"
)

README_AND_DIAGRAM_TEMPLATE = PromptTemplate(
    input_variables=["file_summaries"],
    template="Create a README based on the following file summaries:\n\n{file_summaries}"
)

# Create the LCEL chain using pipe syntax
chain = SYSTEM_COMMENT_TEMPLATE | llm 

# Run it
response = chain.invoke({"code": test_code})
print(response)

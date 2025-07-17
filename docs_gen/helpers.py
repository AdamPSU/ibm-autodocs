import os
import shutil
import tempfile
import atexit
import logging
from dotenv import load_dotenv
from typing import List, Dict, Tuple
from pathlib import Path
from git import Repo
 
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import AzureChatOpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('docs_generator')

# Load environment variables
load_dotenv()

llm = AzureChatOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT")
)

SUPPORTED_EXTENSIONS = {    
    ".py", ".js", ".ts", ".java", ".cpp", ".c", ".cs", ".rb", ".go", ".rs",
    ".php", ".html", ".css", ".scss", ".swift", ".kt", ".m", ".sh", ".bat",
    ".ps1", ".lua", ".pl", ".r", ".jl", ".sql", ".xml", ".json",
}

# Load prompt templates from files
def load_prompt_from_file(file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to load prompt from {file_path}: {e}")
        # Fallback to default prompts if file can't be loaded
        if "system_comment" in file_path:
            return "Add helpful comments to the following code without changing it:\n\n{code}"
        elif "file_summary" in file_path:
            return "Write a concise summary of the following:\n\n{code}"
        else:
            return """The following is a set of summaries:
{file_summaries}
Take these and distill it into a final, consolidated README of the main themes. Include working examples
when possible. Include clickable links to the most relevant files in the README."""

# Prompt templates
comment_template = PromptTemplate(
    input_variables=["code"],
    template=load_prompt_from_file("prompts/system_comment.txt") + "\n\n{code}"
)

summary_template = PromptTemplate(
    input_variables=["code"],
    template=load_prompt_from_file("prompts/file_summary.txt") + "\n\n{code}"
)

readme_template = PromptTemplate(
    input_variables=["file_summaries"],
    template=load_prompt_from_file("prompts/readme_and_diagram.txt") + "\n{file_summaries}"
)

comment_chain = comment_template | llm | StrOutputParser()
summary_chain = summary_template | llm | StrOutputParser()
readme_chain = readme_template | llm | StrOutputParser()

def get_all_code_files(directory: str, extensions: set) -> List[Path]:
    return [p for p in Path(directory).rglob("*") if p.suffix in extensions]

def get_all_folder_code_files(base_dir: str) -> Dict[Path, List[Path]]:
    file_map = {}
    for path in Path(base_dir).rglob("*"):
        if path.is_file() and path.suffix in SUPPORTED_EXTENSIONS:
            parent = path.parent
            file_map.setdefault(parent, []).append(path)
    return file_map

def overwrite_commented_code(file_path: Path, commented_code: str):
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(commented_code)

def comment_all_code_files(base_dir: str):
    code_files = get_all_code_files(base_dir, SUPPORTED_EXTENSIONS)
    logger.info(f"Found {len(code_files)} code files to comment.")
    for file_path in code_files:
        logger.info(f"Commenting {file_path}...")
        try:
            code = file_path.read_text(encoding='utf-8')
            commented_code = comment_chain.invoke({"code": code})
            overwrite_commented_code(file_path, commented_code)
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}", exc_info=True)

def summarize_code_file(file_path: Path) -> str:
    code = file_path.read_text(encoding="utf-8")
    return summary_chain.invoke({"code": code})

def generate_readme_from_summaries(file_summaries: Dict[str, str]) -> str:
    summary_text = "\n".join([f"{filename}: {summary}" for filename, summary in file_summaries.items()])
    return readme_chain.invoke({"file_summaries": summary_text})

def write_readme(folder: Path, readme_content: str):
    readme_path = folder / "README.md"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

def generate_readmes(base_dir: str):
    folder_files = get_all_folder_code_files(base_dir)
    for folder, files in folder_files.items():
        readme_path = folder / "README.md"
        if len(files) < 2:
            logger.info(f"Skipping {folder} (only {len(files)} code file(s)).")
            continue
        if readme_path.exists():
            logger.info(f"Skipping {folder} (README already exists).")
            continue

        logger.info(f"Generating README for {folder}...")
        file_summaries = {}
        for file_path in files:
            try:
                summary = summarize_code_file(file_path)
                file_summaries[file_path.name] = summary
                logger.debug(f"Generated summary for {file_path.name}")
            except Exception as e:
                logger.error(f"Error summarizing {file_path.name}: {e}", exc_info=True)

        try:
            readme_content = generate_readme_from_summaries(file_summaries)
            # Ensure the Mermaid diagram is properly formatted for GitHub
            if "```mermaid" not in readme_content:
                logger.warning(f"No Mermaid diagram detected in generated README for {folder}")
            write_readme(folder, readme_content)
            logger.info(f"README created at {readme_path}")
        except Exception as e:
            logger.error(f"Failed to generate README for {folder}: {e}", exc_info=True)

def process_repo(repo_url: str):
    temp_dir = tempfile.mkdtemp()
    atexit.register(lambda: shutil.rmtree(temp_dir, ignore_errors=True))  # cleanup

    logger.info(f"Cloning repository {repo_url} into temporary directory: {temp_dir}")
    repo = Repo.clone_from(repo_url, temp_dir)
    branch_name = "autocomment-branch"

    new_branch = repo.create_head(branch_name)
    new_branch.checkout()
    logger.info(f"Checked out new branch: {branch_name}")

    comment_all_code_files(temp_dir)
    generate_readmes(temp_dir)

    repo.git.add(A=True)
    repo.index.commit("Add auto-generated comments and README files with architecture diagrams")
    logger.info(f"Committed changes to branch '{branch_name}'.")

    origin = repo.remote(name='origin')
    try:
        origin.push(refspec=f"{branch_name}:{branch_name}")
        logger.info(f"Branch '{branch_name}' pushed to remote.")
    except Exception as e:
        logger.error(f"Failed to push branch: {e}", exc_info=True)

    repo.close()
    logger.info(f"Repository processing completed successfully")

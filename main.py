import os
import tempfile
from dotenv import load_dotenv
from typing import List, Dict
from openai import AzureOpenAI
from pathlib import Path
from git import Repo  # GitPython

# Load environment variables from .env file
load_dotenv()

# Initialize Azure OpenAI client with values from environment variables
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".cpp", ".c", ".cs", ".rb", ".go", ".rs",
    ".php", ".html", ".css", ".scss", ".swift", ".kt", ".m", ".sh", ".bat",
    ".ps1", ".lua", ".pl", ".r", ".jl", ".sql", ".xml", ".json", ".yml", ".yaml"
}

with open("prompts/system_comment.txt", "r", encoding="utf-8") as f:
    SYSTEM_COMMENT_PROMPT = f.read()

with open("prompts/file_summary.txt", "r", encoding="utf-8") as f:
    FILE_SUMMARY_PROMPT = f.read()

with open("prompts/readme_and_diagram.txt", "r", encoding="utf-8") as f:
    README_AND_DIAGRAM_PROMPT = f.read()


def get_all_code_files(directory: str, extensions: set) -> List[Path]:
    return [p for p in Path(directory).rglob("*") if p.suffix in extensions]


def comment_code_with_openai(code: str) -> str:
    response = client.chat.completions.create(
        model="o4-mini",
        messages=[
            {"role": "system", "content": SYSTEM_COMMENT_PROMPT},
            {"role": "user", "content": f"Add helpful comments to the following code without changing it:\n\n{code}"}
        ],
    )
    return response.choices[0].message.content


def overwrite_commented_code(file_path: Path, commented_code: str):
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(commented_code)


def comment_all_code_files(base_dir: str):
    code_files = get_all_code_files(base_dir, SUPPORTED_EXTENSIONS)
    print(f"Found {len(code_files)} code files to comment.")
    for file_path in code_files:
        print(f"Commenting {file_path}...")
        try:
            code = file_path.read_text(encoding='utf-8')
            commented_code = comment_code_with_openai(code)
            overwrite_commented_code(file_path, commented_code)
        except Exception as e:
            print(f"Error processing {file_path.name}: {e}")


def get_all_folder_code_files(base_dir: str) -> Dict[Path, List[Path]]:
    file_map = {}
    for path in Path(base_dir).rglob("*"):
        if path.is_file() and path.suffix in SUPPORTED_EXTENSIONS:
            parent = path.parent
            file_map.setdefault(parent, []).append(path)
    return file_map


def summarize_code_file(file_path: Path) -> str:
    code = file_path.read_text(encoding="utf-8")
    response = client.chat.completions.create(
        model="o4-mini",
        messages=[
            {"role": "system", "content": FILE_SUMMARY_PROMPT},
            {"role": "user", "content": f"Summarize the following file:\n\n{code}"}
        ],
    )
    return response.choices[0].message.content.strip()


def generate_readme_from_summaries(file_summaries: Dict[str, str]) -> str:
    summary_text = "\n".join([f"{filename}: {summary}" for filename, summary in file_summaries.items()])
    response = client.chat.completions.create(
        model="o4-mini",
        messages=[
            {"role": "system", "content": README_AND_DIAGRAM_PROMPT},
            {"role": "user", "content": f"{summary_text}"}
        ],
    )
    return response.choices[0].message.content.strip()


def write_readme(folder: Path, readme_content: str):
    readme_path = folder / "README.md"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)


def generate_readmes(base_dir: str):
    folder_files = get_all_folder_code_files(base_dir)
    for folder, files in folder_files.items():
        readme_path = folder / "README.md"
        if len(files) < 2:
            print(f"Skipping {folder} (only {len(files)} code file(s)).")
            continue
        if readme_path.exists():
            print(f"Skipping {folder} (README already exists).")
            continue

        print(f"Generating README for {folder}...")
        file_summaries = {}
        for file_path in files:
            try:
                summary = summarize_code_file(file_path)
                file_summaries[file_path.name] = summary
            except Exception as e:
                print(f"Error summarizing {file_path.name}: {e}")

        try:
            readme_content = generate_readme_from_summaries(file_summaries)
            write_readme(folder, readme_content)
            print(f"README created at {readme_path}")
        except Exception as e:
            print(f"Failed to generate README for {folder}: {e}")


def process_repo(repo_url: str):
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Cloning into temporary directory: {temp_dir}")
        repo = Repo.clone_from(repo_url, temp_dir)
        branch_name = "autocomment-branch"

        # Create and checkout new branch
        new_branch = repo.create_head(branch_name)
        new_branch.checkout()
        print(f"Checked out new branch: {branch_name}")

        # Run modifications
        comment_all_code_files(temp_dir)
        generate_readmes(temp_dir)

        # Stage and commit
        repo.git.add(A=True)
        repo.index.commit("Add auto-generated comments and README files")
        print(f"Committed changes to branch '{branch_name}'.")

        # Push to remote
        origin = repo.remote(name='origin')
        try:
            origin.push(refspec=f"{branch_name}:{branch_name}")
            print(f"✅ Branch '{branch_name}' pushed to remote.")
        except Exception as e:
            print(f"❌ Failed to push branch: {e}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python script.py <repo_url>")
    else:
        repo_url = sys.argv[1]
        process_repo(repo_url)
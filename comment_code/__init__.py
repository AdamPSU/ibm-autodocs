import os
from azure.functions import HttpRequest, HttpResponse
import azure.functions as func
from pathlib import Path
from openai import AzureOpenAI

client = AzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_version="2024-12-01-preview"
)

SUPPORTED_EXTENSIONS = {".py", ".js", ".ts", ".java", ".cpp", ".c", ".cs"}
SYSTEM_COMMENT_PROMPT = Path("prompts/system_comment.txt").read_text()

def comment_code_with_openai(code: str) -> str:
    response = client.chat.completions.create(
        model="o4-mini",
        messages=[
            {"role": "system", "content": SYSTEM_COMMENT_PROMPT},
            {"role": "user", "content": f"Add helpful comments:\n\n{code}"}
        ],
    )
    return response.choices[0].message.content

def get_all_code_files(directory: str, extensions: set):
    return [p for p in Path(directory).rglob("*") if p.suffix in extensions]

def main(req: HttpRequest) -> HttpResponse:
    try:
        for file_path in get_all_code_files(".", SUPPORTED_EXTENSIONS):
            code = file_path.read_text(encoding="utf-8")
            commented_code = comment_code_with_openai(code)
            file_path.write_text(commented_code, encoding="utf-8")
        return HttpResponse("Commenting completed.", status_code=200)
    except Exception as e:
        return HttpResponse(str(e), status_code=500)

import azure.functions as func
import logging
import json
from .helpers import process_repo

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('docs_gen HTTP trigger function processed a request.')

    try:
        req_body = req.get_json()
        repo_url = req_body.get("repo_url")
        if not repo_url:
            return func.HttpResponse("Missing 'repo_url' in request body.", status_code=400)

        process_repo(repo_url)
        return func.HttpResponse(f"Processed repository: {repo_url}", status_code=200)

    except Exception as e:
        logging.error(f"Failed to process repository: {e}")
        return func.HttpResponse(f"Error: {e}", status_code=500)

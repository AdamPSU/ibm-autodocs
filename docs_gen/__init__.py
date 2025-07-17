import azure.functions as func
import logging
import json
import time
from .helpers import process_repo, logger

def main(req: func.HttpRequest) -> func.HttpResponse:
    start_time = time.time()
    request_id = req.headers.get('x-request-id', 'unknown')
    logger.info(f'docs_gen HTTP trigger function processing request {request_id}')

    try:
        req_body = req.get_json()
        repo_url = req_body.get("repo_url")
        
        if not repo_url:
            logger.warning("Request received without 'repo_url' in body")
            return func.HttpResponse("Missing 'repo_url' in request body.", status_code=400)
        
        logger.info(f"Starting processing for repository: {repo_url}")
        process_repo(repo_url)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Successfully processed repository: {repo_url} in {elapsed_time:.2f} seconds")
        
        return func.HttpResponse(
            json.dumps({
                "status": "success",
                "message": f"Processed repository: {repo_url}",
                "processing_time_seconds": round(elapsed_time, 2)
            }),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Failed to process repository: {e}", exc_info=True)
        
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": str(e),
                "processing_time_seconds": round(elapsed_time, 2)
            }),
            mimetype="application/json",
            status_code=500
        )

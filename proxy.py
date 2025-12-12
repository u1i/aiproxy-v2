from flask import Flask, request, Response, stream_with_context
import requests
import sys
import os
import json
import uuid
import datetime
import time

app = Flask(__name__)

# Configuration
TARGET_BASE_URL = 'https://openrouter.ai/api/v1'
LOG_DIR_BASE = 'logs'

def log_transaction(req_data, res_data, duration_ms):
    """
    Writes the transaction details to a sharded JSON file.
    Structure: logs/YYYY/MM/DD/timestamp_uuid.json
    """
    try:
        now = datetime.datetime.now()
        year = now.strftime('%Y')
        month = now.strftime('%m')
        day = now.strftime('%d')
        
        # Create directory path
        log_dir = os.path.join(LOG_DIR_BASE, year, month, day)
        os.makedirs(log_dir, exist_ok=True)
        
        # Filename
        ts_str = now.strftime('%H-%M-%S-%f')
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{ts_str}_{unique_id}.json"
        filepath = os.path.join(log_dir, filename)
        
        log_entry = {
            "timestamp": now.isoformat(),
            "request": req_data,
            "response": res_data,
            "duration_ms": duration_ms
        }
        
        with open(filepath, 'w') as f:
            json.dump(log_entry, f, indent=2)
            
    except Exception as e:
        print(f"FAILED TO LOG: {e}", file=sys.stderr)

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def proxy(path):
    start_time = time.time()
    
    # --- Request Processing ---
    # Construct the target URL (Path Normalization)
    clean_path = path
    if clean_path.startswith('api/v1/'):
        clean_path = clean_path[7:]
    elif clean_path.startswith('v1/'):
        clean_path = clean_path[3:]
        
    target_url = f"{TARGET_BASE_URL}/{clean_path}"
    
    # Header Manipulation
    headers = {key: value for (key, value) in request.headers if key != 'Host'}
    
    # Strip unwanted headers
    removed_headers = {}
    if 'Http-Referer' in headers:
        removed_headers['Http-Referer'] = headers['Http-Referer']
        del headers['Http-Referer']
    if 'Referer' in headers:
        removed_headers['Referer'] = headers['Referer']
        del headers['Referer']

    # --- Capture Request Data for Log ---
    req_body_snippet = None
    try:
        data = request.get_data()
        # Always try to decode the full body
        req_body_snippet = data.decode('utf-8', errors='ignore')
    except:
        req_body_snippet = "[Binary data]"

    req_data = {
        "method": request.method,
        "url": target_url,
        "client_ip": request.remote_addr,
        "headers_sent": headers,
        "headers_removed": removed_headers,
        "body": req_body_snippet
    }

    # --- Forwarding ---
    try:
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            stream=True
        )

        # Response Headers
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers_back = [
            (name, value) for (name, value) in resp.raw.headers.items()
            if name.lower() not in excluded_headers
        ]
        
        # --- Response Logging Wrapper ---
        response_content = []
        
        def generate():
            for chunk in resp.iter_content(chunk_size=1024):
                if chunk:
                    response_content.append(chunk)
                    yield chunk
            
            # End of stream logging
            duration = (time.time() - start_time) * 1000
            
            # Reconstruct body for logs (FULL BODY)
            full_body_bytes = b''.join(response_content)
            res_body_str = ""
            try:
                res_body_str = full_body_bytes.decode('utf-8', errors='ignore')
            except:
                res_body_str = "[Binary data]"

            res_data = {
                "status_code": resp.status_code,
                "headers": dict(headers_back),
                "body": res_body_str
            }
            log_transaction(req_data, res_data, duration)

        return Response(
            generate(),
            status=resp.status_code,
            headers=headers_back
        )

    except Exception as e:
        return Response(f"Proxy Error: {str(e)}", status=502)

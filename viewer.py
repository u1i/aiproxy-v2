from flask import Flask, render_template_string, request, abort
import os
import json
import glob
from pathlib import Path

app = Flask(__name__)
LOG_DIR = 'logs'
ITEMS_PER_PAGE = 50

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Local AI Proxy Logs</title>
    <style>
        :root { --bg: #0f172a; --card: #1e293b; --text: #e2e8f0; --accent: #3b82f6; --success: #22c55e; --error: #ef4444; --key: #93c5fd; --string: #a5b4fc; --number: #fca5a5; --bool: #86efac; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }
        h1 { margin-bottom: 20px; font-weight: 300; }
        .container { max-width: 1200px; margin: 0 auto; }
        .pagination { margin: 20px 0; display: flex; gap: 10px; justify-content: center; }
        .btn { background: var(--card); border: 1px solid #334155; color: var(--text); padding: 8px 16px; text-decoration: none; border-radius: 4px; transition: all 0.2s; }
        .btn:hover { border-color: var(--accent); color: var(--accent); }
        .btn.disabled { opacity: 0.5; pointer-events: none; }
        
        .log-entry { background: var(--card); border-radius: 8px; margin-bottom: 12px; overflow: hidden; border: 1px solid #334155; }
        .log-header { padding: 12px 16px; display: grid; grid-template-columns: 200px 80px 1fr 80px 100px; align-items: center; gap: 15px; cursor: pointer; user-select: none; }
        .log-header:hover { background: #27354f; }
        
        .method { font-weight: bold; padding: 4px 8px; border-radius: 4px; font-size: 0.85em; text-align: center;}
        .GET { background: #0c4a6e; color: #38bdf8; }
        .POST { background: #064e3b; color: #34d399; }
        .timestamp { color: #94a3b8; font-size: 0.9em; font-family: monospace; }
        .url { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-family: monospace; color: #cbd5e1; }
        .status { font-weight: bold; text-align: center; }
        .status-200 { color: var(--success); }
        .status-error { color: var(--error); }
        .duration { text-align: right; color: #64748b; font-size: 0.9em; }

        /* Main Details Toggle */
        details > summary { list-style: none; outline: none; }
        details > summary::-webkit-details-marker { display: none; }
        
        .log-body { padding: 0; border-top: 1px solid #334155; background: #0b1120; }
        .json-wrapper { padding: 20px; overflow-x: auto; font-family: "Menlo", "Monaco", "Courier New", monospace; font-size: 13px; line-height: 1.5; }

        /* JSON Tree Styles */
        .json-tree { word-wrap: break-word; white-space: pre-wrap; }
        .json-key { color: var(--key); }
        .json-string { color: var(--string); word-break: break-all; }
        .json-number { color: var(--number); }
        .json-bool { color: var(--bool); font-weight: bold; }
        .json-null { color: #94a3b8; font-style: italic; }
        
        /* Interactive tree toggles */
        /* Interactive tree toggles */
        .collapsible > summary { cursor: pointer; user-select: none; position: relative; list-style: none; }
        .collapsible > summary::-webkit-details-marker { display: none; }
        .collapsible > summary::before { content: '▶'; display: inline-block; font-size: 0.8em; margin-right: 5px; color: #64748b; transition: transform 0.1s; }
        .collapsible[open] > summary::before { transform: rotate(90deg); }
        
        .collapsible-content { padding-left: 20px; border-left: 1px solid #334155; margin-left: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Local AI Proxy Logs <span style="font-size: 0.5em; opacity: 0.6">v1.1</span></h1>
        
        <div class="pagination">
            {% if page > 1 %}
            <a href="/?page={{ page - 1 }}" class="btn">&larr; Previous</a>
            {% else %}
            <span class="btn disabled">&larr; Previous</span>
            {% endif %}
            <span style="align-self: center; padding: 0 10px;">Page {{ page }} of {{ total_pages }}</span>
            {% if page < total_pages %}
            <a href="/?page={{ page + 1 }}" class="btn">Next &rarr;</a>
            {% else %}
            <span class="btn disabled">Next &rarr;</span>
            {% endif %}
        </div>

        {% for log in logs %}
        <div class="log-entry">
            <details>
                <summary class="log-header">
                    <span class="timestamp">{{ log.timestamp }}</span>
                    <span class="method {{ log.request.method }}">{{ log.request.method }}</span>
                    <span class="url" title="{{ log.request.url }}">{{ log.request.url }}</span>
                    <span class="status {% if 200 <= log.response.status_code < 300 %}status-200{% else %}status-error{% endif %}">
                        {{ log.response.status_code }}
                    </span>
                    <span class="duration">{{ "%.0f"|format(log.duration_ms) }}ms</span>
                </summary>
                <div class="log-body">
                    <div class="json-wrapper" id="log-{{ loop.index }}"></div>
                    <script>
                        (function() {
                            const data = {{ log | tojson | safe }};
                            const container = document.getElementById('log-{{ loop.index }}');
                            
                            function renderJSON(value, keyName) {
                                if (value === null) return '<span class="json-null">null</span>';
                                if (typeof value === 'boolean') return `<span class="json-bool">${value}</span>`;
                                if (typeof value === 'number') return `<span class="json-number">${value}</span>`;
                                if (typeof value === 'string') {
                                    // Try to parse stringified JSON in body
                                    if (value.startsWith('{') || value.startsWith('[')) {
                                        try {
                                            const parsed = JSON.parse(value);
                                            return renderJSON(parsed, keyName);
                                        } catch(e) {}
                                    }
                                    return `<span class="json-string">"${value.replace(/"/g, '&quot;')}"</span>`;
                                }
                                
                                const collapsedKeys = ['body', 'response'];
                                const shouldOpen = collapsedKeys.includes(keyName) ? '' : 'open';

                                if (Array.isArray(value)) {
                                    if (value.length === 0) return '[]';
                                    let html = `<details class="collapsible" ${shouldOpen}><summary>Array[${value.length}]</summary><div class="collapsible-content">`;
                                    value.forEach(item => {
                                        html += '<div>' + renderJSON(item) + ',</div>';
                                    });
                                    html += '</div></details>';
                                    return html;
                                }
                                
                                if (typeof value === 'object') {
                                    if (Object.keys(value).length === 0) return '{}';
                                    let html = `<details class="collapsible" ${shouldOpen}><summary>Object</summary><div class="collapsible-content">`;
                                    for (const [key, val] of Object.entries(value)) {
                                        html += `<div><span class="json-key">"${key}"</span>: ${renderJSON(val, key)},</div>`;
                                    }
                                    html += '</div></details>';
                                    return html;
                                }
                            }
                            
                            container.innerHTML = '<div class="json-tree">' + renderJSON(data) + '</div>';
                        })();
                    </script>
                </div>
            </details>
        </div>
        {% endfor %}
        
        {% if logs|length == 0 %}
        <div style="text-align: center; padding: 40px; color: #64748b;">No logs found.</div>
        {% endif %}

        <div class="pagination">
             {% if page > 1 %}
            <a href="/?page={{ page - 1 }}" class="btn">&larr; Previous</a>
            {% else %}
            <span class="btn disabled">&larr; Previous</span>
            {% endif %}
             {% if page < total_pages %}
            <a href="/?page={{ page + 1 }}" class="btn">Next &rarr;</a>
            {% else %}
            <span class="btn disabled">Next &rarr;</span>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    # Gather all JSON files
    all_files = []
    # Using recursive glob to find all json files in nested subdirectories
    search_path = os.path.join(LOG_DIR, '**', '*.json')
    for filepath in glob.glob(search_path, recursive=True):
        all_files.append(filepath)
    
    # Sort by modification time (newest first) or filename (assuming timestamp in filename)
    # Filename contains timestamp, so sorting by filename desc is efficient and correct
    # Format: YYYY/MM/DD/HH-MM-SS...
    all_files.sort(reverse=True)
    
    # Pagination Logic
    page = request.args.get('page', 1, type=int)
    total_files = len(all_files)
    total_pages = (total_files + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    
    files_to_show = all_files[start_idx:end_idx]
    
    # Load content (only for the page)
    logs_data = []
    for fpath in files_to_show:
        try:
            with open(fpath, 'r') as f:
                logs_data.append(json.load(f))
        except Exception as e:
            # Fallback for corrupted files
            logs_data.append({
                "timestamp": "ERROR", 
                "request": {"method": "ERR", "url": str(e)}, 
                "response": {"status_code": 0},
                "duration_ms": 0
            })
            
    return render_template_string(
        HTML_TEMPLATE, 
        logs=logs_data, 
        page=page, 
        total_pages=total_pages
    )

if __name__ == '__main__':
    print("LOG VIEWER running on http://localhost:5002")
    app.run(port=5002, debug=True)

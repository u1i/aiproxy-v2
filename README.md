# Local AI Proxy

A lightweight, privacy-focused local proxy server for interacting with LLM providers like OpenRouter. This tool sits between your chat application and the API provider to give you full control and visibility over your data.

## Features

*   **Privacy & Control**: Automatically filters out unwanted tracking headers from your API requests.
*   **Detailed Logging**: Captures full request and response payloads (JSON) for every interaction.
*   **Log Viewer**: Built-in web interface to inspect your chat history and API traffic in a structured, collapsible tree view.
*   **Performance**: Uses Gunicorn for handling concurrent requests efficiently.

## Prerequisites

*   macOS / Linux
*   Python 3.x

## Installation

1.  Open a terminal in this directory.
2.  Install the required dependencies (Flask, Gunicorn, Requests):

```bash
pip3 install flask requests gunicorn
```

*(Note: The provided scripts will handle installation if you haven't done it yet)*

## Usage

### 1. Start the Proxy Server

This runs the proxy on port **5001**.

```bash
./run_proxy.sh
```

**Configuration for Clients:**
*   **Base URL / Endpoint**: `http://localhost:5001/api/v1`
*   **API Key**: Use your normal OpenRouter (or compatible) API key.

### 2. Start the Log Viewer (Optional)

This runs the web viewer on port **5002**.

```bash
./run_viewer.sh
```

*   Open [http://localhost:5002](http://localhost:5002) in your browser.
*   Click on any request to expand detailed information.
*   JSON payloads (Body, Response) are collapsed by default for better readability.

## Directory Structure

*   `proxy.py`: Core proxy logic.
*   `viewer.py`: Flask app for the log viewer.
*   `logs/`: Directory where all traffic is saved (organized by Date).

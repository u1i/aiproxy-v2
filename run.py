#!/usr/bin/env python3
import argparse
import subprocess
import sys

def main():
    parser = argparse.ArgumentParser(description="Start the Proxy Server with Gunicorn")
    parser.add_argument('--workers', type=int, default=4, help='Number of Gunicorn workers')
    parser.add_argument('--port', type=int, default=5001, help='Port to bind to')
    args = parser.parse_args()

    cmd = [
        "gunicorn",
        "-w", str(args.workers),
        "-b", f"0.0.0.0:{args.port}",
        "proxy:app",
        "--access-logfile", "/dev/null",  # Silence access logs (stdout)
        "--error-logfile", "-",           # Errors still go to stderr/stdout
        "--log-level", "error"            # Reduce verbosity to errors only
    ]

    print(f"🚀 Starting Proxy with {args.workers} workers...")
    print(f"👉 OpenAI compatible proxy is: http://0.0.0.0:{args.port}/api/v1")
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nStopping server...")

if __name__ == "__main__":
    main()

"""
Launcher script to seamlessly boot the Project Auricle FastAPI server
and open the React UI in the default web browser.

Usage:
  python test_live_ui.py          # Launches UI silently
  python test_live_ui.py --debug  # Launches UI and streams server logs 
"""
import subprocess
import time
import webbrowser
import sys
import argparse
import socket
import os


def is_port_in_use(port: int) -> bool:
    """Check if the local port is already bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


def launch_ui():
    """Boot the uvicorn server and launch the browser."""
    parser = argparse.ArgumentParser(description="Launch the Auricle React UI.")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Stream Uvicorn server logs to the console for debugging."
    )
    parser.add_argument(
        "--cache-ttl",
        type=int,
        default=60,
        help="Cache expiration TTL in minutes (default: 60)."
    )
    args = parser.parse_args()

    print("========================================")
    print("Project Auricle - Seamless UI Launcher")
    print("========================================")

    if is_port_in_use(8000):
        print("❌ Error: Port 8000 is already in use!")
        print("A dangling Uvicorn process is likely running in the background.")
        print("Run this to kill it: lsof -t -i :8000 | xargs kill -9")
        sys.exit(1)

    print("🚀 Booting up the Uvicorn FastAPI Server...")

    # Configure logging output based on the debug flag
    stdout_target = sys.stdout if args.debug else subprocess.DEVNULL
    stderr_target = sys.stderr if args.debug else subprocess.DEVNULL

    if args.debug:
        print("🐛 Debug mode ON. Streaming backend logs below:\n")

    env = os.environ.copy()
    env["GEMINI_CACHE_TTL_MINUTES"] = str(args.cache_ttl)

    # Start the server as a subprocess
    with subprocess.Popen(
        ["./venv/bin/uvicorn", "server:app", "--port", "8000"],
        stdout=stdout_target,
        stderr=stderr_target,
        env=env
    ) as server_process:

        # Wait for the server to bind to the port
        time.sleep(2)

        # Check if process crashed immediately (e.g. syntax error)
        if server_process.poll() is not None:
            print("❌ Server crashed immediately upon boot. Run with --debug to see why.")
            sys.exit(1)

        url = "http://127.0.0.1:8000"
        print(f"🌐 Launching browser at {url}...\n")
        webbrowser.open(url)

        try:
            print("✅ Server is running. Press Ctrl+C to stop.")
            server_process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Stopping server...")
            server_process.terminate()
            server_process.wait()
            print("Done.")


if __name__ == "__main__":
    launch_ui()

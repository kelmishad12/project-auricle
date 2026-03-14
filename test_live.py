import requests
import json
import time
import subprocess
import os
from dotenv import load_dotenv

from src.services.elevenlabs import ElevenLabsService

load_dotenv()

print("====================================")
print("Project Auricle - Live API Test")
print("====================================")

# TODO: Update this URL to the production web app (e.g., Cloud Run) once
# deployed
url = "http://127.0.0.1:8000/api/v1/briefings/generate"
payload = {
    "user_email": "auricle.test.user@gmail.com",
    "env": "prod"
}
headers = {
    "Content-Type": "application/json"
}

print(f"Sending request to {url}...")
print("This may take a minute as the agent fetches emails, events, and calls Gemini.")

start_time = time.time()
try:
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    data = response.json()

    print(f"\n✅ Request completed in {time.time() - start_time:.2f} seconds\n")
    print("--- RAW BRIEFING TEXT ---")
    print(data.get("briefing"))
    print("-------------------------\n")
    print(f"Safety Passed: {data.get('safety_passed')}\n")

    print("🎙️ Synthesizing audio with ElevenLabs...")
    try:
        elevenlabs = ElevenLabsService()
        audio_bytes = elevenlabs.generate_audio_stream(data.get("briefing"))
        
        audio_file = "briefing.mp3"
        with open(audio_file, "wb") as f:
            f.write(audio_bytes)
        print(f"✅ Audio saved to {audio_file}. Playing now...")
        
        # macOS native audio player
        subprocess.run(["afplay", audio_file])
    except Exception as audio_e:
        print(f"⚠️ Could not synthesize/play audio: {audio_e}")

except requests.exceptions.ConnectionError:
    print("❌ Connection Error: Is the uvicorn server running?")
    print("Run this command in a separate terminal: ./venv/bin/uvicorn server:app --reload --port 8000")
except Exception as e:
    print(f"❌ Error: {e}")
    if 'response' in locals():
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")

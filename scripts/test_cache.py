import os
import json
from dotenv import load_dotenv

load_dotenv()

def test_caching():
    cred_path = os.environ.get("GEMINI_VERTEX_AI_CREDENTIALS")
    if cred_path:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_path
        with open(cred_path, 'r', encoding='utf-8') as f:
            project_id = json.load(f).get('project_id')
        # pylint: disable=import-outside-toplevel
        import vertexai
        vertexai.init(project=project_id, location="us-central1")
        try:
            from vertexai.preview.generative_models import CachedContent # pylint: disable=unused-import
            print("Found CachedContent in preview")
        except ImportError as e:
            print("Not in preview", e)

        try:
            from vertexai.generative_models import CachedContent # pylint: disable=unused-import
            print("Found CachedContent in standard")
        except ImportError as e:
            print("Not in standard", e)
    else:
        print("No creds")
test_caching()

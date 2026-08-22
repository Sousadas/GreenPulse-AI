import os
from dotenv import load_dotenv

from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

load_dotenv()

api_key = os.getenv("WATSONX_API_KEY")
project_id = os.getenv("WATSONX_PROJECT_ID")
url = os.getenv("WATSONX_URL")
model_id = os.getenv("WATSONX_MODEL_ID") or os.getenv("GRANITE_MODEL_ID")

print("=" * 50)
print(" GreenPulse AI - IBM Granite Connection Test")
print("=" * 50)

print("API Key:", "OK" if api_key else "MISSING")
print("Project ID:", project_id)
print("URL:", url)
print("Model:", model_id)

if not api_key:
    raise RuntimeError("WATSONX_API_KEY não encontrada")

if not project_id:
    raise RuntimeError("WATSONX_PROJECT_ID não encontrada")

if not url:
    raise RuntimeError("WATSONX_URL não encontrada")

credentials = Credentials(
    url=url,
    api_key=api_key
)

client = APIClient(credentials)

model = ModelInference(
    model_id=model_id,
    api_client=client,
    project_id=project_id,
    params={
        "max_new_tokens": 200,
        "temperature": 0.2
    }
)

prompt = """
You are GreenPulse AI, an intelligent renewable-energy monitoring system.

Analyze this current simulated hybrid renewable-energy situation:

Solar generation: 2.43 MW
Wind generation: 2.23 MW
Total generation: 4.66 MW
Grid demand: 17.98 MW

Calculate whether the system has a generation surplus or deficit.

Then provide:
1. Current situation
2. Energy deficit or surplus
3. Operational recommendation

Keep the answer concise and professional.
"""

print("\nSending request to IBM watsonx.ai...")
print("Please wait...\n")

try:
    response = model.generate_text(prompt=prompt)

    print("=" * 50)
    print(" IBM GRANITE RESPONSE")
    print("=" * 50)
    print(response)
    print("=" * 50)
    print("SUCCESS: GreenPulse is connected to IBM Granite.")
    print("=" * 50)

except Exception as e:
    print("=" * 50)
    print(" IBM GRANITE ERROR")
    print("=" * 50)
    print(type(e).__name__)
    print(str(e))
    print("=" * 50)
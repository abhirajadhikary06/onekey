import os
import json
import requests

from onekey_sdk import OnekeyClient
from onekey_sdk.llm import LLMClient
from dotenv import load_dotenv
load_dotenv()

def get_platform_key(base_url: str, jwt_token: str) -> str:
    resp = requests.get(
        f"{base_url.rstrip('/')}/keys/platform-key",
        headers={"Authorization": f"Bearer {jwt_token}"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["platform_api_key"]


def main():
    # base_url = os.getenv("ONEKEY_BASE_URL", "https://onekey-ciwz.onrender.com")
    base_url = os.getenv("ONEKEY_BASE_URL", "http://localhost:8000/")
    provider = os.getenv("ONEKEY_PROVIDER", "groq")
    model = os.getenv("ONEKEY_MODEL", "llama-3.3-70b-versatile")
    prompt = os.getenv("ONEKEY_PROMPT", "What is GROQ?")
    operation = os.getenv("ONEKEY_OPERATION")
    payload_json = os.getenv("ONEKEY_PAYLOAD_JSON", "")

    platform_key = os.getenv("ONEKEY_PLATFORM_API_KEY")
    jwt_token = os.getenv("ONEKEY_JWT")

    if not platform_key:
        if not jwt_token:
            raise RuntimeError(
                "Set ONEKEY_PLATFORM_API_KEY or ONEKEY_JWT in environment variables."
            )
        platform_key = get_platform_key(base_url, jwt_token)

    client = OnekeyClient(base_url=base_url, platform_api_key=platform_key)

    payload = {}
    if payload_json:
        payload = json.loads(payload_json)

    if operation and "operation" not in payload:
        payload["operation"] = operation

    try:
        if category == "llm" and not payload:
            llm = LLMClient(client)
            payload_messages = [{"role": "user", "content": prompt}]
            result = llm.chat(
                provider=provider,
                model=model,
                messages=payload_messages,
            )
        else:
            result = client.invoke(category=category, provider=provider, payload=payload)
    except requests.HTTPError as e:
        print("HTTP error:", e)
        if e.response is not None:
            print("Status:", e.response.status_code)
            print("Body:", e.response.text)
        raise

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
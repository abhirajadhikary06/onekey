from onekey import OnekeyClient
from dotenv import load_dotenv
load_dotenv()
# Automatically picks up ONEKEY_PLATFORM_API_KEY from .env
client = OnekeyClient()
# Chat with any model (OpenAI, Anthropic, Groq, etc.)
response = client.llm.chat(
    provider="openrouter",
    model="openrouter/free",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response)
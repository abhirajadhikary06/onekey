import logging
logging.getLogger("langchain").setLevel(logging.INFO)
from backend.rag import _build_chain
try:
    chain = _build_chain()
    res = chain.invoke({"question": "how many users do we have?"})
    print("FINAL RES:", res)
except Exception as e:
    print(f"ERROR: {e}")

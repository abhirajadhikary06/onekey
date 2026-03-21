from backend.rag import ask_rag, _build_chain
chain = _build_chain()
question = "can you tell me anout my usage of the api keys"
print(f"Question: {question}")
print("---")
res = chain.invoke({"question": question})
print(f"Full Result: {res}")

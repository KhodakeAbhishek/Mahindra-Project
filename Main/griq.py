from Main.shared_config import get_groq_client
 
client = get_groq_client()
models = client.models.list()
 
print("Available Groq models for this API key:")
print("=" * 50)
for m in models.data:
    print(f"  - {m.id}")
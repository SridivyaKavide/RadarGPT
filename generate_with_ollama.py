# generate_with_ollama.py
import ollama

def generate_with_ollama(prompt, model="mistral:7b-instruct-q4_0", system=None):
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        response = ollama.chat(model=model, messages=messages)
        return response['message']['content']
    except Exception as e:
        print(f"[Ollama Error]: {e}")
        return f"Error: {e}"

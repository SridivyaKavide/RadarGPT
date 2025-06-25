#!/usr/bin/env python3
"""
Test script to verify Ollama integration is working correctly
"""

from langchain_ollama import OllamaLLM

def test_ollama():
    """Test basic Ollama functionality"""
    try:
        # Initialize Ollama
        llm = OllamaLLM(model="mistral:7b-instruct-q4_0")
        
        # Test a simple prompt
        test_prompt = "Hello! Can you respond with a simple 'Hello from Ollama' message?"
        
        print("Testing Ollama integration...")
        print(f"Prompt: {test_prompt}")
        
        response = llm.invoke(test_prompt)
        
        print(f"Response: {response}")
        print("✅ Ollama integration test successful!")
        
        return True
        
    except Exception as e:
        print(f"❌ Ollama integration test failed: {e}")
        return False

if __name__ == "__main__":
    test_ollama() 
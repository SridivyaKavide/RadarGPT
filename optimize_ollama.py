#!/usr/bin/env python3
"""
Ollama Performance Optimization Script
"""

import time
from langchain_ollama import OllamaLLM

def test_ollama_configurations():
    """Test different Ollama configurations for performance"""
    
    configurations = [
        {
            "name": "Fast (q4_0)",
            "model": "mistral:7b-instruct-q4_0",
            "params": {
                "temperature": 0.7,
                "num_ctx": 2048,  # Smaller context for speed
                "num_thread": 8,  # More threads
                "repeat_penalty": 1.1,
                "top_k": 20,
                "top_p": 0.9
            }
        },
        {
            "name": "Balanced",
            "model": "mistral:7b-instruct-q4_0",
            "params": {
                "temperature": 0.7,
                "num_ctx": 4096,
                "num_thread": 4,
                "repeat_penalty": 1.1,
                "top_k": 40,
                "top_p": 0.9
            }
        },
        {
            "name": "Quality",
            "model": "mistral:7b-instruct-q4_0",
            "params": {
                "temperature": 0.5,
                "num_ctx": 8192,
                "num_thread": 2,
                "repeat_penalty": 1.2,
                "top_k": 50,
                "top_p": 0.8
            }
        }
    ]
    
    test_prompt = """<s>[INST] You are a helpful AI assistant. Please provide a brief analysis of the following topic in 2-3 paragraphs:

Topic: Remote work productivity challenges

Please provide a structured response with clear points. [/INST]"""
    
    print("Testing Ollama configurations for performance...\n")
    
    for config in configurations:
        print(f"Testing: {config['name']}")
        print(f"Model: {config['model']}")
        print(f"Parameters: {config['params']}")
        
        try:
            # Initialize LLM with configuration
            llm = OllamaLLM(model=config['model'], **config['params'])
            
            # Test response time
            start_time = time.time()
            response = llm.invoke(test_prompt)
            end_time = time.time()
            
            response_time = end_time - start_time
            response_length = len(response)
            
            print(f"✅ Response time: {response_time:.2f} seconds")
            print(f"✅ Response length: {response_length} characters")
            print(f"✅ Speed: {response_length/response_time:.0f} chars/second")
            print(f"✅ Response preview: {response[:100]}...")
            print("-" * 50)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            print("-" * 50)

def optimize_for_speed():
    """Create optimized configuration for speed"""
    print("\n=== SPEED OPTIMIZATION ===")
    print("For faster responses, use these settings:")
    print("- Model: mistral:7b-instruct-q4_0")
    print("- num_ctx: 2048 (smaller context)")
    print("- num_thread: 8 (more threads)")
    print("- temperature: 0.7")
    print("- top_k: 20")
    print("- top_p: 0.9")

def optimize_for_quality():
    """Create optimized configuration for quality"""
    print("\n=== QUALITY OPTIMIZATION ===")
    print("For better quality responses, use these settings:")
    print("- Model: mistral:7b-instruct-q4_0")
    print("- num_ctx: 8192 (larger context)")
    print("- num_thread: 2 (fewer threads)")
    print("- temperature: 0.5")
    print("- top_k: 50")
    print("- top_p: 0.8")

if __name__ == "__main__":
    test_ollama_configurations()
    optimize_for_speed()
    optimize_for_quality() 
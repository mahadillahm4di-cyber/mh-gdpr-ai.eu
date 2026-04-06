"""Streaming — receive tokens as they are generated.

Run:
    export AI_INFRA_API_KEY="sk-your-key-here"
    python examples/streaming.py
"""

from ai_infra import Client

client = Client()

# Stream the response token by token
stream = client.chat.completions.create(
    model="auto",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Write a haiku about cloud computing."},
    ],
    stream=True,
)

# Use as a context manager for clean resource handling
with stream:
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            print(content, end="", flush=True)

    # After streaming, access routing metadata
    print(f"\n\nRouting: {stream.metadata}")

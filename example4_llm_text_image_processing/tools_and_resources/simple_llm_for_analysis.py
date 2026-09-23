



# ollama 

from ollama import chat
from ollama import ChatResponse

response: ChatResponse = chat(model='gemma3', messages=[
    {
        'role': 'user',
        'content': 'Why is the sky blue?',
    },
])

# Print the response text
print(response.message.content)



# format structure reg expression


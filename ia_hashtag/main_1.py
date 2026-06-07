from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {
            "role": "user",
            "content": "Why is Python great?"
        }
    ]
)

print(response.choices[0].message.content)
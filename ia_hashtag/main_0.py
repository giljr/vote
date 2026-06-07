from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()

response = client.responses.create(
    model="gpt-4o-2024-08-06",
    input="Why Python is great?"
)

print(response.output_text)

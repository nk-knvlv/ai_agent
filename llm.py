from openai import AsyncOpenAI
from json import dumps
from google.genai import Client


class LLM:
    def __init__(self, model_name="gemini-2.5-flash"):
        self.model = model_name
        self.client = Client(
            api_key='api key'
        )

    async def send(self, message):
        print('думаю...')
        response = self.client.models.generate_content(
            model=self.model, contents=message
        )
        return response.text

    async def test(self):
        print('думаю...')
        response = self.client.models.generate_content(
            model=self.model, contents='pisi i popi'
        )
        return response.text

    async def close(self):
        self.client.close()

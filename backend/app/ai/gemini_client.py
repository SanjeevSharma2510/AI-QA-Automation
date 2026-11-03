
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types


class GeminiClient:

    def __init__(self):

        load_dotenv()

        api_key = os.getenv("GEMINI_API_KEY")

        self.model = os.getenv(
            "GEMINI_MODEL",
            "gemini-3.7-flash"
        )

        if not api_key:

            raise ValueError(
                "GEMINI_API_KEY is missing from the .env file."
            )

        self.client = genai.Client(
            api_key=api_key
        )

    def generate_json(self, prompt):
        """
        Send a prompt to Gemini and receive JSON output.
        """

        print(f"\nCalling Gemini model: {self.model}")

        response = self.client.models.generate_content(

            model=self.model,

            contents=prompt,

            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json"
            )
        )

        if not response.text:

            raise ValueError(
                "Gemini returned an empty response."
            )

        return response.text

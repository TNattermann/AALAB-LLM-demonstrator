import json
import base64
import re
from pathlib import Path
from typing import Dict
from openai import OpenAI

class StoryCompletion:
    """
    A class to generate fairytales / LLMTimes and matching images using OpenAI's API.

    Attributes:
        starting_text (str): The beginning text of the fairytale provided at instantiation.
    """

    def __init__(self, starting_text: str, config):
        """
        Initializes the Fairytale instance with starting text.

        Args:
            starting_text (str): The initial text that starts the fairytale.
        """
        self.starting_text = starting_text
        self.config = config

    def generate_items(self, file_path: str, index: str) -> Dict[str, str]:
        """
        Generates a full fairytale and a matching image using OpenAI's API.

        This method reads the API key from a fixed file path, validates it,
        sends prompts to OpenAI's GPT-4o-mini model to generate a fairytale text
        and title, and then sends a second prompt to create a related image. The
        results are saved as a JSON and PNG file using the provided file path.

        Args:
            file_path (str): The base path where output files will be saved.
            index (str): Index of each fairytale.
            
        Returns:
            dict: A dictionary with keys 'full_text' and 'title'.
        """
        api_key_path = Path("./openai_key.txt")

        if not api_key_path.exists():
            raise FileNotFoundError(f"API key file not found at: {api_key_path}")

        # Read API key
        with open(api_key_path, 'r') as key_file:
            api_key = key_file.read().strip()

        # Set up OpenAI client
        client = OpenAI(api_key=api_key)
        text_prompt = self.config["text_completion"]["prompt"]  + self.starting_text
        print(text_prompt)

        text_response = client.chat.completions.create(
            model = self.config["text_completion"]["name"],
            messages = [
                {"role": "user", "content": text_prompt}
            ],
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "simple_story",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "full_text": {"type": "string"},
                            "title": {"type": "string"}
                        },
                        "required": ["full_text", "title"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            }
        )

        raw_json_string = text_response.choices[0].message.content
        response_data = json.loads(raw_json_string)
        title = response_data["title"]
        full_text = response_data["full_text"]


        # Save the fairytale text and title to TXT files
        output_title_path = f"{file_path}/{index}_headline.txt"
        with open(output_title_path, 'w', encoding='utf-8') as title_file:
            title_file.write(title)

        output_full_text_path = f"{file_path}/{index}_story.txt"
        with open(output_full_text_path, 'w', encoding='utf-8') as full_text_file:
            full_text_file.write(full_text)

        # Generate an image matching the title and full_text
        image_prompt = self.config["image_completion"]["prompt"] + full_text

        image_response = client.images.generate(
            model = self.config["image_completion"]["name"],
            prompt = image_prompt,
            quality = self.config["image_completion"]["quality"],
            size = self.config["image_completion"]["size"]
        )

        image_base64 = image_response.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)

        # Save the image as a PNG file
        image_output_path = f"{file_path}/{index}_image.png"
        with open(image_output_path, "wb") as image_file:
            image_file.write(image_bytes)

        return {"title": title, "full_text": full_text}


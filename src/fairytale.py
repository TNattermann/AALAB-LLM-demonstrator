import json
import base64
import re
from pathlib import Path
from typing import Dict
from openai import OpenAI

class Fairytale:
    """
    A class to generate fairytales and matching images using OpenAI's API.

    Attributes:
        starting_text (str): The beginning text of the fairytale provided at instantiation.
    """

    def __init__(self, starting_text: str):
        """
        Initializes the Fairytale instance with starting text.

        Args:
            starting_text (str): The initial text that starts the fairytale.
        """
        self.starting_text = starting_text

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

        # Generate fairytale text and title
        old_prompt = (
            f"Vervollständige diese Märchengeschichte bis zu einem abgeschlossenen Ende "
            f"und gib den gesamten Text nochmal aus ohne vorherige oder nachgelagerte Erklärungen. "
            f"Die Geschichte sollte maximal 300 Wörter lang sein. "
            f"Danach schreibe einen kurzen, prägnanten Titel zu dieser Geschichte. "
            f"Im Anschluss generiere noch ohne weitere Rückfragen eine Illustration im Hochformat für ein Märchenbuch.\n\n"
        )
        text_prompt = (
            f"Based on the following fairytale starting text, write a completed fairytale of at most 200 words "
            f"in the same language like the starting text, "
            f"Generate the full story including the starting text as a floating text without intermediate titles! "
            f"After that, generate a beautiful, short and creative title for this story, also in the same language.\n"
            f"Format the response as JSON object, with 'full_text' as the first key and 'title' as second key.\n"
            f"\nStarting Text:\n{self.starting_text}"
        )

        text_response = client.chat.completions.create(
            model = "gpt-4o-mini",
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
        output_title_path = f"{file_path}_{index}_headline.txt"
        with open(output_title_path, 'w', encoding='utf-8') as title_file:
            title_file.write(title)

        output_full_text_path = f"{file_path}_{index}_story.txt"
        with open(output_full_text_path, 'w', encoding='utf-8') as full_text_file:
            full_text_file.write(full_text)

        # Generate an image matching the title and full_text
        image_prompt = (
            f"Create a beautiful, colorful and imaginative illustration "
            f"for the following fairytale entitled '{title}':\n\n"
            f"{full_text}"
        )

        image_response = client.images.generate(
            model = "gpt-image-1",
            prompt = image_prompt,
            #size = "1024x1536"
            size = "1024x1024"
        )

        image_base64 = image_response.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)

        # Save the image as a PNG file
        image_output_path = f"{file_path}_{index}_image.png"
        with open(image_output_path, "wb") as image_file:
            image_file.write(image_bytes)

        return {"title": title, "full_text": full_text}


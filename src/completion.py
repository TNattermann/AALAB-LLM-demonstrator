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
        self.api_key_path = Path("./openai_key.txt")
        self.full_text = "This is a story about a cute little minion with a spoon in his hand."
        self.title = ""
        self.prompt_prefix = self.config["image_completion"]["prompt"]
        self.img_prompt = "Nice flower"

        if not self.api_key_path.exists():
            raise FileNotFoundError(f"API key file not found at: {self.api_key_path}")

        # Read API key
        with open(self.api_key_path, 'r') as key_file:
            api_key = key_file.read().strip()

        # Set up OpenAI client
        self.client = OpenAI(api_key=api_key)

    def generate_text(self, file_path: str, index: str) -> Dict[str, str]:
        """
        Generates a full fairytale / llmtimes story using OpenAI's API.

        This method sends prompts to OpenAI's GPT-4o-mini model to generate a fairytale text
        and title. The results are saved as a JSON and PNG file using the provided file path.

        Args:
            file_path (str): The base path where output files will be saved.
            index (str): Index of each fairytale.
            
        Returns:
            dict: A dictionary with keys 'full_text' and 'title'.
        """

        text_prompt = self.config["text_completion"]["prompt"]  + self.starting_text

        text_response = self.client.chat.completions.create(
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
        self.title = title

        output_full_text_path = f"{file_path}/{index}_story.txt"
        with open(output_full_text_path, 'w', encoding='utf-8') as full_text_file:
            full_text_file.write(full_text)
        self.full_text = full_text

        return {"title": title, "full_text": full_text}

    def generate_imgprompt(self, file_path: str, index: str) -> str:
        title_txt = f"{file_path}/{index}_headline.txt"
        story_txt = f"{file_path}/{index}_headline.txt"
        with open(title_txt, "r", encoding="utf-8") as f:
            title = f.read()
        with open(story_txt, "r", encoding="utf-8") as f:
            story = f.read()
        if title == self.title and story == self.full_text:
            input_prompt = self.config["image_prompt_generation"]["prompt"] + self.title + self.full_text
        else:
            input_prompt = self.config["image_prompt_generation"]["prompt"] + title + story

        text_response = self.client.chat.completions.create(
            model = self.config["text_completion"]["name"],
            messages = [
                {"role": "user", "content": input_prompt}
            ],
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "img_prompt",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "img_prompt": {"type": "string"}
                        },
                        "required": ["img_prompt"],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            }
        )

        raw_json_string = text_response.choices[0].message.content
        response_data = json.loads(raw_json_string)
        img_prompt = response_data["img_prompt"]

        output_image_prompt_path = f"{file_path}/{index}_imgprompt.txt"
        with open(output_image_prompt_path, 'w', encoding='utf-8') as image_prompt_file:
            image_prompt_file.write(img_prompt)
        self.img_prompt = img_prompt
        return img_prompt


    def generate_image(self, file_path: str, index: str) -> None:
        """
        Generates a matching image using OpenAI's API.

        This method sends a second prompt to create a related image. The
        results are saved as a JSON and PNG file using the provided file path.

        Args:
            file_path (str): The base path where output files will be saved.
            index (str): Index of each fairytale.

        Returns:
            dict: Nothing needs to be returned
        """

        # Generate an image matching the title and full_text
        #image_prompt = self.config["image_completion"]["prompt"] + self.full_text
        #image_prompt = "A minion from despicable me"
        image_prompt = self.prompt_prefix + self.generate_imgprompt(file_path, index)
        image_response = self.client.images.generate(
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

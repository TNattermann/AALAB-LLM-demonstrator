from fastapi import FastAPI
from pydantic import BaseModel
import ollama
from diffusers import StableDiffusionPipeline
import torch
import subprocess

TEXT_MODEL = "llama3:8b"
IMAGE_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"

def ensure_model(model_name=TEXT_MODEL):
    try:
        subprocess.run(["ollama", "pull", model_name], check=True)
        print(f"✅ Model '{model_name}' is ready.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to pull model '{model_name}':", e)

# Pull the model before starting the app
ensure_model("llama3")


app = FastAPI()

# Load image model once
pipe = StableDiffusionPipeline.from_pretrained(
    IMAGE_MODEL, torch_dtype=torch.float16
).to("cpu")

class Prompt(BaseModel):
    beginning: str

@app.post("/generate")
def generate_story_and_image(prompt: Prompt):
    # Step 1: Generate story
    response = ollama.chat(model=TEXT_MODEL, messages=[
        {'role': 'user', 'content': f'{prompt.text_beginning}'}
    ])
    story = response['message']['content']

    # Step 2: Generate image
    image = pipe(prompt.image_beginning + story).images[0]
    image_path = "generated_image.png"
    image.save(image_path)

    return {"story": story, "image_path": image_path}

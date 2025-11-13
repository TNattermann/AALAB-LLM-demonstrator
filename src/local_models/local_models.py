from fastapi import FastAPI
from pydantic import BaseModel
import ollama
from diffusers import StableDiffusionPipeline
import torch
import subprocess
import time

TEXT_MODEL = "mistral"#-> 4.4GB #"llama3"
IMAGE_MODEL = "stabilityai/sd-turbo"
# "stabilityai/stable-diffusion-v1-4" # about 4 GB
# "stabilityai/stable-diffusion-v1-5" # about 6 GB
# "stabilityai/sd-turbo" # speed
text_prompt = (
            f"Based on the following fairytale starting text, write a completed fairytale of at most 300 words "
            f"in the same language like the starting text, "
            f"Generate the full story including the starting text as a floating text without intermediate titles! "
            f"After that, generate a beautiful, short and creative title for this story, also in the same language.\n"
            f"Format the response as JSON object, with 'full_text' as the first key and 'title' as second key.\n"
            f"\nStarting Text: " )

def ensure_model(model_name=TEXT_MODEL):
    try:
        subprocess.run(["ollama", "pull", model_name], check=True)
        print(f"✅ Model '{model_name}' is ready.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to pull model '{model_name}':", e)

# Pull the model before starting the app
ensure_model(TEXT_MODEL)


app = FastAPI()

# Load image model once
pipe = StableDiffusionPipeline.from_pretrained(
    IMAGE_MODEL, torch_dtype=torch.float16
).to("cuda" if torch.cuda.is_available() else "cpu")

class Prompt(BaseModel):
    text_beginning: str
    image_beginning: str

@app.post("/generate")
def generate_story_and_image(prompt: Prompt):
    start_time = time.time()

    # --- Step 1: Generate story ---
    t1 = time.time()
    response = ollama.chat(model=TEXT_MODEL, messages=[
        {'role': 'user', 'content': f'{text_prompt}+{prompt.text_beginning}'}
    ])
    story = response['message']['content']
    with open("../../data/generated_tale.txt", "w", encoding="utf-8") as f:
        f.write(story)
    print(f"🕒 Step 1 (Story generation): {time.time() - t1:.2f} sec")

    # --- Step 2: Summarize story ---
    t2 = time.time()
    response = ollama.chat(model=TEXT_MODEL, messages=[
        {'role': 'user', 'content': f'Given the following fairytale, provide an instruction for '
                                    f'a diffusion model to generate a matching image : {story}'}
    ])
    story_summary = response['message']['content']
    with open("../../data/generated_summary.txt", "w", encoding="utf-8") as f:
        f.write(story_summary)
    print(f"🕒 Step 2 (Summary): {time.time() - t2:.2f} sec")

    # --- Step 3: Generate image ---
    t3 = time.time()
    image = pipe(story_summary, num_inference_steps=1).images[0]
    image_path = "../../data/generated_image.png"
    image.save(image_path)
    print(f"🕒 Step 3 (Image generation): {time.time() - t3:.2f} sec")

    total_time = time.time() - start_time
    print(f"✅ Total runtime: {total_time:.2f} sec")

    return {
        "story_file": "generated_tale.txt",
        "summary_file": "generated_summary.txt",
        "image_path": image_path,
        "story_runtime_sec": round(time.time() - t1, 2),
        "summary_runtime_sec": round(time.time() - t2, 2),
        "image_runtime_sec": round(time.time() - t3, 2),
        "total_runtime_sec": round(total_time, 2)
    }

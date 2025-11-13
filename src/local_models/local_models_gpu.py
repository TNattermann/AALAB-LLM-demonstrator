from fastapi import FastAPI
from pydantic import BaseModel
import ollama
from diffusers import StableDiffusionPipeline
import torch
import subprocess
import gc
import time
import os

# === Configuration ===
TEXT_MODEL = "mistral"           # Ollama model (ensure it's pulled locally)
IMAGE_MODEL = "stabilityai/sd-turbo"  # Hugging Face Diffusion model

DATA_DIR = "../../data"
os.makedirs(DATA_DIR, exist_ok=True)

# === Fairytale generation prompt template ===
TEXT_PROMPT = (
    "Based on the following fairytale starting text, write a completed fairytale "
    "of at most 250 words in the same language as the starting text. "
    "Generate the full story including the starting text as a floating text without intermediate titles! "
    "After that, generate a beautiful, short and creative title for this story, also in the same language.\n"
    "Format the response as JSON with 'full_text' as the first key and 'title' as second key.\n\n"
    "Starting Text: "
)

# === FastAPI setup ===
app = FastAPI()

# Global references for lazy loading
pipe = None


def ensure_model(model_name: str = TEXT_MODEL):
    """Make sure the Ollama model is available locally."""
    try:
        subprocess.run(["ollama", "pull", model_name], check=True)
        print(f"✅ Model '{model_name}' is ready.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to pull model '{model_name}':", e)


def unload_model(model=None):
    """Free GPU memory (diffusion model)."""
    global pipe
    if model is not None:
        del model
    gc.collect()
    torch.cuda.empty_cache()
    pipe = None
    print("🧹 GPU memory cleared.")


class TextPrompt(BaseModel):
    text_beginning: str


class ImagePrompt(BaseModel):
    story_text: str


# === TEXT GENERATION ENDPOINT ===
@app.post("/generate-text")
def generate_text(prompt: TextPrompt):
    """
    Step 1: Generate a full fairytale using Mistral via Ollama.
    Step 2: Summarize story into an image prompt (both in sequence).
    """
    start_time = time.time()

    # Ensure Ollama model is preloaded before every use
    ensure_model(TEXT_MODEL)

    # --- Step 1: Generate fairytale ---
    t1 = time.time()
    response = ollama.chat(model=TEXT_MODEL, messages=[
        {'role': 'user', 'content': f'{TEXT_PROMPT}{prompt.text_beginning}'}
    ])
    story = response['message']['content']
    story_path = os.path.join(DATA_DIR, "generated_tale.txt")
    with open(story_path, "w", encoding="utf-8") as f:
        f.write(story)
    print(f"🕒 Story generation: {time.time() - t1:.2f} sec")

    # --- Step 2: Summarize for image prompt ---
    t2 = time.time()
    response = ollama.chat(model=TEXT_MODEL, messages=[
        {'role': 'user', 'content': f'Given the following fairytale, provide a short, descriptive prompt '
                                    f'for a diffusion model to generate a matching image: {story}'}
    ])
    summary = response['message']['content']
    summary_path = os.path.join(DATA_DIR, "generated_summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"🕒 Summary generation: {time.time() - t2:.2f} sec")

    total_time = time.time() - start_time
    print(f"✅ Total text pipeline time: {total_time:.2f} sec")

    return {
        "story_file": os.path.basename(story_path),
        "summary_file": os.path.basename(summary_path),
        "story_runtime_sec": round(time.time() - t1, 2),
        "summary_runtime_sec": round(time.time() - t2, 2),
        "total_runtime_sec": round(total_time, 2)
    }


# === IMAGE GENERATION ENDPOINT ===
@app.post("/generate-image")
def generate_image(prompt: ImagePrompt):
    """
    Generate an image from a text description using the SD-Turbo model.
    """
    global pipe
    start_time = time.time()

    # Lazy load image model only when needed
    if pipe is None:
        print("🚀 Loading Stable Diffusion Turbo model...")
        pipe = StableDiffusionPipeline.from_pretrained(
            IMAGE_MODEL,
            torch_dtype=torch.float16
        ).to("cuda" if torch.cuda.is_available() else "cpu")

    # Generate image
    t1 = time.time()
    image = pipe(prompt.story_text, num_inference_steps=1).images[0]
    image_path = os.path.join(DATA_DIR, "generated_image.png")
    image.save(image_path)
    print(f"🕒 Image generation: {time.time() - t1:.2f} sec")

    # Immediately free GPU memory after generation
    unload_model(pipe)

    total_time = time.time() - start_time
    print(f"✅ Total image pipeline time: {total_time:.2f} sec")

    return {
        "image_path": image_path,
        "image_runtime_sec": round(time.time() - t1, 2),
        "total_runtime_sec": round(total_time, 2)
    }

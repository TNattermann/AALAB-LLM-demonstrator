import requests
import json
import time

# Your FastAPI server address
BASE_URL = "http://127.0.0.1:8000"

# Step 1 input text
starting_text = "Once upon a time, a little fox found a glowing stone in the forest."

def run_text_and_image_pipeline():
    # --- Step 1: Call /generate-text ---
    print("📘 Starting text generation...")
    t1 = time.time()
    text_payload = {"text_beginning": starting_text}
    text_response = requests.post(f"{BASE_URL}/generate-text", json=text_payload)

    if text_response.status_code != 200:
        raise RuntimeError(f"Text generation failed: {text_response.text}")

    text_data = text_response.json()
    print("✅ Text generation complete:", json.dumps(text_data, indent=2))
    print(f"⏱ Duration: {text_data['total_runtime_sec']} sec")

    # Read the generated summary file
    summary_file = text_data["summary_file"]
    summary_path = f"../data/{summary_file}"
    with open(summary_path, "r", encoding="utf-8") as f:
        story_summary = f.read().strip()

    # --- Step 2: Call /generate-image ---
    print("\n🖼️ Starting image generation...")
    image_payload = {"story_text": story_summary}
    image_response = requests.post(f"{BASE_URL}/generate-image", json=image_payload)

    if image_response.status_code != 200:
        raise RuntimeError(f"Image generation failed: {image_response.text}")

    image_data = image_response.json()
    print("✅ Image generation complete:", json.dumps(image_data, indent=2))
    print(f"⏱ Duration: {image_data['total_runtime_sec']} sec")

    # --- Done ---
    total_time = time.time() - t1
    print(f"\n🏁 Pipeline completed in {total_time:.2f} sec")
    print(f"📂 Output files: {summary_path}, {image_data['image_path']}")


if __name__ == "__main__":
    run_text_and_image_pipeline()

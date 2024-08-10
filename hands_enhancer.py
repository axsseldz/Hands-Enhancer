import requests
import uuid
import json
import os
import urllib.parse
from PIL import Image
import io
import websocket

server_address = "URL"

client_id = str(uuid.uuid4())

def queue_prompt(prompt, files):
    payload = {"workflow_id": client_id, "prompt": prompt, "files": files}
    data = json.dumps(payload)
    headers = {'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    url = f"https://{server_address}/prompt"
    print(f"Sending POST request to {url} with payload:\n{json.dumps(payload, indent=2)}")
    
    response = requests.post(url, data=data, headers=headers)
    if response.status_code != 200:
        print(f"HTTP Error: {response.status_code} - {response.reason}")
        print(f"Response: {response.text}")
        response.raise_for_status()
    return response.json()

def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    headers = {'User-Agent': 'Mozilla/5.0'}
    url = f"https://{server_address}/view?{url_values}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.content

def get_history(prompt_id):
    headers = {'User-Agent': 'Mozilla/5.0'}
    url = f"https://{server_address}/history/{prompt_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def connect_to_websocket():
    ws = websocket.WebSocket()
    try:
        ws.connect(f"wss://{server_address}/ws?clientId={client_id}")
        return ws
    except websocket.WebSocketException as e:
        print(f"WebSocket connection error: {e}")
        return None

def get_images(ws, prompt, files):
    prompt_id = queue_prompt(prompt, files).get('prompt_id')
    if not prompt_id:
        print("Failed to get prompt_id.")
        return {}

    output_images = {}
    while True:
        try:
            out = ws.recv()
            print(f"Received WebSocket message: {out}")
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        print("Execution complete.")
                        break  
            else:
                continue
        except Exception as e:
            print(f"Error receiving WebSocket message: {e}")
            break

    history = get_history(prompt_id)
    print(f"History data: {json.dumps(history, indent=2)}")
    if prompt_id not in history:
        print(f"Prompt ID {prompt_id} not found in history.")
        return {}

    history_data = history[prompt_id]
    for node_id in history_data['outputs']:
        node_output = history_data['outputs'][node_id]
        if 'images' in node_output:
            images_output = []
            for image in node_output['images']:
                image_data = get_image(image['filename'], image['subfolder'], image['type'])
                images_output.append(image_data)
            output_images[node_id] = images_output

    return output_images


with open("workflow.json", "r", encoding="utf-8") as f:
    workflow_data = f.read()

prompt = json.loads(workflow_data)

image_path = "./images/image.png"

files = {
    "/input/image.png": image_path,
}

prompt["18"]["inputs"]["image"] = "image.png"
prompt["32"]["inputs"]["text"] = "<lora:eli_decaso_v0.2:0.9> olivia newton-john, (her hand signing towards the top right side with an open hand:1.2), (overweight:1.3), (40y.o. woman), (looking at the camera:1.3), <lora:add-detail-xl:2>, full body, <lora:cinematic-lighting:2> cinematic lighting, (high-resolution background:1.2), wearing a high-quality white blouse and black jeans, barely smiling, dark background, (real-life moment:1.3), (Fujifilm X-T4, 1/125s, f/4, ISO 800), (natural pose:1.3), masterpiece, high resolution, skin imperfections, photorealistic, DSLR, depth of field, (perfect eyes:1.3)"

def process_images():
    ws = connect_to_websocket()
    if ws is None:
        print("Failed to connect to WebSocket.")
        return

    try:
        images = get_images(ws, prompt, files)
    finally:
        ws.close()

    os.makedirs("./images/output_imgs", exist_ok=True)
    image_counter = 1
    for node_id in images:
        for image_data in images[node_id]:
            image = Image.open(io.BytesIO(image_data))
            image_path = f"./images/output_imgs/output_image_{image_counter}.png"
            image.save(image_path)
            print(f"Saved image {image_counter} to {image_path}")
            image_counter += 1

process_images()

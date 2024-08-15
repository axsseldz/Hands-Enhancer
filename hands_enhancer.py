import websocket  # NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
import uuid
import json
import urllib.request
import urllib.parse
from PIL import Image
import io
import requests
import os
from pathlib import Path

server_address = "URL"
client_id = str(uuid.uuid4())


headers = {'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}

def queue_prompt(prompt):
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    
    url = f"https://{server_address}/prompt"
    response = requests.post(url, data=data, headers=headers)
    if response.status_code != 200:
        print(f"HTTP Error: {response.status_code} - {response.reason}")
        print(f"Response: {response.text}")
        response.raise_for_status()
    return response.json()

def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    url = f"https://{server_address}/view?{url_values}"
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.content

def get_history(prompt_id):
    url = f"https://{server_address}/history/{prompt_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def get_images(ws, prompt):
    prompt_id = queue_prompt(prompt)['prompt_id']
    output_images = {}
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break  
        else:
            continue 

    history = get_history(prompt_id)[prompt_id]
    for o in history['outputs']:
        for node_id in history['outputs']:
            node_output = history['outputs'][node_id]
            if 'images' in node_output:
                images_output = []
                for image in node_output['images']:
                    image_data = get_image(image['filename'], image['subfolder'], image['type'])
                    images_output.append(image_data)
            output_images[node_id] = images_output

    return output_images

with open("hands_wf.json", "r", encoding="utf-8") as f:
    workflow_jsondata = f.read()

jsonwf = json.loads(workflow_jsondata)

jsonwf["32"]["inputs"]["text"] = "<lora:austin_reaves_v0.1:0.9> tom holland (looking at the camera:1.3), <lora:add-detail-xl:2>, <lora:cinematic-lighting:2> cinematic lighting, (high-resolution background:1.2), full body, showing the thumbs up, wearing a white shirt and blue jeans, sitting in a bench at the beach, natural light, (real-life moment:1.3), (Fujifilm X-T4, 1/125s, f/4, ISO 800), (natural pose:1.3), masterpiece, high resolution, skin imperfections, photorealistic, DSLR, depth of field, (perfect eyes:1.3)"
jsonwf["31"]["inputs"]["seed"] = 6

ws_protocol = "wss"  
ws_url = "{}://{}/ws?clientId={}".format(ws_protocol, server_address, client_id)


print("Connecting to WebSocket URL:", ws_url)

ws = websocket.WebSocket()
ws.connect(ws_url)  

images = get_images(ws, jsonwf)


os.makedirs("./output_imgs", exist_ok=True)
image_counter = 1
for node_id in images:
    for image_data in images[node_id]:
        image = Image.open(io.BytesIO(image_data))
        image_path = f"./output_imgs/image_{image_counter}.png"
        image.save(image_path)
        print(f"Saved image {image_counter} to {image_path}")
        image_counter += 1

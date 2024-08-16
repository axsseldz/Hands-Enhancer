import websocket 
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


def upload_img(image_path):
    """ Upload image to the path workspace/ComfyUI/input """


    url = f"https://{server_address}/upload/image"
    
    if not os.path.isfile(image_path):
        print(f"File not found: {image_path}")
        return None

    with open(image_path, 'rb') as img_file:
        files = {
            'image': (os.path.basename(image_path), img_file, 'image/png')
        }
        data = {
            'type': 'input', 
            'subfolder': ''  
        }
        
        response = requests.post(url, data=data, files=files)
        
        if response.status_code == 200:
            print("Image uploaded successfully.")
            return response.json() 
        else:
            print(f"HTTP Error: {response.status_code} - {response.reason}")
            print(f"Response: {response.text}")
            response.raise_for_status()


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

ws_protocol = "wss"  
ws_url = "{}://{}/ws?clientId={}".format(ws_protocol, server_address, client_id)

print("Connecting to WebSocket URL:", ws_url)

ws = websocket.WebSocket()
ws.connect(ws_url)  


# Upload source image
upload_response = upload_img("./images/man.png")

jsonwf["18"]["inputs"]["image"] = "man.png" # this name needs to be changed according the img just uploaded above
jsonwf["32"]["inputs"]["text"] = "man waving with both hands" # prompt used to generate the source image
jsonwf["31"]["inputs"]["seed"] = 5

# Get output images
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

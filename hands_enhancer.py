import websocket 
import uuid
import json
import urllib.request
import urllib.parse
import os

server_address = "s5bop2hnkp0977-3000.proxy.runpod.net"
client_id = str(uuid.uuid4())

def queue_prompt(prompt):
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    headers = {'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request("https://{}/prompt".format(server_address), data=data, headers=headers)
    return json.loads(urllib.request.urlopen(req).read())

def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request("https://{}/view?{}".format(server_address, url_values), headers=headers)
    with urllib.request.urlopen(req) as response:
        return response.read()

def get_history(prompt_id):
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request("https://{}/history/{}".format(server_address, prompt_id), headers=headers)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())

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
                    break  # Execution is done
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

# Load workflow from file 
with open("workflow.json", "r", encoding="utf-8") as f:
    workflow_data = f.read()

prompt = json.loads(workflow_data)
# Set the text prompt for our positive CLIPTextEncode
prompt["2"]["inputs"]["text"] = "white woman, white background, looking at the camera, waving with both hands, wearing a white t-shirt and blue jeans"

# Set the seed for our KSampler node
prompt["3"]["inputs"]["seed"] = 5

ws = websocket.WebSocket()
ws.connect("wss://{}/ws?clientId={}".format(server_address, client_id))
images = get_images(ws, prompt)

# Save the output images to the imgs directory:
image_counter = 1
for node_id in images:
    for image_data in images[node_id]:
        from PIL import Image
        import io
        image = Image.open(io.BytesIO(image_data))
        image_path = f"./output_image_{image_counter}.png"
        image.save(image_path)
        print(f"Saved image {image_counter} to {image_path}")
        image_counter += 1

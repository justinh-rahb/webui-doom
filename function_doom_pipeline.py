from pydantic import BaseModel
from typing import Union, Generator, Iterator, Dict
from utils.misc import get_last_user_message
from apps.webui.models.files import Files

import requests
import time
import uuid
import os
import json

from config import UPLOAD_DIR


class Pipe:
    class Valves(BaseModel):
        OPENAI_API_BASE_URL: str = "http://localhost:8080/openai/v1"
        MODEL_NAME: str = "DOOM:latest"
        AUTH_ENDPOINT: str = os.getenv(
            "AUTH_ENDPOINT", "http://localhost:8080/get-bearer-token"
        )
        GITHUB_REPO_URL: str = (
            "https://raw.githubusercontent.com/justinh-rahb/webui-doom/main/src/"
        )
        WAD_FILE_URL: str = f"{GITHUB_REPO_URL}doom1.wad"
        pass

    def __init__(self):
        self.type = "manifold"
        self.valves = self.Valves()
        self.pipes = [{"name": self.valves.MODEL_NAME, "id": self.valves.MODEL_NAME}]
        self.token = None
        pass

    def get_bearer_token(self) -> str:
        try:
            response = requests.post(self.valves.AUTH_ENDPOINT)
            response.raise_for_status()
            self.token = response.json().get("token")
            return self.token
        except requests.RequestException as e:
            raise Exception(f"Error fetching bearer token: {str(e)}")

    def create_file(
        self, file_name: str, title: str, content: Union[str, bytes], content_type: str
    ):
        base_path = UPLOAD_DIR + "/"
        file_id = str(uuid.uuid4())

        file_path = base_path + file_id + "_" + file_name
        # Create a file
        mode = "w" if isinstance(content, str) else "wb"
        with open(file_path, mode) as f:
            f.write(content)

        meta = {
            "source": file_path,
            "title": title,
            "content_type": content_type,
            "size": os.path.getsize(file_path),
            "path": file_path,
        }

        class FileForm(BaseModel):
            id: str
            filename: str
            meta: dict = {}

        formData = FileForm(id=file_id, filename=file_name, meta=meta)

        file = Files.insert_new_file(self.user_id, formData)
        return file.id

    def get_file_url(self, file_id: str) -> str:
        return f"/api/v1/files/{file_id}/content"

    def responses(
        self, command: str, messages: list
    ) -> Union[str, Generator, Iterator]:
        print(f"responses:{__name__}")

        command_body = get_last_user_message(messages)[len(command) + 2 :]
        print("Command Body:", command_body)

        list_of_responses = [
            "![DOOM](data:image/png;base64,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)\n\n",
        ]

        # Determine the WAD file to download
        # wad_filename = "doom2.wad" if command == "doom2" else "doom1.wad"
        wad_filename = "doom1.wad"

        # Check if the files already exist
        files = Files.get_files()
        files = [file for file in files if file.user_id == self.user_id]

        existing_html = next(
            (file for file in files if "index.html" in file.filename), None
        )

        if existing_html:
            list_of_responses.append(
                "Looks like you already have the game files... 🤘\n\n"
            )
            list_of_responses.append(
                "{{HTML_FILE_ID_{FILE_ID}}}".replace("{FILE_ID}", existing_html.id)
            )
        else:
            cfg_url = f"{self.valves.GITHUB_REPO_URL}default.cfg"
            wad_url = f"{self.valves.GITHUB_REPO_URL}{wad_filename}"
            html_url = f"{self.valves.GITHUB_REPO_URL}index.html"
            js_url = f"{self.valves.GITHUB_REPO_URL}websockets-doom.js"
            wasm_url = f"{self.valves.GITHUB_REPO_URL}websockets-doom.wasm"

            # Step 1: Download and upload the WAD file as doom1.wad
            list_of_responses.append("```console\nDownloading WAD.......... ")
            wad_id = self.download_and_create_file(
                "doom1.wad", wad_url, "application/x-doom"
            )
            list_of_responses.append(f"ID: {wad_id} DONE\n")
            print(f"doom1.wad ID: {wad_id}")

            # Step 2: Download and upload the default.cfg file
            list_of_responses.append("Downloading CFG.......... ")
            cfg_id = self.download_and_create_file(
                "default.cfg", cfg_url, "application/octet-stream"
            )
            list_of_responses.append(f"ID: {cfg_id} DONE\n")
            print(f"default.cfg ID: {cfg_id}")

            # Step 3: Download and upload the WASM file
            list_of_responses.append("Downloading WASM......... ")
            wasm_id = self.download_and_create_file(
                "websockets-doom.wasm", wasm_url, "application/wasm"
            )
            list_of_responses.append(f"ID: {wasm_id} DONE\n")
            print(f"websockets-doom.wasm ID: {wasm_id}")

            # Step 4: Download, modify, and upload the JavaScript file
            list_of_responses.append("Downloading JS........... ")
            js_content = requests.get(js_url).text
            js_content = js_content.replace(
                "websockets-doom.wasm", self.get_file_url(wasm_id)
            )
            js_content = js_content.replace(
                "doom1.wad", self.get_file_url(wad_id)
            ).replace("default.cfg", self.get_file_url(cfg_id))
            js_id = self.create_file(
                "websockets-doom.js",
                "websockets-doom.js",
                js_content,
                "application/javascript",
            )
            list_of_responses.append(f"ID: {js_id} DONE\n")
            print(f"websockets-doom.js ID: {js_id}")

            # Step 5: Download, modify, and upload the HTML file
            list_of_responses.append("Downloading HTML......... ")
            html_content = requests.get(html_url).text

            html_content = html_content.replace(
                'Module.FS.createPreloadedFile("", "doom1.wad", "doom1.wad", true, true);',
                f'Module.FS.createPreloadedFile("", "doom1.wad", "{self.get_file_url(wad_id)}/doom1.wad", true, true);',
            )
            html_content = html_content.replace(
                'Module.FS.createPreloadedFile("", "default.cfg", "default.cfg", true, true);',
                f'Module.FS.createPreloadedFile("", "default.cfg", "{self.get_file_url(cfg_id)}/default.cfg", true, true);',
            )
            html_content = html_content.replace(
                "websockets-doom.js", self.get_file_url(js_id)
            )
            html_id = self.create_file(
                "index.html", "index.html", html_content, "text/html"
            )
            list_of_responses.append(f"ID: {html_id} DONE\n```\n\n")
            print(f"index.html ID: {html_id}")

            # Step 6: Provide the final HTML ID to display in iframe
            list_of_responses.append("Time to play... 😈\n\n")
            list_of_responses.append(
                "{{HTML_FILE_ID_{FILE_ID}}}".replace("{FILE_ID}", html_id)
            )

        for response in list_of_responses:
            time.sleep(1)
            yield response

        return "Done"

    def download_and_create_file(self, file_name: str, url: str, content_type: str):
        try:
            response = requests.get(url)
            response.raise_for_status()
            content = response.content

            # Create the file with the correct content type
            return self.create_file(file_name, file_name, content, content_type)
        except Exception as e:
            raise Exception(f"Error handling {file_name}: {str(e)}")

    def pipe(self, body: dict, __user__: dict) -> Union[str, Generator, Iterator]:
        print(f"pipe:{__name__}")

        self.user_id = __user__["id"]

        messages = body["messages"]
        user_message = get_last_user_message(messages)

        if user_message.startswith("/"):
            command = user_message.split(" ")[0][1:]
            print(f"Command: {command}")
            return self.responses(command, messages)
        else:
            print("No command found - calling API")

        headers = {}
        headers["Content-Type"] = "application/json"
        headers["Authorization"] = f"Bearer {self.get_bearer_token()}"

        model_id = body["model"][body["model"].find(".") + 1 :]
        payload = {**body, "model": model_id}

        return self.call_api(body, headers, payload)

    def call_api(
        self, body: dict, headers: dict, payload: dict
    ) -> Union[str, dict, Generator, Iterator]:
        # Call the API based on the API_TYPE
        print(f"call_api:{__name__}")
        print(f"call_api:{body}")

        base_url = self.valves.OPENAI_API_BASE_URL
        endpoint = "/v1/chat/completions"

        try:
            r = requests.post(
                url=f"{base_url}{endpoint}",
                json=payload,
                headers=headers,
                stream=True,
            )

            r.raise_for_status()

            if body["stream"]:
                return r.iter_lines()
            else:
                return r.json()
        except Exception as e:
            return f"Error: {e}"

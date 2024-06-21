from pydantic import BaseModel
from typing import Union, Generator, Iterator
from utils.misc import get_last_user_message
from apps.webui.models.files import Files

import requests
import time
import uuid
import os


class Pipe:
    class Valves(BaseModel):
        API_TYPE: str = "ollama"  # Can be "ollama" or "openai"
        OLLAMA_API_BASE_URL: str = "http://localhost:8080/ollama/v1"
        OPENAI_API_BASE_URL: str = "http://localhost:8080/openai/v1"
        MODEL_NAME: str = "llama3:latest"
        AUTH_ENDPOINT: str = "http://localhost:8080/get-bearer-token"
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

    def create_file(self, file_name: str, title: str, content: str):
        base_path = "/app/backend/data/uploads/"
        file_id = str(uuid.uuid4())

        file_path = base_path + file_id + "_" + file_name
        # Create a file
        with open(file_path, "w") as f:
            f.write(content)

        meta = {
            "source": file_path,
            "title": title,
            "content_type": "text/html",
            "size": os.path.getsize(file_path),
            "path": file_path,
        }

        class FileForm(BaseModel):
            id: str
            filename: str
            meta: dict = {}

        formData = FileForm(id=file_id, filename=file_name, meta=meta)

        return Files.insert_new_file(self.user_id, formData)

    def responses(
        self, command: str, messages: list
    ) -> Union[str, Generator, Iterator]:
        print(f"responses:{__name__}")

        command_body = get_last_user_message(messages)[len(command) + 2 :]
        print("Command Body:", command_body)

        if command == "doom":
            html_file_name = "index.html"
            wasm_file_name = "doom.wasm"
            html_url = "https://raw.githubusercontent.com/justinh-rahb/webui-doom/main/src/index.html"
            wasm_url = "https://github.com/justinh-rahb/webui-doom/releases/latest/download/doom.wasm"
            list_of_responses = [
                "So you want to play Doom?...\n",
                "Okay...\n",
            ]

            # Check if we have the files already
            files = Files.get_files()
            # filter to users files
            files = [file for file in files if file.user_id == self.user_id]
            # filter to html and wasm files
            html_files = [file for file in files if html_file_name in file.filename]
            wasm_files = [file for file in files if wasm_file_name in file.filename]
            print("HTML Files: ", html_files)
            print("WASM Files: ", wasm_files)

            if len(html_files) > 0 and len(wasm_files) > 0:
                print("Files already exist")
                list_of_responses.append(
                    "Looks like you already have Doom ready...\n"
                )
            else:
                try:
                    list_of_responses.append("Downloading and setting up Doom...\n")
                    html_content = requests.get(html_url).text
                    wasm_content = requests.get(wasm_url).content
                except:
                    raise Exception("Error downloading Doom files")

                try:
                    self.create_file(html_file_name, "Doom Game", html_content)
                    wasm_file_path = f"/app/backend/data/uploads/{str(uuid.uuid4())}_{wasm_file_name}"
                    with open(wasm_file_path, "wb") as wasm_file:
                        wasm_file.write(wasm_content)
                except:
                    raise Exception("Error creating files")

            if len(html_files) > 0:
                html_file = html_files[0]
                list_of_responses.append(
                    "{{HTML_FILE_ID_{FILE_ID}}}".replace("{FILE_ID}", html_file.id)
                )
            if len(wasm_files) > 0:
                wasm_file = wasm_files[0]
                list_of_responses.append(
                    "{{WASM_FILE_ID_{FILE_ID}}}".replace("{FILE_ID}", wasm_file.id)
                )

        for response in list_of_responses:
            time.sleep(1.5)
            yield response

        return "Done"

    def pipe(self, body: dict) -> Union[str, Generator, Iterator]:
        print(f"pipe:{__name__}")

        if "user" in body:
            print(body["user"])
            self.user_id = body["user"]["id"]
            del body["user"]

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

        base_url = (
            self.valves.OLLAMA_API_BASE_URL
            if self.valves.API_TYPE == "ollama"
            else self.valves.OPENAI_API_BASE_URL
        )
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

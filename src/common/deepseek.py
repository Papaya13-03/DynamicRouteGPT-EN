import os
from dotenv import load_dotenv
import requests

class DeepSeekApi:
    def __init__(self):
        load_dotenv()
        self.api_url = os.getenv("DEEPSEEK_API_URL")
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.tracking_file = os.getenv("DEEPSEEK_TRACKING_FILE")

    def tracking(self, prompt:str, response:requests.Response):
        with open(self.tracking_file, "a") as f:
            f.write(f"Prompt: \n{prompt}\n\n")
            if response.status_code == 200:
                response_content = response.json()["choices"][0]["message"]["content"]
                f.write(f"Response: \n{response_content}\n\n")
            else:
                f.write(f"Error: {response.status_code} - {response.text}")

            f.write("="*50 + "\n")

    def request(self, prompt:str) -> str:
        body = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            self.api_url,
            json=body,
            headers=headers
        )

        self.tracking(prompt, response)

        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            response.raise_for_status()
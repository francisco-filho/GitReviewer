import ollama

from gitreviewer.models import CommitMessage
from gitreviewer.util import logger
from google import genai
from google.genai import types

default_model = "deepseek-r1:8b"

def get_client(model: str = default_model):
    if model == "default":
        return LLMOllama()
    elif model == "deepseek-r1:8b":
        return LLMOllama()
    elif model.startswith("gemini"):
        return LLMGoogle(model)
    else:
        return LLMOllama()

class LLM:
    def chat_stream(self, prompt, model_name=default_model, think=False):
        pass

    def chat(self, prompt, model_name=default_model, output=None, think=False):
        pass


class LLMGoogle(LLM):
    default_model = "gemini-2.5-flash-preview-05-20"
    def __init__(self, model_name=default_model):
        self.model = model_name
        self.client = genai.Client()

    def _get_config(self, **kwargs):
        thinking = 0 if not kwargs["think"] else kwargs["think"]
        config = genai.types.GenerateContentConfig(
            thinking_config=genai.types.ThinkingConfig(thinking_budget=thinking)
        )
        if kwargs["output"]:
            config.response_mime_type =  "application/json"
            config.response_schema = kwargs["output"]
        return config;

    def chat(self, prompt, model_name=default_model, output=None, think=None):
        resp = self.client.models.generate_content(
            contents=prompt,
            model=model_name,
            config=self._get_config(output=output, think=think)
        )
        return resp.text

    def chat_stream(self, prompt, model_name=default_model, think=False):
        thinking = 0 if not think else think
        chunks = self.client.models.generate_content_stream(
            contents=prompt,
            model=model_name,
            config=genai.types.GenerateContentConfig(
                thinking_config=genai.types.ThinkingConfig(thinking_budget=thinking)
            )
        )

        for chunk in chunks:
            yield chunk.text


class LLMOllama(LLM):
    default = "deepseek-r1:8b"

    def __init__(self, model_name=default_model):
        self.model = model_name

    def chat_stream(self, prompt, model_name=default, think=False):
        try:
            stream = ollama.chat(
                model=model_name,
                messages=[{'role': 'user', 'content': prompt},],
                stream=True,
                think=think)

            logger.info("Receiving chunks")
            for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    yield chunk['message']['content']

        except ollama.ResponseError as e:
            logger.error(f"\nError communicating with Ollama LLM: {e}. Make sure your Ollama server is running and the model '{model_name}' is downloaded.")
            yield None
        except Exception as e:
            logger.error(e)
            logger.error(f"\nAn unexpected error occurred during LLM review: {e}")
            yield None

    def chat(self, prompt, model_name=default, output=None, think=False):
        try:
            chunk = ollama.chat(
                model=model_name,
                messages=[{'role': 'user', 'content': prompt},],
                think=think,
                format=output.model_json_schema() if output else None
            )

            if 'message' in chunk and 'content' in chunk['message']:
                return chunk['message']['content']
            return ""

        except ollama.ResponseError as e:
            logger.error(f"\nError communicating with Ollama LLM: {e}. Make sure your Ollama server is running and the model '{model_name}' is downloaded.")
            return ""
        except Exception as e:
            logger.error(f"\nAn unexpected error occurred during LLM review: {e}")
            return ""


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    llm = get_client("gemini-2.5-flash-preview-05-20")
    resp = llm.chat("hello")
    print(resp)

    for chunk in llm.chat_stream("write a fibonnaci function in go"):
        print(chunk, end="")
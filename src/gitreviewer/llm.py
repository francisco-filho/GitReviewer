import ollama
from typing import Dict
from pydantic import BaseModel

from google import genai
from google.genai import types

from gitreviewer.util import logger

default_model = "deepseek-r1:8b"


class FunctionCall(BaseModel):
    name: str
    args: Dict

class ChatResponse(BaseModel):
    content: str | None
    function_call: FunctionCall | None

def get_client(model: str = default_model):
    """Get a client implementation based on the model name."""

    if model == "default":
        return LLMOllama()
    elif model in ["deepseek-r1:8b", "qwen2.5-coder:14b"]:
        return LLMOllama(model_name=model)
    elif model.startswith("gemini"):
        return LLMGoogle(model)
    else:
        return LLMOllama()

class LLM:
    """ Interface básica """

    def chat_stream(self, prompt, model_name=default_model, think=False):
        pass

    def chat(self, prompt, model_name=default_model, output=None, think=False):
        pass


class LLMGoogle(LLM):
    """ LLM Client for Google Gemini"""

    default_model = "gemini-2.5-flash-preview-05-20"
    def __init__(self, model_name=default_model):
        self.model = model_name
        self.client = genai.Client()

    def _get_config(self, **kwargs):
        """ Create config for google client """
        thinking = 0 if "think" not in kwargs else int(kwargs["think"])

        tools = types.Tool(function_declarations=kwargs["tools"])

        config = genai.types.GenerateContentConfig(
            thinking_config=genai.types.ThinkingConfig(thinking_budget=thinking),
            tools=[tools]
        )

        if kwargs["output"]:
            config.response_mime_type =  "application/json"
            config.response_schema = kwargs["output"]
        if kwargs["tools"]:
            print("--> Using tools")
        #    config.tools = [types.Tool(function_declarations=kwargs["tools"])]
        return config;

    def chat(self, prompt, model_name=default_model, output=None, think=0, tools=[]) -> ChatResponse:
        resp = self.client.models.generate_content(
            contents=prompt,
            model=model_name,
            config=self._get_config(output=output, think=think, tools=tools)
        )
        if resp.candidates[0].content.parts[0].function_call:
            function_call = resp.candidates[0].content.parts[0].function_call
            print(f"Function to call: {function_call.name}")
            print(f"Arguments: {function_call.args}")
            # Example from gemini docs
            # In a real app, you would call your function here:
            # result = schedule_meeting(**function_call.args)
            # return f"call function : {function_call.name}({function_call.args})"
            logger.info("-"*30)
            logger.info(type(function_call.args))
            logger.info(f"----> {function_call.args}")
            return ChatResponse(
                content=None,
                function_call=FunctionCall(name=function_call.name, args=function_call.args)
            )

        return ChatResponse(content=resp.text, function_call=None)

    def chat_stream(self, prompt, model_name=default_model, output=None, think=0):
        chunks = self.client.models.generate_content_stream(
            contents=prompt,
            model=model_name,
            config=self._get_config(output=output, think=think),
        )

        for chunk in chunks:
            yield chunk.text


class LLMOllama(LLM):
    default = "deepseek-r1:8b"

    def __init__(self, model_name=default_model):
        self.model = model_name
        logger.info(f"Using model: {self.model}")

    def chat_stream(self, prompt, think=False):
        try:
            stream = ollama.chat(
                model=self.model,
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

    def chat(self, prompt, output=None, think=False):
        try:
            chunk = ollama.chat(
                model=self.model,
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

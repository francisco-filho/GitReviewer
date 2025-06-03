import ollama
from gitreviewer.util import logger

default_model = "deepseek-r1:8b"

class LLM:

    def chat_stream(self, prompt, model_name=default_model, think=False):
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

    def chat(self, prompt, model_name=default_model, output=None, think=False):
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

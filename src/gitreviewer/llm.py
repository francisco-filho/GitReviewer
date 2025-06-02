import ollama
import logging

logger = logging.getLogger("gitreviewer.llm")

default_model = "deepseek-r1:8b"

class LLM:

    def chat_stream(self, prompt, model_name=default_model, think=False):
        try:
            stream = ollama.chat(
                model=model_name,
                messages=[{'role': 'user', 'content': prompt},],
                think=think)

            for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    yield chunk['message']['content']

        except ollama.ResponseError as e:
            logger.error(f"\nError communicating with Ollama LLM: {e}. Make sure your Ollama server is running and the model '{model_name}' is downloaded.")
            yield None
        except Exception as e:
            logger.error(f"\nAn unexpected error occurred during LLM review: {e}")
            yield None

    def chat(self, prompt, model_name=default_model, think=False):
        try:
            chunk = ollama.chat(
                model=model_name,
                messages=[{'role': 'user', 'content': prompt},],
                think=think)

            if 'message' in chunk and 'content' in chunk['message']:
                return chunk['message']['content']

        except ollama.ResponseError as e:
            logger.error(f"\nError communicating with Ollama LLM: {e}. Make sure your Ollama server is running and the model '{model_name}' is downloaded.")
            return ""
        except Exception as e:
            logger.error(f"\nAn unexpected error occurred during LLM review: {e}")
            return ""

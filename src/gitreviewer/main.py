import argparse
import os
from git import Repo, InvalidGitRepositoryError
import ollama

def get_git_diff(repo_path):
    """
    Gets the diff of the current changes in the specified Git repository.
    This will get the diff between the working tree and the latest commit.
    """
    try:
        repo = Repo(repo_path)
        # Check if there are any changes in the working directory
        if repo.is_dirty(untracked_files=True):
            # Get the diff between the working tree and the index (staged changes)
            # and also between the index and HEAD (committed changes)
            # For simplicity, let's get the diff of all uncommitted changes
            # This includes staged and unstaged changes relative to HEAD
            diff = repo.git.diff('HEAD')
            if not diff:
                return "No changes detected in the working directory relative to HEAD."
            return diff
        else:
            return "No uncommitted changes found in the repository."
    except InvalidGitRepositoryError:
        return f"Error: '{repo_path}' is not a valid Git repository."
    except Exception as e:
        return f"An error occurred while getting git diff: {e}"

def review_code_with_llm(diff_content, model_name="llama2"):
    """
    Sends the code diff to a local Ollama LLM for review and streams the response.
    """
    if not diff_content or "No changes detected" in diff_content or "No uncommitted changes" in diff_content:
        yield "No code changes to review."
        return

    prompt = f"""
    You are a code reviewer. Please review the following git diff and provide feedback on potential issues,
    bugs, improvements, or anything noteworthy. Focus on code quality, security, and best practices.

    Diff:
    ```diff
    {diff_content}
    ```

    Provide your feedback in a concise and clear manner.
    Finish with recommendations.
    """
    try:
        print(f"Sending diff to LLM model: {model_name} and streaming response...")
        # Use ollama.chat with stream=True for streaming responses
        stream = ollama.chat(model=model_name, messages=[
            {'role': 'user', 'content': prompt},
        ], stream=True, think=False)

        for chunk in stream:
            # Check if 'content' exists in the 'message' dictionary
            if 'message' in chunk and 'content' in chunk['message']:
                yield chunk['message']['content']
            # Optionally, handle done status or other meta-information
            # if 'done' in chunk and chunk['done']:
            #     break

    except ollama.ResponseError as e:
        yield f"\nError communicating with Ollama LLM: {e}. Make sure your Ollama server is running and the model '{model_name}' is downloaded."
    except Exception as e:
        yield f"\nAn unexpected error occurred during LLM review: {e}"

def main():
    parser = argparse.ArgumentParser(description="Review code changes in a Git repository using a local LLM.")
    parser.add_argument("--repo", required=True, help="Path to the Git repository.")
    parser.add_argument("--model", default="deepseek-r1:8b", help="Name of the Ollama model to use (default: llama2).")

    args = parser.parse_args()

    repo_path = os.path.abspath(args.repo)

    print(f"Reviewing repository: {repo_path}")

    diff = get_git_diff(repo_path)
    print("\n--- Git Diff ---")
    print(diff)
    print("----------------\n")

    if "Error:" in diff or "No changes" in diff:
        print(diff) # Print the error or no changes message directly
    else:
        print("\n--- LLM Code Review Feedback (Streaming) ---")
        for chunk in review_code_with_llm(diff, args.model):
            print(chunk, end='', flush=True) # Print each chunk without a newline and flush
        print("\n--------------------------------------------\n") # Newline for clean final output


if __name__ == "__main__":
    main()

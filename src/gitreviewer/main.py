import argparse
import os
import ollama
import logging

from gitreviewer.tools.git import GitDiffTool
from gitreviewer.llm import LLM

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gitreviewer.main")


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

    print(f"Sending diff to LLM model: {model_name} and streaming response...")
    llm = LLM()
    for token in llm.chat(prompt):
        yield token

def main():
    parser = argparse.ArgumentParser(description="Review code changes in a Git repository using a local LLM.")
    parser.add_argument("--repo", required=True, help="Path to the Git repository.")
    parser.add_argument("--commit", required=True, type=bool, help="To show commit message")
    parser.add_argument("--model", default="deepseek-r1:8b", help="Name of the Ollama model to use (default: deepseek-r1:8b).")

    args = parser.parse_args()

    repo_path = os.path.abspath(args.repo)

    print(f"Reviewing repository: {repo_path}")

    diff_tool = GitDiffTool()
    diff = diff_tool.get_git_diff(repo_path)
    logger.debug(f"\n--- Git Diff ---\n\n{diff}\n---------------")

    msgprompt = f"""
        Sugest a commit message for the following diff: \n\n
         
        Diff:
         {diff}
        """
    if args.commit:
        llm = LLM()
        print(llm.chat(msgprompt))
        return
    else:
        logger.info("No commit message.")
        return

    if "Error:" in diff or "No changes" in diff:
        print(diff)
    else:
        print("\n--- LLM Code Review Feedback (Streaming) ---")
        for chunk in review_code_with_llm(diff, args.model):
            print(chunk, end='', flush=True) # Print each chunk without a newline and flush
        print("\n--------------------------------------------\n") # Newline for clean final output


if __name__ == "__main__":
    main()

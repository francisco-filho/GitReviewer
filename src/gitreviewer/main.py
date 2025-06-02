import os
import argparse

from gitreviewer.util import logger
from gitreviewer.tools.git import GitDiffTool, GitMessageSugestion
from gitreviewer.tools.code_review import CodeReviewer


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
        sug = GitMessageSugestion()
        print(sug.get_commit_message(diff))
        return
    else:
        logger.info("No commit message.")
        return

    # if not diff:
    #     print("No changes detected.")
    # else:
    #     print("\n--- LLM Code Review Feedback (Streaming) ---")
    #     reviewer = CodeReviewer()
    #     for chunk in reviewer.review(diff):
    #         print(chunk, end='', flush=True) # Print each chunk without a newline and flush
    #     print("\n--------------------------------------------\n") # Newline for clean final output


if __name__ == "__main__":
    main()

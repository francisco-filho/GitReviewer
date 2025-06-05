import os
import argparse

from gitreviewer.repl import init_repl
from gitreviewer.util import logger
from gitreviewer.tools.git import GitDiffTool, GitMessageSuggestion
from gitreviewer.tools.code_review import CodeReviewer


def main():
    parser = argparse.ArgumentParser(description="Review code changes in a Git repository using a local LLM.")
    parser.add_argument("--repo", default=".", help="Path to the Git repository.")
    parser.add_argument("--model", default="gemini-2.5-flash-preview-05-20", help="Name of the model to use")

    args = parser.parse_args()

    repo_path = os.path.abspath(args.repo)
    model = args.model

    init_repl(repo_path, model)


if __name__ == "__main__":
    main()

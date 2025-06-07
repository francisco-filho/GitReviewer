import os
import pathlib
from tqdm import tqdm
from git import Repo, InvalidGitRepositoryError

from gitreviewer.tools.code_review import CodeReviewer
from gitreviewer.tools.git import GitDiffTool, GitMessageSuggestion
from gitreviewer.util import logger, DEFAULT_MODEL

from gitreviewer.llm import get_client
from gitreviewer.parser import PythonParser

def run_commit_command(repo_path, diff):
    """
    Executes the /commit command to generate a commit message suggestion
    and optionally commits the changes.
    """
    if not diff:
        print("No changes detected to suggest a commit message.")
        return

    sug = GitMessageSuggestion()
    commit_suggestion = sug.get_commit_message(diff)

    if commit_suggestion:
        print("\n--- Commit Message Suggestion ---")
        print(f"Message: {commit_suggestion.message}")
        if commit_suggestion.details:
            print("Details:")
            for detail in commit_suggestion.details:
                print(f"- {detail}")
        print("---------------------------------\n")

        try:
            repo = Repo(repo_path)
            # Get the current status of the repository
            status_output = repo.git.status('--short')

            if status_output:
                print("\n--- Files to be staged and committed ---")
                print(status_output)
                print("----------------------------------------\n")
            else:
                print("\nNo changes detected in the working directory or staging area.")
                print("Commit will not proceed as there's nothing to commit.\n")
                return

        except InvalidGitRepositoryError:
            logger.error(f"Error: '{repo_path}' is not a valid Git repository.")
            return
        except Exception as e:
            logger.error(f"An error occurred while getting repository status: {e}")
            return

        # Ask the user if they want to commit
        while True:
            user_confirm = input("Do you want commit the changes staged for commit? (y/N): ").strip().lower()
            if user_confirm == 'y':
                try:
                    #repo.git.add(U=True)

                    commit_message_full = commit_suggestion.message
                    if commit_suggestion.details:
                        commit_message_full += "\n\n" + "\n".join([f"- {d}" for d in commit_suggestion.details])

                    repo.git.commit(m=commit_message_full)
                    print("\nChanges staged and committed successfully!")
                    break
                except InvalidGitRepositoryError:
                    logger.error(f"Error: '{repo_path}' is not a valid Git repository.")
                    break
                except Exception as e:
                    logger.error(f"An error occurred during commit: {e}")
                    break
            elif user_confirm == 'n' or user_confirm == '':
                print("Commit aborted. No changes were committed.")
                break
            else:
                print("Invalid input. Please enter 'y' or 'N'.")
    else:
        print("Could not generate a commit message suggestion.")

def run_review_command(diff_content):
    """
    Executes the /review command to perform a code review and stream the response.
    """
    if not diff_content:
        print("No changes detected to review.")
        return

    reviewer = CodeReviewer()
    print("\n--- LLM Code Review Feedback (Streaming) ---")
    for chunk in reviewer.review(diff_content):
        if chunk is not None:
            print(chunk, end='', flush=True)
    print("\n--------------------------------------------\n")

def run_index_command(repo_path):
    """
    Indexes all Python files in the repository and saves the parsed output to a file.
    """
    logger.info(f"Indexing Python files in: {repo_path}")
    project_name = pathlib.Path(repo_path).name
    output_filename = f"{project_name}-index.txt"
    indexed_files_count = 0

    ignored_directories = ['.venv', '.git', '__pycache__', '.pytest_cache', 'build', 'dist'] # Added common ignored directories


    # Check if it's a Python project
    is_python_project = False
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".py"):
                is_python_project = True
                break
        if is_python_project:
            break

    if not is_python_project:
        print(f"'{project_name}' does not appear to be a Python project (no .py files found). Indexing aborted.")
        return

    with open(output_filename, "w", encoding="utf-8") as outfile:
        for root, dirs, files in tqdm(os.walk(repo_path)):
            dirs[:] = [d for d in dirs if d not in ignored_directories]

            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    logger.debug(f"Parsing file: {file_path}")
                    try:
                        parser = PythonParser()
                        parsed_content = parser.parse(file_path)
                        if not parsed_content:
                            continue
                        outfile.write(parsed_content)
                        outfile.write("\n" + "-"*80 + "\n") # Separator between files
                        indexed_files_count += 1
                    except Exception as e:
                        logger.error(f"Error parsing {file_path}: {e}")

    if indexed_files_count > 0:
        print(f"Successfully indexed {indexed_files_count} Python files. Output saved to '{output_filename}'")
    else:
        print(f"No Python files were indexed in '{repo_path}'.")

def run_chat_command(message):
    """
    Executes the /chat command to send a message to the LLM and stream the response.
    """
    if not message:
        print("No message provided for chat.")
        return

    llm_client = get_client(DEFAULT_MODEL)  # Assuming get_client returns an instance of the LLM client
    print("\n--- Chat with LLM (Streaming) ---")
    for chunk in llm_client.chat_stream(message):
        if chunk is not None:
            print(chunk, end='', flush=True)
    print("\n---------------------------------\n")


def init_repl(repo_path, model=None):
    print(f"GitReviewer REPL. Reviewing repository: {repo_path}")
    print("Type /commit to get a commit message suggestion based on current diff.")
    print("Type /review to get a code review based on current diff.")
    print("Type /index to index all Python files in the repository.")
    print("Type /chat {message} - send the message to the LLM and stream the response")
    print("Type /exit to quit.")

    diff_tool = GitDiffTool()

    while True:
        user_input = input("gitreviewer> ").strip()

        if user_input.startswith("/"):
            command_parts = user_input[1:].split(' ', 1)
            command = command_parts[0]

            if len(command_parts) > 1:
                message = command_parts[1]
            else:
                message = ""

            if command == "commit":
                logger.info("Getting git diff...")
                diff = diff_tool.get_git_diff(repo_path)
                logger.debug(f"\n--- Git Diff ---\n\n{diff}\n---------------")
                run_commit_command(repo_path, diff)
            elif command == "review":
                logger.info("Getting git diff for code review...")
                diff = diff_tool.get_git_diff(repo_path)
                logger.debug(f"\n--- Git Diff for Review ---\n\n{diff}\n---------------")
                run_review_command(diff)
            elif command == "index":
                run_index_command(repo_path)
            elif command == "chat":
                run_chat_command(message)
            elif command == "exit":
                print("Exiting GitReviewer REPL.")
                break
            else:
                print(f"Unknown command: /{command}")
        else:
            print("Unknown command. Commands start with '/'.")


if __name__ == "__main__":
    init_repl(".", "gemini-2.5-flash-preview-05-20")

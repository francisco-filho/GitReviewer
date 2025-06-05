from git import Repo, InvalidGitRepositoryError

from gitreviewer.tools.code_review import CodeReviewer
from gitreviewer.tools.git import GitDiffTool, GitMessageSuggestion
from gitreviewer.util import logger


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
            user_confirm = input("Do you want commit the changes of all modified files using the message above? (y/N): ").strip().lower()
            if user_confirm == 'y':
                try:
                    # Add all changes to the staging area
                    repo.git.add(A=True) # Use A=True to add all untracked and modified files
                    # Commit with the suggested message
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

def init_repl(repo_path, model=None):
    print(f"GitReviewer REPL. Reviewing repository: {repo_path}")
    print("Type /commit to get a commit message suggestion based on current diff.")
    print("Type /review to get a code review based on current diff.") # New command
    print("Type /exit to quit.")

    diff_tool = GitDiffTool()

    while True:
        user_input = input("gitreviewer> ").strip()

        if user_input.startswith("/"):
            command_parts = user_input[1:].split(' ', 1)
            command = command_parts[0]

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
            elif command == "exit":
                print("Exiting GitReviewer REPL.")
                break
            else:
                print(f"Unknown command: /{command}")
        else:
            print("Unknown command. Commands start with '/'.")


if __name__ == "__main__":
    init_repl(".", "gemini-2.5-flash-preview-05-20")

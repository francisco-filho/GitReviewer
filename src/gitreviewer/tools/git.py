from git import Repo, InvalidGitRepositoryError

from gitreviewer.models import CommitMessage
from gitreviewer.util import logger, DEFAULT_MODEL
from gitreviewer.llm import get_client

GIT_MODEL = DEFAULT_MODEL


class GitMessageSuggestion:
    def get_commit_message(self, diff):
        msgprompt = f"""
            You are a developer that write good commit messages:


            The first line should be the main description of the changes
            You can follow with a flat list of details, 3 at maximum

            Sugest a commit message for the following diff: \n\n

            Diff:\n
             {diff}

            Respond only with the commit message, do not explain anything.

            """

        """
        {"message": "Refactor GitReviewer for improved LLM integration and REPL functionality", "details": ["Introduced a `_get_config` method in `LLMGoogle` to centralize configuration handling for LLM calls.", "Refactored `main.py` to use a new `init_repl` function, streamlining the application's entry point and focusing on a REPL interface.", "Moved the `CommitMessage` Pydantic model to a dedicated `models.py` file for better organization and reusability."]}
        """

        llm = get_client(GIT_MODEL)
        msg = llm.chat(msgprompt, output=CommitMessage)
        return CommitMessage.model_validate_json(msg)


class GitDiffTool:

    def get_git_diff(self, repo_path):
        """
        Gets the diff of the current changes in the specified Git repository.
        This will get the diff between the working tree and the latest commit.
        """
        try:
            repo = Repo(repo_path)
            if repo.is_dirty(untracked_files=True):
                # get staged and unstaged changes relative to HEAD
                diff = repo.git.diff('HEAD', staged=True)
                if not diff:
                    logger.info("No changes detected in the working directory relative to HEAD.")
                    return None
                return diff
            else:
                return None
        except InvalidGitRepositoryError:
            logger.error(f"Error: '{repo_path}' is not a valid Git repository.")
        except Exception as e:
            logger.error(f"An error occurred while getting git diff: {e}")

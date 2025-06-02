import logging
from git import Repo, InvalidGitRepositoryError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gitreviewer")

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
                diff = repo.git.diff('HEAD')
                if not diff:
                    logger.info("No changes detected in the working directory relative to HEAD.")
                return diff
            else:
                return None
        except InvalidGitRepositoryError:
            logger.error(f"Error: '{repo_path}' is not a valid Git repository.")
        except Exception as e:
            logger.error(f"An error occurred while getting git diff: {e}")

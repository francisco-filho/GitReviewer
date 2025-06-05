from gitreviewer.llm import get_client
from gitreviewer.util import logger, DEFAULT_MODEL

REVIEW_PROMPT = """
You are a code reviewer. Please review the following git diff and provide feedback on potential issues,
bugs, improvements, or anything noteworthy. Focus on code quality, security, and best practices.

Diff:
```diff
{diff_content}
```

Provide your feedback in a concise and clear manner.
Finish with recommendations.
"""

MODEL_REVIEWER = DEFAULT_MODEL

class CodeReviewer(object):

    def review(self, diff_content):
        if not diff_content:
            logger.info("No code changes to review.")
            yield None
            return

        logger.debug("Sending diff to LLM model and streaming response...")
        llm = get_client(MODEL_REVIEWER)
        for token in llm.chat_stream(REVIEW_PROMPT.format(diff_content=diff_content)):
            yield token

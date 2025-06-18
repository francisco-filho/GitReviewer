from gitreviewer.util import logger


def diff(project_dir: str) -> str:
    logger.info("Executing function 'diff'")
    logger.info(f"Diffing project: {dir}")
    changes = """
diff --git a/src/gitreviewer/tools.py b/src/gitreviewer/tools.py
index 89a323e..d25c7b2 100644
--- a/src/gitreviewer/tools.py
+++ b/src/gitreviewer/tools.py
@@ -1,14 +1,25 @@
-class GitTool:
-    def __init__(self):
-        pass
+from gitreviewer.util import logger

-    def diff():
-        pass
+def diff(files: list[str]):
+    logger.info(f"Diffing: {dir}")


-class FileTool:
-    def __init__(self):
-        pass
+def list_files(dir: str):
+    logger.info(f"List files: {dir}")
+    file_paths = [
+        "gitreviewer/__init__.py",
+        "gitreviewer/main.py",
+        "gitreviewer/tools.py",
+        "gitreviewer/util.py",
+        "gitreviewer/parser.py",
+        "gitreviewer/llm.py",
+        "gitreviewer/repl.py",
+        "gitreviewer/models.py",
+        "gitreviewer/tools/__init__.py",
+        "gitreviewer/tools/git.py",
+        "gitreviewer/tools/prompts.py",
+        "gitreviewer/tools/code_review.py",
+        "gitreviewer/tools/parser.py"
+    ]
+    return file_paths
    """

    return changes

def list_files(project_dir: str) -> list[str]:
    logger.info("Executing function 'list_files'")
    logger.info(f"List files: {dir}")
    file_paths = [
        "gitreviewer/__init__.py",
        "gitreviewer/main.py",
        "gitreviewer/tools.py",
        "gitreviewer/util.py",
        "gitreviewer/parser.py",
        "gitreviewer/llm.py",
        "gitreviewer/repl.py",
        "gitreviewer/models.py",
        "gitreviewer/tools/__init__.py",
        "gitreviewer/tools/git.py",
        "gitreviewer/tools/prompts.py",
        "gitreviewer/tools/code_review.py",
        "gitreviewer/tools/parser.py"
    ]
    return file_paths

def read_file(file_path: str):
    logger.info("Executing function 'read_file'")
    logger.info(f"Read file: {file_path}")
    return """
def list_files(dir: str):
    logger.info(f"List files: {dir}")
    file_paths = [
        "gitreviewer/__init__.py",
        "gitreviewer/main.py",
        "gitreviewer/tools.py",
        "gitreviewer/util.py",
        "gitreviewer/parser.py",
        "gitreviewer/llm.py",
        "gitreviewer/repl.py",
        "gitreviewer/models.py",
        "gitreviewer/tools/__init__.py",
        "gitreviewer/tools/git.py",
        "gitreviewer/tools/prompts.py",
        "gitreviewer/tools/code_review.py",
        "gitreviewer/tools/parser.py"
    ]
    return file_paths
"""

def fn_definitions():
    return [
    {
        "name": "list_files",
        "description": "Lists all files in the specified project directory.",
        "parameters": {
        "type": "object",
        "properties": {
            "project_dir": {
            "type": "string",
            "description": "The path to the project directory."
            }
        },
        "required": [
            "project_dir"
        ]
        }
    },
    {
        "name": "read_file",
        "description": "Reads the content of the specified file.",
        "parameters": {
        "type": "object",
        "properties": {
            "file_path": {
            "type": "string",
            "description": "The path to the file to be read."
            }
        },
        "required": [
            "file_path"
        ]
        }
    },
        {
        "name": "diff",
        "description": "Compares the current state of the project directory with the last committed state and returns the differences as a string.",
        "parameters": {
            "type": "object",
            "properties": {
            "project_dir": {
                "type": "string",
                "description": "The path to the project directory."
            }
            },
            "required": [
            "project_dir"
            ]
        }
    }]

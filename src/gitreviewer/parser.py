import os
import sys
from tree_sitter_language_pack import get_language, get_parser

from gitreviewer.util import logger

language = "python"
parser = get_parser(language)
lang = get_language(language)

body_placeholder = "#...#"

def text(node, source_code_bytes):
    """Extracts the text content of a Tree-sitter node.

    Args:
        node: The Tree-sitter node.
        source_code_bytes: The original source code as bytes.

    Returns:
        The decoded string content of the node, or an empty string if the node is None.
    """
    if node is None:
        return ""
    return source_code_bytes[node.start_byte:node.end_byte].decode('utf8')

def get_node(match, key: str):
    """Extracts a specific node from a Tree-sitter match based on a key.

    Args:
        match: A Tree-sitter match object.
        key: The key to look for in the match dictionary.

    Returns:
        The first node associated with the key, or None if the key is not found.
    """
    dt = match[1]
    if key in dt:
        return dt[key][0]
    return None


class PythonParser():
    """A parser for Python code using Tree-sitter.

    This class provides functionality to parse Python source code
    and extract information such as classes, methods, and imports.
    """

    def parse(self, file):
        """Parse the Python file and create a tree-sitter tree, then return a formatted string of definitions.

        Args:
            file: The path to the Python file to be parsed.

        Returns:
            A string containing all definitions (imports, module functions, classes and their methods)
            formatted in a Python-like syntax, or an empty string if parsing fails.
        """
        with open(file, "rb") as f:
            self.contents = f.read()

        if os.path.getsize(file) == 0:
            logger.info(f"# file: {file}\n# File is empty, no definitions to extract.")
            return None

        self.tree = parser.parse(self.contents)

        output_lines = []
        output_lines.append("#" + "="*30)
        output_lines.append(f"# file: {os.path.relpath(file, os.getcwd())}")
        output_lines.append("#" + "="*30)

        imports = self.get_imports()
        for i in imports:
            output_lines.append(i)
        if imports:
            output_lines.append("")


        module_functions = self.get_module_functions()
        for f in module_functions:
            doc_string = f['doc'] if f['doc'] else ''
            output_lines.append(f"def {f['name']}{f['params']}:\n  {doc_string}")
        if module_functions:
            output_lines.append("")

        classes = self.get_classes()
        for c in classes:
            class_doc_string = c['doc'] if 'doc' in c else ''
            class_params = c['params'] if 'params' in c else ''
            output_lines.append(f"class {c['name']}{class_params}:\n  {class_doc_string}")
            for m in c['methods']:
                method_doc_string = f"{m['doc']}\n" if m['doc'] else ''
                method_params = m['params'] if 'params' in m else ''
                method_return = f" -> {m['ret']}" if 'ret' in m and m['ret'] else ''
                output_lines.append(f"  def {m['name']}{method_params}{method_return}:\n    {method_doc_string}  {body_placeholder}")
            output_lines.append("")

        return "\n".join(output_lines)


    def _get_methods_of_class(self, clazz):
        """Extracts methods from a given class node.

        This is a private helper method.

        Args:
            clazz: The Tree-sitter node representing the class definition.

        Returns:
            A list of dictionaries, where each dictionary represents a method
            with 'name', 'params', and 'doc' (docstring) keys.
        """
        methods_scm = """
        (function_definition
            name: (identifier) @nm
            parameters: (parameters) @param
            return_type: (type)? @ret
            body: (block
                (expression_statement (string))? @doc)
            )
        """

        qm = lang.query(methods_scm)
        matches = qm.matches(clazz)

        methods = []
        for m in matches:
            method = dict()
            method['name'] = text(get_node(m, 'nm'), self.contents)
            method['params'] = text(get_node(m, 'param'), self.contents)
            method['ret'] = text(get_node(m, 'ret'), self.contents)
            method['doc'] = text(get_node(m, 'doc'), self.contents)
            methods.append(method)

        return methods


    def get_classes(self):
        """Extracts class definitions and their associated methods from the parsed Python file.

        Returns:
            A list of dictionaries, where each dictionary represents a class
            with 'name', 'params' (superclasses), 'doc' (docstring), and 'methods' keys.
        """
        classe_scm = """
        ((class_definition
                    name: (identifier) @cdn
                    superclasses: (argument_list)? @cds
                    body: (block (expression_statement (string) @doc)?)
        ) @clazz)
        """

        qc = lang.query(classe_scm)
        matches = qc.matches(self.tree.root_node)

        classes = []

        for m in matches:
            clazz = dict()
            name = text(get_node(m, 'cdn'), self.contents)
            if name: clazz['name'] = name
            params = text(get_node(m, 'cds'), self.contents)
            if params: clazz['params'] = params # Only add if not empty
            doc = text(get_node(m, 'doc'), self.contents)
            if doc: clazz['doc'] = doc # Only add if not empty
            clazz['methods'] = self._get_methods_of_class(get_node(m, 'clazz'))
            classes.append(clazz)

        return classes


    def get_imports(self):
        """Extracts import statements from the parsed Python file.

        Returns:
            A list of strings, where each string represents an import statement.
        """
        imports_scm = """
        (module
            (import_statement)? @is
            (import_from_statement)? @is
        )
        """

        qi = lang.query(imports_scm)
        matches = qi.captures(self.tree.root_node)

        return [text(i, self.contents) for i in matches['is']]

    def get_module_functions(self):
        """Extracts top-level function definitions from the parsed Python file.

        Returns:
            A list of dictionaries, where each dictionary represents a function
            with 'name', 'params', and 'doc' (docstring) keys. The format is
            the same as returned by `_get_methods_of_class`.
        """
        functions_scm = """
        (module
            (function_definition
                name: (identifier) @nm
                parameters: (parameters) @param
                return_type: (type)? @ret
                body: (block
                    (expression_statement (string))? @doc)
            ) @function)
        """

        qf = lang.query(functions_scm)
        matches = qf.matches(self.tree.root_node)

        functions = []
        for m in matches:
            function = dict()
            function['name'] = text(get_node(m, 'nm'), self.contents)
            function['params'] = text(get_node(m, 'param'), self.contents)
            function['ret'] = text(get_node(m, 'ret'), self.contents)
            function['doc'] = text(get_node(m, 'doc'), self.contents)
            functions.append(function)

        return functions


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Inform the path of the file")
        exit(1)
    #file_path = "/home/ff/desenv/GitReviewer/src/gitreviewer/llm.py"
    file_path = sys.argv[1]
    p = PythonParser()
    # Call parse and directly print the returned string
    parsed_output = p.parse(file_path)
    print(f"```python\n{parsed_output}```")

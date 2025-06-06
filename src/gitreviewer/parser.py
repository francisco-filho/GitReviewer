from tree_sitter_language_pack import get_language, get_parser

language = "python"
parser = get_parser(language)
lang = get_language(language)

def text(node, source_code_bytes):
    """Extracts the text content of a Tree-sitter node."""
    if node is None:
        return ""
    return source_code_bytes[node.start_byte:node.end_byte].decode('utf8')

def get_node(match, key: str):
  dt = match[1]
  if key in dt:
    return dt[key][0]
  return None


class PythonParser():

  def init_parser(self, file):
    with open(file, "rb") as f:
      self.contents = f.read()

    self.tree = parser.parse(self.contents)

  def _get_methods_of_class(self, clazz):
    methods_scm = """
    (function_definition
          name: (identifier) @nm
          parameters: (parameters) @param
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
      method['doc'] = text(get_node(m, 'doc'), self.contents)
      methods.append(method)
    
    return methods


  def get_classes(self):
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
      if name: clazz['params'] = params
      doc = text(get_node(m, 'doc'), self.contents)
      if name: clazz['doc'] = doc
      clazz['methods'] = self._get_methods_of_class(get_node(m, 'clazz'))
      classes.append(clazz)

    return classes


  def get_imports(self):
    imports_scm = """
    (module
      (import_statement)? @is
      (import_from_statement)? @is
    )
    """

    qi = lang.query(imports_scm)
    matches = qi.captures(self.tree.root_node)

    return [text(i, self.contents) for i in matches['is']]


if __name__ == "__main__":
  file_path = "src/gitreviewer/parser_test.py"
  p = PythonParser()
  p.init_parser(file_path)


  print(f"# Code structure of file: {file_path}\n\n```python")
  print(f"# {file_path}")
  for i in p.get_imports():
    print(i)
  print()
  for c in p.get_classes():
    print(f"class {c['name']}{c['params']}:\n{c['doc']}")
    for m in c['methods']:
      print(f"  def {m['name']}{m['params']}:\n  {m['doc']}")
      print()
  print("```")
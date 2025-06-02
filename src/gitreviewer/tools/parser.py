import os
import json
import tree_sitter
from time import sleep
from tqdm import tqdm
from tree_sitter import Language, Parser
from tree_sitter_language_pack import get_binding, get_language, get_parser

try:
    parser = get_parser("java")
    JAVA_LANGUAGE = get_language("java")
    #parser.set_language(JAVA_LANGUAGE)
    print("Tree-sitter parser for Java initialized successfully.")

except Exception as e:
    print(f"Error initializing Tree-sitter: {e}")
    print("Please ensure you have installed `tree-sitter` (`pip install tree-sitter`)")
    print("and have compiled the `tree-sitter-java` grammar correctly.")
    print("Refer to the instructions in the comments of this script.")
    exit(1) # Exit if parser cannot be initialized

def get_node_text(node, source_code_bytes):
    """Extracts the text content of a Tree-sitter node."""
    return source_code_bytes[node.start_byte:node.end_byte].decode('utf8')

def extract_modifiers(node, source_code_bytes):
    """Extracts modifiers from a declaration node."""
    modifiers = []
    for child in node.children:
        if child.type == 'modifiers':
            for modifier_node in child.children:
                modifiers.append(get_node_text(modifier_node, source_code_bytes))
            break
    return ' '.join(modifiers)

def extract_type_parameters(node, source_code_bytes):
    """Extracts type parameters (e.g., <T, U>)."""
    type_params = []
    for child in node.children:
        if child.type == 'type_parameters':
            for param_node in child.children:
                if param_node.type == 'type_parameter':
                    type_params.append(get_node_text(param_node, source_code_bytes))
            break
    return '<' + ', '.join(type_params) + '>' if type_params else ''

def extract_extends_implements(node, source_code_bytes):
    """Extracts extended classes and implemented interfaces."""
    extends_clause = ""
    implements_clause = ""
    for child in node.children:
        if child.type == 'superclass':
            extends_clause = "extends " + get_node_text(child.children[1], source_code_bytes) # [1] is the type_identifier
        elif child.type == 'super_interfaces':
            interfaces = []
            for interface_node in child.children:
                if interface_node.type == 'type_list':
                    for type_node in interface_node.children:
                        if type_node.type == 'type_identifier': # Or other type nodes
                            interfaces.append(get_node_text(type_node, source_code_bytes))
            implements_clause = "implements " + ', '.join(interfaces)
    return extends_clause, implements_clause

def extract_method_parameters(node, source_code_bytes):
    """Extracts parameters from a method declaration."""
    params = []
    for child in node.children:
        if child.type == 'formal_parameters':
            for param_child in child.children:
                if param_child.type == 'formal_parameter':
                    param_text = get_node_text(param_child, source_code_bytes)
                    params.append(param_text)
            break # Found formal_parameters, no need to search further
    return ', '.join(params)

def extract_throws_clause(node, source_code_bytes):
    """Extracts the throws clause from a method declaration."""
    throws_clause = ""
    for child in node.children:
        if child.type == 'throws':
            exceptions = []
            for exception_node in child.children:
                if exception_node.type == 'type_identifier':
                    exceptions.append(get_node_text(exception_node, source_code_bytes))
            throws_clause = "throws " + ', '.join(exceptions)
            break
    return throws_clause

def parse_java_file(file_path):
    """
    Parses a single Java file and extracts its structural index.
    Returns a list of strings, each representing a structural element.
    """
    index_entries = []
    entry = {
        'package': '',
        'entity': {},
        'type': '',
        'imports': [],
        'methods': [],
        'fields': []
    }
    try:
        with open(file_path, 'rb') as f:
            source_code_bytes = f.read()

        tree = parser.parse(source_code_bytes)
        root_node = tree.root_node

        # Add FILE entry first for this file
        index_entries.append(f"FILE: {os.path.basename(file_path)}")

        # Determine package name
        current_package = "default" # Default package if no declaration found
        #package_declaration_node = root_node.child_by_field_name('package_declaration')
        #q = JAVA_LANGUAGE.query("(package_declaration (scoped_identifier) @package_name)")
        q = JAVA_LANGUAGE.query("""
        (
            (package_declaration (scoped_identifier) @package_name)
            (import_declaration (scoped_identifier) @import_name)?
            (class_declaration)? @clazz
            (record_declaration)? @rec
            (interface_declaration)? @itf
            (enum_declaration)? @enum
        )
        """)
        captures = q.captures(tree.root_node)

        if "package_name" in captures:
            pkg = captures["package_name"]
            if q :
                package_name_node = pkg[0]
                current_package = get_node_text(package_name_node, source_code_bytes)

            index_entries.append(f"PACKAGE: {current_package}")
            entry['package'] = current_package

        entry['package'] = current_package

        if "import_name" in captures:
            imports = []
            imp = captures["import_name"]
            if q :
                for i in imp:
                    import_name_node = i
                    current_imp = get_node_text(import_name_node, source_code_bytes)
                    index_entries.append(f"IMPORT: {current_imp}")
                    imports.append(current_imp)

            entry['imports'] = imports

        # Iterate through top-level declarations (classes, interfaces, enums, records)
        #for child in root_node.children:
        types = ["clazz", "rec", "itf", "enum"]
        for t in types:
            if t in captures and len(captures[t]):
                for child in captures[t]:
                    node_type = child.type.replace('_declaration', '')
                    modifiers = extract_modifiers(child, source_code_bytes)
                    name = get_node_text(child.child_by_field_name('name'), source_code_bytes)
                    type_parameters = extract_type_parameters(child, source_code_bytes)
                    extends_clause, implements_clause = extract_extends_implements(child, source_code_bytes)
                    class_signature = f"{modifiers} {node_type} {name}{type_parameters} {extends_clause} {implements_clause}".strip().replace('  ', ' ')

        # Add the class entry, now including the package name
                    index_entries.append(f"  {node_type.upper()}: {class_signature}")
                    entry['entity'] = class_signature
                    entry['name'] = name
                    entry['type'] = node_type
                    entry['modifiers'] = modifiers

                    body_node = child.child_by_field_name('body')
                    methods = []
                    fields = []
                    constructors = []
                    if body_node:
                        for member_node in body_node.children:
                            if member_node.type == 'method_declaration':
                                method_modifiers = extract_modifiers(member_node, source_code_bytes)
                                return_type_node = member_node.child_by_field_name('type')
                                return_type = get_node_text(return_type_node, source_code_bytes) if return_type_node else ""
                                method_name_node = member_node.child_by_field_name('name')
                                method_name = get_node_text(method_name_node, source_code_bytes) if method_name_node else ""
                                method_params = extract_method_parameters(member_node, source_code_bytes)
                                throws_clause = extract_throws_clause(member_node, source_code_bytes)
                                method_type_parameters = extract_type_parameters(member_node, source_code_bytes)

                                method_signature = f"{method_modifiers} {method_type_parameters} {return_type} {method_name}({method_params}) {throws_clause}".strip().replace('  ', ' ')
                                index_entries.append(f"    METHOD: {method_signature}")
                                methods.append(method_signature)

                            elif member_node.type == 'field_declaration':
                                field_modifiers = extract_modifiers(member_node, source_code_bytes)
                                field_type_node = member_node.child_by_field_name('type')
                                field_type = get_node_text(field_type_node, source_code_bytes) if field_type_node else ""
                                # A field_declaration can have multiple variable_declarators
                                for declarator in member_node.children:
                                    if declarator.type == 'variable_declarator':
                                        field_name_node = declarator.child_by_field_name('name')
                                        field_name = get_node_text(field_name_node, source_code_bytes) if field_name_node else ""
                                        field_signature = f"{field_modifiers} {field_type} {field_name}".strip().replace('  ', ' ')
                                        index_entries.append(f"    FIELD: {field_signature}")
                                        fields.append(field_signature)

                            elif member_node.type == 'constructor_declaration':
                                constructor_modifiers = extract_modifiers(member_node, source_code_bytes)
                                constructor_name_node = member_node.child_by_field_name('name')
                                constructor_name = get_node_text(constructor_name_node, source_code_bytes) if constructor_name_node else ""
                                constructor_params = extract_method_parameters(member_node, source_code_bytes)
                                throws_clause = extract_throws_clause(member_node, source_code_bytes)

                                constructor_signature = f"{constructor_modifiers} {constructor_name}({constructor_params}) {throws_clause}".strip().replace('  ', ' ')
                                index_entries.append(f"    CONSTRUCTOR: {constructor_signature}")
                                constructors.append(constructor_signature)
                    entry['constructors'] = constructors
                    entry['fields'] = fields
                    entry['methods'] = methods

    except FileNotFoundError:
        index_entries.append(f"Error: File not found at {file_path}")
    except Exception as e:
        index_entries.append(f"Error parsing {file_path}: {e}")

    return entry

def create_project_index(project_root_dir):
    """
    Traverses a project directory, parses all Java files, and
    generates a comprehensive structural index.
    """
    full_project_index = []
    for root, _, files in tqdm(os.walk(project_root_dir), desc="Parsing files", unit="file"):
        sleep(.1)
        for file in files:
            if file.endswith(".java"):# and "Options" in file:
                file_path = os.path.join(root, file)
                #print(f"Processing: {file_path}")
                file_index = parse_java_file(file_path)
                full_project_index.append(file_index)
                #print(file_index)
                #ull_project_index.extend(file_index)
                #full_project_index.append("-" * 50) # Separator for readability
    return full_project_index

if __name__ == "__main__":
    # --- Instructions for User ---
    print("--- Java Codebase Indexer ---")
    print("Before running:")
    print("1. Install tree-sitter: pip install tree-sitter")
    print("2. Clone the tree-sitter-java grammar:")
    print("   git clone https://github.com/tree-sitter/tree-sitter-java.git ./grammars/tree-sitter-java")
    print("3. Ensure the JAVA_GRAMMAR_PATH and LANGUAGE_SO_FILE are correctly set in this script.")
    print("   The script will attempt to compile the grammar for you if the .so/.dll file is not found.")
    print("-" * 30)

    # --- User Input for Project Path ---
    #project_path = input("Enter the path to your Java project root directory: ")
    project_path = "/home/ff/desenv/jcurl-http-client/src/main/java"
    if not os.path.isdir(project_path):
        print(f"Error: '{project_path}' is not a valid directory.")
    else:
        print(f"\nGenerating index for project: {project_path}\n")
        project_index = create_project_index(project_path)

        for entry in project_index:
            print(json.dumps(entry))

        # Optional: Save the index to a file
        output_file = "java_codebase_index.txt"
        with open(output_file, "w") as f:
            for entry in project_index:
                f.write(json.dumps(entry) + "\n")

        print("You can now feed the content of 'java_codebase_index.txt' to your LLM.")


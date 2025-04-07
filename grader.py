import os
import sys
import importlib.util
import shutil
from io import StringIO
import contextlib
import traceback
import glob
import builtins
import time
import signal
import threading
import ast
import types


def extract_function_code(file_path, func_name):
    with open(file_path) as f:
        tree = ast.parse(f.read())

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            return ast.unparse(node)  # Python 3.9+

# Example usage

def extract_all_fns(file_path):
    try:
        main_code =  extract_function_code(file_path, "main")
        
        show_info_code =  extract_function_code(file_path, "show_student_information")

        roman_binary_code =  extract_function_code(file_path, "show_roman_binary_number")

        population_code = extract_function_code(file_path, "show_population")
            
        allCode = []
        allCode.append(main_code)
        allCode.append(show_info_code)
        allCode.append(roman_binary_code)
        allCode.append(population_code)
        return allCode
    except Exception as e:
        print(f"error in extracting fns in {file_path}, error is : {e}")
        return None

def print_ast(code_str) -> None:
    for s in code_str:
        if "def" in s:
            print("~" * 50)
        print(str(s))

def create_virtual_module_from_strings(name, function_strings):
    """Create a virtual module-like object from a list of function strings (without execution)."""
    for index in range(len(function_strings)):
        fn = function_strings[index]
        print(f"fn number {index + 1} is : \n {fn}")
    source_code = "\n\n\n".join(function_strings)
    tree = ast.parse(source_code)

    # Create a dummy module object
    module = types.SimpleNamespace()
    module.__name__ = name
    module.__source__ = source_code
    module.__ast__ = tree
    module.__functions__ = [
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    ]

    # Optionally store in sys.modules if needed (disabled by default)
    # sys.modules[name] = module

    return module


def extract_using_ast(file_path):
    with open(file_path) as f:
        tree = ast.parse(f.read(), filename=file_path)

    functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
    classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    return functions, classes

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("Program execution timed out")

def load_input_prompts():
    """Load input prompts from input.txt"""
    with open('input.txt', 'r') as f:
        return [line.strip() for line in f.readlines()]

def import_student_module(file_path):
    #! old code
    """Dynamically import a Python file"""
    #spec = importlib.util.spec_from_file_location("student_module", file_path)
    #module = importlib.util.module_from_spec(spec)
    #sys.modules["student_module"] = module
    #spec.loader.exec_module(module)
    #return module
    
    res =  extract_all_fns(file_path)    
    if res is not None:
        main_code = ""
        stu_info_code = ""
        binary_code = ""
        pop_code = ""

        inside_main = False
        inside_stu = False
        inside_binary = False
        inside_pop = False

        for index in range(len(res)):
            s = res[index]


            if "def" in s:
                if "main" in s:
                    main_code += s
                    inside_main = True
                    inside_stu = False
                    inside_binary = False
                    inside_pop = False
                    continue

                elif "student" in s:
                    stu_info_code += s
                    inside_main = False
                    inside_stu = True
                    inside_binary = False
                    inside_pop = False
                    continue
                elif "binary" in s:
                    binary_code += s
                    inside_main = False
                    inside_stu = False
                    inside_binary = True
                    inside_pop = False
                    continue
                elif "population" in s:
                    pop_code += s
                    inside_main = False
                    inside_stu = False
                    inside_binary = False
                    inside_pop = True
                    continue

            if inside_main:
                main_code += s
            elif inside_stu:
                stu_info_code += s
            elif inside_binary:
                binary_code += s
            elif inside_pop:
                pop_code += s

        print(f"maincode str is \n {main_code}")
        print('-' * 50 )
        print(f"stuinfo str is \n {stu_info_code}")
        print('-' * 50 )
        print(f"binary_code str is \n {binary_code}")
        print('-' * 50 )
        print(f"pop_code str is \n {pop_code}")
        print('-' * 50 )
        return create_virtual_module_from_strings("main",[main_code, stu_info_code, binary_code, pop_code])
    else:
        print("error in import_student_module")
        return None


def create_project_folder(project_name):
    """Create a folder for the project if it doesn't exist"""
    folder_name = project_name.replace('.py', '')
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    return folder_name

def run_with_timeout(func, args=(), timeout_duration=10):
    """Run a function with a timeout"""
    result = []
    error = []

    def target():
        try:
            result.append(func(*args))
        except Exception as e:
            error.append(str(e))
            error.append(traceback.format_exc())

    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout_duration)

    if thread.is_alive():
        return None, ["Program execution timed out after {} seconds".format(timeout_duration)]
    
    if error:
        return None, error
        
    return result[0] if result else None, None

def capture_output_and_files(module, input_prompts, folder_name):
    """Capture stdout and handle inputs while running all functions in a SimpleNamespace-based student module"""
    captured_lines = []
    input_idx = 0
    stdout_buffer = StringIO()

    # Get initial state of txt files
    initial_txt_files = set(f for f in os.listdir('.') if f.endswith('.txt'))

    def mock_input(prompt=''):
        nonlocal input_idx
        stdout_content = stdout_buffer.getvalue()
        if stdout_content:
            captured_lines.extend(stdout_content.splitlines())
            stdout_buffer.seek(0)
            stdout_buffer.truncate()

        if prompt:
            captured_lines.append(prompt.rstrip())

        if input_idx < len(input_prompts):
            value = input_prompts[input_idx]
            captured_lines.append(value)
            input_idx += 1
            return value
        return '9'  # Default fallback input

    original_input = builtins.input
    builtins.input = mock_input

    try:
        with contextlib.redirect_stdout(stdout_buffer):
            print(f"module type is {type(module)}")
            print(f"vars is {vars(module)}")

            exec_globals = {}
            functions_run = False

            # Compile and execute the source code from the namespace
            try:
                compiled_code = compile(module.__source__, filename="<student_code>", mode="exec")
                exec(compiled_code, exec_globals)

                for name, obj in exec_globals.items():
                    if callable(obj) and not name.startswith("__"):
                        try:
                            functions_run = True
                            print(f"Running function: {name}")
                            # Use your own run_with_timeout or just call obj() directly if not defined
                            result = obj()
                        except Exception as e:
                            captured_lines.append(f"Error running {name}: {str(e)}")
                            captured_lines.append(traceback.format_exc())
            except Exception as e:
                captured_lines.append(f"Compilation or execution error: {str(e)}")
                captured_lines.append(traceback.format_exc())

            if not functions_run:
                captured_lines.append("No callable functions found after executing the source.")

            # Capture any remaining output
            final_output = stdout_buffer.getvalue()
            if final_output:
                captured_lines.extend(final_output.splitlines())

    except Exception as e:
        captured_lines.append(f"Error occurred: {str(e)}")
        captured_lines.append(traceback.format_exc())

    finally:
        builtins.input = original_input

        try:
            time.sleep(1)
            current_txt_files = set(f for f in os.listdir('.') if f.endswith('.txt'))
            new_txt_files = current_txt_files - initial_txt_files - {'input.txt'}

            for txt_file in new_txt_files:
                try:
                    if os.path.exists(txt_file):
                        shutil.move(txt_file, os.path.join(folder_name, txt_file))
                except Exception as e:
                    captured_lines.append(f"Error moving {txt_file}: {str(e)}")
        except Exception as e:
            captured_lines.append(f"Error handling files: {str(e)}")

    return captured_lines


def process_project(project_file):
    """Process a single project file"""
    try:
        # Create project folder
        folder_name = create_project_folder(project_file)
        
        # Import student's module
        module = import_student_module(project_file)
        # module will be a list of Strs that are all the fns in their code 


        # Load input prompts
        input_prompts = load_input_prompts()
        
        # Run the project, capture output and handle file movements
        output = capture_output_and_files(module, input_prompts, folder_name)
        
        
        # Write output to file
        output_path = os.path.join(folder_name, 'output.txt')
        with open(output_path, 'w') as f:
            f.write('\n'.join(output))
        # Move project file to its folder after processing
        #if os.path.exists(project_file):
        #    shutil.move(project_file, os.path.join(folder_name, project_file))
        return  
        #print(f"Successfully processed {project_file}")
        
    except Exception as e:
        print(f"Failed to process {project_file}: {str(e)}")
        traceback.print_exc()
        return 
        # Even if processing failed, try to create output file with error message
        try:
            if not os.path.exists(folder_name):
                os.makedirs(folder_name)
            output_path = os.path.join(folder_name, 'output.txt')
            with open(output_path, 'w') as f:
                f.write(f"Error processing project: {str(e)}\n")
                f.write(traceback.format_exc())
            
            # Try to move the project file if it exists
            if os.path.exists(project_file):
                shutil.move(project_file, os.path.join(folder_name, project_file))
        except Exception as move_error:
            print(f"Failed to handle error case: {str(move_error)}")

def main():
    """Main function to process all Python files in the current directory"""
    python_files = [f for f in os.listdir('.') if f.endswith('.py') and f != 'grader.py']
    print(f"Found {len(python_files)} Python files to process")
    for project_file in python_files:
        print(f"\nProcessing {project_file}...")
        process_project(project_file)
        print(f"Completed processing {project_file}")

if __name__ == "__main__":
    main()

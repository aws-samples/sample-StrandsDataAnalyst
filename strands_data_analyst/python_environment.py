import io
from contextlib import redirect_stdout, redirect_stderr

from strands import tool


class PythonInterpreter:
    def __init__(self):
        self.state = {}
    
    def clear_state(self):
        self.state.clear()

    def get_tool(self):
        @tool
        def python_repl(code: str) -> str:
            """
            Executes Python code in a REPL environment with state persistence.

            Args:
                code: The Python code to execute
            """
            stdout_buffer = io.StringIO()
            stderr_buffer = io.StringIO()
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exec(code, self.state)
                        
            observation = []

            stdout_output = stdout_buffer.getvalue().strip()
            if stdout_output:
                observation.append(f"STDOUT: {stdout_output}")
            
            stderr_output = stderr_buffer.getvalue().strip()
            if stderr_output:
                observation.append(f"STDERR: {stderr_output}")
            
            if not observation:
                observation.append("Code executed successfully.")
            
            return '\n'.join(observation)

        return python_repl

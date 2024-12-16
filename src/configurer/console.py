import subprocess
from .errors import ConfigurerException

class NonZeroExitError(ConfigurerException):
    pass


def run_cmd(cmd_tokens):
    p = subprocess.run(cmd_tokens, text=True, encoding='cp437', capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    if p.returncode != 0:
        raise NonZeroExitError(_format_proc_output(p))


def run_pwsh(cmd_tokens):
    if cmd_tokens[0] != 'powershell.exe':
        cmd_tokens.insert(0, 'powershell.exe')
    return run_cmd(cmd_tokens)


def _format_proc_output(proc):
    return f"ARGS: {proc.args}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
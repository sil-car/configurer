from .console import run_cmd
from .console import NonZeroExitError


def run_manage_bde(cmd_tokens):
    p = run_cmd(cmd_tokens)
    if p.returncode != 0:
        # NOTE: The returncode is identical for non-existent drive and
        # for a drive already unencrypted.
        raise NonZeroExitError(f"Erreur dans '{cmd_tokens}':\n{p.stdout}\n{p.stderr}")


def is_active(drive):
    try:
        run_manage_bde(['manage-bde', '-status', drive, '-ProtectionAsErrorLevel'])
    except NonZeroExitError:
        return False
    return True


def deactivate(drive):
    run_manage_bde(['manage-bde', '-off', drive])

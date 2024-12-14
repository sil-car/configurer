import csv
import subprocess
import sys
import threading
from pathlib import Path
from pathlib import PurePath
from tkinter import messagebox
from tkinter import Tk

from tkinter.scrolledtext import ScrolledText
from tkinter.ttk import Button
from tkinter.ttk import Frame
from tkinter.ttk import Label

if sys.platform == 'win32':
    import win32api
    import win32net
    from win32com.shell import shell


__appname__ = 'Configurer'
__version__ = '0.1.1'


class App:
    def __init__(self):
        if sys.platform == 'win32':
            self.ensure_privileges()
            self._set_execution_policy_bypass()

        # Set user folder locations.
        self.downloads_dir = Path.home() / 'Downloads'
        self.apps_dir = self.downloads_dir / 'apps'
        self.fonts_dir = self.downloads_dir / 'polices'

        # Set app folder locations.
        if is_bundled():
            self.root_dir = Path(sys._MEIPASS)
        else:
            self.root_dir = Path(__file__).parents[2]
        self.data_dir = self.root_dir / 'data'
        self.installer_args_data = self._get_installer_args_data()
        self.registry_values_data = self._get_registry_values_data()

    def disable_bitlocker(self):
        for drive in ['C:', 'D:']:
            status_p = self._cmd(['manage-bde', '-status', drive, '-ProtectionAsErrorLevel'])
            if status_p.returncode == 0:
                off_p = self._cmd(['manage-bde', '-off', drive])
                if off_p.returncode == 0:
                    self.msg_status(f"BitLocker désactivé sur {drive}")
                else:
                    detail = self._format_proc_error(off_p)
                    self.msg_error("Échéc de désactivation de BitLocker", detail=detail)
            else:
                # NOTE: The returncode is identical for non-existent drive and
                # for a drive already unencrypted.
                pass

    def ensure_admin_account(self):
        admin_user = 'Admin'

        # Ensure user exists.
        admin_user_exists = False
        for user in win32net.NetUserEnum(None, 0)[0]:
            if user.get('name') == admin_user:
                self.msg_status(f"Compte \"{admin_user}\" existe déjà.")
                admin_user_exists = True
                break
        if not admin_user_exists:
            user_data = {
                'name': admin_user,
                'password': 'administrator',
                'comment': 'Compte Administrateur',
                'priv': 1,  # win32netcon.USER_PRIV_ADMIN = 2, *USER = 1
                'flags': 512 | 1,
            }
            win32net.NetUserAdd(None, 1, user_data)
            self.msg_status(f"Compte \"{admin_user}\" a été créé.")

        # Ensure user in Admin group.
        admin_group = 'Administrators'
        for group in win32net.NetLocalGroupEnum(None, 0)[0]:
            if group.get('name') == 'Administrateurs':
                admin_group = 'Administrateurs'
                break
        self.msg_status(f"Groupe des admins : {admin_group}")
        admin_user_in_group = False
        for member in win32net.NetLocalGroupGetMembers(None, admin_group, 1)[0]:
            if member.get('name') == admin_user:
                admin_user_in_group = True
                self.msg_status(f"Compte \"{admin_user}\" déjà configuré comme Administrateur.")
                break
        if not admin_user_in_group:
            domain = win32api.GetDomainName()
            group_data = [{'domainandname': f"{domain}\\{admin_user}"}]
            win32net.NetLocalGroupAddMembers(None, admin_group, 3, group_data)
            self.msg_status(f"Compte {admin_user} a été configuré comme Administrateur.")

    def ensure_privileges(self):
        if not shell.IsUserAnAdmin():
            self.msg_error("Il faut exécuter en tant qu'administrateur")
            sys.exit(1)

    def install_apps(self):
        if self.apps_dir.is_dir():
            for app in self._get_installers():
                ans = self.msg_ask(f"Installer {app.name} ?")
                if ans == 'yes':
                    self._install_app(app)
                    self.msg_status(f"\"{app.name}\" installé.")
        else:
            self.msg_status(f"\"{self.apps_dir}\" n'existe pas.")

    def msg_ask(self, question):
        return input(question)

    def msg_debug(self, text):
        print(text, file=sys.stderr)

    def msg_error(self, text, detail=None):
        print(text, file=sys.stderr)
        if detail:
            print(detail, file=sys.stderr)

    def msg_status(self, text, detail=None):
        print(text)
        if detail:
            print(detail)

    def set_config(self):
        try:
            self.ensure_admin_account()
            self.set_locale_etc()
            self.set_timezone()
            self.update_registry()
            self.disable_bitlocker()
            self.install_apps()
        except Exception as e:
            self.msg_error("Un problème est arrivé lors de la configuration.", detail=e)

    def set_locale_etc(self):
        self._pwsh(["Set-WinSystemLocale", "-SystemLocale" "fr-FR"])
        self._pwsh(["Set-WinHomeLocation", "-GeoId", "55"])

    def set_timezone(self):
        current_tz = self._pwsh(['(Get-Timezone).Id'])
        tz_id = "W. Central Africa Standard Time"
        if current_tz != tz_id:
            self.msg_status("Configuration de fuseau horaire à WAT.")
            self._pwsh(['Set-Timezone', '-Id', tz_id])
        else:
            self.msg_status("Fuseau horaire est déjà configuré à WAT.")

    def update_registry(self):
        for values in self.registry_values_data:
            detail = '; '.join(values)
            try:
                ec = self._set_registry_item(values)
            except Exception:
                self.msg_error('Error setting registry item', detail=detail)
                return
            if ec != 0:
                self.msg_error('Failed to set registry item', detail=detail)
                return

    def _get_csv_data(self, csvfilepath):
        values = []
        if csvfilepath.is_file():
            with csvfilepath.open() as f:
                reader = csv.DictReader(f)
                for row in reader:
                    values.append(row)
        else:
            self.msg_status(f"\"{csvfilepath}\" n'existe pas.")
        return values

    def _get_files_by_type(self, parent_dir, suffix):
        return [p for p in parent_dir.iterdir() if p.suffix == suffix]

    def _get_installer_args_data(self):
        return self._get_csv_data(self.data_dir / 'installer-args.csv')

    def _get_installers(self):
        exts = ('.exe', '.msi', '.zip')
        return [p for p in self.apps_dir.iterdir() if p.suffix in exts]

    def _get_registry_values_data(self):
        return self._get_csv_data(self.data_dir / 'registry-values.csv')

    def _install_app(self, installer):
        self.msg_debug(f"{installer=}")
        if installer.is_file():
            installer_args = []
            if self.installer_args_data:
                installer_pats = {i.get('Fichier'): i.get('Args') for i in self.installer_args_data}
                self.msg_debug(f"{installer_pats=}")
                for pat, args in installer_pats.items():
                    self.msg_debug(f"{pat=}; {args=}")
                    if PurePath(installer).match(pat):
                        installer_args = args.split()
                        break
            self.msg_debug(f"{installer_args=}")
            if installer.suffix in ['.exe', '.msi']:
                if 'Paratext' in installer.name:
                    # Add patch file params.
                    patches = self._get_files_by_type(self.apps_dir, '.msp')
                    if patches:
                        # TODO: This might not sort version numbers correctly?
                        patch = sorted(patches)[-1]
                        installer_args.append(f"PATCH={patch}")
                self._run_installer(installer, installer_args)
            elif installer.suffix == '.zip':
                pass

    def _run_installer(self, filepath, args):
        cmd = [str(filepath), *args]
        self.msg_status(f"Installation de \"{' '.join(cmd)}\"")
        p = self._cmd(cmd)
        if p.returncode != 0:
            self.msg_error(f"Échéc d'installation de {filepath}.")

    def _pwsh(self, cmd_tokens):
        if cmd_tokens[0] != 'powershell.exe':
            cmd_tokens.insert(0, 'powershell.exe')
        return self._cmd(cmd_tokens)

    def _set_execution_policy_bypass(self):
        p = self._pwsh(["Set-ExecutionPolicy", "-ExecutionPolicy", "Bypass", "-Scope", "Process"])
        if p.returncode != 0:
            detail = self._format_proc_error(p)
            self.msg_error("Échéc d'exécution", detail=detail)
        return p.returncode

    def _set_registry_item(self, values):
        path = values.get('Path')
        key = values.get('Key')
        dtype = values.get('Type')
        dvalue = values.get('Value')
        if None in [path, key, dtype, dvalue]:
            detail = f"Valeur invalide dans : {values}"
            self.msg_error("Valeur invalide", detail=detail)
            return 1
        self.msg_status(f"{path} -> {key} [{dtype}] = {dvalue}")
        p = self._cmd(['reg', 'add', path, '/f', '/v', key, '/t', dtype, '/d', dvalue])
        if p.returncode != 0:
            detail = self._format_proc_error(p)
            self.msg_error("Échéc d'exécution", detail=detail)
        return p.returncode

    def _cmd(self, cmd_tokens):
        self.msg_debug(f"Exécution de : {cmd_tokens}")
        return subprocess.run(cmd_tokens, text=True, encoding='cp437', capture_output=True)


class Cli(App):
    def __init__(self):
        super().__init__()
        self.msg_error("CLI mode not yet implemented.")
        sys.exit(1)


class Gui(App):
    def __init__(self):
        self.root = Tk()
        self.root.title(f"ACATBA - {__appname__}")
        self.root.resizable(False, False)
        self.root.minsize(320, 180)
        # self.root.icon = app_dir / 'img' / 'icon.png'
        # self.root.pi = PhotoImage(file=f'{self.icon}')
        # self.root.iconphoto(False, self.pi)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.win = MainWindow(self)

        # Init App only after self.win exists so that messages can be handled
        # properly.
        super().__init__()
        try:
            self.root.mainloop()
        except Exception as e:
            self.msg_error("Un problème est arrivé : ", detail=e)

    def handle_run_clicked(self):
        evt = '<<RunDone>>'
        self.win.bind(evt, self.win._reset_run_button)
        t = threading.Thread(
            target=self._set_config,
            args=[evt],
            daemon=True,
        )
        self.win.run.state(['disabled'])
        t.start()

    def msg_ask(self, question):
        return messagebox.askquestion(
            title="Question",
            message=question,
        )

    def msg_error(self, text, detail=None):
        messagebox.showerror(
            title="Erreur",
            message=text,
            detail=detail,
        )
        full_text = text
        if detail:
            full_text += f"\n{detail}"
        print(full_text, file=sys.stderr)

    def msg_status(self, text):
        self.win.status['state'] = 'normal'
        if self.win.status.index('end - 1 chars') != '1.0':
            self.win.status.insert('end', '\n')
        self.win.status.insert('end', text)
        self.win.status['state'] = 'disabled'

    def _set_config(self, evt):
        self.set_config()
        self.win.event_generate(evt)

    def _format_proc_error(self, proc):
        return f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"


def is_bundled():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return True
    else:
        return False


class MainWindow(Frame):
    def __init__(self, app, **kwargs):
        super().__init__(app.root, **kwargs)
        # Configure window.
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.grid(column=0, row=0, sticky='nsew')
        self.columnconfigure('all', uniform='uniform')
        # Configure widgets.
        self.app = app
        self.info = Label(self, text="Configurer l'ordinateur : ")
        self.run = Button(self, text="Lancer", command=self.app.handle_run_clicked)
        self.status = ScrolledText(self)
        # Layout widgets.
        w_cols_total = 2
        w_cols_info = 1
        w_cols_run = 1
        row = 0
        self.info.grid(column=0, row=row, columnspan=w_cols_info, sticky='w')
        self.run.grid(column=1, row=row, columnspan=w_cols_run, sticky='w')
        row += 1
        self.status.grid(column=0, row=row, columnspan=w_cols_total, sticky='nsew')

    def _reset_run_button(self, evt):
        if evt:
            self.run.state(['!disabled'])
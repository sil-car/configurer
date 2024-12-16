import csv
import logging
import sys
import threading
from pathlib import Path
from pathlib import PurePath
from tkinter import messagebox
from tkinter import Tk

from . import __appname__
from . import __bundled__
from . import __platform__
from . import bitlocker
from . import reg
from .console import run_cmd
from .console import run_pwsh
from .console import NonZeroExitError
from .errors import ConfigurerException
from .window import Main

if __platform__ == 'win32':
    import win32api
    import win32net
    from win32com.shell import shell


class App:
    def __init__(self):
        # Set app folder locations.
        if __bundled__:
            self.root_dir = Path(sys._MEIPASS)
            self.exe_parent_dir = Path(sys.executable).parent
        else:
            self.root_dir = Path(__file__).parents[2]
            self.exe_parent_dir = self.root_dir

        # Configure logging.
        logging.basicConfig(
            level=logging.DEBUG,
            filename=self.exe_parent_dir / f"{__appname__}.log",
            mode='w',
        )
        if __platform__ == 'win32':
            self.ensure_privileges()
            self._set_execution_policy_bypass()

        # Set user folder locations.
        self.downloads_dir = Path.home() / 'Downloads'
        self.apps_dir = self.downloads_dir / 'apps'
        self.fonts_dir = self.downloads_dir / 'polices'

        self.data_dir = self.root_dir / 'data'
        self.installer_args_data = self._get_installer_args_data()
        logging.info(f"{self.installer_args_data=}")
        self.registry_values_data = self._get_registry_values_data()
        logging.info(f"{self.registry_values_data=}")

    def disable_bitlocker(self):
        for drive in ['C:', 'D:']:
            if bitlocker.is_active(drive):
                try:
                    bitlocker.deactivate(drive)
                except NonZeroExitError as e:
                    self.msg_error("Échéc de désactivation de BitLocker", detail=e)
                self.msg_status(f"BitLocker désactivé sur {drive}")
            else:
                self.msg_status(f"BitLocker n'est pas activé sur {drive}")

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
        logging.debug(text)
        print(text, file=sys.stderr)

    def msg_error(self, text, detail=None):
        logging.error(text)
        print(text, file=sys.stderr)
        if detail:
            print(detail, file=sys.stderr)

    def msg_status(self, text, detail=None):
        logging.info(text)
        print(text)
        if detail:
            logging.info(detail)
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
        try:
            run_pwsh(["Set-WinSystemLocale", "-SystemLocale", "fr-FR"])
            self.msg_status("Langue vérifiée comme français")
            run_pwsh(["Set-WinHomeLocation", "-GeoId", "55"])
            self.msg_status("Emplacement vérifié comme Centrafrique")
        except NonZeroExitError as e:
            self.msg_error("Échéc d'exécution de commande powershell", detail=e)

    def set_timezone(self):
        current_tz = run_pwsh(['(Get-Timezone).Id'])
        tz_id = "W. Central Africa Standard Time"
        if current_tz != tz_id:
            try:
                run_pwsh(['Set-Timezone', '-Id', f'"{tz_id}"'])
            except NonZeroExitError as e:
                self.msg_error("Échéc d'exécution de commande powershell", detail=e)
        self.msg_status("Fuseau horaire vérifié comme WAT.")

    def update_registry(self):
        for values in self.registry_values_data:
            try:
                self._set_registry_item(values)
            except ConfigurerException:
                continue
            except Exception as e:
                detail = f"{values}\n{e}"
                self.msg_error("Erreur lors de la modification du registre", detail=detail)


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
        try:
            run_cmd(cmd)
        except NonZeroExitError as e:
            detail = f"{filepath}\n{e}"
            self.msg_error("Échéc d'installation d'appli", detail=detail)

    def _set_execution_policy_bypass(self):
        cmd = ["Set-ExecutionPolicy", "-ExecutionPolicy", "Bypass", "-Scope", "Process"]
        try:
            run_pwsh(cmd)
        except NonZeroExitError as e:
            self.msg_error("Erreur lors de la modification de 'ExecutionPolicy", detail=e)

    def _set_registry_item(self, values):
        path = values.get('Path')
        name = values.get('Name')
        data_type = values.get('Type')
        value = values.get('Value')
        if None in [path, name, data_type, value]:
            detail = f"Valeur invalide dans : {values}"
            self.msg_error("Valeur invalide", detail=detail)
            return 1
        self.msg_status(f"{path} -> {name} [{data_type}] = {value}")
        # try:
        #     reg.reg_add(path, name, data_type, value)
        # except NonZeroExitError as e:
        #     self.msg_error("Échéc lors de la modification du registre", detail=e)
        if reg.get_key_value(path, name)[0] != value:
            reg.set_key_value(path, name, data_type, value)
        else:
            self.msg_status("Valeur déjà configurée")


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

        self.win = Main(self)

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
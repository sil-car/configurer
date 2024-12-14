from tkinter.scrolledtext import ScrolledText
from tkinter.ttk import Button
from tkinter.ttk import Frame
from tkinter.ttk import Label


class Main(Frame):
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
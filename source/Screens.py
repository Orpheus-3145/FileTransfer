from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.app import App

# from DefaultWidgets import *
from DefaultLayouts import *
from Popups import *


class ManagerScreen(ScreenManager):
    pass


class MainScreen(Screen):
    def __init__(self, sounds, **kw):
        super().__init__(**kw)
        self.sounds = sounds
        self.source_path = "C:\\repo"
        self.destination_path = "C:\\users\\franc\\Desktop\\prova\\repo"

    def on_enter(self, *args):
        self.clear_labels()

    def set_source_path(self, new_path):
        # self.source_path = new_path
        self.ids.source_lbl.text = new_path
        self.ids.source_lbl.show_widget()
        if self.destination_path:
            self.check_input_paths(self.source_path, self.destination_path)

    def set_destination_path(self, new_path):
        # self.destination_path = new_path
        self.ids.destination_lbl.text = new_path
        self.ids.destination_lbl.show_widget()
        if self.source_path:
            self.check_input_paths(self.source_path, self.destination_path)

    def check_input_paths(self, source_path, destination_path):
        try:
            App.get_running_app().check_input_paths(source_path, destination_path)
        except Exception as error:
            if isinstance(error, PathError):
                self.clear_labels()
            ErrorPopup(error_text=str(error)).open()
        else:
            self.ids.start_analisys_btn.show_widget()

    def start_analysis(self):
        try:
            App.get_running_app().start_analysis()
        except Exception as error:
            ErrorPopup(error_text=str(error)).open()
            self.clear_labels()
        else:
            self.ids.start_transfer_btn.show_widget()
            AnalyzerPopup().open()

    def clear_labels(self):
        # self.source_path = ""
        # self.destination_path = ""
        self.ids.source_lbl.text = ""
        self.ids.destination_lbl.text = ""
        self.ids.source_lbl.hide_widget()
        self.ids.destination_lbl.hide_widget()
        self.ids.start_analisys_btn.hide_widget()
        self.ids.start_transfer_btn.hide_widget()


if __name__ == "__main__":
    pass

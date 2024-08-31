from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.app import App

# from DefaultWidgets import *
from DefaultLayouts import *
from Popups import *


class ManagerScreen(ScreenManager):
    pass


class MainScreen(Screen):
    # def __init__(self, sounds, **kw):
    #     super().__init__(**kw)
    #     self.sounds = sounds

    def on_enter(self, *args):
        self.refresh()

    def set_source_path(self, new_path):
        self.ids.source_lbl.text = "D:\\test_ft\\A\\TEST"  # new_path
        self.ids.source_lbl.show_widget()
        if self.ids.destination_lbl.text:
            self.ids.analisys_btn.show_widget()

    def set_destination_path(self, new_path):
        self.ids.destination_lbl.text = "D:\\test_ft\\B\\TEST"  # new_path
        self.ids.destination_lbl.show_widget()
        if self.ids.source_lbl.text:
            self.ids.analisys_btn.show_widget()

    def start_analysis(self):
        try:
            App.get_running_app().start_analysis(self.ids.source_lbl.text, self.ids.destination_lbl.text)
        except Exception as error:
            ErrorPopup(error_text=str(error)).open()
        else:
            self.ids.analisys_btn.hide_widget()
            self.ids.transfer_btn.show_widget()
            AnalyzerPopup().open()

    def start_transfer(self):
        pass

    def refresh(self):
        App.get_running_app().refresh()
        self.ids.source_lbl.hide_widget()
        self.ids.destination_lbl.hide_widget()
        self.ids.analisys_btn.hide_widget()
        self.ids.transfer_btn.hide_widget()


if __name__ == "__main__":
    pass

from kivy.uix.modalview import ModalView
from kivy.properties import StringProperty, ObjectProperty
from kivy.core.audio import SoundLoader
from kivy.factory import Factory

import os
import Tools

# class MainPopup(ModalView):
#     """Popup principale, apre tutti gli altri"""
#
#     @sound_decorator(Config["app"]["start_sound"])
#     def on_open(self):
#         """Lo dichiaro solo per potere legarci un suono al termine"""
#         pass


class SetFolderPopup(ModalView):
    """Popup che permette di selezionare la cartella SRC o DST, tramite il widget ListView"""
    def __init__(self, callback=None, **kw):
        super().__init__(**kw)
        self.callback = callback
        self.drive_dict = Tools.get_drive_dict()

    def on_open(self):
        self.ids.filechooser.path = f"{self.drive_dict[0]}:\\"

    def set_path(self):
        self.dismiss()
        self.callback(self.ids.filechooser.path)

    def open_drive_popup(self):
        Factory.SetDrivePopup(filechooser_to_update=self.ids.filechooser, drive_dict=Tools.get_drive_dict()).open()


class SetDrivePopup(ModalView):
    """Popup che permette di cambiare disco per la ricerca di SRC e DST"""
    new_drive = ObjectProperty(None)    # a questo attributo è legato il callback on_new_drive() che aggiorna l'istanza di ListView al nuovo disco

    def __init__(self, filechooser_to_update, drive_dict, **kw):
        super().__init__(**kw)
        self.filechooser_to_update = filechooser_to_update      # reference per aggiornare il nuovo drive scelto
        self.ids.drive_layout.f_to_launch = self.change_drive
        self.drive_dict = drive_dict

    def on_open(self):
        self.ids.drive_layout.update_layout(self.drive_dict)
        # for drive in disk_list:     # aggiungo i bottoni per ogni disco accessibile dal pc
        #     drive_layout.add_widget(DriveButton(change_driver_popup=self,
        #                                         text=drive[0],
        #                                         font_size=(self.height / 8) * 0.85,
        #                                         bold=True,
        #                                         bkg_color=App.get_running_app().colors["lightblue_rgba"],
        #                                         size_hint_y=None,
        #                                         height=self.height / 8,
        #                                         on_press=self.dismiss))

    def change_drive(self, drive_index):
        new_drive = f"{self.drive_dict[drive_index]}:\\"
        if os.path.exists(new_drive) is False:  # se il percorso non esiste allora il disco è protetto da bitlocker
            ErrorPopup(error_text=str("Disco protetto da crittografia Bitlocker, deve essere sbloccato")).open()
        else:
            self.filechooser_to_update.path = new_drive  # aggiorno ListView e chiudo il popup
            self.dismiss()


class AnalyzerPopup(ModalView):
    """Popup che permette di gestire le azioni al termine dell'analisi e della creazione del file compare, definito in
    Style.kv"""

    # @sound_decorator(Config["app"]["compare_sound"])
    def on_open(self):
        """Lo dichiaro solo per legarci un suono al termine"""


class TransferingPopup(ModalView):
    """popup aperto durante il trasferimento"""
    pass


class TransferPopup(ModalView):
    """Popup che si apre al termine del trasferimento, definito in Style.kv"""

    # @sound_decorator(Config["app"]["transfer_sound"])
    def on_open(self):
        """Lo dichiaro solo per legarci un suono al termine"""
        pass


class InfoPopup(ModalView):
    pass


class ErrorPopup(ModalView):
    """Popup informativo sull'errore verificatosi, definito in Style.kv"""
    error_text = StringProperty("")

    # @sound_decorator(Config["app"]["error_sound"])
    def on_open(self):
        """Lo dichiaro solo per legarci un suono al termine"""
        pass


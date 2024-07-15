from kivy.uix.modalview import ModalView
from kivy.properties import StringProperty, ObjectProperty
from kivy.core.audio import SoundLoader


class MainPopup(ModalView):
    """Popup principale, apre tutti gli altri"""

    @sound_decorator(Config["app"]["start_sound"])
    def on_open(self):
        """Lo dichiaro solo per potere legarci un suono al termine"""
        pass


class SetFolderPopup(ModalView):
    """Popup che permette di selezionare la cartella SRC o DST, tramite il widget ListView"""
    selected_path = StringProperty("")

    def __init__(self, type_folder, label_to_update, **kw):
        super().__init__(**kw)
        self.type_folder = type_folder          # se è 'S' aggiorno la parte SRC, DST se è 'D'
        self.label_to_update = label_to_update  # casella di testo da aggiornare con il nuovo percorso

    def on_selected_path(self, instance, new_path):
        """Callback per quando valorizzo la variabile self.selected_path, aggiorna la variabile dell'app (source o destination)
        il testo mostrato dalla casella associata e chiude il popup"""
        if self.type_folder == "S":
            App.get_running_app().source_path = new_path

        elif self.type_folder == "D":
            App.get_running_app().destination_path = new_path

        self.label_to_update.text = new_path
        self.dismiss()


class SetDrivePopup(ModalView):
    """Popup che permette di cambiare disco per la ricerca di SRC e DST"""
    new_drive = ObjectProperty(None)    # a questo attributo è legato il callback on_new_drive() che aggiorna l'istanza di ListView al nuovo disco

    def __init__(self, filechooser_to_update, **kw):
        super().__init__(**kw)
        self.filechooser_to_update = filechooser_to_update      # reference per aggiornare il nuovo drive scelto

    def on_open(self):
        """All'apertura del popup popolo il layout con ogni bottone corrispondente ad un disco disponibile"""
        drive_layout = self.ids.drive_layout
        disk_list = Tools.get_drive_list()

        for drive in disk_list:     # aggiungo i bottoni per ogni disco accessibile dal pc
            drive_layout.add_widget(DriveButton(change_driver_popup=self,
                                                text=drive[0],
                                                font_size=(self.height / 8) * 0.85,
                                                bold=True,
                                                bkg_color=App.get_running_app().colors["lightblue_rgba"],
                                                size_hint_y=None,
                                                height=self.height / 8,
                                                on_release=self.dismiss))

    def on_new_drive(self, instance, new_drive):
        if os.path.exists(new_drive) is False:  # se il percorso non esiste allora il disco è protetto da bitlocker
            ErrorPopup(error_text=str("Disco protetto da crittografia Bitlocker, deve essere sbloccato")).open()

        else:
            self.filechooser_to_update.path = new_drive  # aggiorno ListView e chiudo il popup
            self.dismiss()


class AnalyzerPopup(ModalView):
    """Popup che permette di gestire le azioni al termine dell'analisi e della creazione del file compare, definito in
    Style.kv"""

    @sound_decorator(Config["app"]["compare_sound"])
    def on_open(self):
        """Lo dichiaro solo per legarci un suono al termine"""


class TransferingPopup(ModalView):
    """popup aperto durante il trasferimento"""
    pass


class TransferPopup(ModalView):
    """Popup che si apre al termine del trasferimento, definito in Style.kv"""

    @sound_decorator(Config["app"]["transfer_sound"])
    def on_open(self):
        """Lo dichiaro solo per legarci un suono al termine"""
        pass


class InfoPopup(ModalView):
    pass


class ErrorPopup(ModalView):
    """Popup informativo sull'errore verificatosi, definito in Style.kv"""
    error_text = StringProperty("")

    @sound_decorator(Config["app"]["error_sound"])
    def on_open(self):
        """Lo dichiaro solo per legarci un suono al termine"""
        pass


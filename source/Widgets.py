from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.lang import Builder
from kivy.properties import StringProperty, ObjectProperty
from kivy.uix.widget import Widget
from kivy.core.audio import SoundLoader
from kivy.clock import Clock



class BackgroundLabel(Widget):
    """Colore delle caselle testuali"""
    bkg_color = ObjectProperty(None)
    border_color = ObjectProperty(None)


class BackgroundButton(Widget):
    """Colore dei bottoni"""
    bkg_color = ObjectProperty(None)
    border_color = ObjectProperty(None)


class MyDefaultLabel(Label, BackgroundLabel):
    """Casella testuale di default, è definita in MyDefaultWidgets.kv"""
    pass


class MyAppearingLabel(MyDefaultLabel):
    """Casella testuale creata non visibile, compare quando le viene inserito del testo"""
    def on_text(self, instance, text):
        if text != "":
            self.opacity = 1

        else:
            self.opacity = 0


class MyDefaultButton(Button, BackgroundButton):
    """Bottone di default, è definito in MyDefaultWidgets.kv, il colore alla pressione cambia tramite il callback su
    on_state()"""

    def on_state(self, instance, pressed):
        """Se viene selezionato, il colore del bottone diventa più trasparente: rimuovo l'ultimo valore dell'RGBA,
        lo schiarisco (inserisco 0.5 al posto di 1) e lo riassegno al colore di sfondo"""

        if pressed == "down":
            self.bkg_color.pop()
            self.bkg_color.append("0.5")
            self.background_color = self.bkg_color

        else:
            self.bkg_color.pop()
            self.bkg_color.append("1")
            self.background_color = self.bkg_color


class MyDefaultCloseButton(MyDefaultButton):
    """Bottone preposto alla chiusura dell'app"""

    def __init__(self, func_on_close=None, **kw):
        """func_on_close è la funzione che viene lanciata alla pressione del bottone, di default è app.stop()"""
        self.func_on_close = func_on_close if func_on_close else App.get_running_app().stop
        super().__init__(**kw)

    @sound_decorator(Config["app"]["end_sound"])
    def on_release(self):
        time.sleep(0.4)     # faccio passare un po' di tempo così l'app si chiude dopo la riproduzione del suono
        self.func_on_close()


class DriveButton(MyDefaultButton):
    """Ogni istanza di questa classe rappresenta un disco collegato al pc, una volta che questo bottone viene premuto esso
    aggiorna il popup dei driver (DriverPopup) sulla periferica scelta"""
    def __init__(self, change_driver_popup, **kw):
        """L'attributo change_driver_popup rappresenta l'istanza da aggiornare con il nuovo disco scelto"""
        super().__init__(**kw)
        self.change_driver_popup = change_driver_popup

    def on_release(self):
        self.change_driver_popup.new_drive = "{}:\\".format(self.text)


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
        """Lo dichiaro solo per potere legarci un suono al termine"""


class TransferingPopup(ModalView):
    """popup aperto durante il trasferimento"""
    pass
    # current_action = ObjectProperty(None)

    # def on_current_action(self, instance, new_action):
    #     display_lbl = self.ids.display_label
    #     display_lbl.text = new_action

    # def update_label(self, new_value, *args):
    #     print("henlo!")
    #     display_lbl = self.ids.display_label
    #     display_lbl.text = new_value


class TransferPopup(ModalView):
    """Popup che si apre al termine del trasferimento, definito in Style.kv"""

    @sound_decorator(Config["app"]["transfer_sound"])
    def on_open(self):
        """Lo dichiaro solo per potere legarci un suono al termine"""
        pass


class InfoPopup(ModalView):
    """Popup informativo sul funzionamento dell'app, viene aperto in MainPopup di fianco all'icona i, definito in Style.kv"""
    pass


class ErrorPopup(ModalView):
    """Popup informativo sull'errore verificatosi, definito in Style.kv"""
    error_text = StringProperty("")

    @sound_decorator(Config["app"]["error_sound"])
    def on_open(self):
        """Lo dichiaro solo per potere legarci un suono al termine"""
        pass


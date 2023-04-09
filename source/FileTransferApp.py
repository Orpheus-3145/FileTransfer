import os.path

import Tools
from FileTransfer import FileTransfer, SelectingFoldersError, TransferingFilesError, ComparingFoldersError
from Tools import *
from kivy.config import Config
from functools import partial

Config.read("settings\\config_filetransfer.ini")
Tools.set_center_app(Config)

LOG_LEVELS = {10: logging.DEBUG, 20: logging.INFO, 30: logging.WARNING, 40: logging.ERROR, 50: logging.CRITICAL}


from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.lang import Builder
from kivy.properties import StringProperty, ObjectProperty
from kivy.uix.widget import Widget
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
# from kivy.animation import Animation
# from kivy.graphics import Ellipse, Color


class FileTransferAppError(Exception):
    """Eccezione del modulo FileTransferApp.py """

    def __init__(self, error_text):
        super().__init__()
        self.error_text = error_text  # creo la proprietà di classe per avere maggiori informazioni sull'errore verificatosi

    def __str__(self):
        return self.error_text


def sound_decorator(sound_file_path):
    """Decoratore per associare l'esecuzione di un suono al termine di una funzione"""
    def wrap(function_to_wrap):
        def sound_function(*args, **kwargs):
            sound = SoundLoader.load(sound_file_path)  # suono da riprodurre
            if sound:
                sound.play()

            else:
                logging.warning("[%-15s]: file audio %s non trovato!", "FileTransferApp", sound_file_path)

            function_to_wrap(*args, **kwargs)

        return sound_function

    return wrap


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

    # @sound_decorator(Config["app"]["end_sound"])
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

    # @sound_decorator(Config["app"]["start_sound"])
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

    # @sound_decorator(Config["app"]["compare_sound"])
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

    # @sound_decorator(Config["app"]["transfer_sound"])
    def on_open(self):
        """Lo dichiaro solo per potere legarci un suono al termine"""
        pass


class InfoPopup(ModalView):
    """Popup informativo sul funzionamento dell'app, viene aperto in MainPopup di fianco all'icona i, definito in Style.kv"""
    pass


class ErrorPopup(ModalView):
    """Popup informativo sull'errore verificatosi, definito in Style.kv"""
    error_text = StringProperty("")

    # @sound_decorator(Config["app"]["error_sound"])
    def on_open(self):
        """Lo dichiaro solo per potere legarci un suono al termine"""
        pass

# class PreAnalisysPopup(ModalView):
#     pass
#
# class Shape(Widget):
#     def __init__(self, **kw):
#         super().__init__(**kw)
#         with self.canvas.before:
#             Color(1, 0, 0, 1)
#             self.ellipse = Ellipse(pos=self.pos, size=self.size)
#
#             self.bind(pos=self.update_ellipse,
#                       size=self.update_ellipse)
#
#     def animate_it(self, *args):
#         anim_start_1 = Animation(pos_hint={"y": 0.35}, transition="in_out_circ")
#         anim_start_1 &= Animation(size_hint=(self.size_hint_x * 1.5, self.size_hint_y * 1.5), transition="in_out_circ")
#         anim_start_2 = Animation(pos_hint={"y": 0.7}, transition="in_out_circ")
#         anim_start_2 &= Animation(size_hint=(self.size_hint_x / 1.5, self.size_hint_y / 1.5), transition="in_out_circ")
#         anim_end_1 = Animation(pos_hint={"y": 0.35}, transition="in_out_circ")
#         anim_end_1 &= Animation(size_hint=(self.size_hint_x * 1.5, self.size_hint_y * 1.5), transition="in_out_circ")
#         anim_end_2 = Animation(pos_hint={"y": 0}, transition="in_out_circ")
#         anim_end_2 &= Animation(size_hint=(self.size_hint_x / 1.5, self.size_hint_y / 1.5), transition="in_out_circ")
#         anim = anim_start_1 + anim_start_2 + anim_end_1 + anim_end_2
#         anim.repeat = True
#         anim.start(self)
#
#     def update_ellipse(self, *args):
#         self.ellipse.pos = self.pos
#         self.ellipse.size = self.size
#
#
# class WaitingContainer(FloatLayout):
#     def __init__(self, **kw):
#         super().__init__(**kw)
#         for i in range(10):
#             moving_wid = Shape(pos_hint={"x": 0 + 0.1 * i, "y": 0}, size_hint=[0.05, (1920 / 1080) * 0.05])
#             self.add_widget(moving_wid)
#             Clock.schedule_once(moving_wid.animate_it, i/10)


class FileTransferApp(App):
    colors = {key: [float(element.strip()) for element in value[1:len(value) - 1].split(",")] for key, value in Config["kivy_colors"].items()}  # dizionario --> nome_colore: rgba
    source_path = ObjectProperty("")              # percorso di origine (più aggiornato)
    destination_path = ObjectProperty("")         # percorso di destinazione (da aggiornare)

    def __init__(self, **kwargs):
        create_logger(level=LOG_LEVELS[Config.getint("log", "log_level")],
                      log_path=Config["log"]["log_path"],
                      log_name=Config["log"]["log_name"],
                      fmt=Config["log"]["format"])

        logging.info("[%-15s]: %s", "FileTransferApp", "#" * 80)
        logging.info("[%-15s]: applicazione avviata", "FileTransferApp")
        self.ft = FileTransfer()                # istanza di FileTransfer, con cui gestirò le azioni più a basso livello
        self._stopped = False                   # variabile interna mi serve per evitare di scrivere due volte sul log quando chiudo l'app
        self.main_popup_instance = None         # reference del popup principale

        super().__init__(**kwargs)

    def build(self):
        Builder.load_file("kv\\Style.kv")
        Builder.load_file("kv\\MyDefaultWidgets.kv")
        logging.debug("[%-15s]: caricati i fogli di stile .kv", "FileTransferApp")
        self.main_popup_instance = MainPopup()
        self.main_popup_instance.open()

    def check_src_dst(self):
        """Se entrambi self.source_path e self.destination_path sono popolati (cioè <> ""), verifica i valori inseriti
        con il metodo FileTransfer.check_folders()"""

        if self.source_path != "" and self.destination_path != "":
            try:
                self.ft.check_folders(self.source_path, self.destination_path)

            except SelectingFoldersError as error:
                ErrorPopup(error_text=str(error)).open()
                App.get_running_app().main_popup_instance.ids.start_analisys_btn.opacity = 0

            else:   # rendo visibile il bottone per iniziare l'analisi e chiudo il popup
                self.main_popup_instance.ids.start_analisys_btn.opacity = 1

    def start_analysis(self):
        """Funzione per l'analisi di SRC e DST, prima crea gli alberi di directory (FileTransfer.set_foders()) poi scrive
        il file compare.txt (FileTransfer.compare())"""
        try:
            self.ft.set_folders()
            self.ft.compare()

        except (ComparingFoldersError, SelectingFoldersError) as error:
            ErrorPopup(error_text=str(error)).open()
            self.clear_labels()

        else:   # se tutto è andato come previsto apro il popup ad analisi terminata
            AnalyzerPopup().open()

    def start_transfer(self, popup_to_close):
        """Metodo lanciato all'inizio del trasferimento, apre il popup 'trasferimento in corso' durante l'effettivo
        trasferimento e chiude quello dell'analisi (popup_to_update)"""
        transfering_popup = TransferingPopup()
        transfering_popup.open()
        Clock.schedule_once(popup_to_close.dismiss, 0)                      # chiudo il popup precedentemente aperto (AnalyzerPopup)
        Clock.schedule_once(partial(self.transfer, transfering_popup), 1)   # avvio il trasferimento

    def transfer(self, popup_to_close, *args):
        """Metodo per eseguire le azioni di allineamento di DST a SRC, wrappa FileTransfer.transfer(), al termine apre
        il popup informativo sull'avvenuto trasferimento, avvisando nel caso di errori verificatisi"""
        popup_to_close.dismiss()

        try:
            errors_occurred = self.ft.transfer()

        except TransferingFilesError as error:
            ErrorPopup(error_text=str(error)).open()

        else:
            if errors_occurred is False:
                TransferPopup().open()

            else:
                ErrorPopup(error_text="Il trasferimento è terminato, tuttavia si sono verificati alcuni errori, controlla nel log per ulteriori dettagli").open()

            self.clear_labels()     # pulisco le etichette su SRC e DST scelte, inoltre nascondo il tasto per avviare l'analisi

    def get_compare_file(self):
        """Apre il file compare.txt"""
        try:
            self.ft.cmp_manager.compare_file.inspect()

        except ComparingFoldersError as error:
            ErrorPopup(error_text=str(error)).open()

    def on_stop(self):
        """Non è chiaro perchè ma il metodo app.stop() viene chiamato due volte, per evitare di scrivere due volte sul log
        utilizzo il parametro _stopped"""
        if not self._stopped:
            self._stopped = True

            if self.ft:
                self.ft.close()

            logging.info("[%-15s]: chiusura applicazione", "FileTransferApp")
            logging.info("[%-15s]: %s", "FileTransferApp", "#" * 80)

    def on_source_path(self, instance, path):
        """Ogni volta che viene valorizzato source verifico che source e destination siano corretti per attivare i
        bottoni e iniziare l'analisi"""
        self.check_src_dst()

    def on_destination_path(self, instance, path):
        """Come sopra"""
        self.check_src_dst()

    def clear_labels(self):
        """Alla fine del trasferimento o in caso di errore in caso di analisi/trasferimento bisogna riprendere da 0 il
        processo: pertanto rimuovo i valori sulle label di SRC e DST e delle variabili dell'app, inoltre nascondo il
        bottone di 'Avvia Analisi', questo ricompare quando il metodo self.check_src_dst() va a buon fine"""

        self.main_popup_instance.ids.source_lbl.text = ""               # testo etichetta SRC
        self.main_popup_instance.ids.destination_lbl.text = ""          # testo etichetta DST
        self.source_path = ""                         # variabile dell'app di SRC
        self.destination_path = ""                    # variabile dell'app di DST
        self.main_popup_instance.ids.start_analisys_btn.opacity = 0     # disattivo (opacità a 0) il pulsante di avvio analisi, lo riattiverò quando verifico i nuovi SRC e DST


if __name__ == "__main__":
    app = FileTransferApp()
    app.run()

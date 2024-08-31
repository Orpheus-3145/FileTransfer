import os.path
from functools import partial
from datetime import date
import Tools
from win32api import GetSystemMetrics
from Exceptions import *


if os.environ.get("FileTransferAppPath") == os.getcwd():
    os.chdir("_internal")
else:
    os.chdir("..")
LOG_PATH = Tools.get_abs_path("logs")
CONFIG_PATH = Tools.get_abs_path("settings\\config_filetransfer.ini")
COMPARE_FILE_PATH = Tools.get_abs_path("compare")


from kivy.config import Config
Config.read(CONFIG_PATH)


# from Widgets import *       # DefaultWidgets
# from Popups import *
from Screens import *
from kivy.app import App
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.clock import Clock

from FileTransfer import *


class FileTransferApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._stopped = False                   # variabile interna mi serve per evitare di scrivere due volte sul log quando chiudo l'app
        self.manager = None
        self.config_info = {}
        self.create_logger(LOG_PATH, Config.get("log", "log_level", fallback=20))
        self.read_config(Config)
        self.ft = FileTransfer()                # istanza di FileTransfer, con cui gestirò le azioni più a basso livello

    def read_config(self, config):
        try:
            self.config_info["kv_files"] = [Tools.get_abs_path(kv_file) for kv_file in config["kivy_files"].values()]
            self.config_info["bk_image_path"] = Tools.get_abs_path(config["kivy"]["bk_image_path"])
            self.config_info["logo_path"] = Tools.get_abs_path(config["kivy"]["logo_path"])
            self.config_info["font_path"] = Tools.get_abs_path(config["kivy"]["font_path"])
            self.config_info["font_size"] = config.getint("kivy", "font_size")
            self.config_info["width_app"] = config.getint("graphics", "width")
            self.config_info["height_app"] = config.getint("graphics", "height")
            self.config_info["colors"] = {}
            for color_rgba in config["colors"].keys():
                self.config_info["colors"][color_rgba] = Tools.str_to_list_float(config["colors"][color_rgba])
            self.config_info["sounds"] = {}
            for sound in config["sounds"].keys():
                self.config_info["sounds"][sound] = Tools.get_abs_path(config["sounds"][sound])
        except (KeyError, ValueError) as error:
            self.update_log("errore nel file .ini - trace: %s", 40, str(error))
            raise AppException("Errore nel file .ini - trace: {}".format(str(error)))

    def get_bk_image(self):
        return self.config_info["bk_image_path"]

    def get_logo(self):
        return self.config_info["logo_path"]

    def get_font_name(self):
        return self.config_info["font_path"]

    def get_font_size(self):
        return self.config_info["font_size"]

    def get_color(self, color_name):
        return self.config_info["colors"][color_name]

    def get_sound(self, sound_name):
        return self.config_info["sounds"][sound_name]

    def create_logger(self, log_path, log_level):
        log_name = "Logfile_{}.log".format(date.today().strftime("%d-%m-%Y"))
        log_path = os.path.join(log_path, log_name)
        log_levels = {10: logging.DEBUG, 20: logging.INFO, 30: logging.WARNING, 40: logging.ERROR, 50: logging.CRITICAL}
        log_level_is_wrong = False
        try:
            log_level = int(log_level)
            if log_level not in log_levels:
                raise KeyError()
        except KeyError:
            log_level_is_wrong = True
            log_level = 20
        finally:
            log_level = log_levels[log_level]
        log_encoding = "utf-8"
        log_format = "%(asctime)s | %(levelname)-9s | %(message)s"
        log_date_format = "%m/%d/%Y %H:%M:%S"

        logger = logging.getLogger(__name__)
        logging.root = logger
        logger.setLevel(log_level)
        file_handler = logging.FileHandler(filename=log_path, encoding=log_encoding)
        log_formatter = logging.Formatter(fmt=log_format, datefmt=log_date_format)
        file_handler.setFormatter(log_formatter)
        file_handler.setLevel(log_level)
        logger.addHandler(file_handler)

        self.update_log("#" * 80, 20)
        self.update_log("app avviata", 20)
        if log_level_is_wrong is True:
            self.update_log("livello log in .ini file non valido [usage: 10, 20, 30, 40, 50]", 30)

    def update_log(self, message, level, *args):
        log_alerts = {10: logging.debug, 20: logging.info, 30: logging.warning, 40: logging.error, 50: logging.critical}
        try:
            log_alerts[level](message, *args)
        except KeyError:
            self.update_log("invalid log level provided: {}, original message: '{}'".format(level, message), 30, *args)

    def build(self):
        # width_screen = GetSystemMetrics(0)
        # height_screen = GetSystemMetrics(1)
        # print(Window.size)
        # print(Window.left)
        # print(Window.top)
        # Window.left = 0#(width_screen - self.config_info["width_app"]) // 2
        # Window.top = 0#(height_screen - self.config_info["height_app"]) // 2
        # print(width_screen, self.config_info["width_app"], (width_screen - self.config_info["width_app"]) // 2)
        # print(height_screen, self.config_info["height_app"], (height_screen - self.config_info["height_app"]) // 2)
        for kv_file in self.config_info["kv_files"]:
            try:
                Builder.load_file(kv_file)
            except Exception as error:
                self.update_log("caricamento front-end - errore in %s - %s", 40, kv_file, str(error))
                raise AppException("Errore nel cariamento del front-end, consulta il log per ulteriori dettagli")
            self.update_log("caricamento front-end - %s", 10, kv_file)
        self.manager = ManagerScreen()
        self.manager.add_widget(MainScreen())  # self.config_info["colors"]))
        return self.manager

    def start_analysis(self, source_path, destination_path):
        self.ft.set_src_and_dst(source_path, destination_path)
        self.ft.write_compare_file()

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

    def refresh(self):
        self.ft.refresh()

    def inspect_compare_file(self):
        """Apre il file compare.txt"""
        try:
            self.ft.inspect_compare_file()
        except ComparingFoldersError as error:
            ErrorPopup(error_text=str(error)).open()

    def on_stop(self):
        """Non è chiaro perchè ma il metodo app.stop() viene chiamato due volte, per evitare di scrivere due volte sul log
        utilizzo il parametro _stopped"""
        if not self._stopped:
            self._stopped = True
            if self.ft:
                self.ft.close()
        self.update_log("app chiusa", 20)
        self.update_log("#" * 80, 20)


if __name__ == "__main__":
    app = FileTransferApp()
    app.run()

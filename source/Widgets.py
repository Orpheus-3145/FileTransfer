from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.properties import StringProperty, ObjectProperty
from kivy.uix.widget import Widget
from kivy.core.audio import SoundLoader
from kivy.clock import Clock

import time


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


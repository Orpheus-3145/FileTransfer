from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.properties import ObjectProperty
from kivy.properties import ListProperty
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.core.audio import SoundLoader

import time


def sound_decorator(sound_file_path):
    """Decoratore per associare l'esecuzione di un suono al termine di una funzione"""
    def wrap(function_to_wrap):
        def sound_function(*args, **kwargs):
            sound = SoundLoader.load(sound_file_path)  # suono da riprodurre
            if sound:
                sound.play()
            else:       # NB: throw some exception
                pass
            function_to_wrap(*args, **kwargs)
        return sound_function
    return wrap


class Writable(Widget):
    def __init__(self, font_size_scale=1, **kw):
        super().__init__(**kw)
        self.font_size_scale = font_size_scale

    def on_kv_post(self, base_widget):
        self.font_size *= self.font_size_scale


class Showable(Widget):
    def __init__(self, **kw):
        self.tmp_size_hint_x = 0
        self.visible = True
        super().__init__(**kw)

    def on_kv_post(self, base_widget):
        self.tmp_size_hint_x = self.size_hint[0]

    def show_widget(self):
        self.opacity = 1
        self.disabled = False
        self.visible = True

    def hide_widget(self):
        self.opacity = 0
        self.disabled = True
        self.visible = False

    def is_visible(self):
        return self.visible


class DefaultWidget(Writable, Showable):
    pass


class BKG(Widget):
    border_color = ListProperty([1, 1, 1, 1])


class BKGlabel(BKG):
    background_color = ListProperty([1, 1, 1, 1])


class BKGrowLayout(BKG):
    pass


class DefaultLabel(Label, BKGlabel, DefaultWidget):
    pass


class DefaultButton(Button, DefaultWidget):
    def __init__(self, parent_layout=None, alt_id=None, **kw):
        super().__init__(**kw)
        self.parent_layout = parent_layout
        self.alt_id = alt_id

    def get_alt_id(self):
        return self.alt_id

    def on_state(self, instance, pressed):
        if pressed == "down":
            self.background_color.pop()
            self.background_color.append(0.75)
            if self.parent_layout:
                self.parent_layout.update_state(self)
        else:
            self.background_color.pop()
            self.background_color.append(1)


class SelectionButton(DefaultButton):
    active = ObjectProperty(False)

    def on_active(self, instance, active):
        """Ad ogni pressione attivo il bottone se era disattivato o viceversa"""
        if active is True:
            self.background_color = self.bk_active
        else:
            self.background_color = self.bk_inactive

    def on_press(self):
        self.active = not self.active
        if self.parent_layout:
            self.parent_layout.update_state(self)

    def on_state(self, instance, pressed):  # override of DefaultButton.on_state() to not execute that functionality
        pass


class DefaultTextInput(TextInput, DefaultWidget):
    pass


class DefaultScrollView(ScrollView, Showable):
    pass


# class MyDefaultCloseButton(DefaultButton):
#     """Bottone preposto alla chiusura dell'app"""
#
#     def __init__(self, func_on_close=None, **kw):
#         """func_on_close è la funzione che viene lanciata alla pressione del bottone, di default è app.stop()"""
#         self.func_on_close = func_on_close if func_on_close else App.get_running_app().stop
#         super().__init__(**kw)
#
#     # @sound_decorator(Config["app"]["end_sound"])        # NB legare il suono alla funzione eseguita, non a on_press()
#     def on_press(self):
#         time.sleep(0.4)     # faccio passare un po' di tempo così l'app si chiude dopo la riproduzione del suono
#         self.func_on_close()


class DriveButton(DefaultButton):
    """Ogni istanza di questa classe rappresenta un disco collegato al pc, una volta che questo bottone viene premuto esso
    aggiorna il popup dei driver (DriverPopup) sulla periferica scelta"""
    def __init__(self, change_driver_popup, **kw):
        """L'attributo change_driver_popup rappresenta l'istanza da aggiornare con il nuovo disco scelto"""
        super().__init__(**kw)
        self.change_driver_popup = change_driver_popup

    def on_press(self):
        self.change_driver_popup.new_drive = "{}:\\".format(self.text)


if __name__ == "__main__":
    pass

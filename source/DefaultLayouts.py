from kivy.uix.boxlayout import BoxLayout
from DefaultWidgets import *
from AppExceptions import *


class Showable(Widget):
    def __init__(self, **kw):
        self.tmp_size_hint_x = 0
        super().__init__(**kw)

    def on_kv_post(self, base_widget):
        self.tmp_size_hint_x = self.size_hint[0]

    def show_widget(self):
        self.disabled = False
        self.opacity = 1
        self.size_hint[0] = self.tmp_size_hint_x

    def hide_widget(self):
        self.disabled = True
        self.opacity = 0
        self.size_hint[0] = 0


class DefaultLayout(BoxLayout, Showable):
    """Lo dichiaro per settare alcuni valori (padding, spacing e orientation) in DefaultLayouts.kv"""
    pass


class BorderLayout(DefaultLayout, BKGrowLayout):
    pass


class InputLayout(DefaultLayout):
    def __init__(self, f_to_launch=None, **kw):
        super().__init__(**kw)
        self.f_to_launch = f_to_launch
        self.active_widgets = []

    def update_state(self, active_widget):
        self.active_widgets.append(active_widget)
        if self.f_to_launch:
            self.f_to_launch(active_widget.get_alt_id())

    def id_active_widgets(self):
        if self.active_widgets:
            return [active_widget.get_alt_id() for active_widget in self.active_widgets]
        else:
            return []


class DynamicLayout(DefaultLayout):
    """Questo Layout contiene il comportamento per venire riempito in automatico con il metodo self.update_layout() una
    una volta che gli viene passata una lista in argomento. Parametri da valorizzare del file .kv:
        - font_size_scale: proporzione del font di ogni widget figlio;
        - color_widgets: colore di ogni widget figlio"""
    def __init__(self, font_size_chars=1, **kw):
        super().__init__(**kw)
        self.font_size_chars = font_size_chars

    def update_layout(self, field_list):
        pass


class LabelDynamicLayout(DynamicLayout):
    def update_layout(self, field_list):
        self.clear_widgets()
        for label_name in field_list:
            label = DefaultLabel(text=label_name,
                                 font_size=self.font_size_chars,
                                 background_color=self.color_widgets,
                                 border_color=[1, 1, 1, 1],
                                 color=[1, 1, 1, 1])
            self.add_widget(label)


class ButtonDynamicInputLayout(DynamicLayout, InputLayout):
    def update_layout(self, field_map):
        self.clear_widgets()
        self.active_widgets.clear()
        for field_id, field_name in field_map.items():
            btn = SelectionButton(text=field_name,
                                  font_size=self.font_size_chars,
                                  alt_id=field_id,
                                  background_color=self.color_widgets,
                                  parent_layout=self)
            self.add_widget(btn)

    def update_state(self, btn_instance):
        if btn_instance not in self.active_widgets:
            for active_widget in self.active_widgets:
                active_widget.active = False
            self.active_widgets.clear()
            self.active_widgets.append(btn_instance)
        else:
            self.active_widgets.clear()
        if self.f_to_launch:
            self.f_to_launch(btn_instance.get_alt_id())

    def id_active_widgets(self):
        if self.active_widgets:     # this class can have the list of only 0 or 1 active btn at the same time
            return self.active_widgets[0].get_alt_id()
        else:
            return ""


class TableDynamicInputLayout(DynamicLayout, InputLayout):

    def update_layout(self, records):
        """Aggiorna la tabella con la lista records, crea n righe di RowDynamicInputLayout ciascuna composta da m bottoni"""
        self.clear_widgets()
        self.height = len(records) * self.size_records
        for record in records:
            id_record = record[-1]
            record.pop()
            row = DefaultLayout(
                                font_size_chars=self.font_size_chars,
                                spacing=2,
                                padding=0,
                                height=self.size_records,
                                orientation="horizontal")
            for field in record:
                button = SelectionButton(text=str(field),
                                         font_size=self.font_size_chars,
                                         alt_id=id_record,
                                         background_color=self.color_widgets,
                                         bk_inactive=self.color_widgets,
                                         parent_layout=self)
                row.add_widget(button)
            self.add_widget(row)

    def update_state(self, btn_selected):       # multiple rows selection is allowed
        for row in self.children:
            if btn_selected in row.children:
                if row in self.active_widgets:
                    for btn in row.children:
                        btn.active = False
                    self.active_widgets.remove(row)
                else:
                    for btn in row.children:
                        btn.active = True
                    self.active_widgets.append(row)
        if self.f_to_launch:
            self.f_to_launch(btn_selected.get_alt_id())


if __name__ == "__main__":
    pass
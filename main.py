from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.properties import StringProperty

class RootWidget(BoxLayout):
    label_text = StringProperty("اضغط الزر")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"  # اتجاه العناصر عمودي

        # إضافة اللابل
        self.label = Label(text=self.label_text, font_size=30)
        self.add_widget(self.label)

        # ربط اللابل بالخاصية
        self.bind(label_text=self.update_label)

        # إضافة الزر
        button = Button(text="اضغطني", font_size=24, size_hint=(1, 0.3))
        button.bind(on_press=self.on_button_press)
        self.add_widget(button)

    def update_label(self, instance, value):
        self.label.text = value

    def on_button_press(self, *args):
        self.label_text = "تم الضغط!"

class MyApp(App):
    def build(self):
        return RootWidget()

if __name__ == "__main__":
    MyApp().run()

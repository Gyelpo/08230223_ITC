"""Part A hello-world in Kivy: a greeting and a button that counts presses."""
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

Window.size = (340, 150)


class HelloLibraryApp(App):
    title = "Hello Kivy - Tshering Gyelpo (08230223)"

    def build(self):
        self.presses = 0
        root = BoxLayout(orientation="vertical", padding=12, spacing=8)
        self.label = Label(text="Welcome to the library!")
        button = Button(text="Borrow a book")
        button.bind(on_press=self.on_press)            # event binding
        root.add_widget(self.label)
        root.add_widget(button)
        return root

    def on_press(self, _button):
        self.presses += 1
        self.label.text = f"Books borrowed: {self.presses}"


if __name__ == "__main__":
    HelloLibraryApp().run()

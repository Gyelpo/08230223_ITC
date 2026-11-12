"""Part A hello-world in Tkinter: a greeting and a button that counts presses."""
import tkinter as tk

root = tk.Tk()
root.title("Hello Tkinter - Tshering Gyelpo (08230223)")
root.geometry("340x150")

presses = tk.IntVar(value=0)                           # Tk variable instead of a global counter
label = tk.Label(root, text="Welcome to the library!")


def on_press():
    presses.set(presses.get() + 1)
    label.config(text=f"Books borrowed: {presses.get()}")


tk.Button(root, text="Borrow a book", command=on_press).pack(side="bottom", pady=12)   # callback
label.pack(expand=True)
root.mainloop()

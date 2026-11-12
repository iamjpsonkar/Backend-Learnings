import tkinter as tk
from tkinter import ttk 

def greetme():
    print("Hello World!!!")

root=tk.Tk()

greet_button=ttk.Button(root, text="Greet", command=greetme)
greet_button.pack(side="left",fill="both",expand=True) 
# side: left, top,right, bottom
# fill: x, y, both
# expand: True , False

quit_button=ttk.Button(root, text="Quit",command=root.destroy)
quit_button.pack(side="left",fill="both",expand=True)
# side: left, top,right, bottom
# fill: x, y, both
# expand: True , False

root.mainloop()

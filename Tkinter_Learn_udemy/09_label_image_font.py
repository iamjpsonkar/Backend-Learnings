import tkinter as tk
from tkinter import ttk 
from PIL import Image, ImageTk

root=tk.Tk() 
root.geometry("600x400")
root.resizable(False,False)
root.title("Widget Example")

image=Image.open("logo.png")
image=image.resize((64,64))
photo=ImageTk.PhotoImage(image)

label=ttk.Label(root,text="Google -> ", image=photo,padding=(10,10,10,10), compound="right") 
#compound: right,left,top,bottom,center

label.config(font=("Sego UI",20))
label.pack()




root.mainloop()
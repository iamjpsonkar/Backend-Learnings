import tkinter as tk 
from tkinter import ttk 

root=tk.Tk() 
root.geometry("600x400")
root.resizable(False,False)
root.title("Scrollbar Widget")

root.grid_rowconfigure(0,weight=1)
root.grid_columnconfigure(0,weight=1)

text=tk.Text(root,height=8)
text.grid(row=0,column=0,sticky="EW")
text.insert("1.0","Please Enter some Comments...")

text_scroll=ttk.Scrollbar(root,orient="vertical",command=text.yview)
text_scroll.grid(row=0,column=1,sticky="NS")
text['yscrollcommand']=text_scroll.set

# text_scroll_h=ttk.Scrollbar(root,orient="horizontal",command=text.xview)
# text_scroll_h.grid(row=1,column=0,sticky="EW")
# text['xscrollcommand']=text_scroll_h.set


root.mainloop()
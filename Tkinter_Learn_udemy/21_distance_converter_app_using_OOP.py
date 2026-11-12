import tkinter as tk



class MyFrame(tk.Frame):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        
        self.mval=tk.StringVar()
        self.fval=tk.StringVar(value="Feet shown here")
        
        self.mlabel=tk.Label(self,text="Meter: ")
        
        self.minput=tk.Entry(self,textvariable=self.mval)
        self.minput.focus()
        
        self.flabel=tk.Label(self,text="Feet: ")
        
        self.fout=tk.Label(self,textvariable=self.fval)
        
        self.calc=tk.Button(self,text="Calculate",command=self.meter2feet)
        
        
        self.mlabel.grid(row=0,column=0,sticky="W")
        self.minput.grid(row=0,column=1,sticky="EW")
        self.flabel.grid(row=1,column=0,sticky="W")
        self.fout.grid(row=1,column=1,sticky="EW")
        
        self.calc.grid(row=2,column=0,columnspan=2,sticky="EW")
        
        for child in self.winfo_children():
            child.grid_configure(padx=10,pady=10)
            
        
        
        
    def meter2feet(self,*args):
        try:
            m=float(self.mval.get())
            f=m*3.281
            self.fval.set(f"{f:.3f}")
        except:
            pass
        

class Root(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Distance Converter App")
        self.columnconfigure(0,weight=1)
        self.mframe=MyFrame(self)
        self.mframe.grid(padx=10,pady=10)
        self.bind("<Return>",self.mframe.meter2feet)
        self.bind("<KP_Enter>",self.mframe.meter2feet)
        
root=Root()
root.mainloop()
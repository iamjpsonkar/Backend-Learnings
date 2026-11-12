import tkinter as tk



class M2F(tk.Frame):
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
        
class F2M(tk.Frame):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        
        self.mval=tk.StringVar(value="Meter shown here")
        self.fval=tk.StringVar()
        
        self.flabel=tk.Label(self,text="Feet: ")
        
        self.finput=tk.Entry(self,textvariable=self.fval)
        self.finput.focus()
        
        self.mlabel=tk.Label(self,text="Meter: ")
        
        self.mout=tk.Label(self,textvariable=self.mval)
        
        self.calc=tk.Button(self,text="Calculate",command=self.feet2meter)
        
        
        self.flabel.grid(row=0,column=0,sticky="W")
        self.finput.grid(row=0,column=1,sticky="EW")
        self.mlabel.grid(row=1,column=0,sticky="W")
        self.mout.grid(row=1,column=1,sticky="EW")
        
        self.calc.grid(row=2,column=0,columnspan=2,sticky="EW")
        
        for child in self.winfo_children():
            child.grid_configure(padx=10,pady=10)
        
        
    def feet2meter(self,*args):
        try:
            f=float(self.fval.get())
            m=f/3.281
            self.mval.set(f"{m:.3f}")
        except:
            pass
        

class Root(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Distance Converter App")
        self.columnconfigure(0,weight=1)
        self.mframe=M2F(self)
        self.mframe.grid(row=0,column=0,padx=10,pady=10)
        self.fframe=F2M(self)
        self.fframe.grid(row=0,column=0,padx=10,pady=10)
        self.sbtn=tk.Button(self,text="Switch",command=self.switch)
        self.sbtn.grid(row=1,column=0,sticky="EW")
        
        self.bind("<Return>",self.mframe.meter2feet)
        self.bind("<KP_Enter>",self.mframe.meter2feet)
        
        self.WinD=[self.mframe,self.fframe]
        self.WinL=1
        
    def switch(self,*args,**kwargs):
        self.WinL=(self.WinL+1)%2
        self.WinD[self.WinL].tkraise()
root=Root()
root.mainloop()
# interface.py

# Improved UI for Bluetooth Printer App

import tkinter as tk
from tkinter import messagebox

class BluetoothPrinterApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Bluetooth Printer App")
        self.create_widgets()

    def create_widgets(self):
        tk.Label(self.master, text="Select Device:").pack(pady=10)
        self.device_var = tk.StringVar()  
        self.device_dropdown = tk.OptionMenu(self.master, self.device_var, *self.get_available_devices())
        self.device_dropdown.pack(pady=10)
         
        self.print_button = tk.Button(self.master, text="Print", command=self.print_document)
        self.print_button.pack(pady=20)

        self.status_label = tk.Label(self.master, text="Status: Ready")
        self.status_label.pack(pady=10)

    def get_available_devices(self):
        # Placeholder for device discovery logic
        return ["Printer 1", "Printer 2", "Printer 3"]

    def print_document(self):
        selected_device = self.device_var.get()
        if not selected_device:
            messagebox.showerror("Error", "No device selected!")
            return
        self.status_label.config(text="Status: Printing...")
        try:
            # Placeholder for actual print logic
            self.print_to_device(selected_device)
            self.status_label.config(text="Status: Printed Successfully")
        except Exception as e:
            self.status_label.config(text="Status: Error")
            messagebox.showerror("Printing Error", str(e))

    def print_to_device(self, device):
        # Simulated print function; replace with actual printing logic
        if device == "Printer 1":
            print("Printing to Printer 1...")
        else:
            raise Exception("Print failed due to unknown device error.")

if __name__ == '__main__':
    root = tk.Tk()
    app = BluetoothPrinterApp(root)
    root.mainloop()
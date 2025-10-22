import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import numpy as np
import json
from datetime import datetime
import os

# LSB encode/decode helpers

def str_to_bin(s):
    return ''.join([format(ord(i), '08b') for i in s])

def bin_to_str(b):
    chars = [b[i:i+8] for i in range(0, len(b), 8)]
    return ''.join([chr(int(c, 2)) for c in chars if len(c) == 8])

def embed_watermark(img, watermark):
    data = str_to_bin(watermark)
    data += '1111111111111110'  # EOF marker
    arr = np.array(img)
    flat = arr.flatten()
    if len(data) > len(flat):
        raise ValueError('Watermark data too large for this image.')
    for i in range(len(data)):
        flat[i] = (flat[i] & 0xFE) | int(data[i])
    arr = flat.reshape(arr.shape)
    return Image.fromarray(arr)

def extract_watermark(img):
    arr = np.array(img)
    flat = arr.flatten()
    bits = []
    for i in range(len(flat)):
        bits.append(str(flat[i] & 1))
    bits = ''.join(bits)
    eof = bits.find('1111111111111110')
    if eof == -1:
        return None
    data = bits[:eof]
    return bin_to_str(data)

class WatermarkApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Invisible Watermark GUI')
        self.img_path = None
        self.img = None
        self.create_widgets()

    def create_widgets(self):
        frm = tk.Frame(self.root)
        frm.pack(padx=10, pady=10)

        tk.Label(frm, text='Owner:').grid(row=0, column=0, sticky='e')
        self.owner_entry = tk.Entry(frm, width=30)
        self.owner_entry.grid(row=0, column=1)

        tk.Label(frm, text='Buyer:').grid(row=1, column=0, sticky='e')
        self.buyer_entry = tk.Entry(frm, width=30)
        self.buyer_entry.grid(row=1, column=1)

        tk.Label(frm, text='Date/Time:').grid(row=2, column=0, sticky='e')
        self.datetime_entry = tk.Entry(frm, width=30)
        self.datetime_entry.grid(row=2, column=1)
        self.datetime_entry.insert(0, datetime.now().isoformat(sep=' ', timespec='seconds'))

        tk.Button(frm, text='Select Image', command=self.select_image).grid(row=3, column=0, pady=5)
        tk.Button(frm, text='Embed Watermark', command=self.embed).grid(row=3, column=1, pady=5)
        tk.Button(frm, text='Save Image', command=self.save_image).grid(row=4, column=0, pady=5)
        tk.Button(frm, text='Scan Image', command=self.scan_image).grid(row=4, column=1, pady=5)

        self.status = tk.Label(self.root, text='', fg='blue')
        self.status.pack(pady=5)

    def select_image(self):
        path = filedialog.askopenfilename(filetypes=[('PNG Images', '*.png'), ('All Files', '*.*')])
        if path:
            self.img_path = path
            self.img = Image.open(path).convert('RGB')
            self.status.config(text=f'Loaded: {os.path.basename(path)}')

    def embed(self):
        if not self.img:
            messagebox.showerror('Error', 'No image selected.')
            return
        owner = self.owner_entry.get().strip()
        buyer = self.buyer_entry.get().strip()
        dt = self.datetime_entry.get().strip()
        if not owner:
            messagebox.showerror('Error', 'Owner is required.')
            return
        data = {
            'owner': owner,
            'buyer': buyer,
            'datetime': dt
        }
        try:
            wm_img = embed_watermark(self.img, json.dumps(data))
            self.img = wm_img
            self.status.config(text='Watermark embedded.')
            messagebox.showinfo('Success', 'Watermark embedded. Now save the image.')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def save_image(self):
        if not self.img:
            messagebox.showerror('Error', 'No image to save.')
            return
        path = filedialog.asksaveasfilename(defaultextension='.png', filetypes=[('PNG Images', '*.png')])
        if path:
            self.img.save(path)
            self.status.config(text=f'Saved: {os.path.basename(path)}')

    def scan_image(self):
        path = filedialog.askopenfilename(filetypes=[('PNG Images', '*.png'), ('All Files', '*.*')])
        if not path:
            return
        img = Image.open(path).convert('RGB')
        wm = extract_watermark(img)
        if wm:
            try:
                data = json.loads(wm)
                msg = '\n'.join([f'{k}: {v}' for k, v in data.items()])
                messagebox.showinfo('Watermark Found', msg)
            except Exception as e:
                # Show raw watermark and error
                messagebox.showwarning('Watermark Found (Raw)', f'Raw watermark: {wm}\n\nError parsing JSON: {e}')
        else:
            messagebox.showwarning('No Watermark', 'No watermark found in this image. It may not have been watermarked, or the watermark is corrupted or too large for this image.')

if __name__ == '__main__':
    root = tk.Tk()
    app = WatermarkApp(root)
    root.mainloop() 
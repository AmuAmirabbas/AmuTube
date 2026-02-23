import os
import sys
import tkinter as tk
import threading
import subprocess
from io import BytesIO
from tkinter import filedialog, messagebox
from PIL import Image
import customtkinter
import requests
from downloader import YouTubeDownloader

class YouTubeDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.geometry("680x580") 
        self.root.resizable(False, False)
        self.root.title("AmuTube - YTDL")

        # هندل کردن بستن برنامه
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        try:
            if os.path.exists("icon.ico"):
                self.root.iconbitmap("icon.ico")
        except: pass

        self.downloader = YouTubeDownloader(self)
        self.url_var = tk.StringVar()
        self.quality_var = tk.StringVar(value="720p")
        self.save_path_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads"))
        self.selected_format = tk.StringVar(value="MP4")
        self.yt = None 
        self.checkboxes = [] 

        self.create_widgets_1()

    def create_widgets_1(self):
        self.theme_switch = customtkinter.CTkSwitch(self.root, text="Dark Mode", command=self.change_theme)
        self.theme_switch.select()
        self.theme_switch.pack(pady=5, padx=10, anchor="ne")

        customtkinter.CTkLabel(self.root, text="AmuTube", font=("Arial", 26, "bold"), text_color="#FF0000").pack(pady=5)
        
        self.url_entry = customtkinter.CTkEntry(self.root, height=40, width=500, textvariable=self.url_var, placeholder_text="Paste Video or Playlist link here...")
        self.url_entry.pack(pady=10)

        self.find_button = customtkinter.CTkButton(self.root, height=45, text="Analyze & Load", fg_color="#3d3d3d", font=("Arial", 13, "bold"), width=500, command=self.on_find_click)
        self.find_button.pack(pady=5)

        self.progressbar = customtkinter.CTkProgressBar(master=self.root, mode="indeterminate", height=0)
        self.progressbar.pack(pady=10)

    def change_theme(self):
        customtkinter.set_appearance_mode("dark" if self.theme_switch.get() == 1 else "light")

    def on_find_click(self):
        if not self.url_var.get().strip():
            messagebox.showwarning("Empty URL", "Please paste a link first!")
            return
        threading.Thread(target=self.process_link, daemon=True).start()

    def process_link(self):
        self.root.after(0, self.start_spinner)
        url = self.url_var.get()
        if "playlist" in url:
            entries, title = self.downloader.fetch_playlist()
            if entries: self.root.after(0, lambda: self.create_playlist_layout(entries, title))
            else: self.root.after(0, self.handle_error)
        else:
            qualities = self.downloader.fetch_qualities()
            if qualities: self.root.after(0, lambda: self.create_video_layout(qualities))
            else: self.root.after(0, self.handle_error)

    def create_video_layout(self, qualities):
        self.hide_widgets()
        self.video_info_frame = customtkinter.CTkFrame(self.root)
        self.video_info_frame.pack(padx=10, pady=5, fill="x")

        thumb_url = self.yt.get('thumbnail')
        if thumb_url:
            try:
                res = requests.get(thumb_url, timeout=5)
                img = Image.open(BytesIO(res.content))
                self.main_thumb_img = customtkinter.CTkImage(light_image=img, size=(140, 80))
                customtkinter.CTkLabel(self.video_info_frame, image=self.main_thumb_img, text="").grid(row=0, column=0, padx=10, pady=5)
            except: pass

        title = self.yt.get('title', 'Video')[:45]
        customtkinter.CTkLabel(self.video_info_frame, text=f"Video: {title}...", justify="left", font=("Arial", 12)).grid(row=0, column=1, padx=5)

        select_frame = customtkinter.CTkFrame(self.root, fg_color="transparent")
        select_frame.pack(pady=10)
        self.quality_menu = customtkinter.CTkOptionMenu(select_frame, values=qualities, variable=self.quality_var, width=120)
        self.quality_menu.grid(row=0, column=0, padx=5)
        self.format_menu = customtkinter.CTkOptionMenu(select_frame, values=["MP4", "MP3", "MKV"], variable=self.selected_format, width=100)
        self.format_menu.grid(row=0, column=1, padx=5)

        self.save_button = customtkinter.CTkButton(self.root, textvariable=self.save_path_var, command=self.open_folder_selector, fg_color="#3d3d3d", width=420)
        self.save_button.pack(pady=5)

        self.button_frame = customtkinter.CTkFrame(self.root, fg_color="transparent")
        self.button_frame.pack(pady=15)
        self.download_button = customtkinter.CTkButton(self.button_frame, text="Start Download", fg_color="#FF0000", hover_color="#CC0000", font=("Arial", 14, "bold"), width=170, command=self.downloader.download)
        self.download_button.grid(row=0, column=0, padx=5)
        
        self.open_folder_btn = customtkinter.CTkButton(self.button_frame, text="Open Folder 📂", command=self.open_saved_path, fg_color="#3498db", width=170)
        
        self.finish_label = customtkinter.CTkLabel(self.root, text="")
        self.finish_label.pack()
        self.update_layout()

    def create_playlist_layout(self, entries, title):
        self.hide_widgets()
        customtkinter.CTkLabel(self.root, text=f"Playlist: {title}", text_color="#FF0000", font=("Arial", 14, "bold")).pack(pady=5)
        
        self.scroll_frame = customtkinter.CTkScrollableFrame(self.root, width=580, height=200)
        self.scroll_frame.pack(pady=5)
        
        self.checkboxes = []
        for entry in entries:
            var = tk.IntVar(value=1) 
            cb = customtkinter.CTkCheckBox(self.scroll_frame, text=entry['title'][:70], variable=var, font=("Arial", 11))
            cb.pack(anchor="w", padx=10, pady=3)
            self.checkboxes.append(var)

        select_frame = customtkinter.CTkFrame(self.root, fg_color="transparent")
        select_frame.pack(pady=5)
        self.quality_menu = customtkinter.CTkOptionMenu(select_frame, values=["1080p", "720p", "480p", "360p"], variable=self.quality_var, width=120)
        self.quality_menu.grid(row=0, column=0, padx=5)
        self.format_menu = customtkinter.CTkOptionMenu(select_frame, values=["MP4", "MP3", "MKV"], variable=self.selected_format, width=100)
        self.format_menu.grid(row=0, column=1, padx=5)

        self.save_button = customtkinter.CTkButton(self.root, textvariable=self.save_path_var, command=self.open_folder_selector, fg_color="#3d3d3d", width=420)
        self.save_button.pack(pady=5)

        self.button_frame = customtkinter.CTkFrame(self.root, fg_color="transparent")
        self.button_frame.pack(pady=10)
        self.download_button = customtkinter.CTkButton(self.button_frame, text="Download Selected", fg_color="#FF0000", hover_color="#CC0000", font=("Arial", 14, "bold"), width=170, command=self.start_playlist_download)
        self.download_button.grid(row=0, column=0, padx=5)
        self.open_folder_btn = customtkinter.CTkButton(self.button_frame, text="Open Folder 📂", command=self.open_saved_path, fg_color="#3498db", width=170)
        
        self.finish_label = customtkinter.CTkLabel(self.root, text="")
        self.finish_label.pack()
        self.update_layout()

    def start_playlist_download(self):
        selected_indices = [i for i, var in enumerate(self.checkboxes) if var.get() == 1]
        if not selected_indices:
            messagebox.showwarning("Selection", "Select at least one video!")
            return
        self.downloader.download(selected_indices)

    def show_open_folder_button(self):
        self.open_folder_btn.grid(row=0, column=1, padx=5)

    def open_saved_path(self):
        path = self.save_path_var.get()
        if os.path.exists(path):
            if sys.platform == "win32": os.startfile(path)
            else: subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", path])

    def open_folder_selector(self):
        path = filedialog.askdirectory()
        if path: self.save_path_var.set(path)

    def start_spinner(self):
        self.progressbar.configure(height=10); self.progressbar.start()

    def handle_error(self):
        self.progressbar.stop(); self.progressbar.configure(height=0)
        messagebox.showerror("Error", "Invalid or Private Link!")

    def hide_widgets(self):
        for widget in self.root.winfo_children():
            if widget not in [self.url_entry, self.find_button, self.progressbar, self.theme_switch]:
                widget.pack_forget()

    def update_layout(self):
        self.root.update_idletasks()
        self.progressbar.stop(); self.progressbar.configure(height=0)

    def on_closing(self):
        self.root.destroy()
        sys.exit()

if __name__ == "__main__":
    root = customtkinter.CTk()
    app = YouTubeDownloaderApp(root)
    root.mainloop()
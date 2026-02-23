import threading
import os
import re
import sys
import yt_dlp

class YouTubeDownloader:
    def __init__(self, main_app):
        self.main_app = main_app
        self.playlist_entries = [] 

    def fetch_qualities(self):
        """دریافت کیفیت‌های موجود برای یک ویدیو تکی"""
        url = self.main_app.url_var.get()
        try:
            ydl_opts = {'quiet': True, 'no_warnings': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                self.main_app.yt = info 
                formats = info.get('formats', [])
                qualities = set()
                for f in formats:
                    if f.get('vcodec') != 'none' and f.get('height'):
                        qualities.add(f"{f['height']}p")
                return sorted(list(qualities), key=lambda x: int(x[:-1]), reverse=True)
        except Exception as e:
            print(f"Error fetching qualities: {e}")
            return None

    def fetch_playlist(self):
        """دریافت لیست ویدیوهای داخل یک پلی‌لیست"""
        url = self.main_app.url_var.get()
        try:
            ydl_opts = {'extract_flat': True, 'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info:
                    self.playlist_entries = [{'title': x.get('title'), 'url': x.get('url')} for x in info['entries']]
                    return self.playlist_entries, info.get('title', 'Playlist')
        except Exception as e:
            print(f"Playlist Error: {e}")
            return None, None

    def sanitize_title(self, title):
        """تمیز کردن نام فایل (حذف ایموجی و متون اضافی)"""
        title = re.sub(r'\([^)]*\)|\[[^\]]*\]', '', title)
        title = re.sub(r'[^\w\s\u0600-\u06FF-]', '', title)
        title = " ".join(title.split()).strip()
        return title[:50] if title else "Downloaded_File"

    def download(self, selected_indices=None):
        """شروع عملیات دانلود در یک رشته (Thread) مجزا"""
        threading.Thread(target=self.download_in_background, args=(selected_indices,), daemon=True).start()

    def download_in_background(self, selected_indices):
        import sys # اطمینان از ایمپورت شدن sys
        save_path = self.main_app.save_path_var.get()
        selected_format = self.main_app.selected_format.get().lower()
        
        # ۱. پیدا کردن مسیر صحیح FFmpeg در حالت EXE یا کد معمولی
        if getattr(sys, 'frozen', False):
            # اگر برنامه EXE شده باشد، فایل‌ها در پوشه موقت sys._MEIPASS هستند
            ffmpeg_base = os.path.join(sys._MEIPASS, 'ffmpeg', 'bin')
        else:
            # اگر در حالت اسکریپت پایتون اجرا شود
            ffmpeg_base = os.path.join(os.getcwd(), 'ffmpeg', 'bin')

        # فیلتر کردن لینک‌ها بر اساس تیک‌های کاربر
        if selected_indices is not None:
            urls_to_download = [self.playlist_entries[i]['url'] for i in selected_indices]
        else:
            urls_to_download = [self.main_app.url_var.get()]

        for i, url in enumerate(urls_to_download):
            try:
                with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                    clean_title = self.sanitize_title(info.get('title', 'video'))
            except:
                clean_title = f"video_{i+1}"

            current_status = f"Downloading {i+1}/{len(urls_to_download)}..."
            self.main_app.root.after(0, lambda s=current_status: self.main_app.finish_label.configure(text=s, text_color="yellow"))
            
            # ۲. تنظیمات اصلی با مسیر اصلاح شده FFmpeg
            ydl_opts = {
                'outtmpl': os.path.join(save_path, f'{clean_title}.%(ext)s'),
                'progress_hooks': [self.progress_hook],
                'ffmpeg_location': ffmpeg_base, # استفاده از مسیر هوشمند
                'noplaylist': True # برای جلوگیری از دانلود کل پلی‌لیست در هر لینک
            }

            if selected_format == "mp3":
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }]
                })
            else:
                res = self.main_app.quality_var.get().replace('p', '') if self.main_app.quality_var.get() else '720'
                ydl_opts['format'] = f'bestvideo[height<={res}]+bestaudio/best'
                ydl_opts['merge_output_format'] = selected_format

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except Exception as e:
                print(f"Error on {url}: {e}")

        self.main_app.root.after(0, self.on_download_finished)

    def on_download_finished(self):
        self.main_app.finish_label.configure(text="All Downloads Complete! ✨", text_color="#2ecc71")
        self.main_app.root.after(0, self.main_app.show_open_folder_button)

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            if total > 0:
                percent = (downloaded / total) * 100
                p_text = f"Progress: {percent:.1f}%"
                self.main_app.root.after(0, lambda: self.main_app.finish_label.configure(text=p_text))
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton, MDIconButton, MDFloatingActionButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list import MDList, TwoLineAvatarListItem, ImageLeftWidget
from kivymd.uix.tab import MDTabs, MDTabsBase
from kivymd.uix.floatlayout import MDFloatLayout
from kivy.core.window import Window
from kivy.utils import platform
from kivy.core.text import LabelBase
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
import arabic_reshaper
from bidi.algorithm import get_display
import yt_dlp
import re
import os
import threading
import requests
import sys
import tempfile
import json
import subprocess
from PIL import Image
from io import BytesIO
import sqlite3
from datetime import datetime

# Register Arial font
LabelBase.register(name='Arial',
                  fn_regular='C:\\Windows\\Fonts\\arial.ttf')

def reshape_arabic(text):
    try:
        reshaped_text = arabic_reshaper.reshape(text)[::-1]  # Reverse the text
        return reshaped_text
    except:
        return text

class ArabicLabel(MDLabel):
    def __init__(self, **kwargs):
        if 'text' in kwargs:
            kwargs['text'] = reshape_arabic(kwargs['text'])
        super().__init__(**kwargs)
        self.font_name = 'Arial'
        self.font_size = '18sp'

class EnglishLabel(MDLabel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_name = 'Arial'
        self.font_size = '18sp'
        self.halign = 'left'  # Left alignment for English text

class ArabicButton(MDRaisedButton):
    def __init__(self, **kwargs):
        if 'text' in kwargs:
            kwargs['text'] = reshape_arabic(kwargs['text'])
        super().__init__(**kwargs)
        self.font_name = 'Arial'
        self.font_size = '18sp'

class ContextMenu(MDDialog):
    def __init__(self, text_field, **kwargs):
        super().__init__(
            title="Options",
            type="simple",
            items=[
                MDFlatButton(
                    text="Paste",
                    on_release=lambda x: self.paste(text_field)
                )
            ],
            **kwargs
        )
        self.text_field = text_field
        Window.bind(on_touch_down=self.on_touch_down)
    
    def on_touch_down(self, instance, touch):
        # If touch is outside the dialog, dismiss it
        if not self.ids.container.collide_point(*touch.pos):
            self.dismiss()
            Window.unbind(on_touch_down=self.on_touch_down)
            return True
        return False
    
    def paste(self, text_field):
        from kivy.core.clipboard import Clipboard
        text_field.text = Clipboard.paste()
        self.dismiss()
        Window.unbind(on_touch_down=self.on_touch_down)

class EnglishTextField(MDTextField):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_name = 'Arial'
        self.font_size = '18sp'
        self.halign = 'left'  # Left alignment for English text

    def paste_text(self, *args):
        from kivy.core.clipboard import Clipboard
        self.text = Clipboard.paste()

class ArabicTextField(MDTextField):
    def __init__(self, **kwargs):
        if 'hint_text' in kwargs:
            kwargs['hint_text'] = reshape_arabic(kwargs['hint_text'])
        if 'helper_text' in kwargs:
            kwargs['helper_text'] = reshape_arabic(kwargs['helper_text'])
        super().__init__(**kwargs)
        self.font_name = 'Arial'
        self.font_size = '18sp'

class Tab(MDFloatLayout, MDTabsBase):
    pass

class VideoHistoryItem(TwoLineAvatarListItem):
    video_path = StringProperty()
    
    def __init__(self, **kwargs):
        if 'text' in kwargs:
            kwargs['text'] = reshape_arabic(kwargs['text'])
        super().__init__(**kwargs)
        
        # Add delete button
        delete_button = MDIconButton(
            icon="delete",
            pos_hint={'right': 1, 'center_y': 0.5},
            on_release=self.show_delete_dialog
        )
        self.add_widget(delete_button)
    
    def show_delete_dialog(self, *args):
        content = MDBoxLayout(
            orientation='vertical',
            spacing=15,
            padding=[20, 20, 20, 20],
            size_hint_y=None,
            height=dp(150)
        )
        
        title = MDLabel(
            text="Choose deletion method",
            theme_text_color="Secondary",
            font_style="H6",
            halign="center",
            size_hint_y=None,
            height=dp(50)
        )
        content.add_widget(title)
        
        buttons_layout = MDBoxLayout(
            orientation='vertical',
            spacing=10,
            size_hint_y=None,
            height=dp(100)
        )
        
        remove_history_btn = MDRaisedButton(
            text="Remove from History",
            md_bg_color=self.theme_cls.primary_color,
            size_hint=(1, None),
            height=dp(40),
            on_release=lambda x: self.delete_video(False)
        )
        
        delete_file_btn = MDRaisedButton(
            text="Delete File and History",
            md_bg_color=self.theme_cls.primary_color,
            size_hint=(1, None),
            height=dp(40),
            on_release=lambda x: self.delete_video(True)
        )
        
        buttons_layout.add_widget(remove_history_btn)
        buttons_layout.add_widget(delete_file_btn)
        content.add_widget(buttons_layout)
        
        self.delete_dialog = MDDialog(
            title="Delete Video",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(
                    text="Cancel",
                    theme_text_color="Custom",
                    text_color=self.theme_cls.primary_color,
                    on_release=lambda x: self.delete_dialog.dismiss()
                )
            ],
            size_hint=(0.8, None),
            width=dp(300)
        )
        self.delete_dialog.open()
    
    def delete_video(self, delete_file=False):
        app = MDApp.get_running_app()
        
        # Delete from database
        conn = sqlite3.connect(app.db_path)
        c = conn.cursor()
        
        # Get thumbnail path before deleting from database
        c.execute("SELECT thumbnail FROM videos WHERE path=?", (self.video_path,))
        result = c.fetchone()
        thumbnail_path = result[0] if result else None
        
        # Delete from database
        c.execute("DELETE FROM videos WHERE path=?", (self.video_path,))
        conn.commit()
        conn.close()
        
        # Delete the actual video file if requested
        if delete_file and os.path.exists(self.video_path):
            try:
                os.remove(self.video_path)
            except Exception as e:
                print(f"Error deleting video file: {e}")
        
        # Delete thumbnail if it exists
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                os.remove(thumbnail_path)
            except Exception as e:
                print(f"Error deleting thumbnail: {e}")
        
        # Close the dialog
        self.delete_dialog.dismiss()
        
        # Update the history list
        app.update_history()
    
    def on_release(self):
        # Open video with default player
        if platform == "win":
            os.startfile(self.video_path)
        elif platform == "linux":
            subprocess.Popen(["xdg-open", self.video_path])
        elif platform == "macosx":
            subprocess.Popen(["open", self.video_path])
        elif platform == "android":
            from jnius import autoclass
            Intent = autoclass('android.content.Intent')
            Uri = autoclass('android.net.Uri')
            File = autoclass('java.io.File')
            
            file = File(self.video_path)
            uri = Uri.fromFile(file)
            intent = Intent()
            intent.setAction(Intent.ACTION_VIEW)
            intent.setDataAndType(uri, "video/*")
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            currentActivity = PythonActivity.mActivity
            currentActivity.startActivity(intent)

class DownloaderApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'video_history.db')
        self.setup_database()
        
    def setup_database(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS videos
                    (title TEXT, path TEXT, thumbnail TEXT, date TEXT)''')
        conn.commit()
        conn.close()
    
    def add_to_history(self, title, path, thumbnail_url):
        try:
            # Download and save thumbnail
            response = requests.get(thumbnail_url)
            if response.status_code == 200:
                # Resize thumbnail
                img = Image.open(BytesIO(response.content))
                img.thumbnail((100, 100))
                
                # Save thumbnail
                thumbnail_dir = os.path.join(os.path.dirname(path), 'thumbnails')
                os.makedirs(thumbnail_dir, exist_ok=True)
                thumbnail_path = os.path.join(thumbnail_dir, f"{os.path.basename(path)}.jpg")
                img.save(thumbnail_path)
                
                # Save to database with reshaped Arabic title
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()
                c.execute("INSERT INTO videos VALUES (?, ?, ?, ?)",
                         (reshape_arabic(title), path, thumbnail_path, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                conn.close()
                
                # Update history tab
                Clock.schedule_once(lambda dt: self.update_history())
        except Exception as e:
            print(f"Error adding to history: {e}")
    
    def update_history(self, *args):
        if not hasattr(self, 'history_list'):
            return
            
        # Clear current list
        self.history_list.clear_widgets()
        
        # Get videos from database
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT title, path, thumbnail, date FROM videos ORDER BY date DESC")
        videos = c.fetchall()
        conn.close()
        
        # Create a box layout for history items
        history_box = MDBoxLayout(
            orientation='vertical',
            spacing=10,
            size_hint_y=None
        )
        history_box.bind(minimum_height=history_box.setter('height'))
        
        # Add videos to list
        for title, path, thumbnail, date in videos:
            if os.path.exists(path):  # Only show if video still exists
                item = VideoHistoryItem(
                    text=title,
                    secondary_text=date,
                    video_path=path,
                    size_hint_y=None,
                    height=72  # Standard height for two-line items
                )
                if thumbnail and os.path.exists(thumbnail):
                    item.add_widget(ImageLeftWidget(source=thumbnail))
                history_box.add_widget(item)
        
        # Clear and update the history list
        self.history_list.clear_widgets()
        self.history_list.add_widget(history_box)

    def download_video(self, format_info):
        try:
            url = self.url_input.text.strip()
            self.status_label.text = "Starting download..."
            
            # Set download options
            download_path = os.path.join(os.path.expanduser("~"), "Downloads")
            if not os.path.exists(download_path):
                os.makedirs(download_path)

            is_facebook = 'facebook.com' in url or 'fb.watch' in url
            
            # Get video info for thumbnail
            if not self.video_info:
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    self.video_info = ydl.extract_info(url, download=False)
            
            # Get thumbnail URL
            thumbnail_url = self.video_info.get('thumbnail', '')
            title = self.video_info.get('title', 'Unknown')
            
            # Set download options
            ydl_opts = {
                'format': 'best' if is_facebook else format_info['format_id'],
                'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
                'progress_hooks': [self.download_progress_hook],
            }

            if is_facebook:
                cookie_file = self.get_facebook_cookies()
                if cookie_file:
                    ydl_opts.update({
                        'cookiefile': cookie_file
                    })

            # Download the video
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_path = ydl.prepare_filename(info)
                
                # Add to history
                self.add_to_history(title, video_path, thumbnail_url)

        except Exception as e:
            error_msg = str(e)
            if is_facebook and "requested format not available" in error_msg.lower():
                self.status_label.text = "Error: Cannot download this Facebook video.\nVideo might be private or restricted"
            else:
                self.status_label.text = f"Download failed: {error_msg}"

    def download_progress_hook(self, d):
        if d['status'] == 'downloading':
            try:
                percent = d['_percent_str']
                speed = d.get('_speed_str', 'N/A')
                eta = d.get('_eta_str', 'N/A')
                self.status_label.text = (
                    f"Downloading: {percent}\n"
                    f"Speed: {speed}\n"
                    f"Time remaining: {eta}"
                )
            except:
                pass
        elif d['status'] == 'finished':
            self.status_label.text = "Download complete! Check your Downloads folder"
        elif d['status'] == 'error':
            self.status_label.text = "Download error"

    def exit_app(self, *args):
        sys.exit(0)

    def reset_app(self, *args):
        self.url_input.text = ""
        self.info_label.text = ""
        self.status_label.text = ""
        self.video_info = None
        if hasattr(self, 'quality_dialog') and self.quality_dialog:
            self.quality_dialog.dismiss()
            self.quality_dialog = None

    def format_size(self, size_bytes):
        if size_bytes is None:
            return "Unknown"
        size = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0

    def format_duration(self, duration):
        if duration is None:
            return "Unknown"
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{int(hours)}:{int(minutes):02d}:{int(seconds):02d}"
        else:
            return f"{int(minutes):02d}:{int(seconds):02d}"

    def get_facebook_cookies(self):
        try:
            # Create a temporary file for cookies
            cookie_file = os.path.join(tempfile.gettempdir(), 'fb_cookies.txt')
            
            # Import browser_cookie3 here to avoid potential import errors
            import browser_cookie3
            
            # Get cookies from Chrome browser
            cookies = browser_cookie3.chrome(domain_name='.facebook.com')
            
            # Write cookies to file
            with open(cookie_file, 'w', encoding='utf-8') as f:
                for cookie in cookies:
                    secure = "TRUE" if cookie.secure else "FALSE"
                    f.write(f".facebook.com\tTRUE\t{cookie.path}\t{secure}\t"
                           f"{int(cookie.expires) if cookie.expires else 0}\t{cookie.name}\t{cookie.value}\n")
            
            return cookie_file
        except Exception as e:
            print(f"Error getting Facebook cookies: {e}")
            return None

    def get_video_info(self, *args):
        threading.Thread(target=self._get_video_info).start()

    def _get_video_info(self):
        url = self.url_input.text.strip()
        if not url:
            self.info_label.text = "Please enter a video URL"
            return

        try:
            self.info_label.text = "Getting video information..."
            
            # Special handling for Facebook videos
            is_facebook = 'facebook.com' in url or 'fb.watch' in url
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'format': 'best' if is_facebook else None,
            }
            
            if is_facebook:
                cookie_file = self.get_facebook_cookies()
                if cookie_file:
                    ydl_opts.update({
                        'cookiefile': cookie_file
                    })
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    self.video_info = ydl.extract_info(url, download=False)
                except Exception as e:
                    if is_facebook:
                        self.info_label.text = "Error: Cannot access Facebook video.\nMake sure you're logged in to Chrome"
                    else:
                        self.info_label.text = f"Error getting video info: {str(e)}"
                    return
                
                # Get available formats
                self.formats = []
                
                if is_facebook:
                    # For Facebook, just use the best format
                    best_format = None
                    for f in self.video_info.get('formats', []):
                        if f.get('format_id') == self.video_info.get('format_id'):
                            best_format = f
                            break
                    if best_format:
                        self.formats.append(best_format)
                else:
                    # For other platforms (like YouTube)
                    for f in self.video_info.get('formats', []):
                        if f.get('vcodec', 'none') != 'none' and f.get('acodec', 'none') != 'none':
                            self.formats.append(f)

                if not self.formats:
                    if is_facebook:
                        direct_url = self.video_info.get('url')
                        if direct_url:
                            self.formats.append({
                                'format_id': 'best',
                                'url': direct_url,
                                'ext': self.video_info.get('ext', 'mp4'),
                                'format': 'Best Quality'
                            })
                        else:
                            raise Exception("Cannot find video URL. Make sure you can watch the video in browser")
                    else:
                        raise Exception("No valid formats found. Video might be private or restricted")

                title = self.video_info.get('title', 'Unknown')
                duration = self.format_duration(self.video_info.get('duration'))
                
                if is_facebook:
                    size_text = "Size will be determined during download"
                else:
                    size_text = f"Size (best quality): {self.format_size(self.formats[-1].get('filesize'))}"
                
                self.info_label.text = (
                    f"Title: {title}\n"
                    f"Duration: {duration}\n"
                    f"{size_text}\n"
                    f"Available Qualities: {len(self.formats)}"
                )
        except Exception as e:
            self.info_label.text = f"Error: {str(e)}"

    def show_quality_dialog(self, *args):
        if not self.video_info:
            self.status_label.text = "Please get video information first"
            return

        if not hasattr(self, 'quality_dialog') or not self.quality_dialog:
            dialog_items = []
            for f in self.formats:
                height = f.get('height', 'Unknown')
                size = self.format_size(f.get('filesize'))
                
                # Create a custom button for each quality
                btn = MDFlatButton(
                    text=f"{height}p - {size}",
                    size_hint=(0.8, None),
                    height=40,
                    pos_hint={'center_x': 0.5},
                    on_release=lambda x, f=f: self.handle_quality_selection(f)
                )
                dialog_items.append(btn)

            # Create a vertical box layout for the buttons
            content = MDBoxLayout(
                orientation='vertical',
                spacing=10,
                padding=20,
                adaptive_height=True
            )
            
            # Add all quality buttons to the layout
            for item in dialog_items:
                content.add_widget(item)

            self.quality_dialog = MDDialog(
                title="Select Quality",
                type="custom",
                content_cls=content,
                buttons=[
                    MDFlatButton(
                        text="Cancel",
                        theme_text_color="Custom",
                        text_color=self.theme_cls.primary_color,
                        on_release=lambda x: self.quality_dialog.dismiss()
                    )
                ],
            )
        self.quality_dialog.open()

    def handle_quality_selection(self, format_info):
        if hasattr(self, 'quality_dialog') and self.quality_dialog:
            self.quality_dialog.dismiss()
        threading.Thread(target=lambda: self.download_video(format_info)).start()

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        Window.size = (400, 600)
        
        screen = MDScreen()
        
        # Create tabs
        self.tabs = MDTabs(
            pos_hint={"center_x": .5, "center_y": .5},
            size_hint=(1, 1)
        )
        
        # Download tab
        download_tab = Tab(title="Download")
        
        # Main layout for download tab
        main_layout = MDBoxLayout(
            orientation='vertical',
            spacing=10,
            padding=[20, 20, 20, 20],
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            size_hint=(1, 1)
        )
        
        # Title with developer info
        title_card = MDCard(
            orientation='vertical',
            size_hint=(1, None),
            height=120,
            padding=15,
            elevation=4,
            radius=[20, 20, 20, 20],
            md_bg_color=self.theme_cls.primary_color
        )
        
        title = MDLabel(
            text="Video Downloader",
            halign="center",
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
            font_style="H5",
            bold=True
        )
        title_card.add_widget(title)
        
        dev_info = MDLabel(
            text="Mhamed Magdy\n01551106611 - 01014239656",
            halign="center",
            theme_text_color="Custom",
            text_color=(1, 1, 1, 0.9),
            font_style="Caption"
        )
        title_card.add_widget(dev_info)
        
        main_layout.add_widget(title_card)
        
        # Main card
        card = MDCard(
            orientation='vertical',
            padding=20,
            size_hint=(1, 0.8),
            elevation=4,
            radius=[20, 20, 20, 20],
            md_bg_color=(1, 1, 1, 1)
        )
        
        # Reset button
        reset_button = MDIconButton(
            icon="refresh",
            pos_hint={'right': 1},
            on_release=self.reset_app
        )
        card.add_widget(reset_button)
        
        # URL input layout
        url_layout = MDBoxLayout(
            orientation='horizontal',
            spacing=10,
            size_hint=(1, None),
            height=dp(48)
        )
        
        self.url_input = EnglishTextField(
            hint_text="URL",
            helper_text="youtube.com, facebook.com, fb.watch, ...",
            helper_text_mode="on_focus",
            size_hint_x=0.85,
            multiline=False,
            hint_text_color_normal=(0, 0, 0, 0.7),
            text_color_normal=(0, 0, 0, 1),
            line_color_normal=(0, 0, 0, 0.5)
        )
        url_layout.add_widget(self.url_input)
        
        # Paste button
        paste_button = MDIconButton(
            icon="content-paste",
            on_release=self.url_input.paste_text,
            size_hint_x=0.15
        )
        url_layout.add_widget(paste_button)
        
        card.add_widget(url_layout)
        
        # Info button
        info_button = MDFlatButton(
            text="Get Video Info",
            pos_hint={'center_x': 0.5},
            size_hint_x=0.8,
            height=50,
            padding=10,
            md_bg_color=self.theme_cls.primary_color,
            text_color=(1, 1, 1, 1),
            on_release=self.get_video_info
        )
        card.add_widget(info_button)
        
        # Video info label
        self.info_label = MDLabel(
            text="",
            halign="center",
            theme_text_color="Custom",
            text_color=(0, 0, 0, 0.7),
            size_hint_y=None,
            height=150
        )
        card.add_widget(self.info_label)
        
        download_button = MDFlatButton(
            text="Download Video",
            pos_hint={'center_x': 0.5},
            size_hint_x=0.8,
            height=50,
            padding=10,
            md_bg_color=self.theme_cls.primary_color,
            text_color=(1, 1, 1, 1),
            on_release=self.show_quality_dialog
        )
        card.add_widget(download_button)
        
        self.status_label = MDLabel(
            text="",
            halign="center",
            theme_text_color="Custom",
            text_color=(0, 0, 0, 0.7),
            size_hint_y=None,
            height=100
        )
        card.add_widget(self.status_label)
        
        main_layout.add_widget(card)
        download_tab.add_widget(main_layout)
        
        # History tab
        history_tab = Tab(title="History")
        history_layout = MDBoxLayout(
            orientation='vertical',
            spacing=10,
            padding=[10, 10, 10, 10]
        )
        
        # Create scrollable list for history
        scroll = ScrollView(
            size_hint=(1, 1),
            do_scroll_x=False
        )
        
        self.history_list = MDList(
            spacing=2,
            padding=[0, 0, 0, 0]
        )
        
        scroll.add_widget(self.history_list)
        history_layout.add_widget(scroll)
        history_tab.add_widget(history_layout)
        
        # Add tabs
        self.tabs.add_widget(download_tab)
        self.tabs.add_widget(history_tab)
        screen.add_widget(self.tabs)
        
        # Add exit button
        exit_button = MDIconButton(
            icon="close",
            pos_hint={'right': 0.98, 'top': 0.98},
            on_release=self.exit_app
        )
        screen.add_widget(exit_button)
        
        self.video_info = None
        self.quality_dialog = None
        
        # Update history
        self.update_history()
        
        return screen

if __name__ == '__main__':
    if platform == 'android':
        from android.permissions import request_permissions, Permission
        request_permissions([Permission.WRITE_EXTERNAL_STORAGE])
    
    Window.softinput_mode = "below_target"
    DownloaderApp().run()

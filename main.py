#!/usr/bin/env python3
import os
import re
import sys
import time
import json
import glob
import shutil
from pathlib import Path
from typing import Optional, List
import threading
from functools import partial

# -- Kivy Imports --
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import StringProperty, ObjectProperty, BooleanProperty, ListProperty, NumericProperty
from kivy.clock import mainthread, Clock
from kivy.storage.jsonstore import JsonStore

# -- Plyer for Android features --
from kivy.utils import platform
try:
    from plyer import filechooser, notification
    # On Android, we need to request permissions
    if platform == 'android':
        from android.permissions import request_permissions, Permission
except ImportError:
    # Mock classes for desktop testing
    class MockFileChooser:
        def open_file(self, on_selection=None, multiple=True):
            print("PLYER: FileChooser not available on this platform.")
            # Return a dummy list for testing
            if on_selection:
                on_selection(["/fake/path/doc1.pdf", "/fake/path/doc2.pdf"])
    filechooser = MockFileChooser()

    class MockNotification:
        def notify(self, title, message, app_name, ticker, toast=False, app_icon=''):
             print(f"PLYER-NOTIFY: [{title}] {message}")
    notification = MockNotification()

# -- Project Imports for Core Logic --
from PIL import Image, ImageOps, ImageEnhance
from pdf2image import convert_from_path
import pandas as pd
import google.generativeai as genai

# ======================================================
# KIVY UI DEFINITION (KV Language as a String)
# ======================================================

KV_STRING = """
#:kivy 2.1.0

<ListItemWithCheckbox@BoxLayout>:
    file_path: ''
    file_name: ''
    size_hint_y: None
    height: dp(50)
    spacing: dp(10)

    CheckBox:
        id: checkbox
        size_hint_x: 0.15

    Label:
        text: root.file_name
        halign: 'left'
        valign: 'middle'
        text_size: self.size

<FileBrowserScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(10)
        spacing: dp(10)

        ActionBar:
            ActionView:
                ActionPrevious:
                    title: 'PDF to Excel Extractor'
                    with_previous: False
                ActionOverflow:
                ActionButton:
                    text: 'Settings'
                    on_release: app.root.current = 'settings'

        Label:
            id: status_label
            size_hint_y: None
            height: dp(40)
            text: "Welcome! Add PDF files to continue."

        ScrollView:
            GridLayout:
                id: file_list_grid
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(5)

        BoxLayout:
            size_hint_y: None
            height: dp(50)
            spacing: dp(10)
            
            Button:
                text: "Refresh List"
                on_release: root.refresh_file_list()

            Button:
                text: "Select from Device"
                on_release: root.select_from_device()
        
        Button:
            text: "Start Processing Selected Files"
            size_hint_y: None
            height: dp(60)
            font_size: '18sp'
            background_color: (0.2, 0.6, 0.2, 1)
            on_release: root.start_processing()


<ProcessingScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(10)
        spacing: dp(10)

        ActionBar:
            ActionView:
                ActionPrevious:
                    title: 'Processing...'
                    with_previous: False
        
        BoxLayout:
            size_hint_y: None
            height: dp(50)
            orientation: 'vertical'
            
            Label:
                id: progress_label
                text: root.progress_message
                font_size: '16sp'
                
            ProgressBar:
                id: progress_bar
                value: root.progress_value
                max: 100
        
        ScrollView:
            Label:
                id: log_label
                text: root.log_text
                font_size: '14sp'
                size_hint_y: None
                height: self.texture_size[1]
                text_size: self.width, None
                padding: dp(10)
                halign: 'left'
                valign: 'top'
                markup: True
        
        BoxLayout:
            size_hint_y: None
            height: dp(60)
            spacing: dp(10)

            Button:
                text: "Stop"
                background_color: (0.8, 0.2, 0.2, 1)
                on_release: root.stop_processing()
                disabled: not app.processing
            
            Button:
                text: "Back to Main Screen"
                on_release: root.go_to_main_screen()
                disabled: app.processing

<SettingsScreen>:
    api_key_input: api_key_field
    BoxLayout:
        orientation: 'vertical'
        padding: 20
        spacing: 20
        ActionBar:
            ActionView:
                ActionPrevious:
                    title: 'Settings'
                    on_release: app.root.current = 'file_browser'
        Label:
            text: 'Enter your Google Generative AI API Key'
            font_size: '18sp'
        TextInput:
            id: api_key_field
            hint_text: 'AIzaSy...'
            multiline: False
            password: True
        Button:
            text: 'Save and Return'
            on_release: root.save_settings()
        Label:

"""

# ======================================================
# CONSTANTS
# ======================================================
MODEL_NAME = "gemini-1.5-pro"
RATE_LIMIT_SLEEP = 3
MAX_RETRIES = 3
BACKOFF_FACTOR = 1.5
DPI = 300
APP_INPUT_FOLDER_NAME = "PDF_to_Excel_Input"
CHECKPOINT_FILE = "checkpoint.json"

# ======================================================
# Core Logic (Modified for progress reporting)
# ======================================================
class CoreProcessor:
    def __init__(self, app_instance):
        self.app = app_instance
        self.client = None
        self.running = False

    def log(self, msg: str):
        self.app.update_log(msg)
    
    def update_progress(self, percent, message):
        self.app.update_progress(percent, message)

    def retry_loop(self, func, *args, **kwargs):
        retries = 0
        sleep_time = RATE_LIMIT_SLEEP
        while retries < MAX_RETRIES:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if "RATE_LIMIT_EXCEEDED" in str(e) or "429" in str(e):
                    retries += 1
                    self.log(f"Rate limit hit. Retrying in {sleep_time:.1f}s... (Attempt {retries}/{MAX_RETRIES})")
                    time.sleep(sleep_time)
                    sleep_time *= BACKOFF_FACTOR
                else:
                    self.log(f"[ERROR] An unexpected error occurred: {e}")
                    raise  # Re-raise other errors
        self.log("Max retries exceeded for rate limiting. Aborting.")
        return None

    def init_genai_client(self, api_key):
        try:
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(MODEL_NAME)
            self.log("Generative AI client initialized successfully.")
            return True
        except Exception as e:
            self.log(f"[ERROR] Failed to initialize AI client: {e}")
            self.log("Please check your API key in Settings.")
            return False

    def process_single_pdf(self, pdf_path: str, file_index: int, total_files: int):
        base_filename = Path(pdf_path).stem
        output_folder = self.app.get_input_folder_path()
        image_folder = os.path.join(output_folder, f"{base_filename}_images")
        os.makedirs(image_folder, exist_ok=True)
        
        file_progress_start = (file_index - 1) / total_files * 100
        
        # 1. Convert PDF to Images
        self.log(f"({file_index}/{total_files}) Converting {base_filename}.pdf to images...")
        self.update_progress(file_progress_start, f"Processing {base_filename}...")
        try:
            images = convert_from_path(pdf_path, dpi=DPI, output_folder=image_folder, fmt='jpeg', thread_count=2)
            image_paths = [img.filename for img in images]
        except Exception as e:
            self.log(f"[ERROR] Could not convert PDF {pdf_path}: {e}")
            return
            
        self.log(f"Converted {len(image_paths)} pages to images.")

        # 2. Process with AI
        self.log("Sending images to AI for data extraction...")
        prompt = """
        Analyze the following images which are pages from a single document.
        Extract all tabular data into a single, clean, comma-separated CSV format.
        - The first row must be the header row.
        - Combine data from all pages into one CSV.
        - Do not include any introductory text, explanations, or the '```csv' '```' markers.
        - Only output the raw CSV data.
        - Ensure all values are properly quoted if they contain commas.
        """
        uploaded_files = [self.retry_loop(partial(genai.upload_file, path=p)) for p in image_paths if self.running]
        
        if not all(uploaded_files):
             self.log("File uploading failed after multiple retries.")
             return

        if not self.running: return

        self.update_progress(file_progress_start + 20, f"Extracting data from {base_filename}...")
        response = self.retry_loop(self.client.generate_content, [prompt] + uploaded_files)
        
        for up_file in uploaded_files:
            self.retry_loop(genai.delete_file, name=up_file.name)

        if not response or not hasattr(response, 'text'):
            self.log(f"[ERROR] Failed to get a valid response from AI for {pdf_path}.")
            return
        
        # 3. Save CSV
        csv_data = response.text.strip()
        csv_output_path = os.path.join(output_folder, f"{base_filename}.csv")
        try:
            with open(csv_output_path, 'w', encoding='utf-8') as f:
                f.write(csv_data)
            self.log(f"Successfully saved data to {base_filename}.csv")
        except Exception as e:
            self.log(f"[ERROR] Failed to save CSV file {csv_output_path}: {e}")
            
        # 4. Cleanup
        shutil.rmtree(image_folder)
        self.update_progress(file_index / total_files * 100, f"Completed {base_filename}")

    def combine_csv_files(self):
        output_folder = self.app.get_input_folder_path()
        csv_files = glob.glob(os.path.join(output_folder, "*.csv"))
        if not csv_files:
            self.log("No CSV files were generated to combine.")
            return

        combined_df = pd.DataFrame()
        for f in csv_files:
            try:
                df = pd.read_csv(f)
                combined_df = pd.concat([combined_df, df], ignore_index=True)
            except Exception as e:
                self.log(f"Could not read or process {os.path.basename(f)}: {e}")

        if not combined_df.empty:
            final_output_path = os.path.join(output_folder, "combined_output.xlsx")
            combined_df.to_excel(final_output_path, index=False)
            self.log(f"Successfully combined all data into 'combined_output.xlsx'")

    def cleanup_temp_files(self):
        output_folder = self.app.get_input_folder_path()
        csv_files = glob.glob(os.path.join(output_folder, "*.csv"))
        for f in csv_files:
            try:
                os.remove(f)
            except OSError as e:
                self.log(f"Error removing temporary file {f}: {e}")
        self.log("Cleaned up intermediate CSV files.")

    def run_processing(self, file_list: List[str]):
        self.running = True
        self.app.set_processing_state(True)
        
        if platform == 'android':
            self.app.start_foreground_notification()
        
        api_key = self.app.store.get('user_settings')['api_key']
        if not self.init_genai_client(api_key):
            self.app.set_processing_state(False)
            return

        total_files = len(file_list)
        for i, file_path in enumerate(file_list):
            if not self.running:
                self.log("Processing stopped by user.")
                break
            
            self.process_single_pdf(file_path, i + 1, total_files)

        if self.running:
            self.log("All files processed. Combining results...")
            self.combine_csv_files()
            self.cleanup_temp_files()
            self.log("All tasks finished successfully.")
            self.update_progress(100, "Completed!")
        else:
             self.update_progress(0, "Stopped")

        self.app.set_processing_state(False)
        if platform == 'android':
            self.app.stop_foreground_notification()
        self.running = False


# ======================================================
# Kivy UI Classes
# ======================================================

class ListItemWithCheckbox(BoxLayout):
    file_path = StringProperty('')
    file_name = StringProperty('')

class FileBrowserScreen(Screen):
    def on_enter(self, *args):
        # Automatically refresh file list when screen is shown
        self.refresh_file_list()

    def refresh_file_list(self):
        self.ids.file_list_grid.clear_widgets()
        input_folder = App.get_running_app().get_input_folder_path()
        pdf_files = glob.glob(os.path.join(input_folder, "*.pdf"))
        
        if not pdf_files:
            self.ids.status_label.text = f"No PDFs found. Please add files to the '{APP_INPUT_FOLDER_NAME}' folder in your Downloads."
        else:
            self.ids.status_label.text = f"Found {len(pdf_files)} PDF file(s). Select files to process."

        for f in sorted(pdf_files):
            item = ListItemWithCheckbox(file_path=f, file_name=os.path.basename(f))
            self.ids.file_list_grid.add_widget(item)

    def select_from_device(self):
        filechooser.open_file(on_selection=self.handle_selection, multiple=True)

    def handle_selection(self, selection: List[str]):
        if not selection:
            return
            
        input_folder = App.get_running_app().get_input_folder_path()
        for src_path in selection:
            try:
                # On Android, paths can be complex content URIs. This is a simplified copy.
                shutil.copy(src_path, os.path.join(input_folder, os.path.basename(src_path)))
            except Exception as e:
                print(f"Error copying file {src_path}: {e}")
        
        self.refresh_file_list()

    def start_processing(self):
        selected_files = []
        for item in self.ids.file_list_grid.children:
            if isinstance(item, ListItemWithCheckbox) and item.ids.checkbox.active:
                selected_files.append(item.file_path)

        if not selected_files:
            self.ids.status_label.text = "No files selected. Please check at least one file."
            return

        app = App.get_running_app()
        app.selected_files_to_process = selected_files
        app.root.current = 'processing'

class ProcessingScreen(Screen):
    log_text = StringProperty("Starting...\n")
    progress_value = NumericProperty(0)
    progress_message = StringProperty("Waiting to start")

    def on_enter(self, *args):
        self.log_text = "Preparing to process files...\n"
        self.progress_value = 0
        self.progress_message = "Starting..."
        app = App.get_running_app()
        
        # Start the background thread
        threading.Thread(target=app.processor.run_processing, args=(app.selected_files_to_process,), daemon=True).start()

    def stop_processing(self):
        App.get_running_app().processor.running = False # Signal thread to stop
    
    def go_to_main_screen(self):
        App.get_running_app().root.current = 'file_browser'


class SettingsScreen(Screen):
    api_key_input = ObjectProperty(None)

    def on_enter(self):
        # Load the saved API key when the screen is entered
        app = App.get_running_app()
        self.api_key_input.text = app.store.get('user_settings').get('api_key', '')

    def save_settings(self):
        app = App.get_running_app()
        app.store.put('user_settings', api_key=self.api_key_input.text)
        app.root.current = 'file_browser'


# ======================================================
# Main App Class
# ======================================================

class PDFtoExcelApp(App):
    processing = BooleanProperty(False)
    selected_files_to_process = ListProperty([])

    def build(self):
        # Load the KV string definition
        Builder.load_string(KV_STRING)

        self.store = JsonStore('settings.json')
        if not self.store.exists('user_settings'):
            self.store.put('user_settings', api_key='')

        self.processor = CoreProcessor(self)

        self.sm = ScreenManager()
        self.file_browser_screen = FileBrowserScreen(name='file_browser')
        self.processing_screen = ProcessingScreen(name='processing')
        self.settings_screen = SettingsScreen(name='settings')
        
        self.sm.add_widget(self.file_browser_screen)
        self.sm.add_widget(self.processing_screen)
        self.sm.add_widget(self.settings_screen)
        
        return self.sm

    def on_start(self):
        self.get_input_folder_path() # Ensure folder exists
        if platform == 'android':
            self.request_android_permissions()
        
        # If API key is missing, go to settings first
        if not self.store.get('user_settings').get('api_key'):
            self.root.current = 'settings'

    @mainthread
    def update_log(self, message):
        self.processing_screen.log_text += f"{message}\n"
        # Optional: Auto-scroll the log view
        self.processing_screen.ids.log_label.parent.scroll_y = 0
    
    @mainthread
    def update_progress(self, percent, message):
        self.processing_screen.progress_value = percent
        self.processing_screen.progress_message = message
        if self.processing and platform == 'android':
            self.update_notification(message)

    @mainthread
    def set_processing_state(self, is_processing):
        self.processing = is_processing

    def request_android_permissions(self):
        try:
            request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
        except Exception as e:
            self.update_log(f"Permission request failed: {e}")
        
    def get_download_folder_path(self):
        if platform == 'android':
            from android.storage import primary_external_storage_path
            return os.path.join(primary_external_storage_path(), 'Download')
        else:
            return str(Path.home() / "Downloads")
    
    def get_input_folder_path(self):
        download_folder = self.get_download_folder_path()
        input_folder = os.path.join(download_folder, APP_INPUT_FOLDER_NAME)
        if not os.path.exists(input_folder):
            os.makedirs(input_folder)
        return input_folder

    def start_foreground_notification(self):
        if platform == 'android':
            notification.notify(
                title='PDF Processing Active',
                message='Starting file conversion...',
                app_name='PDF to Excel',
                ticker='Processing started.'
            )
    
    def update_notification(self, message):
         if platform == 'android':
            notification.notify(
                title='PDF Processing Active',
                message=message,
                app_name='PDF to Excel',
                toast=False # Make sure it's a persistent notification
            )

    def stop_foreground_notification(self):
         if platform == 'android':
            notification.notify(
                title='Processing Finished',
                message='Tasks completed successfully.',
                app_name='PDF to Excel'
            )

if __name__ == '__main__':
    PDFtoExcelApp().run()

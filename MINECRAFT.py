import os
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import urllib.request
import zipfile
import shutil
import tempfile
from PIL import Image, ImageTk
import webbrowser
import tkinter.ttk as ttk
import pyperclip 
import re
import time
import sys
import ctypes
import socket
import urllib.error


if sys.executable.endswith("ServerCraftv0.6.exe"):
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

spam = "false"
SERVER_JAR_URL = "https://piston-data.mojang.com/v1/objects/e6ec2f64e6080b9b5d9b471b291c33cc7f509733/server.jar"
SERVER_JAR_NAME = "server.jar"
JAVA_ZIP_URL = "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.3%2B9/OpenJDK21U-jdk_x64_windows_hotspot_21.0.3_9.zip"
JAVA_FOLDER_NAME = "jdk"

class MinecraftServerSetup:
    def __init__(self, root):
        self.root = root
        self.root.title("ServerCraft")
        self.root.geometry("600x700")
        self.root.configure(bg="#222")

        self.icon_path = None
        self.download_icon()

        self.output_folder = tk.StringVar()
        self.min_ram = tk.StringVar(value="1G")
        self.max_ram = tk.StringVar(value="2G")
        self.eula_accepted = tk.BooleanVar()
        self.serveo_link = tk.StringVar()
        self.tunnel_service = tk.StringVar(value="serveo")  
        self.custom_tunnel_command = tk.StringVar()
        self.last_tunnel_address = ""  
        
       
        self.server_address_frame = tk.Frame(self.root, bg="#222")
        self.server_address_frame.pack(pady=(10, 0))
        
        self.address_label = tk.Label(self.server_address_frame, 
                                    text="Server Address: ", 
                                    bg="#222", fg="white", 
                                    font=('Arial', 10))
        self.address_label.pack(side="left")
        
        self.address_value = tk.Label(self.server_address_frame, 
                                    textvariable=self.serveo_link,
                                    bg="#222", fg="#4a9bff", 
                                    font=('Arial', 10, "underline"),
                                    cursor="hand2")
        self.address_value.pack(side="left")
        self.address_value.bind("<Button-1>", self.copy_server_address)
        self.server_address_frame.pack_forget()

        self.server_started = False
        self.console_visible = False
        self.server_process = None
        self.prop_window = None
        self.serveo_process = None
        self.server_port = 25565  

        self.create_widgets()

    def check_serveo_status(self):
        """Check if Serveo is online"""
        try:
           
            socket.create_connection(("serveo.net", 22), timeout=5)
            self.log_console("Serveo is up!")
        except (socket.timeout, ConnectionRefusedError, urllib.error.URLError) as e:
            self.log_console("It looks like Serveo, our provider is down. This happens often so please try again later. "
                           "If you think this is a mistake, please report it on our github page")
        except Exception as e:
            self.log_console(f"[ERROR] Could not check Serveo status: {e}")

    def check_custom_provider_status(self):
        """Check if the custom provider is online"""
        command = self.custom_tunnel_command.get()
        
        hostname = None
        
        
        patterns = [
            r'ssh.*?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',  
            r'ngrok.*?(tcp://)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', 
            r'localhost\.run', 
            r'localtunnel\.me',  
            r'playit\.gg' 
        ]
        
        for pattern in patterns:
            match = re.search(pattern, command)
            if match:
                hostname = match.group(1) if match.groups() else match.group(0)
                break
        
        if not hostname:
            self.log_console("[INFO] Could not determine provider from custom command")
            return
        
       
        if 'serveo.net' in hostname:
            self.check_serveo_status()
            return
        elif 'localhost.run' in hostname:
            self.check_localhost_run_status()
            return
        elif 'playit.gg' in hostname:
            self.check_playit_gg_status()
            return
        
       
        try:
           
            for port in [80, 443, 22]:
                try:
                    socket.create_connection((hostname, port), timeout=5)
                    self.log_console(f"{hostname} is up!")
                    return
                except (socket.timeout, ConnectionRefusedError):
                    continue
            
           
            self.log_console(f"{hostname} seems to be down. If you think this is a mistake, please report it on our github page")
        except Exception as e:
            self.log_console(f"[ERROR] Could not check {hostname} status: {e}")

    def check_localhost_run_status(self):
        """Check if localhost.run is online"""
        try:
            socket.create_connection(("localhost.run", 443), timeout=5)
            self.log_console("localhost.run is up!")
        except (socket.timeout, ConnectionRefusedError, urllib.error.URLError) as e:
            self.log_console("localhost.run seems to be down. If you think this is a mistake, please report it on our github page")
        except Exception as e:
            self.log_console(f"[ERROR] Could not check localhost.run status: {e}")

    def check_playit_gg_status(self):
        """Check if playit.gg is online"""
        try:
            socket.create_connection(("playit.gg", 443), timeout=5)
            self.log_console("playit.gg is up!")
        except (socket.timeout, ConnectionRefusedError, urllib.error.URLError) as e:
            self.log_console("playit.gg seems to be down. If you think this is a mistake, please report it on our github page")
        except Exception as e:
            self.log_console(f"[ERROR] Could not check playit.gg status: {e}")

    def copy_server_address(self, event=None):
        """Copy server address to clipboard when clicked"""
        address = self.serveo_link.get()
        if address:
            try:
                pyperclip.copy(address)
                messagebox.showinfo("Copied!", "Copied to clipboard successfully!")
                original_text = self.address_value.cget("text")
                self.address_value.config(text="Copied to Clipboard!", fg="lightgreen")
                self.root.after(2000, lambda: self.address_value.config(
                    textvariable=self.serveo_link, 
                    fg="#4a9bff")
                )
            except Exception as e:
                self.log_console(f"[ERROR] Failed to copy address: {e}")

    def download_icon(self):
        try:
            icon_url = "https://raw.githubusercontent.com/lazerkatsweirdstuff/servercraft/refs/heads/main/icon.ico"
            self.icon_path = os.path.join(tempfile.gettempdir(), "servercraft_icon.ico")
            urllib.request.urlretrieve(icon_url, self.icon_path)
            self.root.iconbitmap(self.icon_path)
        except Exception as e:
            print(f"Failed to load icon: {e}")

    def create_widgets(self):
        label_style = {'bg': '#222', 'fg': 'white', 'font': ('Arial', 12)}
        entry_style = {'bg': '#333', 'fg': 'white', 'font': ('Arial', 12)}

        tk.Label(self.root, text="Choose Output Folder:", **label_style).pack(pady=10)
        tk.Entry(self.root, textvariable=self.output_folder, width=40, **entry_style).pack()
        tk.Button(self.root, text="Browse", command=self.browse_folder, bg="#444", fg="white").pack(pady=10)

        tk.Button(self.root, text="Import Minecraft World (.zip)", command=self.import_world,
                 bg="#444", fg="white", font=("Arial", 9)).pack(pady=10)
        
        pmc_frame = tk.Frame(self.root, bg="#222")
        pmc_frame.pack()
        tk.Label(pmc_frame, text="There are a lot of good worlds at", 
                bg="#222", fg="white", font=("Arial", 8)).pack(side="left")
        pmc_link = tk.Label(pmc_frame, text="Planet Minecraft", 
                           bg="#222", fg="#4a9bff", font=("Arial", 8, "underline"), cursor="hand2")
        pmc_link.pack(side="left")
        pmc_link.bind("<Button-1>", lambda e: webbrowser.open("https://www.planetminecraft.com/projects/?platform=1&monetization=0&order=order_downloads&share=world_link"))

        tk.Label(self.root, text="Min RAM (e.g. 1G):", **label_style).pack(pady=10)
        tk.Entry(self.root, textvariable=self.min_ram, **entry_style).pack()

        tk.Label(self.root, text="Max RAM (e.g. 2G):", **label_style).pack(pady=10)
        tk.Entry(self.root, textvariable=self.max_ram, **entry_style).pack()

        
        tunnel_frame = tk.Frame(self.root, bg="#222")
        tunnel_frame.pack(pady=10)
        tk.Label(tunnel_frame, text="Tunnel Service:", bg="#222", fg="white").pack(side="left")
        
        service_menu = tk.OptionMenu(tunnel_frame, self.tunnel_service, 
                                   "serveo", "custom",
                                   command=self.change_tunnel_service)
        service_menu.config(bg="#333", fg="white", highlightthickness=0)
        service_menu.pack(side="left", padx=5)
        
       
        self.custom_command_frame = tk.Frame(self.root, bg="#222")
        tk.Label(self.custom_command_frame, 
                text="Custom SSH Command:", 
                bg="#222", fg="white").pack(anchor="w")
        
        self.custom_command_entry = tk.Entry(
            self.custom_command_frame, 
            textvariable=self.custom_tunnel_command,
            width=50,
            bg="#333", 
            fg="white"
        )
        self.custom_command_entry.pack(fill="x", pady=5)
        
        warning_label = tk.Label(
            self.custom_command_frame,
            text="⚠️ This is for more advanced users only!",
            bg="#222",
            fg="orange",
            font=("Arial", 8)
        )
        warning_label.pack(anchor="w")
        
        self.custom_command_frame.pack_forget()

        self.eula_checkbox = tk.Checkbutton(self.root, text="I accept the EULA",
                                          variable=self.eula_accepted,
                                          bg="#222", fg="white", font=('Arial', 10),
                                          activebackground="#222", activeforeground="white",
                                          selectcolor="#222")
        self.eula_checkbox.pack(pady=10)

        self.java_progress = ttk.Progressbar(self.root, length=400, mode='determinate')
        self.java_progress.pack(pady=5)

        self.setup_button = tk.Button(self.root, text="Setup and Start Server", command=self.run_setup_thread,
                                    bg="green", fg="white", font=("Arial", 12, "bold"))
        self.setup_button.pack(pady=10)

        self.console_toggle = tk.Button(self.root, text="Show Console Output ▼", command=self.toggle_console,
                                      bg="#333", fg="white")
        self.console_toggle.pack(pady=5)

        self.console_output = scrolledtext.ScrolledText(self.root, height=10, bg="black", fg="white",
                                                      font=("Consolas", 10))
        self.console_output.pack_forget()

        self.command_frame = tk.Frame(self.root, bg="#222")
        self.command_entry = tk.Entry(self.command_frame, bg="#333", fg="white", font=("Consolas", 10))
        self.command_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.command_entry.bind("<Return>", self.send_command)
        tk.Button(self.command_frame, text="Send", command=self.send_command,
                 bg="#444", fg="white").pack(side="right")
        self.command_frame.pack_forget()

        self.edit_button = tk.Button(self.root, text="Edit Server Settings", command=self.edit_properties,
                                   bg="#555", fg="white")
        self.edit_button.pack(pady=10)
        self.edit_button.pack_forget()

    def change_tunnel_service(self, service):
        """Handle tunnel service change"""
        self.log_console(f"Tunnel service changed to: {service}")
        
        
        if service == "custom":
            current_command = f"ssh -o StrictHostKeyChecking=no -R 0:localhost:{self.server_port} serveo.net"
            self.custom_tunnel_command.set(current_command)
            self.custom_command_frame.pack(fill="x", padx=10, pady=5)
            
            
            if self.last_tunnel_address:
                self.serveo_link.set(self.last_tunnel_address)
                self.server_address_frame.pack()
        else:
            self.custom_command_frame.pack_forget()
        
        
        if hasattr(self, 'serveo_process') and self.serveo_process:
            try:
                self.serveo_process.terminate()
                self.log_console(f"Stopped previous {self.tunnel_service.get()} tunnel")
            except Exception as e:
                self.log_console(f"Error stopping tunnel: {e}")
        
        if self.server_started:
            threading.Thread(target=self.run_tunnel, daemon=True).start()

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_folder.set(folder)

    def toggle_console(self):
        if self.console_visible:
            self.console_output.pack_forget()
            self.command_frame.pack_forget()
            self.console_toggle.config(text="Show Console Output ▼")
            
            self.root.geometry("600x700")
        else:
            self.console_output.pack(pady=5, fill='both', expand=True)
            self.command_frame.pack(pady=5, fill='x')
            self.console_toggle.config(text="Hide Console Output ▲")
            
            self.root.geometry("800x800")
        self.console_visible = not self.console_visible

    def run_setup_thread(self):
        global spam
        if spam == "false":
            spam = "false"
            threading.Thread(target=self.setup_server_thread).start()

    def setup_server_thread(self):
        folder = self.output_folder.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Error", "Please choose a valid output folder.")
            return

        if not self.eula_accepted.get():
            messagebox.showerror("EULA", "You must accept the EULA to continue.")
            return

        
        provider = self.tunnel_service.get()
        if provider == "serveo":
            self.check_serveo_status()
        elif provider == "custom":
           
            self.check_custom_provider_status()

        ssh_path = self.check_or_install_ssh(folder)
        if not ssh_path:
            messagebox.showerror("SSH Error", "Could not install SSH client.")
            return
        self.ssh_path = ssh_path

        java_path = os.path.join(folder, JAVA_FOLDER_NAME, "bin", "java.exe")
        if not os.path.exists(java_path):
            self.log_console("Java not found. Downloading...")
            if not self.download_and_extract_java(folder):
                return

        jar_path = os.path.join(folder, SERVER_JAR_NAME)
        if not os.path.exists(jar_path):
            try:
                self.log_console("Downloading Minecraft server...")
                urllib.request.urlretrieve(SERVER_JAR_URL, jar_path)
                self.log_console("Server download complete.")
            except Exception as e:
                messagebox.showerror("Download Error", f"Failed to download server.jar:\n{e}")
                return

        if not os.path.exists(os.path.join(folder, "eula.txt")):
            with open(os.path.join(folder, "eula.txt"), "w") as f:
                f.write("eula=true\n")

       
        icon_path = os.path.join(folder, "server-icon.png")
        if not os.path.exists(icon_path):
            try:
                self.log_console("Setting default server icon...")
                default_icon_url = "https://raw.githubusercontent.com/lazerkatsweirdstuff/servercraft/refs/heads/main/iconserver.png"
                urllib.request.urlretrieve(default_icon_url, icon_path)
            except Exception as e:
                self.log_console(f"[WARNING] Could not set default server icon: {e}")

       
        self.read_server_port(folder)

        self.log_console("Starting server...")
        try:
          
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

            self.server_process = subprocess.Popen(
                [java_path, f"-Xms{self.min_ram.get()}", f"-Xmx{self.max_ram.get()}", "-jar", SERVER_JAR_NAME, "nogui"],
                cwd=folder,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                startupinfo=startupinfo
            )
            self.server_started = True
            self.update_button_state()
            self.edit_button.pack()
            threading.Thread(target=self.read_console_output, daemon=True).start()
            threading.Thread(target=self.run_tunnel, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start server:\n{e}")
            self.server_started = False
            self.server_process = None

    def run_tunnel(self):
        """Run the selected tunnel service"""
        service = self.tunnel_service.get()
        
        if service == "serveo":
            self.run_serveo_ssh()
        elif service == "custom":
            self.run_custom_tunnel()
        else:
            self.log_console(f"[ERROR] Unknown tunnel service: {service}")

    def run_serveo_ssh(self):
        try:
            self.log_console("Starting Serveo tunnel...")
            
            self.read_server_port(self.output_folder.get())
            
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

            process = subprocess.Popen(
                ['ssh', '-o', 'StrictHostKeyChecking=no',
                 '-R', f'0:localhost:{self.server_port}', 'serveo.net'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                startupinfo=startupinfo
            )
            self.serveo_process = process

            while True:
                line = process.stdout.readline()
                if not line:
                    break
                self.log_console("[Serveo] " + line.strip())

                if "Forwarding TCP" in line:
                    parts = line.strip().split(" ")
                    if len(parts) >= 5:
                        serveo_address = parts[-1] 
                        self.serveo_link.set(serveo_address)
                        self.last_tunnel_address = serveo_address 
                        self.server_address_frame.pack()
                        self.server_address_frame.lift()
                        self.update_window_size()

        except Exception as e:
            self.log_console(f"[ERROR] Serveo tunnel failed: {e}")

    def run_custom_tunnel(self):
        try:
            self.log_console("Starting custom tunnel...")
            self.read_server_port(self.output_folder.get())
            
        
            command = self.custom_tunnel_command.get()
            
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

            
            command_parts = command.split()
            
            process = subprocess.Popen(
                command_parts,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=True,
                startupinfo=startupinfo
            )
            self.serveo_process = process

            while True:
                line = process.stdout.readline()
                if not line:
                    break
                self.log_console("[Custom Tunnel] " + line.strip())

                
                if "Forwarding TCP" in line:  
                    parts = line.strip().split(" ")
                    if len(parts) >= 5:
                        address = parts[-1] 
                        self.serveo_link.set(address)
                        self.last_tunnel_address = address  
                        self.server_address_frame.pack()
                        self.server_address_frame.lift()
                        self.update_window_size()
                elif "tunneled with" in line: 
                    match = re.search(r'https://[^\s]+', line)
                    if match:
                        address = match.group(0)
                        self.serveo_link.set(address)
                        self.last_tunnel_address = address  
                        self.server_address_frame.pack()
                        self.server_address_frame.lift()
                        self.update_window_size()
                elif "started tunnel" in line: 
                    match = re.search(r'url=(tcp://[^\s]+)', line)
                    if match:
                        address = match.group(1)
                        self.serveo_link.set(address)
                        self.last_tunnel_address = address 
                        self.server_address_frame.pack()
                        self.server_address_frame.lift()
                        self.update_window_size()

        except Exception as e:
            self.log_console(f"[ERROR] Custom tunnel failed: {e}")

    def update_window_size(self):
        """Update window size to fit the address"""
        
        self.root.update_idletasks()
        
        
        address_width = self.address_value.winfo_reqwidth()
        label_width = self.address_label.winfo_reqwidth()
        frame_padding = 20
        required_width = address_width + label_width + frame_padding
        
       
        required_height = 700 
        if self.console_visible:
            required_height = 800  
        
        
        current_width = self.root.winfo_width()
        current_height = self.root.winfo_height()
        
        
        new_width = max(600 if not self.console_visible else 800, required_width)
        new_height = max(required_height, current_height)
        
        
        if new_width > current_width or new_height > current_height:
            self.root.geometry(f"{new_width}x{new_height}")
        
        
        self.console_output.see(tk.END)

    def read_server_port(self, folder):
        """Read the server port from server.properties or use default"""
        prop_path = os.path.join(folder, "server.properties")
        if os.path.exists(prop_path):
            try:
                with open(prop_path, 'r') as f:
                    for line in f:
                        if line.startswith('server-port='):
                            port_str = line.split('=')[1].strip()
                            if port_str.isdigit():
                                self.server_port = int(port_str)
                            break
            except Exception as e:
                self.log_console(f"[WARNING] Couldn't read server port: {e}. Using default 25565")
        else:
            self.log_console("[INFO] No server.properties found. Using default port 25565")

    def log_console(self, text):
        self.console_output.insert(tk.END, text + "\n")
        self.console_output.see(tk.END)

    def read_console_output(self):
        while True:
            line = self.server_process.stdout.readline()
            if not line:
                if self.server_process.poll() is not None:
                    self.log_console("[SERVER CRASHED] The server has stopped unexpectedly")
                    self.server_started = False
                    self.server_process = None
                    self.server_address_frame.pack_forget()
                    self.update_button_state()
                break
            
            self.log_console(line.strip())

    def send_command(self, event=None):
        if not hasattr(self, 'server_process') or self.server_process is None:
            self.log_console("[ERROR] Server is not running. Start the server first.")
            return
        
        if self.server_process.poll() is not None:
            self.log_console("[ERROR] Server has stopped running.")
            self.server_started = False
            self.server_process = None
            self.update_button_state()
            return

        command = self.command_entry.get().strip()
        if not command:
            return

        try:
            if self.server_process.stdin.closed:
                self.log_console("[ERROR] Cannot send command - server connection closed")
                return
                
            self.server_process.stdin.write(command + '\n')
            self.server_process.stdin.flush()
            self.log_console(f"> {command}")
            self.command_entry.delete(0, tk.END)
        except BrokenPipeError:
            self.log_console("[ERROR] Server connection broken - server may have crashed")
            self.server_started = False
            self.server_process = None
            self.update_button_state()
        except Exception as e:
            self.log_console(f"[ERROR] Failed to send command: {str(e)}")

    def download_and_extract_java(self, target_folder):
        try:
            os.makedirs(target_folder, exist_ok=True)
            zip_path = os.path.join(tempfile.gettempdir(), "java.zip")

           
            opener = urllib.request.build_opener()
            opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
            urllib.request.install_opener(opener)

            self.log_console("Downloading Java...")
            urllib.request.urlretrieve(JAVA_ZIP_URL, zip_path, self._download_progress_hook)

            self.log_console("Extracting Java...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(target_folder)

            os.remove(zip_path)

            
            jdk_folder = None
            for item in os.listdir(target_folder):
                if item.startswith('jdk-') or item.lower().startswith('openjdk'):
                    jdk_folder = os.path.join(target_folder, item)
                    break

            if not jdk_folder:
                raise Exception("Java ZIP did not extract correctly - no JDK folder found.")

            final_path = os.path.join(target_folder, JAVA_FOLDER_NAME)
            if os.path.exists(final_path):
                shutil.rmtree(final_path)
            shutil.move(jdk_folder, final_path)

            self.log_console("Java installation complete.")
            return True

        except Exception as e:
            messagebox.showerror("Java Error", f"Failed to download or extract Java:\n{e}")
            self.log_console(f"[ERROR] Java setup failed: {e}")
            return False

    def _download_progress_hook(self, count, block_size, total_size):
        if total_size > 0:
            percent = min(int(count * block_size * 100 / total_size), 100)
            self.java_progress['value'] = percent
            self.root.update_idletasks()

    def import_world(self):
        folder = self.output_folder.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Error", "Please choose a valid output folder before importing a world.")
            return

        zip_path = filedialog.askopenfilename(
            title="Select a Minecraft World ZIP File",
            filetypes=[("ZIP files", "*.zip")]
        )
        if not zip_path:
            return

        destination = os.path.join(folder, "world")
        if os.path.exists(destination):
            if not messagebox.askyesno("Overwrite", "A world folder already exists. Overwrite it?"):
                return
            try:
                shutil.rmtree(destination)
            except Exception as e:
                messagebox.showerror("Error", f"Unable to remove existing world folder:\n{e}")
                return

        temp_dir = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            extracted_world = None
            for root_dir, dirs, files in os.walk(temp_dir):
                if 'level.dat' in files:
                    extracted_world = root_dir
                    break

            if extracted_world is None:
                raise Exception("No valid world folder (missing level.dat) was found in the ZIP.")

            if os.path.abspath(extracted_world) != os.path.abspath(temp_dir):
                shutil.move(extracted_world, destination)
            else:
                os.makedirs(destination, exist_ok=True)
                for item in os.listdir(temp_dir):
                    s = os.path.join(temp_dir, item)
                    d = os.path.join(destination, item)
                    shutil.move(s, d)

            messagebox.showinfo("Import Successful", "Minecraft world imported successfully.")
            self.log_console("Minecraft world imported successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import world:\n{e}")
            self.log_console(f"[ERROR] Failed to import world: {e}")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def edit_properties(self):
        if not self.server_started:
            messagebox.showwarning("Wait", "Please start the server before editing settings.")
            return

        if self.prop_window and self.prop_window.winfo_exists():
            self.prop_window.destroy()

        self.prop_window = tk.Toplevel(self.root)
        self.prop_window.title("Edit server.properties")
        self.prop_window.geometry("400x550")
        self.prop_window.configure(bg="#222")
        if self.icon_path:
            self.prop_window.iconbitmap(self.icon_path)

   
        top_frame = tk.Frame(self.prop_window, bg="#222")
        top_frame.pack(fill="x", padx=10, pady=10)

     
        desc_frame = tk.Frame(top_frame, bg="#222")
        desc_frame.pack(fill="x", pady=(0, 10))
        tk.Label(desc_frame, text="Server Description:", bg="#222", fg="white").pack(anchor="w")
        self.desc_entry = tk.Entry(desc_frame, bg="#333", fg="white")
        self.desc_entry.pack(fill="x")


        button_icon_frame = tk.Frame(top_frame, bg="#222")
        button_icon_frame.pack(fill="x", pady=5)
        

        icon_controls_frame = tk.Frame(button_icon_frame, bg="#222")
        icon_controls_frame.pack(side="left", fill="x", expand=True)
        
        tk.Button(icon_controls_frame, text="Set Server Icon", command=self.set_server_icon, 
                bg="#555", fg="white").pack(side="left", padx=(0, 10))
        
        self.icon_preview_label = tk.Label(icon_controls_frame, text="(No preview)", bg="#222", fg="gray")
        self.icon_preview_label.pack(side="left")

       
        apply_button = tk.Button(button_icon_frame, text="Apply Changes", command=self.apply_property_changes,
                               bg="green", fg="white")
        apply_button.pack(side="right")

        
        canvas = tk.Canvas(self.prop_window, bg="#222", highlightthickness=0)
        scrollbar = tk.Scrollbar(self.prop_window, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg="#222")

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.prop_entries = {} 
        prop_path = os.path.join(self.output_folder.get(), "server.properties")
        if not os.path.exists(prop_path):
            messagebox.showerror("Error", "server.properties file not found.")
            self.prop_window.destroy()
            return

      
        with open(prop_path, "r") as f:
            for line in f:
                if line.startswith("motd="):
                    _, value = line.split("=", 1)
                    self.desc_entry.insert(0, value.strip())
                    break

        
        with open(prop_path, "r") as f:
            for line in f:
                if "=" in line and not line.startswith("motd="):
                    key, value = line.split("=", 1)
                    tk.Label(scroll_frame, text=key, bg="#222", fg="white").pack()
                    entry = tk.Entry(scroll_frame, bg="#333", fg="white")
                    entry.insert(0, value)
                    entry.pack(pady=2, fill="x", padx=10)
                    self.prop_entries[key] = entry

       
        icon_path = os.path.join(self.output_folder.get(), "server-icon.png")
        if os.path.exists(icon_path):
            self.update_icon_preview(icon_path)

    def set_server_icon(self):
        file_path = filedialog.askopenfilename(
            title="Select a Server Icon",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp")]
        )
        if not file_path:
            return
        try:
            img = Image.open(file_path).convert("RGBA")
            img = img.resize((64, 64), Image.LANCZOS)
            icon_path = os.path.join(self.output_folder.get(), "server-icon.png")
            img.save(icon_path, "PNG")
            self.update_icon_preview(icon_path)
            self.icon_preview_label.configure(text="✅ Icon updated!", fg="lightgreen")
            self.icon_preview_label.after(3000, lambda: self.icon_preview_label.configure(text=""))
           
            self.prop_window.lift()
            self.prop_window.focus_force()
        except Exception as e:
            messagebox.showerror("Error", f"Could not set icon:\n{e}")

    def update_icon_preview(self, path):
        try:
            img = Image.open(path)
            img.thumbnail((64, 64))
            img = ImageTk.PhotoImage(img)
            self.icon_preview_label.configure(image=img)
            self.icon_preview_label.image = img
        except Exception as e:
            self.icon_preview_label.configure(text="(Preview unavailable)", fg="gray")

    def apply_property_changes(self):
        prop_path = os.path.join(self.output_folder.get(), "server.properties")
        with open(prop_path, "w") as f:
            
            f.write(f"motd={self.desc_entry.get()}\n")
            
            
            for key, entry in self.prop_entries.items():
                f.write(f"{key}={entry.get()}\n")
        
       
        if 'server-port' in self.prop_entries:
            try:
                new_port = int(self.prop_entries['server-port'].get())
                if new_port != self.server_port:
                    self.server_port = new_port
                    self.log_console(f"Server port changed to {new_port}. Restarting tunnel...")
                    if hasattr(self, 'serveo_process') and self.serveo_process:
                        self.serveo_process.terminate()
            except ValueError:
                self.log_console("[ERROR] Invalid port number in server.properties")
        
        messagebox.showinfo("Saved", "Settings applied. Restarting server...")
        self.prop_window.destroy()
        self.restart_server()

    def restart_server(self):
        
        if self.server_process:
            try:
                self.log_console("Kicking all players...")
                kick_msg = "Sorry! The owner has shut down the server! Ask the owner for a new link or if you should stay on the same one, just rejoin"
                self.server_process.stdin.write(f"kick @a {kick_msg}\n")
                self.server_process.stdin.flush()
                
                
                time.sleep(1)
                
                self.log_console("Stopping server...")
                self.server_process.stdin.write("stop\n")
                self.server_process.stdin.flush()
                self.server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.log_console("[WARNING] Server didn't stop gracefully, forcing termination")
                self.server_process.terminate()
            except Exception as e:
                self.log_console(f"[ERROR] Failed to stop server: {e}")
            finally:
                self.server_process = None
                self.server_started = False
                self.update_button_state()
                self.server_address_frame.pack_forget()

        
        folder = self.output_folder.get()
        java_path = os.path.join(folder, JAVA_FOLDER_NAME, "bin", "java.exe")
        
        try:
            self.log_console("Restarting server with new settings...")
           
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

            self.server_process = subprocess.Popen(
                [java_path, f"-Xms{self.min_ram.get()}", f"-Xmx{self.max_ram.get()}", "-jar", SERVER_JAR_NAME, "nogui"],
                cwd=folder,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                startupinfo=startupinfo
            )
            self.server_started = True
            self.update_button_state()
            threading.Thread(target=self.read_console_output, daemon=True).start()
            threading.Thread(target=self.run_tunnel, daemon=True).start()
        except Exception as e:
            self.log_console(f"[ERROR] Failed to restart server: {e}")
            self.server_started = False
            self.server_process = None
            self.update_button_state()
    
    def check_or_install_ssh(self, folder):
        ssh_path = os.path.join(folder, "ssh.exe")
        if os.path.exists(ssh_path):
            return ssh_path

        self.log_console("Downloading SSH client (for tunneling)...")
        try:
            ssh_url = "https://github.com/PowerShell/Win32-OpenSSH/releases/download/v9.5.0.0p1-Beta/OpenSSH-Win64.zip"
            zip_path = os.path.join(tempfile.gettempdir(), "openssh.zip")
            urllib.request.urlretrieve(ssh_url, zip_path)

            temp_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.lower() == "ssh.exe":
                        extracted_path = os.path.join(root, file)
                        shutil.copy(extracted_path, ssh_path)
                        self.log_console("SSH client installed successfully.")
                        shutil.rmtree(temp_dir)
                        return ssh_path

            self.log_console("[ERROR] ssh.exe not found in ZIP.")
            return None
        except Exception as e:
            self.log_console(f"[ERROR] Failed to download SSH: {e}")
            return None

    def stop_server(self):
        """Stop the Minecraft server and tunnel"""
        if not self.server_started:
            return

        try:
            
            if self.server_process and self.server_process.poll() is None:
                self.log_console("Saving world...")
                self.server_process.stdin.write("save-all\n")
                self.server_process.stdin.flush()
                time.sleep(1)  
                
               
                self.log_console("Stopping server...")
                self.server_process.stdin.write("stop\n")
                self.server_process.stdin.flush()
                
               
                try:
                    self.server_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.log_console("[WARNING] Server didn't stop gracefully, forcing termination")
                    self.server_process.terminate()
                
                self.server_process = None
                self.log_console("Server stopped successfully")
            
            
            if hasattr(self, 'serveo_process') and self.serveo_process:
                self.log_console("Stopping tunnel...")
                self.serveo_process.terminate()
                self.serveo_process = None
                self.log_console("Tunnel stopped successfully")
            
           
            self.server_started = False
            self.update_button_state()
            self.server_address_frame.pack_forget()
            self.edit_button.pack_forget()
            
        except Exception as e:
            self.log_console(f"[ERROR] Failed to stop server: {e}")
            messagebox.showerror("Error", f"Failed to stop server:\n{e}")

    def update_button_state(self):
        """Update the button text and color based on server state"""
        if self.server_started:
            self.setup_button.config(text="Stop Server", bg="red", command=self.stop_server)
            self.edit_button.pack()
        else:
            self.setup_button.config(text="Setup and Start Server", bg="green", command=self.run_setup_thread)
            self.edit_button.pack_forget()

    def on_close(self):
        """Handle window closing event"""
        if hasattr(self, 'server_process') and self.server_process and self.server_process.poll() is None:
            try:
                self.log_console("Stopping server...")
                self.server_process.stdin.write("stop\n")
                self.server_process.stdin.flush()
                self.server_process.wait(timeout=5)
            except Exception as e:
                self.log_console(f"Error stopping server: {e}")
        
        if hasattr(self, 'serveo_process') and self.serveo_process:
            try:
                self.serveo_process.terminate()
            except Exception as e:
                self.log_console(f"Error stopping tunnel: {e}")
        
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MinecraftServerSetup(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)  
    root.mainloop()

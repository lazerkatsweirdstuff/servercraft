import os
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import urllib.request
import zipfile
import shutil
import tempfile
from PIL import Image

SERVER_JAR_URL = "https://piston-data.mojang.com/v1/objects/e6ec2f64e6080b9b5d9b471b291c33cc7f509733/server.jar"
SERVER_JAR_NAME = "server.jar"
JAVA_ZIP_URL = "https://api.adoptium.net/v3/binary/latest/21/ga/windows/x64/jdk/hotspot/normal/eclipse?project=jdk"
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
        self.serveo_label = tk.Label(self.root, textvariable=self.serveo_link, bg="#222", fg="white", font=('Arial', 10))
        self.serveo_label.pack(pady=5)
        self.serveo_label.pack_forget()  

        self.server_started = False

        self.console_visible = False
        self.server_process = None

        self.create_widgets()

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
                  bg="#444", fg="white", font=("Arial", 12)).pack(pady=10)

        tk.Label(self.root, text="Min RAM (e.g. 1G):", **label_style).pack(pady=10)
        tk.Entry(self.root, textvariable=self.min_ram, **entry_style).pack()

        tk.Label(self.root, text="Max RAM (e.g. 2G):", **label_style).pack(pady=10)
        tk.Entry(self.root, textvariable=self.max_ram, **entry_style).pack()

        self.eula_checkbox = tk.Checkbutton(self.root, text="I accept the EULA",
                                            variable=self.eula_accepted,
                                            bg="#222", fg="white", font=('Arial', 10),
                                            activebackground="#222", activeforeground="white",
                                            selectcolor="#222")
        self.eula_checkbox.pack(pady=10)

        import tkinter.ttk as ttk
        self.java_progress = ttk.Progressbar(self.root, length=400, mode='determinate')
        self.java_progress.pack(pady=5)

        tk.Button(self.root, text="Setup and Start Server", command=self.run_setup_thread,
                  bg="green", fg="white", font=("Arial", 12, "bold")).pack(pady=10)

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

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_folder.set(folder)

    def toggle_console(self):
        if self.console_visible:
            self.console_output.pack_forget()
            self.command_frame.pack_forget()
            self.console_toggle.config(text="Show Console Output ▼")
        else:
            self.console_output.pack(pady=5, fill='both', expand=True)
            self.command_frame.pack(pady=5, fill='x')
            self.console_toggle.config(text="Hide Console Output ▲")
        self.console_visible = not self.console_visible

    def run_setup_thread(self):
        threading.Thread(target=self.setup_server).start()

    def setup_server(self):
        folder = self.output_folder.get()
        ssh_path = self.check_or_install_ssh(folder)
        if not ssh_path:
            messagebox.showerror("SSH Error", "Could not install SSH client.")
            return
        self.ssh_path = ssh_path

        
        min_ram = self.min_ram.get()
        max_ram = self.max_ram.get()

        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Error", "Please choose a valid output folder.")
            return

        if not self.eula_accepted.get():
            messagebox.showerror("EULA", "You must accept the EULA to continue.")
            return

        java_path = os.path.join(folder, JAVA_FOLDER_NAME, "bin", "java.exe")
        if not os.path.exists(java_path):
            self.log_console("Java not found in this folder. Downloading it for you...")
            if not self.download_and_extract_java(folder):
                return

        jar_path = os.path.join(folder, SERVER_JAR_NAME)
        try:
            self.log_console("Downloading Minecraft server...")
            urllib.request.urlretrieve(SERVER_JAR_URL, jar_path)
            self.log_console("Server download complete.")
        except Exception as e:
            messagebox.showerror("Download Error", f"Failed to download server.jar:\n{e}")
            return

        with open(os.path.join(folder, "eula.txt"), "w") as f:
            f.write("eula=true\n")

        self.log_console("Starting server...")
        try:
            self.server_process = subprocess.Popen(
                [java_path, f"-Xms{min_ram}", f"-Xmx{max_ram}", "-jar", SERVER_JAR_NAME, "nogui"],
                cwd=folder,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            self.server_started = True
            self.edit_button.pack()
            threading.Thread(target=self.read_console_output).start()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start server:\n{e}")

    def log_console(self, text):
        self.console_output.insert(tk.END, text + "\n")
        self.console_output.see(tk.END)

    def read_console_output(self):
        ssh_started = False
        while True:
            line = self.server_process.stdout.readline()
            if not line:
                break
            self.log_console(line.strip())

            if "Done" in line and not ssh_started:
                ssh_started = True
                self.log_console("Server is ready. Starting Serveo SSH tunnel...")
                threading.Thread(target=self.run_serveo_ssh).start()

    def send_command(self, event=None):
        if not self.server_process or self.server_process.poll() is not None:
            self.log_console("[ERROR] Server is not running.")
            return

        command = self.command_entry.get().strip()
        if command:
            try:
                self.server_process.stdin.write(command + '\n')
                self.server_process.stdin.flush()
                self.log_console(f"> {command}")
                self.command_entry.delete(0, tk.END)
            except Exception as e:
                self.log_console(f"[ERROR] Failed to send command: {e}")

    def download_and_extract_java(self, target_folder):
        try:
            os.makedirs(target_folder, exist_ok=True)
            zip_path = os.path.join(tempfile.gettempdir(), "java.zip")

            req = urllib.request.Request(JAVA_ZIP_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                if response.status != 200:
                    raise Exception(f"Download failed with status {response.status}")

                total_size = int(response.getheader('Content-Length', 0))
                with open(zip_path, 'wb') as out_file:
                    downloaded = 0
                    while chunk := response.read(8192):
                        out_file.write(chunk)
                        downloaded += len(chunk)
                        self.java_progress['value'] = (downloaded / total_size) * 100
                        self.root.update_idletasks()

            self.log_console("Java download complete. Extracting...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(target_folder)

            os.remove(zip_path)

            subfolders = [f for f in os.listdir(target_folder)
                          if os.path.isdir(os.path.join(target_folder, f)) and f != JAVA_FOLDER_NAME]
            if not subfolders:
                raise Exception("Java ZIP did not extract correctly.")

            extracted_dir = os.path.join(target_folder, subfolders[0])
            final_path = os.path.join(target_folder, JAVA_FOLDER_NAME)
            if os.path.exists(final_path):
                shutil.rmtree(final_path)
            shutil.move(extracted_dir, final_path)

            return True

        except Exception as e:
            messagebox.showerror("Java Error", f"Failed to download or extract Java:\n{e}")
            self.log_console(f"[ERROR] Java setup failed: {e}")
            return False

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
            messagebox.showwarning("Wait", "Start the server before editing settings.")
            return

        prop_window = tk.Toplevel(self.root)
        prop_window.title("Edit server.properties")
        prop_window.geometry("400x550")
        prop_window.configure(bg="#222")
        if self.icon_path:
            prop_window.iconbitmap(self.icon_path)

        entries = {}
        prop_path = os.path.join(self.output_folder.get(), "server.properties")
        if not os.path.exists(prop_path):
            messagebox.showerror("Error", "server.properties file not found.")
            return

        canvas = tk.Canvas(prop_window, bg="#222", highlightthickness=0)
        scrollbar = tk.Scrollbar(prop_window, orient="vertical", command=canvas.yview)
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

        with open(prop_path, "r") as f:
            lines = [line.strip() for line in f.readlines() if "=" in line]

        for line in lines:
            key, value = line.split("=", 1)
            tk.Label(scroll_frame, text=key, bg="#222", fg="white").pack()
            entry = tk.Entry(scroll_frame, bg="#333", fg="white")
            entry.insert(0, value)
            entry.pack(pady=2, fill="x", padx=10)
            entries[key] = entry

        # Preview and Set Icon section
        preview_label = tk.Label(scroll_frame, text="", bg="#222", fg="white")
        preview_label.pack(pady=(10, 0))

        def update_preview(path):
            try:
                img = Image.open(path)
                img.thumbnail((64, 64))
                img = ImageTk.PhotoImage(img)
                preview_label.configure(image=img)
                preview_label.image = img
            except Exception as e:
                preview_label.configure(text="(Preview unavailable)", fg="gray")

        def set_server_icon():
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
                update_preview(icon_path)
                preview_label.configure(text="✅ Icon updated!", fg="lightgreen")
                preview_label.after(3000, lambda: preview_label.configure(text=""))
            except Exception as e:
                messagebox.showerror("Error", f"Could not set icon:\n{e}")

        tk.Button(scroll_frame, text="Set Server Icon", command=set_server_icon, bg="#555", fg="white").pack(pady=10)

        def apply_changes():
            with open(prop_path, "w") as f:
                for key, entry in entries.items():
                    f.write(f"{key}={entry.get()}\n")
            messagebox.showinfo("Saved", "Settings applied. Restarting server...")
            self.restart_server()

        tk.Button(scroll_frame, text="Apply", command=apply_changes, bg="green", fg="white").pack(pady=20)

    def restart_server(self):
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()
            self.server_process = None
            self.server_started = False
        self.run_setup_thread()
    
    def check_or_install_ssh(self, folder):
        ssh_path = os.path.join(folder, "ssh.exe")
        if os.path.exists(ssh_path):
            return ssh_path

        self.log_console("Downloading SSH client (for Serveo)...")
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

    def on_close(self):
        if self.server_process and self.server_process.poll() is None:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except Exception as e:
                print(f"Error terminating server: {e}")
        self.root.destroy()

    def run_serveo_ssh(self):
        try:
            process = subprocess.Popen(
                ['ssh', '-o', 'StrictHostKeyChecking=no',
                 '-R', '0:localhost:25565', 'serveo.net'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            while True:
                line = process.stdout.readline()
                if not line:
                    break
                self.log_console("[Serveo] " + line.strip())

                if "Forwarding TCP" in line:
                    parts = line.strip().split(" ")
                    if len(parts) >= 5:
                        serveo_address = parts[-1] 
                        self.serveo_link.set(f"Serveo address: {serveo_address}")
                        self.serveo_label.pack() 

        except Exception as e:
            self.log_console(f"[ERROR] Serveo tunnel failed: {e}")

if __name__ == "__main__":
    from PIL import ImageTk
    import tkinter.ttk as ttk
    root = tk.Tk()
    app = MinecraftServerSetup(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

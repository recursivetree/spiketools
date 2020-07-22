import cmd
import os
import random
import sys
from pprint import pformat

import ampy.files
import ampy.pyboard
import serial.tools.list_ports


def read_path(base, child: str, file_mode=False):
    path_segments = []
    if not child.startswith("/"):
        path_segments = list(filter(None, base.split('/')))

    for extension in child.split("/"):
        if extension == "..":
            path_segments = path_segments[:-1]
        elif extension != "":
            path_segments.append(extension)
    path_string = ""
    for path_segment in path_segments:
        path_string += "/" + path_segment

    return path_string


class SpikeConsole(cmd.Cmd):
    def __init__(self):
        super().__init__()
        self.pyboard = None
        self.spike_file_system = None
        self.remote_path = "/"
        self.connected = False
        self.spike_file_cache = []

    def preloop(self):
        self.do_connect("")

    def connect_to(self, port):
        if port is not None:
            try:
                self.pyboard = ampy.pyboard.Pyboard(port)
                self.spike_file_system = ampy.files.Files(self.pyboard)
                self.remote_path = "/"
                self.build_prompt()
                self.connected = True
                print("Loading file cache...")
                self.spike_file_cache = self.spike_file_system.ls(directory="/", long_format=False, recursive=True)
                return True
            except ampy.pyboard.PyboardError:
                print("Failed to connect to {}".format(port))
                self.connected = False
                return False
        self.connected = False
        return False

    def build_prompt(self):
        self.prompt = self.remote_path + " >>"

    def do_connect(self, args):
        """
Connects to a spike.
Usage:
connect <port>
If the port is not specified, a selection menu opens.
        """
        if len(args) > 0:
            if not self.connect_to(args):
                self.prompt = "unconnected >>"
                return
            else:
                device = args
        else:
            # Wizard
            # Detect ports
            ports = serial.tools.list_ports.comports(False)

            # selection menu
            print("Available ports:")
            for x in range(len(ports)):
                print("{}: {}".format(x, ports[x].device))
            try:
                device = ports[int(input("type number of device: "))].device
            except (ValueError, IndexError):
                print("Invalid device number")
                self.prompt = "unconnected >>"
                return

            # Connect
            if not self.connect_to(device):
                return

        print("Successfully connected to {}".format(device))

    def do_cd(self, path):
        """
Changes the directory on the spike
Usage:
cd <path>
If no path is specified, it behaves as cd /.
        """
        if self.connected:
            if len(path) > 0:
                path = read_path(self.remote_path, path)
                found = False
                for iterpath in self.spike_file_cache:
                    if iterpath.startswith(path):
                        found = True
                if found:
                    self.remote_path = path
                else:
                    print("Path not found")
            else:
                self.remote_path = "/"
            self.build_prompt()
        else:
            print("please connect to a spike before using this command.")

    def do_ls(self, args):
        """
Lists all files in a directory.
Usage:
ls <path> <options>
If no path is specified, the current directory is used.
Available Options:
-s print file size
-r recursively print all subdirectories
        """
        if self.connected:
            path = self.remote_path
            recursive = False
            show_size = False
            for arg in args.split(" "):
                if arg.startswith("-"):
                    if arg == "-r":
                        recursive = True
                    elif arg == "-s":
                        show_size = True
                else:
                    path = read_path(self.remote_path, arg)
            try:
                for fs_obj in self.spike_file_system.ls(directory=path, long_format=show_size, recursive=recursive):
                    print(fs_obj)
            except RuntimeError as e:
                print("Failed to list directory contents: {}".format(e))
        else:
            print("please connect to a spike before using this command.")

    def do_cat(self, args):
        """
Prints the content of a file
Usage:
cat <*file> <options>
Available Options:
-r prints the raw data
        """
        if self.connected:
            raw_print = False
            for arg in args.split(" "):
                if arg.startswith("-"):
                    if arg == "-r":
                        raw_print = True
                else:
                    path = read_path(self.remote_path, arg)
            try:
                raw_data = self.spike_file_system.get(path)
                if raw_print:
                    print(raw_data)
                else:
                    try:
                        print(raw_data.decode("utf-8"))
                    except UnicodeDecodeError:
                        print("Not a text file! Try cat -r <file>")
            except RuntimeError as e:
                print("Failed to read file: {}".format(e))

        else:
            print("please connect to a spike before using this command.")

    def do_refresh_cache(self, args):
        """Reloads the file cache"""
        if self.connected:
            print("Refreshing...")
            self.spike_file_cache = self.spike_file_cache = self.spike_file_system.ls(directory="/", long_format=False,
                                                                                      recursive=True)
            print("Done")
        else:
            print("please connect to a spike before using this command.")

    def do_exit(self, args):
        self.pyboard.close()
        sys.exit()

    def do_upload(self, args):
        if self.connected:
            next_is_slot = False

            script_type = "python"
            slot = 0
            filename = None
            for arg in args.split(" "):
                if next_is_slot:
                    try:
                        slot = int(arg)
                    except ValueError:
                        print("Invalid slot id")
                        return
                    if slot > 20 or slot < 0:
                        print("Invalid slot id")
                        return
                    next_is_slot = False
                elif arg.startswith("-"):
                    if arg == "-slot":
                        next_is_slot = True
                    if arg == "-python":
                        script_type = "python"
                    if arg == "-scratch":
                        script_type = "scratch"
                else:
                    filename = arg

            if filename is None:
                print("Missing file to upload!")
                return

            if not os.path.isfile(filename):
                print("File not found!")
                return

            print("Loading slot configuration")
            slots_dict = eval(self.spike_file_system.get("/projects/.slots").decode("utf-8"))

            file_size = os.stat(filename).st_size
            created_time = int(os.path.getctime(filename))
            modified_time = int(os.path.getmtime(filename))
            file_id = 10000 + slot

            slots_dict[slot] = {
                "name": os.path.basename(filename),
                "created": created_time,
                "modified": modified_time,
                "size": file_size,
                "id": file_id,
                "project_id": "prj" + str(file_id),
                "type": script_type
            }

            print("Writing script")
            with open(filename, "rb") as f:
                self.spike_file_system.put("/projects/{}.py".format(file_id), f.read())

            print("Writing slot configuration")
            new_slots_file = str(slots_dict)
            self.spike_file_system.put("/projects/.slots", new_slots_file.encode("utf-8"))

            print("Done")
        else:
            print("please connect to a spike before using this command.")


SpikeConsole().cmdloop()

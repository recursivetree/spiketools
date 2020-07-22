import cmd
import os
import random
import sys
from pprint import pformat

import ampy.files
import ampy.pyboard
import serial.tools.list_ports

PROTECTED_PATHS = [
    '/boot.py',
    '/bt-lk1.dat',
    '/bt-lk2.dat',
    '/commands/__init__.mpy',
    '/commands/abstract_handler.mpy',
    '/commands/hub_methods.mpy',
    '/commands/light_methods.mpy',
    '/commands/linegraphmonitor_methods.mpy',
    '/commands/motor_methods.mpy',
    '/commands/move_methods.mpy',
    '/commands/program_methods.mpy',
    '/commands/sound_methods.mpy',
    '/commands/wait_methods.mpy',
    '/event_loop/__init__.mpy',
    '/event_loop/event_loop.mpy',
    '/hub_runtime.mpy',
    '/local_name.txt',
    '/main.py',
    '/programrunner/__init__.mpy',
    '/projects/.slots',
    '/projects/standalone.mpy',
    '/projects/standalone_/__init__.mpy',
    '/projects/standalone_/animation.mpy',
    '/projects/standalone_/device_helper.mpy',
    '/projects/standalone_/devices.mpy',
    '/projects/standalone_/display.mpy',
    '/projects/standalone_/priority_mapping.mpy',
    '/projects/standalone_/program.mpy',
    '/projects/standalone_/row.mpy',
    '/projects/standalone_/util.mpy',
    '/protocol/__init__.mpy',
    '/protocol/notifications.mpy',
    '/protocol/rpc_protocol.mpy',
    '/protocol/ujsonrpc.mpy',
    '/runtime/__init__.mpy',
    '/runtime/dirty_dict.mpy',
    '/runtime/extensions/__init__.mpy',
    '/runtime/extensions/abstract_extension.mpy',
    '/runtime/extensions/linegraphmonitor.mpy',
    '/runtime/extensions/music.mpy',
    '/runtime/extensions/sound.mpy',
    '/runtime/extensions/weather.mpy',
    '/runtime/multimotor.mpy',
    '/runtime/stack.mpy',
    '/runtime/timer.mpy',
    '/runtime/virtualmachine.mpy',
    '/runtime/vm_store.mpy',
    '/sounds/menu_click',
    '/sounds/menu_fastback',
    '/sounds/menu_program_start',
    '/sounds/menu_program_stop',
    '/sounds/menu_shutdown',
    '/sounds/startup',
    '/spike/__init__.mpy',
    '/spike/app.mpy',
    '/spike/button.mpy',
    '/spike/colorsensor.mpy',
    '/spike/control.mpy',
    '/spike/distancesensor.mpy',
    '/spike/forcesensor.mpy',
    '/spike/lightmatrix.mpy',
    '/spike/motionsensor.mpy',
    '/spike/motor.mpy',
    '/spike/motorpair.mpy',
    '/spike/operator.mpy',
    '/spike/primehub.mpy',
    '/spike/speaker.mpy',
    '/spike/statuslight.mpy',
    '/spike/util.mpy',
    '/system/__init__.mpy',
    '/system/abstractwrapper.mpy',
    '/system/callbacks/__init__.mpy',
    '/system/callbacks/customcallbacks.mpy',
    '/system/display.mpy',
    '/system/motors.mpy',
    '/system/motorwrapper.mpy',
    '/system/move.mpy',
    '/system/movewrapper.mpy',
    '/system/sound.mpy',
    '/ui/__init__.mpy',
    '/ui/hubui.mpy',
    '/util/__init__.mpy',
    '/util/animations.mpy',
    '/util/color.mpy',
    '/util/constants.mpy',
    '/util/error_handler.mpy',
    '/util/log.mpy',
    '/util/motor.mpy',
    '/util/parser.mpy',
    '/util/print_override.mpy',
    '/util/resetter.mpy',
    '/util/rotation.mpy',
    '/util/schedule.mpy',
    '/util/scratch.mpy',
    '/util/sensors.mpy',
    '/util/storage.mpy',
    '/util/time.mpy',
    '/version.py'
]



def read_path(base, child: str, file_mode=False):
    path_segments = set()
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
        self.spike_file_cache = set()

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
                self.spike_file_cache = set(self.spike_file_system.ls(directory="/", long_format=False, recursive=True))
                print(self.spike_file_cache)
                return True
            except ampy.pyboard.PyboardError as e:
                print(e)
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
                    if not show_size:
                        self.spike_file_cache.add(fs_obj)
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
            if path in self.spike_file_cache:
                try:
                    raw_data = self.spike_file_system.get(path)
                    if raw_print:
                        print(raw_data)
                    else:
                        try:
                            print(raw_data.decode("utf-8"))
                        except UnicodeDecodeError:
                            print("Not a text file! Try cat -r <file>")
                except (RuntimeError, ampy.pyboard.PyboardError) as e:
                    print("Failed to read file: {}".format(e))
            else:
                print("File not found!")
        else:
            print("please connect to a spike before using this command.")

    def do_refresh_cache(self, args):
        """Reloads the file cache"""
        if self.connected:
            print("Refreshing...")
            self.spike_file_cache = set(self.spike_file_system.ls(directory="/", long_format=False,
                                                                                      recursive=True))
            print("Done")
        else:
            print("please connect to a spike before using this command.")

    def do_exit(self, args):
        self.pyboard.close()
        sys.exit()

    def do_install(self, args):
        """
Installs a python script as if it is installed by the spike app.
Usage
install <*file> <options>
file is  the path to a file on your computer
Options
-slot    The slot where the script is installed. Number between 0-20, default 0
-python  Installs the script as a python script (default)
-scratch Installs the script as a scratch script
        """
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

            self.spike_file_cache.add("/projects/{}.py".format(file_id))
            print("Done")
        else:
            print("please connect to a spike before using this command.")

    def do_upload(self, path):
        if self.connected:
            if os.path.exists(path):
                if os.path.isfile(path):
                    with open(path, "rb") as f:
                        s_path = read_path(self.remote_path, os.path.basename(path))
                        self.spike_file_system.put(s_path, f.read())
                        self.spike_file_cache.add(s_path)
            else:
                print("path not found")
        else:
            print("please connect to a spike before using this command.")

    def do_rm(self, path):
        if self.connected:
            if path == "": return
            abspath = read_path(self.remote_path,path)
            if not abspath in self.spike_file_cache:
                print("File not found")
                return
            allowed = True
            for element in PROTECTED_PATHS:
                if element.startswith(abspath):
                    allowed = False
            if allowed:
                if not input("Confirm deleting {} with yes: ".format(abspath))=="yes":
                    print("Aborting")
                    return
                self.spike_file_cache.remove(abspath)
                self.spike_file_system.rm(abspath)
            else:
                print("Can't delete protected system files")
                return
        else:
            print("please connect to a spike before using this command.")



SpikeConsole().cmdloop()

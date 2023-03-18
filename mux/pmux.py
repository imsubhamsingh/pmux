import os
import subprocess
import sys
import curses
import signal


class Pane:
    def __init__(self, rows, cols, start_row, start_col):
        self.rows = rows
        self.cols = cols
        self.start_row = start_row
        self.start_col = start_col
        self.process = None

    def start(self, command):
        self.process = subprocess.Popen(
            command,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def stop(self):
        if self.process:
            self.process.terminate()

    def resize(self, rows, cols):
        self.rows = rows
        self.cols = cols

    def send_input(self, data):
        if self.process:
            self.process.stdin.write(data.encode())
            self.process.stdin.flush()

    def read_output(self):
        if self.process:
            return self.process.stdout.read()


class Multiplexer:
    def __init__(self, screen):
        self.screen = screen
        self.panes = []
        self.active_pane = None

    def create_pane(self, rows, cols, start_row, start_col):
        pane = Pane(rows, cols, start_row, start_col)
        self.panes.append(pane)
        return pane

    def get_active_pane(self):
        if not self.active_pane:
            self.active_pane = self.panes[0]
        return self.active_pane

    def resize_active_pane(self, rows, cols):
        pane = self.get_active_pane()
        pane.resize(rows, cols)
        self.draw_panes()

    def switch_active_pane(self, index):
        if index < 0 or index >= len(self.panes):
            return
        self.active_pane = self.panes[index]
        self.draw_panes()

    def start_active_pane(self, command):
        pane = self.get_active_pane()
        pane.start(command)
        self.draw_panes()

    def stop_active_pane(self):
        pane = self.get_active_pane()
        pane.stop()
        self.draw_panes()

    def send_input_to_active_pane(self, data):
        pane = self.get_active_pane()

        # This error occurs because the process being executed
        # in a pane has stopped running, or data is being sent to
        # an already-closed process. You can handle this exception
        # by checking if the pane process is running before sending
        # input to it.

        if pane.process.poll() is None:
            try:
                pane.send_input(data)
            except BrokenPipeError:
                pass

    def draw_panes(self):
        self.screen.clear()
        for pane in self.panes:
            self.screen.addstr(
                pane.start_row, pane.start_col, "+" + "-" * (pane.cols - 2) + "+"
            )
            for row in range(pane.rows - 2):
                self.screen.addstr(
                    pane.start_row + row + 1,
                    pane.start_col,
                    "|" + " " * (pane.cols - 2) + "|",
                )
            self.screen.addstr(
                pane.start_row + pane.rows - 1,
                pane.start_col,
                "+" + "-" * (pane.cols - 2) + "+",
            )
        self.screen.refresh()

    def handle_input(self, key):
        if key == ord("q"):
            sys.exit(0)
        elif key == ord("\t"):
            index = self.panes.index(self.get_active_pane())
            index = (index + 1) % len(self.panes)
            self.switch_active_pane(index)
        elif key == curses.KEY_RESIZE:
            self.draw_panes()
        elif key == ord(":"):  # Add new binding for running command
            curses.echo()
            curses.curs_set(1)
            self.screen.addstr("> ")
            self.screen.refresh()
            command = self.screen.getstr().decode()
            self.run_command_in_active_pane(command)
            curses.noecho()
            curses.curs_set(0)
        else:
            self.send_input_to_active_pane(chr(key))

    def run(self):
        self.draw_panes()
        while True:
            key = self.screen.getch()
            self.handle_input(key)


def signal_handler(signal, frame):
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, signal_handler)
    screen = curses.initscr()
    curses.noecho()

    multiplexer = Multiplexer(screen)
    pane1 = multiplexer.create_pane(10, 50, 0, 0)
    pane2 = multiplexer.create_pane(10, 50, 0, 51)
    multiplexer.start_active_pane('echo "Pane 1"')
    multiplexer.switch_active_pane(1)
    multiplexer.start_active_pane('echo "Pane 2"')

    try:
        multiplexer.run()
    finally:
        curses.echo()
        curses.endwin()
        pane1.stop()
        pane2.stop()


if __name__ == "__main__":
    main()

import asyncio
import json
import sys
import aiohttp
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QPushButton, QTextEdit, QStyleOptionTab, QStyle, QTabBar
)
from PyQt5.QtCore import pyqtSignal, Qt, QSize
from PyQt5.QtGui import QPainter, QColor, QPalette
from qasync import QEventLoop, asyncSlot

server_url = "http://127.0.0.1"

class TerminalTab(QWidget):
    output_updated = pyqtSignal()

    def __init__(self, tab_name, script, directory):
        super().__init__()
        self.tab_name = tab_name
        self.script = script
        self.directory = directory
        self.proc = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        layout.addWidget(self.console_output)
        self.setLayout(layout)

    async def run_commands(self):
        if self.proc:
            self.console_output.append("Commands are already running.")
            return

        command = self.script
        self.console_output.append(f"Starting: {command}")
        self.proc = await asyncio.create_subprocess_shell(
            command,
            cwd=self.directory,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        asyncio.ensure_future(self.read_output(self.proc))
        await self.proc.wait()
        self.console_output.append(f"Finished: {command}\n")
        self.proc = None

    async def read_output(self, proc):
        while proc and not proc.stdout.at_eof():
            line = await proc.stdout.readline()
            if line:
                self.console_output.append(line.decode())
                self.console_output.ensureCursorVisible()
                self.output_updated.emit()
            await asyncio.sleep(0.1)

    def terminate_process(self):
        if self.proc:
            self.proc.terminate()
            self.console_output.append("Process terminated.")
            self.proc = None

class CustomTabBar(QTabBar):
    def __init__(self, parent=None):
        super(CustomTabBar, self).__init__(parent)
        self.tabBackgroundColors = {}
        self.tabFontColors = {}
        self.setExpanding(False)
        self.setStyleSheet("QTabBar::tab { height: 30px; }")

    def setTabBackgroundColor(self, index, bg_color, font_color=None):
        self.tabBackgroundColors[index] = bg_color
        if font_color:
            self.tabFontColors[index] = font_color
        self.update()

    def resetTabBackgroundColor(self, index):
        if index in self.tabBackgroundColors:
            del self.tabBackgroundColors[index]
        if index in self.tabFontColors:
            del self.tabFontColors[index]
        self.update()

    def tabSizeHint(self, index):
        size = super(CustomTabBar, self).tabSizeHint(index)
        # Set max tab width
        size.setWidth(min(size.width(), 200))
        return size

    def paintEvent(self, event):
        painter = QPainter(self)
        option = QStyleOptionTab()

        for index in range(self.count()):
            self.initStyleOption(option, index)

            # Set bg color
            if index in self.tabBackgroundColors:
                bg_color = self.tabBackgroundColors[index]
                painter.save()
                rect = self.tabRect(index)
                painter.fillRect(rect, bg_color)
                painter.restore()

            # font color
            if index in self.tabFontColors:
                font_color = self.tabFontColors[index]
                option.palette.setColor(QPalette.ButtonText, font_color)
                option.palette.setColor(QPalette.WindowText, font_color)
            else:
                # to default font color
                default_font_color = self.palette().color(QPalette.ButtonText)
                option.palette.setColor(QPalette.ButtonText, default_font_color)
                option.palette.setColor(QPalette.WindowText, default_font_color)

            self.style().drawControl(QStyle.CE_TabBarTab, option, painter, self)

    def sizeHint(self):
        total_width = self.parent().width()
        if self.count() > 0:
            max_tab_width = max(self.tabSizeHint(i).width() for i in range(self.count()))
            tabs_per_row = max(1, total_width // max_tab_width)
            rows = (self.count() + tabs_per_row - 1) // tabs_per_row
            tab_height = super(CustomTabBar, self).tabSizeHint(0).height()
        else:
            max_tab_width = total_width
            tabs_per_row = 1
            rows = 1
            default_tab_height = 30
            tab_height = default_tab_height
        return QSize(total_width, rows * tab_height)

class TerminalApp(QMainWindow):
    def __init__(self, command_sets):
        super().__init__()
        self.setWindowTitle("Terminal Manager")
        self.tab_widget = QTabWidget()
        self.tab_bar = CustomTabBar()
        self.tab_widget.setTabBar(self.tab_bar)
        self.setCentralWidget(self.tab_widget)
        self.terminal_tabs = []
        self.services = []
        self.script_pattern = (
            'npx wrangler@latest dev --local '
            #'--local-protocol https '
            #'--https-key-path D:/Project/uwu/ssl/ssl.key '
            #'--https-cert-path D:/Project/uwu/ssl/ssl.crt '
            #'--host '+server_url+' '
            '--port {PORT}'
        )
        self.add_main_tab()
        for command_set in command_sets:
            self.add_terminal_tab(command_set)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

    def add_main_tab(self):
        main_tab = QWidget()
        layout = QVBoxLayout()

        self.start_all_button = QPushButton("Start All")
        self.start_all_button.clicked.connect(self.start_all_tabs)

        self.stop_all_button = QPushButton("Stop All")
        self.stop_all_button.clicked.connect(self.stop_all_processes)

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close_application)

        # Status Checker UI elements
        self.check_button = QPushButton("Check All Services")
        self.check_button.clicked.connect(self.check_all_services)
        self.result_output = QTextEdit()
        self.result_output.setReadOnly(True)

        # 'Mark All as Read' button
        self.mark_all_button = QPushButton("Mark All as Read")
        self.mark_all_button.clicked.connect(self.mark_all_as_read)

        # Add all widgets to the layout
        layout.addWidget(self.start_all_button)
        layout.addWidget(self.stop_all_button)
        layout.addWidget(self.close_button)
        layout.addWidget(self.check_button)
        layout.addWidget(self.result_output)
        layout.addWidget(self.mark_all_button)

        main_tab.setLayout(layout)
        self.tab_widget.addTab(main_tab, "Main")

    @asyncSlot()
    async def start_all_tabs(self):
        self.start_all_button.setEnabled(False)
        tasks = [tab.run_commands() for tab in self.terminal_tabs]
        for task in tasks:
            asyncio.ensure_future(task)

    @asyncSlot()
    async def stop_all_processes(self):
        for tab in self.terminal_tabs:
            tab.terminate_process()
        self.start_all_button.setEnabled(True)

    @asyncSlot()
    async def check_all_services(self):
        self.check_button.setEnabled(False)
        self.result_output.clear()
        tasks = [self.check_service(service) for service in self.services]
        await asyncio.gather(*tasks)
        self.check_button.setEnabled(True)

    async def check_service(self, service):
        name = service['name']
        port = service['port']
        url = f"{server_url}:{port}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, ssl=False, timeout=5) as resp:
                    status = resp.status
        except Exception as e:
            status = f"Error: {str(e)}"
        self.result_output.append(f"{name} (Port {port}) - Status: {status}")
        self.result_output.ensureCursorVisible()

    def add_terminal_tab(self, command_set):
        script_name = command_set.get('script_name', 'Unknown')
        directory = command_set.get('directory', '')
        port = command_set.get('port', None)
        if port is not None:
            self.services.append({'port': port, 'name': script_name})
        script = self.script_pattern.format(PORT=port)
        tab = TerminalTab(script_name, script, directory)
        self.tab_widget.addTab(tab, script_name)
        self.terminal_tabs.append(tab)

        tab.output_updated.connect(lambda tn=script_name: self.highlight_tab(tn))

    def highlight_tab(self, tab_name):
        index = self.get_tab_index_by_name(tab_name)
        if index != -1:
            self.tab_bar.setTabBackgroundColor(index, QColor('yellow'), font_color=QColor('red'))

    def on_tab_changed(self, index):
        self.tab_bar.resetTabBackgroundColor(index)

    def mark_all_as_read(self):
        for i in range(self.tab_widget.count()):
            if i == 0:
                continue
            self.tab_bar.resetTabBackgroundColor(i)

    def get_tab_index_by_name(self, tab_name):
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == tab_name:
                return i
        return -1

    @asyncSlot()
    async def close_application(self):
        for tab in self.terminal_tabs:
            tab.terminate_process()
        await self.make_web_requests()
        self.close()

    async def make_web_requests(self):
        for service in self.services:
            port = service['port']
            url = f"{server_url}:{port}"
            for _ in range(2):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, ssl=False, timeout=5) as resp:
                            pass
                except Exception as e:
                    pass
                await asyncio.sleep(0.5)

    def closeEvent(self, event):
        for tab in self.terminal_tabs:
            tab.terminate_process()
        QApplication.instance().quit()
        event.accept()

async def load_commands():
    with open('commands.json', 'r') as f:
        command_sets = json.load(f)
    return command_sets

async def main():
    command_sets = await load_commands()
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    terminal_app = TerminalApp(command_sets)
    terminal_app.show()
    app.aboutToQuit.connect(loop.stop)
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    asyncio.run(main())

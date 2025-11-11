from textual.widgets import Static


SIGPLAY_ASCII = """
 ███████╗██╗ ██████╗ ██████╗ ██╗      █████╗ ██╗   ██╗
 ██╔════╝██║██╔════╝ ██╔══██╗██║     ██╔══██╗╚██╗ ██╔╝
 ███████╗██║██║  ███╗██████╔╝██║     ███████║ ╚████╔╝ 
 ╚════██║██║██║   ██║██╔═══╝ ██║     ██╔══██║  ╚██╔╝  
 ███████║██║╚██████╔╝██║     ███████╗██║  ██║   ██║   
 ╚══════╝╚═╝ ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═╝   ╚═╝   
"""


class Header(Static):
    def compose(self):
        """Compose the header with ASCII art."""
        yield Static(SIGPLAY_ASCII, id="header")

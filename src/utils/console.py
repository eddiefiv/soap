import re
import datetime
import os
import json

from rich.columns import Columns
from rich.console import Console
from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.style import StyleType

console = Console()

# Get the directory of the script being executed
current_directory = os.path.dirname(os.path.abspath(__file__))

# Navigate to the parent directory (Corporate America) relative to the script's directory
parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir, os.pardir))

# Navigate to the config directory relative to the script's directory
config_directory = os.path.join(parent_directory, 'config')

# Path to the node_metrics.json file relative to the script's directory
node_metrics_file_path = os.path.join(config_directory, 'node_metrics.json')

# Path to the global.jsoon file relative to the script's directory
global_config_file_path = os.path.join(config_directory, 'global.json')

def print_markdown(text):
    """Prints a rich info message. Support Markdown syntax."""

    md = Padding(Markdown(text), 2)
    console.print(md)


def print_step(text, justification='left', style =""):
    """Prints a rich info message."""

    panel = Panel(Text(text, justify=justification), style=style)
    console.print(panel)


def print_table(title, items: list, columns: list, color="yellow"):
    """Prints items in a table."""

    table = Table(title = title)

    for column in columns:
        table.add_column(column)

    for item in items:
        table.add_row(*item, style = color)

    console.print(table)


def make_table(title, items: list, columns: list, color="yellow"):
    """Prints items in a table."""

    table = Table(title = title)

    for column in columns:
        table.add_column(column)

    for item in items:
        table.add_row(*item, style = "blue3")

    return


def print_substep(text, style=""):
    """Prints a rich info message without the panelling."""
    console.print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')}] {text}", style=style)

def print_success(text):
    print_substep(text = text, style = "green1")

def print_info(text):
    print_substep(text = f"INFO: {text}", style = "bright_blue")

def print_warning(text):
    print_substep(text = f"WARNING: {text}", style = "gold3")

def print_error(text):
    print_substep(text = f"ERROR: {text}", style = "red1")

def print_debug(text):
    if global_config['dev']['debug_mode']:
        print_substep(text = f"DEBUG: {text}", style = "dark_green")

try:
    with open(global_config_file_path, 'r') as f:
        _r = f.read()
        global_config = json.loads(_r)
except Exception as e:
    print_error(text = f"Console couldnt load and set configs from config.json, resorting to default configs. {e}")
    global_config = {
        "general": {
            "agent_count": 2,
            "worker_count": 3
        },
        "models": {
            "70b_filepath": None,
            "13b_filepath": None,
            "7b_filepath": None
        },
        "dev": {
            "debug_mode": False
        }
    }

def handle_input(
    message: str = "",
    check_type=False,
    match: str = "",
    err_message: str = "",
    nmin=None,
    nmax=None,
    oob_error="",
    extra_info="",
    options: list = None,
    default=NotImplemented,
    optional=False,
):
    if optional:
        console.print(
            message
            + "\n[green]This is an optional value. Do you want to skip it? (y/n)"
        )
        if input().casefold().startswith("y"):
            return default if default is not NotImplemented else ""
    if default is not NotImplemented:
        console.print(
            "[green]"
            + message
            + '\n[blue bold]The default value is "'
            + str(default)
            + '"\nDo you want to use it?(y/n)'
        )
        if input().casefold().startswith("y"):
            return default
    if options is None:
        match = re.compile(match)
        console.print("[green bold]" + extra_info, no_wrap=True)
        while True:
            console.print(message, end="")
            user_input = input("").strip()
            if check_type is not False:
                try:
                    user_input = check_type(user_input)
                    if (nmin is not None and user_input < nmin) or (
                        nmax is not None and user_input > nmax
                    ):
                        # FAILSTATE Input out of bounds
                        console.print("[red]" + oob_error)
                        continue
                    break  # Successful type conversion and number in bounds
                except ValueError:
                    # Type conversion failed
                    console.print("[red]" + err_message)
                    continue
            elif match != "" and re.match(match, user_input) is None:
                console.print(
                    "[red]"
                    + err_message
                    + "\nAre you absolutely sure it's correct?(y/n)"
                )
                if input().casefold().startswith("y"):
                    break
                continue
            else:
                # FAILSTATE Input STRING out of bounds
                if (nmin is not None and len(user_input) < nmin) or (
                    nmax is not None and len(user_input) > nmax
                ):
                    console.print("[red bold]" + oob_error)
                    continue
                break  # SUCCESS Input STRING in bounds
        return user_input
    console.print(extra_info, no_wrap=True)
    while True:
        console.print(message, end="")
        user_input = input("").strip()
        if check_type is not False:
            try:
                isinstance(eval(user_input), check_type)
                return check_type(user_input)
            except:
                console.print(
                    "[red bold]"
                    + err_message
                    + "\nValid options are: "
                    + ", ".join(map(str, options))
                    + "."
                )
                continue
        if user_input in options:
            return user_input
        console.print(
            "[red bold]"
            + err_message
            + "\nValid options are: "
            + ", ".join(map(str, options))
            + "."
        )
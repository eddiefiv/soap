import requests
import os
import time

from discord import Client, Intents, Color

from utils.console import print_step, print_substep, print_markdown, print_table
from utils.discord_utils import make_embed, send_msg
from utils.ui import print_logo

from platform import system, node, release, version, machine, processor
from socket import gethostname, gethostbyname
from psutil import virtual_memory, cpu_stats, cpu_count, cpu_percent

channel_id = 1195786304563195984
sample_author_url = "https://icons.iconarchive.com/icons/elegantthemes/beautiful-flat/256/Computer-icon.png"

intents = Intents.all()
bot_client = Client(intents = intents)

columns = ["System", "Node Name", "Version", "Machine", "Long Processor"]
items = [[system(), node(), version(), machine(), processor()]]

columns2 = ["Available Virtual Memory", "Percent Allocated (used memory)"]
items2 = [[f"{str(round(virtual_memory().available / (1024.0 **3), 2))} GB", f"{str(virtual_memory().percent)} %"]]

print_logo()

print_table("System Info", items = items, columns = columns, color = "blue1")
print_substep(f"Total System Virtual Memory -> {str(round(virtual_memory().total / (1024.0 **3), 2))} GB", style = "green1")

print_table("System Metrics", items = items2, columns = columns2, color = "yellow1")

@bot_client.event
async def on_ready():
    embed = make_embed(
        title = "Sign On Event",
        color = Color.blue(),
        desc = "\n\n> **Message**\n> Server connected. Clients can log in and connect to the network"
    )
    embed.set_author(
        name = f"{node()} (Server)",
        icon_url = sample_author_url
    )

    await bot_client.get_channel(channel_id).send(embed = embed)

def start_bot():
    with open("disctoken.txt", "r") as f:
        token = f.readline()
    bot_client.run(token)

if __name__ == "__main__":
    start_bot()
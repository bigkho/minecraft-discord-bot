import os
from nextcord.ext import commands
import requests
import asyncio
from dotenv import load_dotenv
import nextcord

intents = nextcord.Intents.default()
intents.message_content = True

load_dotenv()
MINECRAFT_SERVER_IP = os.getenv('MINECRAFT-SERVER-IP')

server_channels = {}


def get_minecraft_server_status():
    try:
        response = requests.get(f'https://api.mcsrvstat.us/3/{MINECRAFT_SERVER_IP}')

        # Check if the response status code is 200 (OK)
        if response.status_code == 200:
            data = response.json()
            return data
        elif response.status_code == 404:
            return None
        else:
            print(f"Received an unexpected response from the Minecraft server status API: {response.status_code}")
            return None

    except Exception as e:
        print(f"Error checking Minecraft server status: {e}")
        return None


previous_state = None


def run_discord_bot():
    TOKEN = os.getenv('TOKEN')
    bot = commands.Bot(command_prefix='!', intents=intents)

    @bot.event
    async def on_ready():
        print(f'Logged in as {bot.user.name} ({bot.user.id})')
        global previous_state, channel

        for guild in bot.guilds:
            # Get the default channel by name, if it exists
            default_channel = next((channel for channel in guild.text_channels if channel.name == "general"),
                                   None)

            # If the default channel is found, store its ID
            if default_channel:
                server_channels[guild.id] = default_channel.id
            else:
                # If the default channel doesn't exist, you can choose another channel or handle this case differently
                # For example, you can select the first available text channel
                text_channels = [channel for channel in guild.text_channels if
                                 isinstance(channel, nextcord.TextChannel)]
                if text_channels:
                    server_channels[guild.id] = text_channels[0].id
                else:
                    # Handle the case where there are no text channels in the server
                    # You can choose to log an error or take another action here
                    pass

        while True:
            server_data = get_minecraft_server_status()
            if server_data:
                current_state = server_data.get('online', False)
                players = server_data.get('players', {})
                player_list = players.get('list', [])

                if current_state != previous_state:

                    for server_id, channel_id in server_channels.items():
                        server = bot.get_guild(int(server_id))
                        channel = server.get_channel(int(channel_id)) if server else None

                    if current_state:
                        await bot.change_presence(status=nextcord.Status.online,
                                                  activity=nextcord.Game("Server Online"))
                        print('Currently Online')
                    else:
                        await bot.change_presence(status=nextcord.Status.dnd,
                                                  activity=nextcord.Game("Server Offline"))
                        print('Currently Offline')

                    if channel:
                        embed = nextcord.Embed(
                            title="Minecraft Server Status",
                            description="The status of the Minecraft server has changed.",
                            color=0x00ff00 if current_state else 0xff0000  # Green for online, red for offline
                        )
                        embed.add_field(name="Server Address", value=MINECRAFT_SERVER_IP, inline=False)
                        embed.add_field(name="Status", value="Online" if current_state else "Offline", inline=False)

                        # Display active players if the server is online
                        if current_state:
                            if player_list:
                                player_names = [player.get('name', 'Unknown') for player in player_list]
                                player_list_str = '\n'.join(player_names)
                                embed.add_field(name="Active Players", value=player_list_str, inline=False)
                            else:
                                embed.add_field(name="Active Players", value="No active players", inline=False)

                        embed.add_field(name="Commands",
                                        value="Use `/server` to see server rules and `/status` to check the server "
                                              "status.",
                                        inline=False)

                        await channel.send(embed=embed)

                    previous_state = current_state

            await asyncio.sleep(60)  # Check server status every minute

    @bot.slash_command(
        name="status",
        description="Check the status of the Minecraft server."
    )
    async def check_server_status(interaction: nextcord.Interaction):
        server_data = get_minecraft_server_status()
        if server_data:
            current_state = server_data.get('online', False)
            players = server_data.get('players', {})
            player_list = players.get('list', [])

            embed = nextcord.Embed(
                title="Minecraft Server Status",
                description="Here is the current status of the Minecraft server:",
                color=nextcord.Color.green() if current_state else nextcord.Color.red()
                # Green for online, red for offline
            )
            embed.add_field(name="Server Address", value=MINECRAFT_SERVER_IP, inline=False)
            embed.add_field(name="Status", value="Online" if current_state else "Offline", inline=False)

            # Display active players if the server is online
            if current_state:
                if player_list:
                    player_names = [player.get('name', 'Unknown') for player in player_list]
                    player_list_str = '\n'.join(player_names)
                    embed.add_field(name="Active Players", value=player_list_str, inline=False)
                else:
                    embed.add_field(name="Active Players", value="No active players", inline=False)

            await interaction.response.send_message(embed=embed, ephemeral=False)

    @bot.slash_command(
        name="server",
        description="Welcome to the LifeSteal server and read the server rules."
    )
    async def display_server_info(interaction: nextcord.Interaction):  # Add the 'interaction' parameter
        # Create an embedded message with the server welcome and rules
        embed = nextcord.Embed(
            title="Welcome to the LifeSteal Server!",
            description=(
                "Here's some important information about our server:\n\n"
                "1. **Server Rules**:\n\n"
                "   - If you die by any means, you will lose a full 1 heart.\n"
                "   - If you are killed by another player by any means, that player will gain a heart, while you lose yours.\n"
                "   - You can put your own hearts into your inventory by using the `/heartdrop` command or `/hd` for short, followed by the number of hearts you would like to remove.\n"
                "   - Be aware that the amount of hearts removed will reflect on your health, so be careful. You may consume these hearts at any time or give them to another player.\n"
                "   - If you lose all your hearts, you are BANNED from the server, but you may be able to come back if desired.\n\n"
                "2. **Basic Rules**:\n\n"
                "   - You can kill players on the server, but you must do so respectfully. Do not spam kill a player, and give them back whatever they need to get back on their feet.\n"
                "   - You should be killing for hearts, not to destroy the player's enjoyment.\n"
                "   - You may hurt and grief other players, but there's a limit. Understand that everyone has their limits, and don't try to upset someone to get them kicked out of the server."
            ),
            color=nextcord.Color.gold()  # You can choose an appropriate color
        )

        await interaction.response.send_message(embed=embed, ephemeral=False)

    @bot.slash_command(
        name="announce",
        description="Choose the server channel you would like announcements in."
    )
    async def set_status_channel(interaction: nextcord.Interaction):
        await interaction.response.defer()
        # Check if the user has administrator permissions
        if interaction.channel.permissions_for(interaction.user).administrator:
            # Store the selected channel's ID for this server
            server_channels[interaction.guild.id] = interaction.channel.id
            await interaction.followup.send(
                f"Server status updates will be sent to {interaction.channel.mention}",
                ephemeral=True  # Make the response ephemeral (visible only to the user who issued the command)
            )
        else:
            await interaction.followup.send(
                "You do not have permission to use this command.",
                ephemeral=True
            )

    @bot.slash_command(
        name="recipes",
        description="Showcase recipes of the server."
    )
    async def set_status_channel(interaction: nextcord.Interaction):
        embed = nextcord.Embed(
            title="Lifesteal Official Recipes",
            color=nextcord.Color.magenta()
        )

        embed.add_field(
            name="Heart",
            value="Crafting a heart is made to be extremely difficult. It's done to show that you have conquered all "
                  "difficult aspects of the game.",
            inline=False,
        )
        embed.set_image(url="https://i.ibb.co/zsP1w08/recipe3.png")

        embed.add_field(
            name="Life Bringer",
            value="Once you lose all your hearts, it's game over. However, by having others sacrifice their hearts, "
                  "you can come back with 5 hearts to your name. This allows you to not be fully lost in the ban "
                  "realm.",
            inline=False,
        )
        embed.set_image(url="https://i.ibb.co/jRt7zcj/recipe1.png")

        embed.add_field(
            name="Totem of Undying",
            value="An actual recipe now exists for the famous Totem of Undying. Obtain a player head by killing other "
                  "players and use it to craft a Totem.",
            inline=False,
        )
        embed.set_image(url="https://i.ibb.co/zsP1w08/recipe3.png")

        await interaction.response.send_message(embed=embed, ephemeral=False)

    bot.run(TOKEN)

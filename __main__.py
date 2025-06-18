import discord, os, datetime
from discord.ext.voice_recv.voice_client import VoiceRecvClient

import openwakeword
from oww_sink import AsyncOpenWakeWordSink

SOUNDBOARD_ID = 1363476761576210616
MODEL = "hit_the_aw_button.tflite"

intents = discord.Intents()
intents.voice_states = True
intents.guilds = True

client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

openwakeword.utils.download_models(model_names=["melspectrogram"])

@client.event
async def on_ready():
    await tree.sync()
    print(f"We have logged in as '{client.user}'")

@tree.command(name="join", description="Join your voice channel.")
async def join(interaction: discord.Interaction):
    if interaction.user.voice is None:
        return await interaction.response.send_message("You are not in a voice channel!", ephemeral=True)
    if interaction.user.voice.channel is None:
        return await interaction.response.send_message("Failed to join voice channel, I may not have the required permissions.", ephemeral=True)

    channel = interaction.user.voice.channel;
    try:
        voice_client = await channel.connect(cls=VoiceRecvClient)
    except Exception as e:
        return await interaction.response.send_message(f"{e}")

    soundboard = interaction.guild.get_soundboard_sound(SOUNDBOARD_ID)
    last_time = datetime.datetime.min

    async def handle_predictions(user: discord.User, predictions: dict):
        nonlocal last_time

        current_time = datetime.datetime.now()
        delta = current_time - last_time

        if any(score > 0.5 for score in predictions.values()) and delta.total_seconds() > 1.0:
            print(f"Wake word detected from {user.name}: {predictions}")
            last_time = current_time
            await channel.send_sound(soundboard)

    sink = AsyncOpenWakeWordSink(
        wakeword_models=["./models/" + MODEL],
        async_pred_cb=handle_predictions
    )
    voice_client.listen(sink)
    
    await interaction.response.send_message(f"Joined {channel.name}!")

@tree.command(name="leave", description="Leave the current voice channel.")
async def leave(interaction: discord.Interaction):
    if interaction.guild.voice_client is None:
        return await interaction.response.send_message("I am not in a voice channel!", ephemeral=True)
    
    channel = interaction.guild.voice_client.channel
    await interaction.guild.voice_client.disconnect()
    await interaction.response.send_message(f"Left {channel.name}.")

@tree.command(name="wtfisthis", description="Explains wtf this bot is.")
async def wtfisthis(interaction: discord.Interaction):
    return await interaction.response.send_message("Haha, definitely not government spyware :)\n\n- Go in voice chat\n- Run the `/join` command\n- Say \"hit the awww button\"\nand the bot will play the 'awww' soundboard.\n\nIt uses speech recognition stuff, it's pretty shit so you'll probably have to say it a few times... and also say it in a british accent that helps for some reason sorry not sorry.")

@tree.command(name="reload", description="Reload the bot. For developers.")
async def reload(interaction: discord.Interaction):
    await tree.sync(guild=interaction.guild)
    await interaction.response.send_message(f"Reloaded!")

token = os.getenv('TOKEN')
if token:
    client.run(token)
else:
    print("Missing environment variable 'TOKEN'")
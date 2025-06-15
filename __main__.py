import discord, os, asyncio
from discord.ext import voice_recv  
from discord.ext.voice_recv.extras import SpeechRecognitionSink  

intents = discord.Intents()
intents.voice_states = True
intents.guilds = True

client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

@client.event
async def on_ready():
    await tree.sync()
    print(f"We have logged in as '{client.user}'")

@tree.command(name="join", description="Join your voice channel")
async def join(interaction: discord.Interaction):
    if interaction.user.voice is None:
        return await interaction.response.send_message("You are not in a voice channel!", ephemeral=True)
    if interaction.user.voice.channel is None:
        return await interaction.response.send_message("Failed to join voice channel, I may not have the required permissions.", ephemeral=True)

    channel = interaction.user.voice.channel;
    voice_client = await channel.connect(cls=voice_recv.VoiceRecvClient)
    await interaction.response.send_message(f"Joined {channel.name}!")

    soundboard = interaction.guild.get_soundboard_sound(1363476761576210616)
    play = lambda: channel.send_sound(soundboard)

    sink = AsyncSpeechRecognitionSink(
        default_recognizer='google',
        phrase_time_limit=16,
        async_text_cb=lambda user, text: handle_text(play, user, text)
    )
    
    voice_client.listen(sink)

class AsyncSpeechRecognitionSink(SpeechRecognitionSink):  
    def __init__(self, async_text_cb=None, **kwargs):  
        self.async_text_cb = async_text_cb  
        super().__init__(text_cb=self._sync_text_wrapper, **kwargs)  
      
    def _sync_text_wrapper(self, user, text):  
        if self.async_text_cb:  
            self._await(self.async_text_cb(user, text))

async def handle_text(play, user: discord.User, text: str):
    accuracy = get_accuracy_full(text)
    if accuracy > 0.45: await play()
    print(f"{user.name} said: {text}  |  accuracy {accuracy} > 0.45")

def get_accuracy_full(text: str):
    text = text.lower()
    start = 0 if text.startswith("hit") else text.find(" hit")
    if start < 0:
        return 0
    
    if get_accuracy(text[start:], "hit the") > 0.65:
        return 1

    last_word = text.find("a", start)
    if last_word < 0:
        return 0

    end = text.find(" ", last_word)
    if end < 0:
        end = len(text)
    
    text = text[start:end]

    accuracyHitThe = get_accuracy(text, "hit the")
    accuracyAw = get_accuracy(text, "auto") + get_accuracy(text, "all") + get_accuracy(text, "aw")
    return accuracyHitThe + accuracyAw

def get_accuracy(s: str, o: str):
    def createBigram(s: str) -> set:
        bigram = set()
        for i in range(len(s)-1):
            bigram.add(s[i:i+2])
        return bigram

    sBigram = createBigram(s.strip().lower())
    oBigram = createBigram(o.strip().lower())
    bigram = sBigram.intersection(oBigram)

    return (len(bigram) * 2) / (len(sBigram) + len(oBigram))

@tree.command(name="leave", description="Leave the current voice channel")
async def leave(interaction: discord.Interaction):
    if interaction.guild.voice_client is None:
        return await interaction.response.send_message("I am not in a voice channel!", ephemeral=True)
    
    channel = interaction.guild.voice_client.channel
    await interaction.guild.voice_client.disconnect()
    await interaction.response.send_message(f"Left {channel.name}.")

@tree.command(name="reload", description="Reload the bot")
async def reload(interaction: discord.Interaction):
    tree.sync(guild=interaction.guild)

token = os.getenv('TOKEN')
if token:
    client.run(token)
else:
    print("Missing environment variable 'TOKEN'")
import discord, os, asyncio
from discord.ext import voice_recv  
from discord.ext.voice_recv.extras import SpeechRecognitionSink  

SOUNDBOARD_ID = 1363476761576210616

intents = discord.Intents()
intents.voice_states = True
intents.guilds = True

client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

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
        voice_client = await channel.connect(cls=voice_recv.VoiceRecvClient)
    except Exception as e:
        return await interaction.response.send_message(f"{e}")

    soundboard = interaction.guild.get_soundboard_sound(SOUNDBOARD_ID)
    play = lambda: channel.send_sound(soundboard)

    sink = AsyncSpeechRecognitionSink(
        default_recognizer='google',
        phrase_time_limit=30,
        async_text_cb=lambda user, text: handle_text(play, user, text)
    )
    voice_client.listen(sink)
    
    await interaction.response.send_message(f"Joined {channel.name}!")

class AsyncSpeechRecognitionSink(SpeechRecognitionSink):  
    def __init__(self, async_text_cb=None, **kwargs):  
        self.async_text_cb = async_text_cb  
        super().__init__(text_cb=self._sync_text_wrapper, **kwargs)  
      
    def _sync_text_wrapper(self, user, text):  
        if self.async_text_cb:  
            self._await(self.async_text_cb(user, text))

async def handle_text(play, user: discord.User, text: str):
    accuracy = get_accuracy(text)
    if accuracy > 0.45: await play()
    print(f"{user.name} said: {text}  |  accuracy {accuracy} > 0.45")

def get_accuracy(text: str):
    """
    Score the similarity of the speech-to-text output and the phrase 'hit the awww button'
    """
    text = text.lower()

    if "50" in text:
        return 1

    start = 0 if text.startswith("hit") else text.find(" hit")
    if start < 0:
        return 0
    
    if bigram_similarity(text[start:], "hit the") > 0.65:
        return 1

    last_word = text.find("a", start)
    if last_word < 0:
        return 0

    end = text.find(" ", last_word)
    if end < 0:
        end = len(text)
    
    text = text[start:end]

    accuracyHitThe = bigram_similarity(text, "hit the")
    accuracyAw = bigram_similarity(text, "auto") + bigram_similarity(text, "all") + bigram_similarity(text, "aw")
    return accuracyHitThe + accuracyAw

def bigram_similarity(s: str, o: str):
    """Compare the bigrams of two strings and score their similarity."""
    def createBigram(s: str) -> set:
        bigram = set()
        for i in range(len(s)-1):
            bigram.add(s[i:i+2])
        return bigram

    sBigram = createBigram(s.strip().lower())
    oBigram = createBigram(o.strip().lower())
    bigram = sBigram.intersection(oBigram)

    if not sBigram and not oBigram:  # Both strings are empty
        return 1.0  # Consider them identical
    if not sBigram or not oBigram:  # One of the strings is empty
        return 0.0  # No similarity

    return (len(bigram) * 2) / (len(sBigram) + len(oBigram))

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
# Importing libraries and modules
import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import yt_dlp # NEW
from collections import deque # NEW
import asyncio # NEW
import spotipy # NEW - Spotify API
from spotipy.oauth2 import SpotifyClientCredentials # NEW
import re # NEW - For URL pattern matching
import logging # NEW - For server logging
from datetime import datetime # NEW - For timestamps
import random # NEW - For shuffle functionality

# Environment variables for tokens and other sensitive data
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('music_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Spotify API setup
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Initialize Spotify client (only if credentials are provided)
spotify_client = None
if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
    try:
        client_credentials_manager = SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET
        )
        spotify_client = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        print("Spotify API initialized successfully!")
    except Exception as e:
        print(f"Failed to initialize Spotify API: {e}")
        spotify_client = None

# Create the structure for queueing songs - Dictionary of queues
SONG_QUEUES = {}

# Track current playing song info for embeds
CURRENT_SONG_INFO = {}

# Audio EQ presets with higher quality settings
AUDIO_PRESETS = {
    "default": "-ar 48000 -ac 2 -b:a 256k -af \"loudnorm=I=-16:TP=-1.5:LRA=11\"",
    "bass_boost": "-ar 48000 -ac 2 -b:a 256k -af \"equalizer=f=60:width_type=h:width=50:g=5,equalizer=f=170:width_type=h:width=50:g=3,loudnorm=I=-16:TP=-1.5:LRA=11\"",
    "enhanced": "-ar 48000 -ac 2 -b:a 320k -af \"equalizer=f=60:width_type=h:width=50:g=6,equalizer=f=170:width_type=h:width=50:g=4,equalizer=f=350:width_type=h:width=50:g=2,equalizer=f=3000:width_type=h:width=100:g=2,equalizer=f=6000:width_type=h:width=100:g=1,loudnorm=I=-16:TP=-1.5:LRA=11\"",
    "vocal_boost": "-ar 48000 -ac 2 -b:a 256k -af \"equalizer=f=1000:width_type=h:width=200:g=3,equalizer=f=3000:width_type=h:width=200:g=2,loudnorm=I=-16:TP=-1.5:LRA=11\"",
    "treble_boost": "-ar 48000 -ac 2 -b:a 256k -af \"equalizer=f=4000:width_type=h:width=100:g=3,equalizer=f=8000:width_type=h:width=100:g=4,loudnorm=I=-16:TP=-1.5:LRA=11\"",
    "cinema": "-ar 48000 -ac 2 -b:a 320k -af \"equalizer=f=60:width_type=h:width=50:g=4,equalizer=f=170:width_type=h:width=50:g=2,equalizer=f=1000:width_type=h:width=200:g=-1,equalizer=f=6000:width_type=h:width=100:g=2,loudnorm=I=-16:TP=-1.5:LRA=11\""
}

# Current EQ setting per guild
GUILD_EQ_SETTINGS = {}

# Store the last now playing message for each guild to update it
GUILD_NOW_PLAYING_MESSAGES = {}

# Helper functions for URL detection and processing
def is_spotify_url(url):
    """Check if the URL is a Spotify URL"""
    spotify_patterns = [
        r'https://open\.spotify\.com/(track|playlist|album)/([a-zA-Z0-9]+)',
        r'spotify:(track|playlist|album):([a-zA-Z0-9]+)'
    ]
    return any(re.match(pattern, url) for pattern in spotify_patterns)

def is_youtube_playlist(url):
    """Check if the URL is a YouTube playlist"""
    youtube_playlist_patterns = [
        r'https://www\.youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)',
        r'https://youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)',
        r'https://m\.youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)'
    ]
    return any(re.match(pattern, url) for pattern in youtube_playlist_patterns)

def extract_spotify_id(url):
    """Extract Spotify ID and type from URL"""
    patterns = [
        r'https://open\.spotify\.com/(track|playlist|album)/([a-zA-Z0-9]+)',
        r'spotify:(track|playlist|album):([a-zA-Z0-9]+)'
    ]
    for pattern in patterns:
        match = re.match(pattern, url)
        if match:
            return match.group(1), match.group(2)
    return None, None

async def get_spotify_tracks(url):
    """Get track information from Spotify URL with metadata including cover art"""
    if not spotify_client:
        return []
    
    try:
        content_type, spotify_id = extract_spotify_id(url)
        tracks = []
        
        if content_type == "track":
            track = spotify_client.track(spotify_id)
            artist_name = ", ".join([artist["name"] for artist in track["artists"]])
            track_name = track["name"]
            # Get album artwork (largest available)
            artwork_url = None
            if track.get("album") and track["album"].get("images"):
                artwork_url = track["album"]["images"][0]["url"]  # First image is usually largest
            
            tracks.append({
                "query": f"{artist_name} - {track_name}",
                "artist": artist_name,
                "title": track_name,
                "artwork_url": artwork_url,
                "is_spotify": True
            })
            
        elif content_type == "playlist":
            playlist = spotify_client.playlist(spotify_id)
            
            # Get all tracks from the playlist with pagination
            playlist_tracks = playlist["tracks"]
            
            # Process initial batch
            for item in playlist_tracks["items"]:
                if item["track"] and item["track"]["artists"]:
                    artist_name = ", ".join([artist["name"] for artist in item["track"]["artists"]])
                    track_name = item["track"]["name"]
                    # Get album artwork
                    artwork_url = None
                    if item["track"].get("album") and item["track"]["album"].get("images"):
                        artwork_url = item["track"]["album"]["images"][0]["url"]
                    
                    tracks.append({
                        "query": f"{artist_name} - {track_name}",
                        "artist": artist_name,
                        "title": track_name,
                        "artwork_url": artwork_url,
                        "is_spotify": True
                    })
            
            # Handle pagination to get ALL tracks
            while playlist_tracks["next"]:
                playlist_tracks = spotify_client.next(playlist_tracks)
                for item in playlist_tracks["items"]:
                    if item["track"] and item["track"]["artists"]:
                        artist_name = ", ".join([artist["name"] for artist in item["track"]["artists"]])
                        track_name = item["track"]["name"]
                        # Get album artwork
                        artwork_url = None
                        if item["track"].get("album") and item["track"]["album"].get("images"):
                            artwork_url = item["track"]["album"]["images"][0]["url"]
                        
                        tracks.append({
                            "query": f"{artist_name} - {track_name}",
                            "artist": artist_name,
                            "title": track_name,
                            "artwork_url": artwork_url,
                            "is_spotify": True
                        })
                    
        elif content_type == "album":
            album = spotify_client.album(spotify_id)
            artist_name = ", ".join([artist["name"] for artist in album["artists"]])
            # Get album artwork (same for all tracks in album)
            artwork_url = None
            if album.get("images"):
                artwork_url = album["images"][0]["url"]
            
            # Get all tracks from the album with pagination
            album_tracks = album["tracks"]
            
            # Process initial batch
            for track in album_tracks["items"]:
                track_name = track["name"]
                tracks.append({
                    "query": f"{artist_name} - {track_name}",
                    "artist": artist_name,
                    "title": track_name,
                    "artwork_url": artwork_url,
                    "is_spotify": True
                })
            
            # Handle pagination for large albums
            while album_tracks["next"]:
                album_tracks = spotify_client.next(album_tracks)
                for track in album_tracks["items"]:
                    track_name = track["name"]
                    tracks.append({
                        "query": f"{artist_name} - {track_name}",
                        "artist": artist_name,
                        "title": track_name,
                        "artwork_url": artwork_url,
                        "is_spotify": True
                    })
        
        return tracks
    except Exception as e:
        print(f"Error getting Spotify tracks: {e}")
        return []

async def get_youtube_playlist_tracks(url):
    """Get track URLs from YouTube playlist"""
    try:
        ydl_options = {
            "extract_flat": True,
            "quiet": True,
            "no_warnings": True,
        }
        
        loop = asyncio.get_running_loop()
        playlist_info = await loop.run_in_executor(None, lambda: _extract_playlist(url, ydl_options))
            
        tracks = []
        if playlist_info and "entries" in playlist_info:
            for entry in playlist_info["entries"]:
                if entry and entry.get('id'):
                    track_url = f"https://www.youtube.com/watch?v={entry['id']}"
                    title = entry.get("title", "Unknown Title")
                    tracks.append((track_url, title))
        
        return tracks
    except Exception as e:
        print(f"Error getting YouTube playlist tracks: {e}")
        return []

def _extract_playlist(url, ydl_options):
    """Helper function to extract playlist in executor"""
    with yt_dlp.YoutubeDL(ydl_options) as ydl:
        return ydl.extract_info(url, download=False)

async def search_ytdlp_async(query, ydl_opts):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: _extract(query, ydl_opts))

def _extract(query, ydl_opts):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(query, download=False)


# Setup of intents. Intents are permissions the bot has on the server
intents = discord.Intents.default()
intents.message_content = True

# Bot setup
bot = commands.Bot(command_prefix="!", intents=intents)

# Bot ready-up code
@bot.event
async def on_ready():
    await bot.tree.sync()
    logger.info(f"Bot {bot.user} is online and ready!")
    print(f"{bot.user} is online!")

@bot.event
async def on_voice_state_update(member, before, after):
    """Handle bot disconnect and cleanup"""
    if member == bot.user:
        # Bot was disconnected from voice channel (any reason)
        if before.channel is not None and after.channel is None:
            guild_id = str(before.channel.guild.id)
            logger.info(f"Bot disconnected from voice channel in guild {guild_id}")
            
            # Clean up the now playing message
            if guild_id in GUILD_NOW_PLAYING_MESSAGES:
                try:
                    message = GUILD_NOW_PLAYING_MESSAGES[guild_id]
                    await message.delete()
                    logger.info(f"Deleted now playing message due to disconnect in guild {guild_id}")
                except Exception as e:
                    logger.debug(f"Failed to delete now playing message in guild {guild_id}: {e}")
                    pass  # Message might already be deleted
                finally:
                    del GUILD_NOW_PLAYING_MESSAGES[guild_id]
            
            # Clear song info and queue
            if guild_id in CURRENT_SONG_INFO:
                del CURRENT_SONG_INFO[guild_id]
            if guild_id in SONG_QUEUES:
                SONG_QUEUES[guild_id].clear()
        
        # Bot was moved to a different channel - update tracking but keep playing
        elif before.channel is not None and after.channel is not None and before.channel != after.channel:
            guild_id = str(after.channel.guild.id)
            logger.info(f"Bot moved from '{before.channel.name}' to '{after.channel.name}' in guild {guild_id}")
            # No need to delete embed when just moving channels


@bot.tree.command(name="skip", description="Skips the current playing song")
async def skip(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    user = interaction.user
    
    if interaction.guild.voice_client and (interaction.guild.voice_client.is_playing() or interaction.guild.voice_client.is_paused()):
        current_song = CURRENT_SONG_INFO.get(guild_id, {}).get('title', 'Unknown')
        interaction.guild.voice_client.stop()
        logger.info(f"User {user} ({user.id}) skipped song '{current_song}' in guild {guild_id}")
        await interaction.response.send_message("Skipped the current song.")
    else:
        logger.info(f"User {user} ({user.id}) attempted to skip but nothing was playing in guild {guild_id}")
        await interaction.response.send_message("Not playing anything to skip.")


@bot.tree.command(name="pause", description="Pause the currently playing song.")
async def pause(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    guild_id = str(interaction.guild_id)
    user = interaction.user

    # Check if the bot is in a voice channel
    if voice_client is None:
        logger.info(f"User {user} ({user.id}) attempted to pause but bot not in voice channel in guild {guild_id}")
        return await interaction.response.send_message("I'm not in a voice channel.")

    # Check if something is actually playing
    if not voice_client.is_playing():
        logger.info(f"User {user} ({user.id}) attempted to pause but nothing playing in guild {guild_id}")
        return await interaction.response.send_message("Nothing is currently playing.")
    
    # Pause the track
    current_song = CURRENT_SONG_INFO.get(guild_id, {}).get('title', 'Unknown')
    voice_client.pause()
    logger.info(f"User {user} ({user.id}) paused song '{current_song}' in guild {guild_id}")
    await interaction.response.send_message("Playback paused!")


@bot.tree.command(name="resume", description="Resume the currently paused song.")
async def resume(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    guild_id = str(interaction.guild_id)
    user = interaction.user

    # Check if the bot is in a voice channel
    if voice_client is None:
        logger.info(f"User {user} ({user.id}) attempted to resume but bot not in voice channel in guild {guild_id}")
        return await interaction.response.send_message("I'm not in a voice channel.")

    # Check if it's actually paused
    if not voice_client.is_paused():
        logger.info(f"User {user} ({user.id}) attempted to resume but not paused in guild {guild_id}")
        return await interaction.response.send_message("I'm not paused right now.")
    
    # Resume playback
    current_song = CURRENT_SONG_INFO.get(guild_id, {}).get('title', 'Unknown')
    voice_client.resume()
    logger.info(f"User {user} ({user.id}) resumed song '{current_song}' in guild {guild_id}")
    await interaction.response.send_message("Playback resumed!")


@bot.tree.command(name="stop", description="Stop playback and clear the queue.")
async def stop(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    guild_id_str = str(interaction.guild_id)
    user = interaction.user

    # Check if the bot is in a voice channel
    if not voice_client or not voice_client.is_connected():
        logger.info(f"User {user} ({user.id}) attempted to stop but bot not connected in guild {guild_id_str}")
        return await interaction.response.send_message("I'm not connected to any voice channel.")

    current_song = CURRENT_SONG_INFO.get(guild_id_str, {}).get('title', 'Unknown')
    queue_length = len(SONG_QUEUES.get(guild_id_str, []))

    # Clear the guild's queue
    if guild_id_str in SONG_QUEUES:
        SONG_QUEUES[guild_id_str].clear()
    
    # Delete and clear the now playing message
    if guild_id_str in GUILD_NOW_PLAYING_MESSAGES:
        try:
            message = GUILD_NOW_PLAYING_MESSAGES[guild_id_str]
            await message.delete()
            logger.info(f"Deleted now playing message for guild {guild_id_str}")
        except:
            pass  # Message might already be deleted
        finally:
            del GUILD_NOW_PLAYING_MESSAGES[guild_id_str]

    # Clear current song info
    if guild_id_str in CURRENT_SONG_INFO:
        del CURRENT_SONG_INFO[guild_id_str]

    # If something is playing or paused, stop it
    if voice_client.is_playing() or voice_client.is_paused():
        voice_client.stop()

    # Disconnect from the channel
    await voice_client.disconnect()

    logger.info(f"User {user} ({user.id}) stopped playback in guild {guild_id_str}. Song: '{current_song}', Queue size: {queue_length}")
    await interaction.response.send_message("Stopped playback and disconnected!")


@bot.tree.command(name="play", description="Play a song/playlist or add it to the queue.")
@app_commands.describe(song_query="Search query, YouTube URL, Spotify URL, or playlist URL")
async def play(interaction: discord.Interaction, song_query: str):
    await interaction.response.defer()
    
    guild_id = str(interaction.guild_id)
    user = interaction.user
    logger.info(f"User {user} ({user.id}) requested to play: '{song_query}' in guild {guild_id}")

    voice_channel = interaction.user.voice.channel

    if voice_channel is None:
        logger.info(f"User {user} ({user.id}) not in voice channel in guild {guild_id}")
        await interaction.followup.send("You must be in a voice channel.")
        return

    voice_client = interaction.guild.voice_client

    if voice_client is None:
        voice_client = await voice_channel.connect()
        logger.info(f"Bot connected to voice channel '{voice_channel.name}' in guild {guild_id}")
    elif voice_channel != voice_client.channel:
        await voice_client.move_to(voice_channel)
        logger.info(f"Bot moved to voice channel '{voice_channel.name}' in guild {guild_id}")

    if SONG_QUEUES.get(guild_id) is None:
        SONG_QUEUES[guild_id] = deque()

    # Check if it's a playlist URL
    if is_spotify_url(song_query):
        await handle_spotify_url(interaction, song_query, voice_client, guild_id)
    elif is_youtube_playlist(song_query):
        await handle_youtube_playlist(interaction, song_query, voice_client, guild_id)
    else:
        # Handle single song (existing logic)
        await handle_single_song(interaction, song_query, voice_client, guild_id)


async def handle_spotify_url(interaction, url, voice_client, guild_id):
    """Handle Spotify URL (track, playlist, or album)"""
    if not spotify_client:
        logger.error(f"Spotify integration not configured for guild {guild_id}")
        await interaction.followup.send("Spotify integration is not configured. Please check your API credentials.")
        return
    
    logger.info(f"Processing Spotify URL: {url} in guild {guild_id}")
    
    tracks = await get_spotify_tracks(url)
    if not tracks:
        logger.warning(f"No tracks found for Spotify URL: {url} in guild {guild_id}")
        await interaction.followup.send("No tracks found or failed to process Spotify content.")
        return
    
    logger.info(f"Found {len(tracks)} tracks from Spotify URL in guild {guild_id}")
    
    # Process first song immediately
    first_track = tracks[0] if tracks else None
    if first_track:
        try:
            song_info = await search_and_queue_song(first_track["query"], guild_id, spotify_metadata=first_track)
            if song_info:
                title, duration_str = song_info
                logger.info(f"Successfully queued Spotify track '{title}' in guild {guild_id}")
                
                if len(tracks) == 1:
                    await interaction.followup.send(f"✅ Now playing: **{title}**{duration_str}")
                else:
                    await interaction.followup.send(f"✅ Now playing: **{title}**{duration_str}")
                
                # Start playing immediately
                if not voice_client.is_playing() and not voice_client.is_paused():
                    await play_next_song(voice_client, guild_id, interaction.channel)
                
                # Process remaining songs in background (no spam messages)
                if len(tracks) > 1:
                    logger.info(f"Processing {len(tracks)-1} additional tracks in background for guild {guild_id}")
                    asyncio.create_task(process_remaining_tracks(tracks[1:], guild_id, interaction.channel))
            else:
                logger.error(f"Could not find Spotify track on YouTube: '{first_track['query']}' in guild {guild_id}")
                await interaction.followup.send("❌ Could not find the first song on YouTube.")
        except Exception as e:
            logger.error(f"Error processing Spotify content in guild {guild_id}: {str(e)}")
            await interaction.followup.send(f"❌ Error processing Spotify content: {str(e)}")
    else:
        logger.warning(f"No tracks found in Spotify content for guild {guild_id}")
        await interaction.followup.send("❌ No tracks found in Spotify content.")


async def handle_youtube_playlist(interaction, url, voice_client, guild_id):
    """Handle YouTube playlist URL"""
    await interaction.followup.send("🎵 Processing YouTube playlist...")
    
    tracks = await get_youtube_playlist_tracks(url)
    if not tracks:
        await interaction.followup.send("No tracks found in the YouTube playlist.")
        return
    
    # Process first song immediately
    first_track_url, first_title = tracks[0] if tracks else (None, None)
    if first_track_url:
        try:
            song_info = await search_and_queue_song(first_track_url, guild_id, is_url=True)
            if song_info:
                title, duration_str = song_info
                if len(tracks) == 1:
                    await interaction.followup.send(f"✅ Now playing: **{title}**{duration_str}")
                else:
                    await interaction.followup.send(f"✅ Now playing: **{title}**{duration_str}\n🎵 Processing {len(tracks)-1} more songs in background...")
                
                # Start playing immediately
                if not voice_client.is_playing() and not voice_client.is_paused():
                    await play_next_song(voice_client, guild_id, interaction.channel)
                
                # Process remaining songs in background
                if len(tracks) > 1:
                    asyncio.create_task(process_remaining_youtube_tracks(tracks[1:], guild_id, interaction.channel))
            else:
                await interaction.followup.send("❌ Could not process the first video.")
        except Exception as e:
            await interaction.followup.send(f"❌ Error processing YouTube playlist: {str(e)}")
    else:
        await interaction.followup.send("❌ No tracks found in YouTube playlist.")


async def process_remaining_tracks(tracks, guild_id, channel):
    """Process remaining Spotify tracks in background without spamming channel"""
    added_count = 0
    total_tracks = len(tracks)
    
    logger.info(f"Starting background processing of {total_tracks} tracks for guild {guild_id}")
    
    for i, track_metadata in enumerate(tracks, 1):  # Process ALL remaining tracks
        try:
            song_info = await search_and_queue_song(track_metadata["query"], guild_id, spotify_metadata=track_metadata)
            if song_info:
                added_count += 1
                logger.debug(f"Added track {i}/{total_tracks}: '{track_metadata.get('query', 'Unknown')}' in guild {guild_id}")
                        
        except Exception as e:
            logger.warning(f"Error adding track '{track_metadata.get('query', 'Unknown')}' in guild {guild_id}: {e}")
            continue
    
    # Final summary in logs only
    logger.info(f"Background processing complete for guild {guild_id}: {added_count}/{total_tracks} tracks added successfully")


async def process_remaining_youtube_tracks(tracks, guild_id, channel):
    """Process remaining YouTube tracks in background without spamming channel"""
    added_count = 0
    total_tracks = len(tracks)
    
    logger.info(f"Starting background processing of {total_tracks} YouTube tracks for guild {guild_id}")
    
    for i, (track_url, title) in enumerate(tracks, 1):  # Process ALL remaining tracks
        try:
            song_info = await search_and_queue_song(track_url, guild_id, is_url=True)
            if song_info:
                added_count += 1
                logger.debug(f"Added YouTube track {i}/{total_tracks}: '{title}' in guild {guild_id}")
                        
        except Exception as e:
            logger.warning(f"Error adding YouTube track '{title}' in guild {guild_id}: {e}")
            continue
    
    # Final summary in logs only
    logger.info(f"YouTube playlist processing complete for guild {guild_id}: {added_count}/{total_tracks} tracks added successfully")


async def handle_single_song(interaction, song_query, voice_client, guild_id):
    """Handle single song search/URL"""
    try:
        song_info = await search_and_queue_song(song_query, guild_id)
        if not song_info:
            await interaction.followup.send("No results found.")
            return
        
        title, duration_str = song_info
        
        if voice_client.is_playing() or voice_client.is_paused():
            await interaction.followup.send(f"Added to queue: **{title}**{duration_str}")
        else:
            await interaction.followup.send(f"Now playing: **{title}**{duration_str}")
            await play_next_song(voice_client, guild_id, interaction.channel)
            
    except Exception as e:
        await interaction.followup.send(f"Error searching for song: {str(e)}")


async def search_and_queue_song(song_query, guild_id, is_url=False, spotify_metadata=None):
    """Search for a song and add it to the queue with metadata"""
    ydl_options = {
        "format": "bestaudio[acodec=opus]/bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio",
        "noplaylist": True,
        "youtube_include_dash_manifest": False,
        "youtube_include_hls_manifest": False,
        "extractaudio": True,
        "audioformat": "opus",
        "audioquality": 0,  # Best quality
        "prefer_ffmpeg": True,
        "quiet": True,  # Reduce output verbosity
        "no_warnings": True,  # Suppress warnings
        "socket_timeout": 30,  # Prevent hanging
        "retries": 3,  # Retry failed downloads
    }

    if is_url:
        query = song_query
    else:
        query = "ytsearch1: " + song_query
    
    results = await search_ytdlp_async(query, ydl_options)
    tracks = results.get("entries", [])

    if not tracks:
        return None

    first_track = tracks[0]
    audio_url = first_track["url"]
    title = first_track.get("title", "Untitled")
    duration = first_track.get("duration", 0)
    
    # Format duration
    if duration:
        minutes, seconds = divmod(duration, 60)
        duration_str = f" ({minutes}:{seconds:02d})"
    else:
        duration_str = ""

    # Create song metadata with Spotify info if available
    song_metadata = {
        "audio_url": audio_url,
        "title": title,
        "duration_str": duration_str,
        "artwork_url": None,
        "artist": None,
        "is_spotify": False
    }
    
    # If we have Spotify metadata, use it for better info and artwork
    if spotify_metadata:
        song_metadata.update({
            "title": spotify_metadata.get("title", title),
            "artist": spotify_metadata.get("artist"),
            "artwork_url": spotify_metadata.get("artwork_url"),
            "is_spotify": spotify_metadata.get("is_spotify", False)
        })

    SONG_QUEUES[guild_id].append(song_metadata)
    return title, duration_str


async def play_next_song(voice_client, guild_id, channel):
    if SONG_QUEUES[guild_id]:
        song_metadata = SONG_QUEUES[guild_id].popleft()
        
        # Extract metadata
        audio_url = song_metadata["audio_url"]
        title = song_metadata["title"]
        duration_str = song_metadata.get("duration_str", "")
        artwork_url = song_metadata.get("artwork_url")
        artist = song_metadata.get("artist")
        is_spotify = song_metadata.get("is_spotify", False)

        logger.info(f"Playing next song in guild {guild_id}: '{title}' (Spotify: {is_spotify})")

        # Store current song info
        CURRENT_SONG_INFO[guild_id] = {
            'title': title,
            'url': audio_url,
            'start_time': discord.utils.utcnow(),
            'artwork_url': artwork_url,
            'artist': artist,
            'is_spotify': is_spotify
        }

        # Get EQ preset for this guild (default to enhanced for better bass)
        eq_preset = GUILD_EQ_SETTINGS.get(guild_id, "enhanced")
        eq_options = AUDIO_PRESETS[eq_preset]

        ffmpeg_options = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": f"-vn {eq_options}",
            # Remove executable if FFmpeg is in PATH
        }

        try:
            source = discord.FFmpegOpusAudio(audio_url, **ffmpeg_options, executable="bin\\ffmpeg\\ffmpeg.exe")
        except Exception as e:
            logger.error(f"Failed to create audio source for '{title}' in guild {guild_id}: {e}")
            # Try next song if this one fails
            asyncio.run_coroutine_threadsafe(play_next_song(voice_client, guild_id, channel), bot.loop)
            return

        def after_play(error):
            if error:
                logger.error(f"Error playing '{title}' in guild {guild_id}: {error}")
            else:
                logger.info(f"Finished playing '{title}' in guild {guild_id}")
            
            # Clear current song info when song ends
            if guild_id in CURRENT_SONG_INFO:
                del CURRENT_SONG_INFO[guild_id]
                
            asyncio.run_coroutine_threadsafe(play_next_song(voice_client, guild_id, channel), bot.loop)

        voice_client.play(source, after=after_play)
        
        # Create rich embed with control buttons and artwork
        embed = create_now_playing_embed(title, duration_str, artwork_url, artist)
        
        # Add source indicator
        if is_spotify:
            embed.add_field(name="🎵 Source", value="Spotify", inline=True)
        
        # Add EQ info
        preset_names = {
            "default": "🎵 Default",
            "bass_boost": "🔊 Bass Boost", 
            "enhanced": "✨ Enhanced",
            "vocal_boost": "🎤 Vocal Boost",
            "treble_boost": "🔔 Treble Boost",
            "cinema": "🎬 Cinema"
        }
        embed.add_field(name="🎛️ EQ", value=preset_names[eq_preset], inline=True)
        
        # Add queue info if there are more songs
        queue_count = len(SONG_QUEUES[guild_id])
        if queue_count > 0:
            embed.add_field(name="📋 Up Next", value=f"{queue_count} songs in queue", inline=True)
        
        view = MusicControlView()
        
        # Try to update the existing now playing message, if any
        try:
            if guild_id in GUILD_NOW_PLAYING_MESSAGES:
                message = GUILD_NOW_PLAYING_MESSAGES[guild_id]
                await message.edit(embed=embed, view=view)
                return  # Message updated, no need to send a new one
        except (discord.NotFound, discord.HTTPException):
            # Message was deleted or can't be edited, remove from tracking
            if guild_id in GUILD_NOW_PLAYING_MESSAGES:
                del GUILD_NOW_PLAYING_MESSAGES[guild_id]
        except Exception:
            pass  # Ignore other errors, fallback to sending a new message
        
        # Send as a new message if update fails or no existing message
        try:
            new_message = await channel.send(embed=embed, view=view)
            GUILD_NOW_PLAYING_MESSAGES[guild_id] = new_message  # Store for future updates
        except:
            # Fallback to simple message if embed fails
            simple_message = await channel.send(f"🎵 Now playing: **{title}**")
            GUILD_NOW_PLAYING_MESSAGES[guild_id] = simple_message
    else:
        # Clear current song info when queue is empty
        if guild_id in CURRENT_SONG_INFO:
            del CURRENT_SONG_INFO[guild_id]
        
        # Delete and clear the now playing message when disconnecting
        if guild_id in GUILD_NOW_PLAYING_MESSAGES:
            try:
                message = GUILD_NOW_PLAYING_MESSAGES[guild_id]
                await message.delete()
                logger.info(f"Deleted now playing message when queue ended in guild {guild_id}")
            except:
                pass  # Message might already be deleted
            finally:
                del GUILD_NOW_PLAYING_MESSAGES[guild_id]
            
        await voice_client.disconnect()
        SONG_QUEUES[guild_id] = deque()


@bot.tree.command(name="queue", description="Show the current song queue with pagination.")
async def queue(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    
    if guild_id not in SONG_QUEUES or not SONG_QUEUES[guild_id]:
        embed = discord.Embed(
            title="📋 Empty Queue",
            description="The queue is currently empty.\nUse `/play` to add some music!",
            color=0x95a5a6
        )
        await interaction.response.send_message(embed=embed)
        return
    
    # Create paginated queue view
    queue_view = QueuePaginationView(guild_id)
    embed = queue_view.create_queue_embed()
    await interaction.response.send_message(embed=embed, view=queue_view)


@bot.tree.command(name="nowplaying", description="Show the currently playing song with controls.")
async def nowplaying(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    guild_id = str(interaction.guild_id)
    
    if not voice_client or not voice_client.is_playing():
        embed = discord.Embed(
            title="🔇 Nothing Playing",
            description="No music is currently playing.",
            color=0x95a5a6
        )
        await interaction.response.send_message(embed=embed)
        return
    
    # Get current song info
    current_song = CURRENT_SONG_INFO.get(guild_id)
    if current_song:
        title = current_song['title']
        start_time = current_song['start_time']
        artwork_url = current_song.get('artwork_url')
        artist = current_song.get('artist')
        is_spotify = current_song.get('is_spotify', False)
        
        # Calculate elapsed time
        elapsed = discord.utils.utcnow() - start_time
        elapsed_str = f"{int(elapsed.total_seconds() // 60)}:{int(elapsed.total_seconds() % 60):02d}"
        
        embed = create_now_playing_embed(title, "", artwork_url, artist)
        
        # Add source indicator if from Spotify
        if is_spotify:
            embed.add_field(name="🎵 Source", value="Spotify", inline=True)
        
        embed.add_field(name="⏰ Elapsed", value=elapsed_str, inline=True)
        
        # Add queue info
        queue_count = len(SONG_QUEUES.get(guild_id, []))
        if queue_count > 0:
            embed.add_field(name="📋 Up Next", value=f"{queue_count} songs in queue", inline=True)
        
        # Add playback status
        status = "⏸️ Paused" if voice_client.is_paused() else "▶️ Playing"
        embed.add_field(name="🎵 Status", value=status, inline=True)
        
        view = MusicControlView()
        await interaction.response.send_message(embed=embed, view=view)
    else:
        # Fallback if no song info stored
        embed = discord.Embed(
            title="🎵 Something is Playing",
            description="A song is currently playing, but details are not available.",
            color=0x1DB954
        )
        view = MusicControlView()
        await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name="help", description="Show all available music bot commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎵 Music Bot Commands",
        description="Here are all the available commands for the music bot:",
        color=0x00ff00
    )
    
    embed.add_field(
        name="🎶 Playback Commands",
        value="`/play` - Play a song, playlist, or add to queue\n"
              "`/pause` - Pause the current song\n"
              "`/resume` - Resume the paused song\n"
              "`/skip` - Skip to the next song\n"
              "`/stop` - Stop playback and clear queue\n"
              "`/eq` - Change audio equalizer settings",
        inline=False
    )
    
    embed.add_field(
        name="📋 Queue Commands",
        value="`/queue` - Show the current song queue\n"
              "`/nowplaying` - Show the currently playing song\n"
              "`/shuffle` - Shuffle the current queue",
        inline=False
    )
    
    embed.add_field(
        name="🎵 Supported Sources",
        value="• YouTube videos and playlists\n"
              "• Spotify tracks, playlists, and albums\n"
              "• Direct song searches\n"
              "• YouTube Music",
        inline=False
    )
    
    embed.add_field(
        name="📝 Usage Examples",
        value="`/play Never Gonna Give You Up`\n"
              "`/play https://open.spotify.com/playlist/...`\n"
              "`/play https://youtube.com/playlist?list=...`\n"
              "`/play https://youtu.be/dQw4w9WgXcQ`",
        inline=False
    )
    
    embed.set_footer(text="🤖 Made with ❤️ using Discord.py")
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/123456789/123456789/music_note.png")
    
    await interaction.response.send_message(embed=embed)


# Music control buttons view
class MusicControlView(discord.ui.View):
    def __init__(self, *, timeout=300):
        super().__init__(timeout=timeout)
    
    @discord.ui.button(label="⏸️ Pause", style=discord.ButtonStyle.secondary)
    async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client
        
        if voice_client is None:
            await interaction.response.send_message("I'm not in a voice channel.", ephemeral=True)
            return
        
        if voice_client.is_playing():
            voice_client.pause()
            button.label = "▶️ Resume"
            button.style = discord.ButtonStyle.success
            
            # Update the embed to show paused status
            embed = interaction.message.embeds[0] if interaction.message.embeds else None
            if embed:
                # Update the embed title to show paused status
                embed.title = "⏸️ Paused"
                embed.color = 0x95a5a6  # Gray color for paused
            
            await interaction.response.edit_message(embed=embed, view=self)
        elif voice_client.is_paused():
            voice_client.resume()
            button.label = "⏸️ Pause"
            button.style = discord.ButtonStyle.secondary
            
            # Update the embed to show playing status
            embed = interaction.message.embeds[0] if interaction.message.embeds else None
            if embed:
                # Update the embed title to show playing status
                embed.title = "🎵 Now Playing"
                embed.color = 0x1DB954  # Spotify green for playing
            
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("Nothing is currently playing.", ephemeral=True)
    
    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.primary)
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client
        guild_id = str(interaction.guild_id)
        user = interaction.user
        
        if not voice_client or not (voice_client.is_playing() or voice_client.is_paused()):
            await interaction.response.send_message("Not playing anything to skip.", ephemeral=True)
            return
        
        current_song = CURRENT_SONG_INFO.get(guild_id, {}).get('title', 'Unknown')
        voice_client.stop()
        logger.info(f"User {user} ({user.id}) used skip button for '{current_song}' in guild {guild_id}")
        await interaction.response.send_message("⏭️ Skipped!", ephemeral=True)
    
    @discord.ui.button(label="🔀 Shuffle", style=discord.ButtonStyle.secondary)
    async def shuffle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = str(interaction.guild_id)
        user = interaction.user
        
        # Check if there are songs in queue or if something is currently playing (meaning more might be added)
        queue_length = len(SONG_QUEUES.get(guild_id, []))
        is_playing = interaction.guild.voice_client and (interaction.guild.voice_client.is_playing() or interaction.guild.voice_client.is_paused())
        
        if queue_length == 0 and not is_playing:
            await interaction.response.send_message("Queue is empty and nothing is playing.", ephemeral=True)
            return
        elif queue_length == 0 and is_playing:
            await interaction.response.send_message("Queue is currently empty, but more songs may be added soon. Try shuffling again in a moment.", ephemeral=True)
            return
        
        import random
        queue_list = list(SONG_QUEUES[guild_id])
        random.shuffle(queue_list)
        SONG_QUEUES[guild_id] = deque(queue_list)
        
        logger.info(f"User {user} ({user.id}) shuffled queue ({len(queue_list)} songs) in guild {guild_id}")
        await interaction.response.send_message(f"🔀 Shuffled {len(queue_list)} songs!", ephemeral=True)
    
    @discord.ui.button(label="📋 Queue", style=discord.ButtonStyle.secondary)
    async def queue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = str(interaction.guild_id)
        
        if guild_id not in SONG_QUEUES or not SONG_QUEUES[guild_id]:
            await interaction.response.send_message("The queue is empty.", ephemeral=True)
            return
        
        # Create paginated queue view
        queue_view = QueuePaginationView(guild_id)
        embed = queue_view.create_queue_embed()
        await interaction.response.send_message(embed=embed, view=queue_view, ephemeral=True)
    
    @discord.ui.button(label="🎛️ EQ", style=discord.ButtonStyle.secondary)
    async def eq_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Create EQ selection view
        eq_view = EQSelectionView()
        embed = eq_view.create_eq_embed(interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=eq_view, ephemeral=True)
    
    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.danger, row=1)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client
        guild_id = str(interaction.guild_id)
        user = interaction.user
        
        if not voice_client or not voice_client.is_connected():
            await interaction.response.send_message("I'm not connected to any voice channel.", ephemeral=True)
            return
        
        current_song = CURRENT_SONG_INFO.get(guild_id, {}).get('title', 'Unknown')
        queue_size = len(SONG_QUEUES.get(guild_id, []))
        
        if guild_id in SONG_QUEUES:
            SONG_QUEUES[guild_id].clear()
        
        # Delete and clear the now playing message
        if guild_id in GUILD_NOW_PLAYING_MESSAGES:
            try:
                message = GUILD_NOW_PLAYING_MESSAGES[guild_id]
                await message.delete()
            except:
                pass  # Message might already be deleted
            finally:
                del GUILD_NOW_PLAYING_MESSAGES[guild_id]
        
        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()
        
        await voice_client.disconnect()
        logger.info(f"User {user} ({user.id}) stopped playback via button in guild {guild_id}. Song: '{current_song}', Queue size: {queue_size}")
        await interaction.response.send_message("⏹️ Stopped playback and disconnected!", ephemeral=True)


# Paginated Queue View
class QueuePaginationView(discord.ui.View):
    def __init__(self, guild_id, *, timeout=300):
        super().__init__(timeout=timeout)
        self.guild_id = guild_id
        self.current_page = 0
        self.songs_per_page = 10
        
    def get_total_pages(self):
        queue_list = list(SONG_QUEUES.get(self.guild_id, []))
        return max(1, (len(queue_list) + self.songs_per_page - 1) // self.songs_per_page)
    
    def create_queue_embed(self):
        queue_list = list(SONG_QUEUES.get(self.guild_id, []))
        total_pages = self.get_total_pages()
        
        embed = discord.Embed(
            title="📋 Music Queue",
            color=0x3498db
        )
        
        # Show currently playing if available
        current_song = CURRENT_SONG_INFO.get(self.guild_id)
        if current_song:
            embed.add_field(
                name="🎵 Now Playing",
                value=f"**{current_song['title']}**",
                inline=False
            )
        
        # Calculate pagination
        start_idx = self.current_page * self.songs_per_page
        end_idx = min(start_idx + self.songs_per_page, len(queue_list))
        
        if queue_list:
            queue_text = ""
            for i in range(start_idx, end_idx):
                song_metadata = queue_list[i]
                title = song_metadata.get("title", "Unknown Title")
                artist = song_metadata.get("artist")
                
                # Show artist name if available (for Spotify tracks)
                if artist:
                    display_title = f"{artist} - {title}"
                else:
                    display_title = title
                    
                queue_text += f"`{i+1}.` {display_title}\n"
            
            if queue_text:
                embed.add_field(
                    name=f"⏭️ Up Next (Page {self.current_page + 1}/{total_pages})",
                    value=queue_text,
                    inline=False
                )
        else:
            embed.add_field(
                name="⏭️ Up Next",
                value="*Queue is empty*",
                inline=False
            )
        
        embed.set_footer(text=f"Total: {len(queue_list)} songs • Page {self.current_page + 1}/{total_pages}")
        
        # Update button states
        self.update_buttons()
        
        return embed
    
    def update_buttons(self):
        total_pages = self.get_total_pages()
        
        # Update previous button
        self.previous_page.disabled = (self.current_page == 0)
        
        # Update next button
        self.next_page.disabled = (self.current_page >= total_pages - 1)
    
    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            embed = self.create_queue_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="▶️ Next", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        total_pages = self.get_total_pages()
        if self.current_page < total_pages - 1:
            self.current_page += 1
            embed = self.create_queue_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.primary)
    async def refresh_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.create_queue_embed()
        await interaction.response.edit_message(embed=embed, view=self)


# EQ Selection View
class EQSelectionView(discord.ui.View):
    def __init__(self, *, timeout=300):
        super().__init__(timeout=timeout)
    
    def create_eq_embed(self, guild_id):
        current_eq = GUILD_EQ_SETTINGS.get(str(guild_id), "enhanced")
        
        preset_names = {
            "default": "🎵 Default - Balanced sound",
            "bass_boost": "🔊 Bass Boost - Enhanced low frequencies",
            "enhanced": "✨ Enhanced - Full range with bass boost",
            "vocal_boost": "🎤 Vocal Boost - Clear vocals",
            "treble_boost": "🔔 Treble Boost - Crisp highs",
            "cinema": "🎬 Cinema - Movie-like sound"
        }
        
        embed = discord.Embed(
            title="🎛️ Audio Equalizer Settings",
            description=f"**Current EQ:** {preset_names[current_eq]}",
            color=0x9b59b6
        )
        
        embed.add_field(
            name="📝 Available Presets",
            value="Use the buttons below to change the EQ preset.\nNew settings will apply to the next song.",
            inline=False
        )
        
        return embed
    
    @discord.ui.button(label="🎵 Default", style=discord.ButtonStyle.secondary)
    async def default_eq(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.set_eq(interaction, "default", "🎵 Default - Balanced sound")
    
    @discord.ui.button(label="🔊 Bass Boost", style=discord.ButtonStyle.success)
    async def bass_boost_eq(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.set_eq(interaction, "bass_boost", "🔊 Bass Boost - Enhanced low frequencies")
    
    @discord.ui.button(label="✨ Enhanced", style=discord.ButtonStyle.primary)
    async def enhanced_eq(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.set_eq(interaction, "enhanced", "✨ Enhanced - Full range with bass boost")
    
    @discord.ui.button(label="🎤 Vocal Boost", style=discord.ButtonStyle.secondary)
    async def vocal_boost_eq(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.set_eq(interaction, "vocal_boost", "🎤 Vocal Boost - Clear vocals")
    
    @discord.ui.button(label="🔔 Treble Boost", style=discord.ButtonStyle.secondary)
    async def treble_boost_eq(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.set_eq(interaction, "treble_boost", "🔔 Treble Boost - Crisp highs")
    
    @discord.ui.button(label="🎬 Cinema", style=discord.ButtonStyle.secondary, row=1)
    async def cinema_eq(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.set_eq(interaction, "cinema", "🎬 Cinema - Movie-like sound")
    
    async def set_eq(self, interaction: discord.Interaction, preset: str, preset_name: str):
        guild_id = str(interaction.guild_id)
        GUILD_EQ_SETTINGS[guild_id] = preset
        
        embed = discord.Embed(
            title="🎛️ EQ Updated!",
            description=f"Audio preset changed to: **{preset_name}**",
            color=0x00ff00
        )
        
        embed.add_field(
            name="📝 Note",
            value="The new EQ settings will apply to the next song that plays.",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=None)


def create_now_playing_embed(title, duration_str="", thumbnail_url=None, author=None):
    """Create a rich embed for now playing"""
    embed = discord.Embed(
        title="🎵 Now Playing",
        description=f"**{title}**{duration_str}",
        color=0x1DB954  # Spotify green
    )
    
    if author:
        embed.add_field(name="👤 Artist", value=author, inline=True)
    
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    else:
        # Default music icon if no thumbnail
        embed.set_thumbnail(url="https://i.imgur.com/QvWbWJ9.png")  # Musical note icon
    
    embed.set_footer(text="Use the buttons below to control playback")
    embed.timestamp = discord.utils.utcnow()
    
    return embed

@bot.tree.command(name="eq", description="Change audio equalizer settings")
@app_commands.describe(preset="Choose an EQ preset for better audio quality")
@app_commands.choices(preset=[
    app_commands.Choice(name="🎵 Default - Balanced sound", value="default"),
    app_commands.Choice(name="🔊 Bass Boost - Enhanced low frequencies", value="bass_boost"),
    app_commands.Choice(name="✨ Enhanced - Full range with bass boost", value="enhanced"),
    app_commands.Choice(name="🎤 Vocal Boost - Clear vocals", value="vocal_boost"),
    app_commands.Choice(name="🔔 Treble Boost - Crisp highs", value="treble_boost"),
    app_commands.Choice(name="🎬 Cinema - Movie-like sound", value="cinema")
])
async def eq_command(interaction: discord.Interaction, preset: str):
    guild_id = str(interaction.guild_id)
    GUILD_EQ_SETTINGS[guild_id] = preset
    
    preset_names = {
        "default": "🎵 Default - Balanced sound",
        "bass_boost": "🔊 Bass Boost - Enhanced low frequencies", 
        "enhanced": "✨ Enhanced - Full range with bass boost",
        "vocal_boost": "🎤 Vocal Boost - Clear vocals",
        "treble_boost": "🔔 Treble Boost - Crisp highs",
        "cinema": "🎬 Cinema - Movie-like sound"
    }
    
    embed = discord.Embed(
        title="🎛️ Audio EQ Updated",
        description=f"EQ preset changed to: **{preset_names[preset]}**",
        color=0x9b59b6
    )
    
    embed.add_field(
        name="📝 Note",
        value="The new EQ settings will apply to the next song that plays.",
        inline=False
    )
    
    # Show what this preset does
    preset_descriptions = {
        "default": "Balanced audio with no modifications",
        "bass_boost": "Boosts 60Hz and 170Hz frequencies for deeper bass",
        "enhanced": "Bass boost + vocal clarity + loudness normalization",
        "vocal_boost": "Enhances 1kHz and 3kHz for clearer vocals",
        "treble_boost": "Boosts 4kHz and 8kHz for crisp high frequencies",
        "cinema": "Bass boost with mid scoop and treble enhancement"
    }
    
    embed.add_field(
        name="🎚️ What this does",
        value=preset_descriptions[preset],
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="shuffle", description="Shuffle the current queue")
async def shuffle_command(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    user = interaction.user
    
    # Check if there are songs in queue
    queue_length = len(SONG_QUEUES.get(guild_id, []))
    is_playing = interaction.guild.voice_client and (interaction.guild.voice_client.is_playing() or interaction.guild.voice_client.is_paused())
    
    if queue_length == 0 and not is_playing:
        embed = discord.Embed(
            title="🔀 Cannot Shuffle",
            description="Queue is empty and nothing is playing.",
            color=0x95a5a6
        )
        await interaction.response.send_message(embed=embed)
        return
    elif queue_length == 0 and is_playing:
        embed = discord.Embed(
            title="🔀 Queue Currently Empty",
            description="The queue is currently empty, but if you just added a playlist, more songs may be added soon.\nTry shuffling again in a moment.",
            color=0xf39c12
        )
        await interaction.response.send_message(embed=embed)
        return
    elif queue_length == 1:
        embed = discord.Embed(
            title="🔀 Only One Song",
            description="There's only one song in the queue. Add more songs to shuffle!",
            color=0xf39c12
        )
        await interaction.response.send_message(embed=embed)
        return
    
    # Shuffle the queue
    import random
    queue_list = list(SONG_QUEUES[guild_id])
    random.shuffle(queue_list)
    SONG_QUEUES[guild_id] = deque(queue_list)
    
    embed = discord.Embed(
        title="🔀 Queue Shuffled!",
        description=f"Successfully shuffled {len(queue_list)} songs in the queue.",
        color=0x00ff00
    )
    
    logger.info(f"User {user} ({user.id}) shuffled queue ({len(queue_list)} songs) in guild {guild_id}")
    await interaction.response.send_message(embed=embed)


# Run the bot
bot.run(TOKEN)
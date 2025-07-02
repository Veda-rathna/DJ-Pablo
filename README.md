# 🎵 Discord Music Bot - Remastered

A powerful, feature-rich Discord music bot with high-quality audio streaming, unlimited playlist support, interactive controls, and advanced EQ capabilities.

## ✨ Features

### 🎧 Audio Quality
- **High-Quality Streaming**: 320kbps audio with advanced FFmpeg optimization
- **Audio Normalization**: Consistent volume levels across all tracks
- **Advanced EQ System**: Multiple presets (Bass Boost, Vocal, Rock, etc.) with per-guild settings
- **No Downloads**: All music is streamed directly for better performance

### 🎵 Music Sources
- **Spotify Integration**: 
  - Tracks, playlists, and albums
  - **Unlimited tracks** - fetches ALL tracks from playlists (no 100-track limit)
  - Album cover art in now playing embeds
  - Background processing for instant playback
- **YouTube Support**:
  - Individual videos and playlists
  - **Unlimited playlist support** - processes all videos
  - High-quality audio extraction

### 🎮 Interactive Controls
- **Discord UI Buttons**: Play/Pause, Skip, Shuffle, Queue, EQ, Stop
- **Rich Embeds**: Beautiful, informative displays with real-time updates
- **Single Now Playing Message**: Updates in place, reduces channel clutter
- **Paginated Queue**: Navigate through your queue with interactive buttons
- **Ephemeral Responses**: Most interactions are private to reduce spam

### ⚙️ Advanced Features
- **Per-Guild Settings**: Each server has its own EQ preferences
- **Background Processing**: Playlists load in the background while music plays
- **Comprehensive Logging**: Server-side logging of all actions
- **Auto-Cleanup**: Now playing embed is destroyed when bot disconnects
- **Error Handling**: Robust error recovery and user-friendly messages

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Discord Application with Bot Token
- Spotify API credentials (for Spotify features)
- FFmpeg (included in `/bin/ffmpeg/`)

### Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/Discord-Music-Bot-Remastered.git
   cd Discord-Music-Bot-Remastered
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   ```bash
   # Copy the example environment file
   copy .env.example .env
   
   # Edit .env with your credentials
   notepad .env
   ```

4. **Set Up Your Bot**
   - Create a Discord Application at [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a bot and copy the token
   - Enable required bot permissions (see [Permissions](#permissions))
   - Create Spotify App at [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)

5. **Run the Bot**
   ```bash
   python MusicBot.py
   ```

## ⚙️ Configuration

### Environment Variables (.env)
```env
# Discord Bot Configuration
DISCORD_TOKEN=your_discord_bot_token_here
GUILD_ID=your_guild_id_here

# Spotify API Configuration (Optional but recommended)
SPOTIFY_CLIENT_ID=your_spotify_client_id_here
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here
```

### Getting Your Credentials

#### Discord Bot Token
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a "New Application"
3. Go to "Bot" section
4. Click "Reset Token" and copy the token
5. Paste it in your `.env` file

#### Guild ID (Server ID)
1. Enable Developer Mode in Discord (Settings > App Settings > Advanced > Developer Mode)
2. Right-click your server name
3. Click "Copy Server ID"
4. Paste it in your `.env` file

#### Spotify Credentials
1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Click "Create app"
3. Fill in the details (name, description)
4. Copy Client ID and Client Secret
5. Paste them in your `.env` file

### Permissions

Your bot needs the following Discord permissions:
- `Send Messages`
- `Use Slash Commands`
- `Connect` (to voice channels)
- `Speak` (in voice channels)
- `Use Voice Activity`
- `Embed Links`
- `Read Message History`

**Invite Link Template:**
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_CLIENT_ID&permissions=3147776&scope=bot%20applications.commands
```

## 🎵 Commands

### Music Commands
- `/play <song/url>` - Play a song, playlist, or album
  - Supports: YouTube videos/playlists, Spotify tracks/playlists/albums
  - Unlimited playlist support (fetches ALL tracks)
- `/pause` - Pause/resume current track
- `/skip` - Skip to next track
- `/stop` - Stop playback and clear queue
- `/queue` - View current queue (paginated)
- `/shuffle` - Shuffle the current queue
- `/nowplaying` - Show current track info
- `/eq` - Select EQ preset for your server

### Utility Commands
- `/help` - Show comprehensive help message

### Interactive Buttons
The now playing embed includes interactive buttons:
- ⏯️ **Play/Pause** - Toggle playback
- ⏭️ **Skip** - Skip current track
- 🔀 **Shuffle** - Randomize queue order
- 📋 **Queue** - View paginated queue
- 🎚️ **EQ** - Adjust equalizer settings
- ⏹️ **Stop** - Stop and disconnect

## 🎚️ EQ Presets

Choose from multiple audio profiles:
- **Flat** - No modifications (default)
- **Bass Boost** - Enhanced low frequencies
- **Vocal** - Emphasizes vocal ranges
- **Rock** - Optimized for rock music
- **Classical** - Balanced for orchestral music
- **Electronic** - Enhanced for electronic music
- **Pop** - Optimized for pop music

Each server can set its own EQ preference, which persists across sessions.

## 📁 Project Structure

```
Discord-Music-Bot-Remastered/
├── MusicBot.py              # Main bot application
├── requirements.txt         # Python dependencies
├── .env                    # Environment variables (create from .env.example)
├── .env.example           # Example environment file
├── .gitignore             # Git ignore rules
├── README.md              # This file
├── music_bot.log          # Generated log file
└── bin/
    └── ffmpeg/            # FFmpeg binaries
        ├── ffmpeg.exe
        ├── ffplay.exe
        └── ffprobe.exe
```

## 📝 Logging

The bot maintains comprehensive server-side logs in `music_bot.log`:
- User commands and interactions
- Music queue operations
- Error tracking and debugging
- Performance monitoring

Logs are **not** displayed in Discord channels to keep them clean.

## 🔧 Troubleshooting

### Common Issues

#### "Application did not respond" error
- Ensure your bot token is correct in `.env`
- Check that your bot has proper permissions
- Verify the guild ID is correct

#### No audio playing
- Confirm FFmpeg is in the `/bin/ffmpeg/` directory
- Check voice channel permissions
- Ensure bot has "Connect" and "Speak" permissions

#### Spotify features not working
- Verify Spotify credentials in `.env`
- Ensure Spotify Client ID and Secret are correct
- Check if Spotify URLs are valid and public

#### Bot disconnects frequently
- Check your internet connection stability
- Ensure adequate system resources
- Review logs in `music_bot.log` for error details

### Performance Tips

#### For Large Playlists
- Playlists process in the background - music starts immediately
- Monitor system resources for very large playlists (1000+ tracks)
- Consider upgrading server specs for heavy usage

#### Audio Quality
- Ensure stable internet connection for high-quality streaming
- Higher EQ settings may require more processing power
- Monitor CPU usage during peak usage

## 🔒 Security

### Environment Variables
- **Never commit `.env` file** to version control
- Use strong, unique tokens
- Regularly rotate API credentials
- Limit bot permissions to minimum required

### Best Practices
- Run bot in isolated environment
- Monitor log files for suspicious activity
- Keep dependencies updated
- Use official Discord and Spotify APIs only

## 🚀 Deployment

### Local Development
```bash
python MusicBot.py
```

### Production Deployment
Consider using:
- **Process managers**: PM2, systemd
- **Containerization**: Docker
- **Cloud platforms**: Heroku, VPS, AWS
- **Monitoring**: Log aggregation, uptime monitoring

## 📋 Dependencies

### Core Libraries
- `discord.py` - Discord API wrapper
- `yt-dlp` - YouTube video downloading
- `spotipy` - Spotify API client
- `aiohttp` - Async HTTP client

### Audio Processing
- `PyNaCl` - Audio encoding for Discord
- `ffmpeg-python` - FFmpeg Python bindings

See `requirements.txt` for complete dependency list with versions.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Getting Help
- Check this README for common solutions
- Review `music_bot.log` for error details
- Open an issue on GitHub with:
  - Error message
  - Steps to reproduce
  - Relevant log entries

### Feature Requests
Open an issue with:
- Clear description of the feature
- Use case examples
- Expected behavior

## 🎯 Roadmap

Future features under consideration:
- Voice channel auto-join
- Playlist saving/loading
- Multi-language support
- Web dashboard
- Advanced queue management
- Custom EQ creation

---

**Made with ❤️ for the Discord community**

*High-quality music streaming, unlimited playlists, modern UI, and advanced features - all in one powerful bot.*

import os
import sys
import re
import requests
import telebot
from telebot import types
from dotenv import load_dotenv
import yt_dlp

# ---------------------------
# Function: Check Internet Connection
# ---------------------------
def check_internet():
    try:
        requests.get("https://api.telegram.org", timeout=20)
        return True
    except requests.ConnectionError:
        print("❌ ConnectionError: Could not connect to https://api.telegram.org")
        return False
    except Exception as e:
        print(f"🔴 Unexpected error: {e}")
        sys.exit(2)

# ---------------------------
# Load Environment Variables
# ---------------------------
load_dotenv()  # Make sure your .env file contains BOT_TOKEN=your_token
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ BOT_TOKEN is missing! Check your .env file.")
    sys.exit(1)

# ---------------------------
# Initialize the Bot
# ---------------------------
bot = telebot.TeleBot(BOT_TOKEN)

# ---------------------------
# Check Internet Before Running
# ---------------------------
if not check_internet():
    print("⚠️ No internet connection! Check your network and restart the bot.")
    sys.exit(1)

# ---------------------------
# Command Handler: /start
# ---------------------------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Hello! Send me a YouTube link to download a video.")

# ---------------------------
# Function: Check for YouTube Link
# ---------------------------
def is_youtube_link(text):
    youtube_regex = r"(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+"
    return re.match(youtube_regex, text)

# ---------------------------
# Function: Extract Video Formats Using yt-dlp
# ---------------------------
def extract_formats(url):
    """
    Returns a list of available formats for the given YouTube URL.
    Each format is a dictionary containing 'format_id', 'format', 'resolution', etc.
    """
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'forcejson': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            # Filter out formats that do not include both video and audio.
            valid_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('acodec') != 'none']
            return valid_formats, info.get('title', 'video')
    except Exception as e:
        print(f"Error extracting formats: {e}")
        return None, None

# ---------------------------
# Function: Download YouTube Video with Specific Format
# ---------------------------
def download_youtube_video(url, format_id):
    ydl_opts = {
        'format': format_id,
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'noplaylist': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # downloads the video into download folder
            info_dict = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info_dict)
            return video_path
    except Exception as e:
        print(f"Error downloading video: {e}")
        return None

# ---------------------------
# Message Handler: YouTube Link
# ---------------------------
@bot.message_handler(func=lambda message: is_youtube_link(message.text))
def receive_video_link(message):
    url = message.text
    bot.reply_to(message, "Processing your YouTube link, please wait...")
    
    # Extract available formats
    formats, title = extract_formats(url)
    if not formats:
        bot.reply_to(message, "❌ Failed to extract video formats. Please try again.")
        return

    # Create inline keyboard with quality options
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    max_num_formats = 5    
    for fmt in formats[:max_num_formats]:
        # Format text: e.g., "720p - mp4"
        quality = fmt.get('height', 'NA')
        ext = fmt.get('ext', '')
        btn_text = f"{quality}p ({ext})"
        callback_data = f"{fmt['format_id']}|{url}"
        keyboard.add(types.InlineKeyboardButton(text=btn_text, callback_data=callback_data))

    bot.send_message(message.chat.id, f"Select quality for '{title}':", reply_markup=keyboard)

# ---------------------------
# Callback Query Handler: Process Quality Selection
# ---------------------------
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    # Expected callback_data: "format_id|url"
    data = call.data.split('|')
    if len(data) != 2:
        bot.answer_callback_query(call.id, "Invalid selection.")
        return

    format_id, url = data
    bot.answer_callback_query(call.id, "Downloading video...")
    # Send a message in chat to indicate the download has started
    bot.send_message(call.message.chat.id, "📥 Downloading video, please wait...")
    video_path = download_youtube_video(url, format_id)
    
    if video_path and os.path.exists(video_path):
        try:
            with open(video_path, 'rb') as video_file:
                bot.send_video(call.message.chat.id, video_file)
            # Optionally, remove the downloaded file after sending
            # os.remove(video_path)
        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ Failed to send video: {e}")
    else:
        bot.send_message(call.message.chat.id, "❌ Failed to download the video.")

# ---------------------------
# Command Handler: /stop (Optional)
# ---------------------------
@bot.message_handler(commands=['stop'])
def stop_bot(message):
    bot.reply_to(message, "Bot is stopping.")
    bot.stop_polling()

# ---------------------------
# Start Polling (Main Loop)
# ---------------------------
if __name__ == "__main__":
    try:
        print('bot is runnig...')   
        bot.polling(none_stop=True, timeout=30,long_polling_timeout=20)
    except KeyboardInterrupt:
        print("Bot stopped by user.")
    # except Exception as e:
    #     print(f"Unexpected error in polling: {e}")

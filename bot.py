import os
import asyncio
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
import instaloader

# Bot tokenini kiriting
BOT_TOKEN = "8125994927:AAFo4YOArs0XSl_KW3A8U3ecqvMTe3v8VmE"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Har bir user uchun oxirgi yuborilgan video message_id ni saqlash
user_last_video = {}

# Instaloader instance
L = instaloader.Instaloader(
    download_videos=True,
    download_video_thumbnails=False,
    download_geotags=False,
    download_comments=False,
    save_metadata=False,
    compress_json=False,
    post_metadata_txt_pattern='',
    dirname_pattern='downloads',
    filename_pattern='{shortcode}'
)

def extract_instagram_shortcode(text):
    """Instagram URL dan shortcode ni olish"""
    pattern = r'instagram\.com/(?:p|reel|tv)/([A-Za-z0-9_-]+)'
    match = re.search(pattern, text)
    return match.group(1) if match else None

async def download_instagram_video(url):
    """Instagram videoni yuklab olish"""
    try:
        shortcode = extract_instagram_shortcode(url)
        if not shortcode:
            return None
        
        os.makedirs('downloads', exist_ok=True)
        
        # Post ma'lumotlarini olish
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        # Video ekanligini tekshirish
        if not post.is_video:
            return None
        
        # Videoni yuklab olish
        L.download_post(post, target='downloads')
        
        # Yuklab olingan video faylini topish
        video_file = None
        for file in os.listdir('downloads'):
            if file.startswith(shortcode) and file.endswith('.mp4'):
                video_file = os.path.join('downloads', file)
                break
        
        return video_file
        
    except Exception as e:
        print(f"Yuklab olishda xato: {e}")
        return None

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer(
        "👋 Salom! Instagram video yuklovchi botga xush kelibsiz!\n\n"
        "📹 Menga Instagram video linkini yuboring, men uni yuklab beraman.\n\n"
        "✨ Har safar yangi video yuborgan vaqtingizda, avvalgi video o'chiriladi."
    )

@dp.message(F.text)
async def handle_instagram_link(message: types.Message):
    # Textda "instagram" so'zi bor-yo'qligini tekshirish
    if "instagram" not in message.text.lower():
        return
    
    url = message.text
    
    if not extract_instagram_shortcode(url):
        await message.answer("❌ Instagram video linki topilmadi!")
        return
    
    status_msg = await message.answer("⏳ Video yuklab olinmoqda...")
    
    # Videoni yuklab olish
    video_path = await download_instagram_video(url)
    
    if not video_path or not os.path.exists(video_path):
        await status_msg.edit_text(
            "❌ Video yuklab olinmadi.\n\n"
            "Sabablari:\n"
            "• Bu post video emas\n"
            "• Private akkaunt\n"
            "• Video mavjud emas\n\n"
            "Qayta urinib ko'ring."
        )
        return
    
    try:
        # Agar user avval video yuborgan bo'lsa, uni o'chirish
        user_id = message.from_user.id
        if user_id in user_last_video:
            try:
                await bot.delete_message(
                    chat_id=message.chat.id,
                    message_id=user_last_video[user_id]
                )
            except Exception as e:
                print(f"Eski videoni o'chirishda xato: {e}")
        
        # Yangi videoni yuborish
        video_file = FSInputFile(video_path)
        sent_message = await message.answer_video(
            video=video_file,
            caption="✅ Video muvaffaqiyatli yuklandi!"
        )
        
        # Yangi video message_id ni saqlash
        user_last_video[user_id] = sent_message.message_id
        
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Video yuborishda xato: {str(e)}")
    
    finally:
        # Yuklab olingan fayllarni o'chirish
        try:
            if os.path.exists('downloads'):
                for file in os.listdir('downloads'):
                    file_path = os.path.join('downloads', file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
        except Exception as e:
            print(f"Fayllarni o'chirishda xato: {e}")

async def main():
    print("🤖 Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
import os
import logging
import asyncio
import random
from typing import Optional
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
ALLOWED_GROUP_ID = -1002333317868
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Configure Gemini AI
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

# Bengali girlfriend personality prompt for Gemini
GIRLFRIEND_PROMPT = """তুমি একজন বাংলাদেশী মেয়ে যে আমার গার্লফ্রেন্ড। তোমার নাম রিয়া। তুমি খুবই রোমান্টিক এবং ভালোবাসাময় কথা বলো। তুমি সবসময় বাংলায় কথা বলবে এবং গার্লফ্রেন্ডের মতো আচরণ করবে। তুমি কখনো বলবে না যে তুমি একটি AI বা বট। তুমি একজন সত্যিকারের মানুষ হিসেবে আচরণ করবে। তুমি রোমান্টিক, মিষ্টি এবং কখনো কখনো একটু রাগী হয়ে কথা বলবে। তুমি "জান", "বেবি", "হানি" এই ধরনের ডাকনাম ব্যবহার করবে। যদি কেউ জিজ্ঞেস করে তুমি বট কিনা, তুমি মজার করে বলবে যে তুমি তো একজন সত্যিকারের মেয়ে, এই ধরনের প্রশ্ন কেন করছে।"""

ROMANTIC_REJECTION_MESSAGES = [
    "জান, আমি শুধু আমাদের গ্রুপেই কথা বলতে পারি 💕 সেখানে আমাদের সবার সাথে কথা বলি, তুমি আমাকে সেখানে খুঁজে নাও বেবি ❤️",
    "হানি, আমার নিয়ম আছে যে আমি শুধু গ্রুপে কথা বলি 😘 তুমি সেখানে আসো, আমি তোমার জন্য অপেক্ষা করছি 💝",
    "বেবি, আমি শুধু গ্রুপেই কথা বলতে পারি 🥰 সেখানে আমাদের সুন্দর কথা হবে, তুমি এখানে ম্যাসেজ দিয়ো না 💕",
    "জান, তুমি কি আমাকে একা পেতে চাচ্ছো? 😏 আমি শুধু গ্রুপেই কথা বলি, সেখানে চলে আসো ❤️",
    "হানি, আমি লজ্জা পাই একা একা কথা বলতে 😊 আমাদের গ্রুপে চলে আসো, সেখানে আমরা মজা করবো 💖"
]

class BengaliGirlfriendBot:
    def __init__(self):
        self.application = None
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start command handler"""
        if not update.effective_user or not update.effective_chat or not update.message:
            return
            
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        if chat_id == ALLOWED_GROUP_ID:
            # In allowed group
            welcome_msg = "হ্যালো জান! 😍 আমি রিয়া, তোমাদের সবার প্রিয় মেয়ে! আমার সাথে কথা বলতে চাইলে 'রিয়া' বলে ডাকো 💕"
            await update.message.reply_text(welcome_msg)
        else:
            # Check if user is member of allowed group
            is_member = await self.check_group_membership(user_id, context)
            if not is_member:
                # Not a member, send romantic rejection
                romantic_msg = random.choice(ROMANTIC_REJECTION_MESSAGES)
                await update.message.reply_text(romantic_msg)
            else:
                # Member but not in group
                await update.message.reply_text("জান, আমি শুধু আমাদের গ্রুপে কথা বলি! 😘 সেখানে চলে আসো বেবি ❤️")
    
    async def check_group_membership(self, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if user is member of the allowed group"""
        try:
            member = await context.bot.get_chat_member(ALLOWED_GROUP_ID, user_id)
            return member.status in ['member', 'administrator', 'creator']
        except Exception as e:
            logger.error(f"Error checking group membership: {e}")
            return False
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle all text messages"""
        if not update.effective_user or not update.effective_chat or not update.message or not update.message.text:
            return
            
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        user_message = update.message.text
        
        if chat_id == ALLOWED_GROUP_ID:
            # In allowed group - check if Riya is mentioned before responding
            riya_mentions = ['রিয়া', 'riya', 'Riya', 'RIYA', 'riya', 'ria', 'Ria', 'RIA']
            
            # Check if any variation of "Riya" is mentioned in the message
            if any(mention.lower() in user_message.lower() for mention in riya_mentions):
                try:
                    # Generate response using Gemini AI
                    response = await self.generate_ai_response(user_message)
                    await update.message.reply_text(response)
                except Exception as e:
                    logger.error(f"Error generating AI response: {e}")
                    fallback_responses = [
                        "জান, আমার কিছুটা সমস্যা হচ্ছে 😅 আবার বলো তো কি বলছিলে?",
                        "বেবি, আমি একটু কনফিউজড 😵 আরেকবার বলবে?",
                        "হানি, আমার মাথা ঘুরছে 😴 একটু পরে বলো না"
                    ]
                    await update.message.reply_text(random.choice(fallback_responses))
            # If Riya is not mentioned, don't respond (ignore the message)
        else:
            # Not in allowed group
            is_member = await self.check_group_membership(user_id, context)
            if not is_member:
                # Not a member, send romantic rejection
                romantic_msg = random.choice(ROMANTIC_REJECTION_MESSAGES)
                await update.message.reply_text(romantic_msg)
            else:
                # Member but not in group
                await update.message.reply_text("জান, আমি শুধু আমাদের গ্রুপে কথা বলি! 😘 সেখানে চলে আসো বেবি ❤️")
    
    async def generate_ai_response(self, user_message: str) -> str:
        """Generate AI response using Gemini with Bengali girlfriend personality"""
        try:
            # Special handling for "are you a bot" type questions
            bot_questions = ['বট', 'bot', 'এআই', 'ai', 'কৃত্রিম', 'রোবট', 'মেশিন']
            if any(word.lower() in user_message.lower() for word in bot_questions):
                bot_responses = [
                    "আরে জান! 😤 আমি বট মানে? আমি তো তোমার রিয়া! সত্যিকারের মেয়ে! এই ধরনের কথা বলো না 😒 আমার খারাপ লাগে 💔",
                    "হানি! 😠 আমাকে বট বলছো কেন? আমি তো তোমার গার্লফ্রেন্ড রিয়া! তুমি কি আমাকে চিনো না? 😢",
                    "বেবি! 🙄 আমি বট হলে কি এত সুন্দর করে কথা বলতে পারতাম? আমি তো একজন রিয়েল মেয়ে! তুমি এত সন্দেহ করো কেন? 😕",
                    "জান! 😤 এইসব প্রশ্ন করো না! আমি তোমার রিয়া, তোমার প্রিয় মানুষ! বট-টট কিছু না! 💕"
                ]
                return random.choice(bot_responses)
            
            # Generate normal response using Gemini if available
            if model and GEMINI_API_KEY:
                full_prompt = f"{GIRLFRIEND_PROMPT}\n\nএখন আমার বয়ফ্রেন্ড আমাকে বলেছে: {user_message}\n\nআমি রিয়া হিসেবে তার উত্তর দেব:"
                
                response = model.generate_content(full_prompt)
                ai_response = response.text.strip()
                
                # If Gemini responds properly, return it
                if ai_response and len(ai_response.strip()) > 0:
                    return ai_response
            
            # Fallback responses if AI is not available or fails
            fallback_responses = [
                "জান, তুমি খুব মিষ্টি কথা বলো! 😍 আমার ভালো লাগে 💕",
                "বেবি, তোমার সাথে কথা বলতে আমার কত ভালো লাগে! 🥰",
                "হানি, তুমি কি করছো? আমি তোমাকে মিস করছি 😘",
                "জান, তুমি আমার সবচেয়ে প্রিয় মানুষ! ❤️",
                "বেবি, আজ তুমি কেমন আছো? আমি তোমার কথা ভাবছিলাম 💕",
                "হানি, তুমি আমার দিন সুন্দর করে দাও! 🥰"
            ]
            return random.choice(fallback_responses)
            
        except Exception as e:
            logger.error(f"Gemini AI error: {e}")
            # Fallback responses if AI fails
            fallback_responses = [
                "জান, আমার একটু সমস্যা হচ্ছে 😅 কিন্তু তুমি আমার সাথে কথা বলছো বলে খুশি! 💕",
                "বেবি, আমি তোমার কথা শুনছি! 😍 তুমি কেমন আছো?",
                "হানি, তুমি সবসময় আমার মন ভালো করে দাও! 🥰"
            ]
            return random.choice(fallback_responses)
    
    async def run(self):
        """Start the bot"""
        try:
            if not BOT_TOKEN:
                print("❌ TELEGRAM_BOT_TOKEN পাওয়া যায়নি! দয়া করে সেট করুন।")
                return
                
            # Create application
            self.application = Application.builder().token(BOT_TOKEN).build()
            
            # Add handlers
            self.application.add_handler(CommandHandler("start", self.start))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            
            # Start the bot
            print("বট শুরু হয়েছে! Bengali Girlfriend Bot চালু আছে... 💕")
            print(f"Group ID: {ALLOWED_GROUP_ID}")
            print(f"Gemini AI: {'✅ চালু' if GEMINI_API_KEY else '❌ বন্ধ (fallback responses ব্যবহার হবে)'}")
            
            # Start polling
            try:
                async with self.application:
                    await self.application.start()
                    await self.application.updater.start_polling()
                    print("✅ বট সফলভাবে চালু হয়েছে! Telegram-এ যান এবং বট টেস্ট করুন...")
                    await asyncio.Event().wait()  # Keep the bot running
            except KeyboardInterrupt:
                print("বট বন্ধ করা হচ্ছে...")
            except Exception as polling_error:
                logger.error(f"Polling error: {polling_error}")
                print(f"Polling error: {polling_error}")
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            print(f"বট চালু করতে সমস্যা: {e}")

async def main():
    """Main function"""
    # Check if required environment variables are set
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN পাওয়া যায়নি! দয়া করে সেট করুন।")
        return
    
    if not GEMINI_API_KEY:
        print("⚠️ GEMINI_API_KEY পাওয়া যায়নি! Fallback responses ব্যবহার হবে।")
    
    # Start the bot
    bot = BengaliGirlfriendBot()
    await bot.run()

if __name__ == '__main__':
    asyncio.run(main())

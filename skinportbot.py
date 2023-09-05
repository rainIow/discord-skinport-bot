import discord
import asyncio
import base64
import socketio
import json

# Load the configuration data from config.json
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# Skinport API credentials
CLIENT_ID = config['skinport']['CLIENT_ID']
CLIENT_SECRET = config['skinport']['CLIENT_SECRET']

# Discord bot token and channel ID
DISCORD_TOKEN = config['discord']['DISCORD_TOKEN']
CHANNEL_ID = config['discord']['CHANNEL_ID']

# Minimum item discount, price and max price
DISCOUNT = config['settings']['DISCOUNT']
MIN_PRICE = config["settings"]["MIN_PRICE"]
MAX_PRICE = config["settings"]["MAX_PRICE"]

# Skinport API endpoint
API_URL = "https://api.skinport.com/v1/items"

# Function to check if a listing contains any filtered keywords
# def contains_filtered_keywords(listing):
#     return "market_hash_name" in listing and any(keyword in listing["market_hash_name"] for keyword in FILTERED_KEYWORDS)

async def process_and_send_listing(result):
    event_type = result.get('eventType')
    if event_type == 'listed':
        print("result")
        # Calculate the discount percentage for the listing
        sale = result.get("sales", [{}])[0]
        if sale:
            suggested_price = sale.get("suggestedPrice", 0) / 100.0
            sale_price = sale.get("salePrice", 0) / 100.0
            discount_percentage = ((suggested_price - sale_price) / suggested_price) * 100
            
            print(f"Discount for listing with Sale ID {sale.get('saleId', '')}: {discount_percentage:.2f}%")
            
            # Check if the discount is greater than or equal to DISCOUNT and the sale price is between MIN_PRICE and MAX_PRICE
            if discount_percentage >= DISCOUNT and MIN_PRICE <= sale_price <= MAX_PRICE:
                await post_new_listing_in_discord(result)

async def post_new_listing_in_discord(listing):
    # Check if the listing contains the required fields
    sale = listing.get("sales", [{}])[0]
    if sale:
        item_page_link = f"https://skinport.com/item/{sale.get('url', '')}/{sale.get('saleId', '')}"
        print(item_page_link)
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            # Send the message to the Discord channel
            message_content = f"New discounted listing:\nItem Page: {item_page_link}"
            await channel.send(message_content)


# Initialize Intents
intents = discord.Intents.default()
intents.guild_messages = True

# Initialize the Discord bot

bot = discord.Client(intents=intents)

# Connect to the socket server
socket = socketio.AsyncClient()

# Listen to the Sale Feed event
@socket.on('saleFeed')
async def handle_sale_feed(result):
    event_type = result.get('eventType')
    if event_type == 'listed':
        await asyncio.gather(process_and_send_listing(result))

# Event: Bot is ready and connected to Discord
@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user.name}#{bot.user.discriminator}")
    await socket.connect('https://skinport.com', transports=['websocket'])
    await socket.emit('saleFeedJoin', {'currency': 'EUR', 'locale': 'en', 'appid': 730})

# Main asynchronous function to run the bot
async def run_bot():
    await bot.login(DISCORD_TOKEN)
    await bot.connect()

    try:
        await asyncio.gather(bot.start())
    except KeyboardInterrupt:
        await bot.logout()

# Run the bot with the specified Discord token
if __name__ == "__main__":
    asyncio.run(run_bot())

import discord

def create_error_embed(title, description):
    embed = discord.Embed(title=title, description=description, color=discord.Color.red())
    return embed

def create_notification_embed(title, description, category="Medium"):
    color = (
        discord.Color.blue() if category == "Low"
        else discord.Color.orange() if category == "Medium"
        else discord.Color.red()
    )
    embed = discord.Embed(title=title, description=description, color=color)
    return embed
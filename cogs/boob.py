import discord
from discord.ext import commands
import random

class Boob:
    """Boob related commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def boob(self, user : discord.Member):
        """Detects user's cup size

        This is 100% accurate."""
        random.seed(user.id)
        b = " "*random.randint(0, 20)
        await self.bot.say("Cup size: (" + b + "." + b + "Y" + b + "." + b + ")")

def setup(bot):
    bot.add_cog(Boob(bot))
import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from random import randint
from copy import deepcopy
from .utils import checks
from __main__ import send_cmd_help
import os
import time
import logging

slot_payouts = """Slot machine payouts:
    :two: :two: :six: Bet * 5000
    :four_leaf_clover: :four_leaf_clover: :four_leaf_clover: +1000
    :cherries: :cherries: :cherries: +800
    :two: :six: Bet * 4
    :cherries: :cherries: Bet * 3

    Three symbols: +500
    Two symbols: Bet * 2"""

class Economy:
    """Economy

    Get rich and have fun with imaginary currency!"""

    def __init__(self, bot):
        self.bot = bot
        self.bank = fileIO("data/economy/bank.json", "load")
        self.settings = fileIO("data/economy/settings.json", "load")
        self.payday_register = {}

    @commands.group(name="bank", pass_context=True)
    async def _bank(self, ctx):
        """Bank operations"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_bank.command(pass_context=True, no_pm=True)
    async def register(self, ctx):
        """Registers an account at the Twentysix bank"""
        user = ctx.message.author
        if user.id not in self.bank:
            self.bank[user.id] = {"name" : user.name, "balance" : 100}
            fileIO("data/economy/bank.json", "save", self.bank)
            await self.bot.say("{} Account opened. Current balance: {}".format(user.mention, str(self.check_balance(user.id))))
        else:
            await self.bot.say("{} You already have an account at the Twentysix bank.".format(user.mention))

    @_bank.command(pass_context=True)
    async def balance(self, ctx, user : discord.Member=None):
        """Shows balance of user.

        Defaults to yours."""
        if not user:
            user = ctx.message.author
            if self.account_check(user.id):
                await self.bot.say("{} Your balance is: {}".format(user.mention, str(self.check_balance(user.id))))
            else:
                await self.bot.say("{} You don't have an account at the Twentysix bank. Type !register to open one.".format(user.mention, str(self.check_balance(user.id))))
        else:
            if self.account_check(user.id):
                balance = self.check_balance(user.id)
                await self.bot.say("{}'s balance is {}".format(user.name, str(balance)))
            else:
                await self.bot.say("That user has no bank account.")

    @_bank.command(pass_context=True)
    async def transfer(self, ctx, user : discord.Member, sum : int):
        """Transfer credits to other users"""
        author = ctx.message.author
        if author == user:
            await self.bot.say("You can't transfer money to yourself.")
            return
        if sum < 1:
            await self.bot.say("You need to transfer at least 1 credit.")
            return
        if self.account_check(user.id):
            if self.enough_money(author.id, sum):
                self.withdraw_money(author.id, sum)
                self.add_money(user.id, sum)
                logger.info("{}({}) transferred {} credits to {}({})".format(author.name, author.id, str(sum), user.name, user.id))
                await self.bot.say("{} credits have been transferred to {}'s account.".format(str(sum), user.name))
            else:
                await self.bot.say("You don't have that sum in your bank account.")
        else:
            await self.bot.say("That user has no bank account.")

    @_bank.command(name="set", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _set(self, ctx, user : discord.Member, sum : int):
        """Sets money of user's bank account

        Admin/owner restricted."""
        author = ctx.message.author
        done = self.set_money(user.id, sum)
        if done:
            logger.info("{}({}) set {} credits to {} ({})".format(author.name, author.id, str(sum), user.name, user.id))
            await self.bot.say("{}'s credits have been set to {}".format(user.name, str(sum)))
        else:
            await self.bot.say("User has no bank account.")

    @commands.command(pass_context=True, no_pm=True)
    async def payday(self, ctx):
        """Get some free credits"""
        author = ctx.message.author
        id = author.id
        if self.account_check(id):
            if id in self.payday_register:
                if abs(self.payday_register[id] - int(time.perf_counter()))  >= self.settings["PAYDAY_TIME"]: 
                    self.add_money(id, self.settings["PAYDAY_CREDITS"])
                    self.payday_register[id] = int(time.perf_counter())
                    await self.bot.say("{} Here, take some credits. Enjoy! (+{} credits!)".format(author.mention, str(self.settings["PAYDAY_CREDITS"])))
                else:
                    await self.bot.say("{} Too soon. You have to wait {} seconds between each payday.".format(author.mention, str(self.settings["PAYDAY_TIME"])))
            else:
                self.payday_register[id] = int(time.perf_counter())
                self.add_money(id, self.settings["PAYDAY_CREDITS"])
                await self.bot.say("{} Here, take some credits. Enjoy! (+{} credits!)".format(author.mention, str(self.settings["PAYDAY_CREDITS"])))
        else:
            await self.bot.say("{} You need an account to receive credits.".format(author.mention))

    @commands.command(pass_context=True)
    async def payouts(self, ctx):
        """Shows slot machine payouts"""
        await self.bot.send_message(ctx.message.author, slot_payouts)

    @commands.command(pass_context=True, no_pm=True)
    async def slot(self, ctx, bid : int):
        """Play the slot machine"""
        author = ctx.message.author
        if self.enough_money(author.id, bid):
            if bid >= self.settings["SLOT_MIN"] and bid <= self.settings["SLOT_MAX"]:
                await self.slot_machine(ctx.message, bid)
            else:
                await self.bot.say("{0} Bid must be between {1} and {2}.".format(author.mention, self.settings["SLOT_MIN"], self.settings["SLOT_MAX"]))
        else:
            await self.bot.say("{0} You need an account with enough funds to play the slot machine.".format(author.mention))

    async def slot_machine(self, message, bid):
        reel_pattern = [":cherries:", ":cookie:", ":two:", ":four_leaf_clover:", ":cyclone:", ":sunflower:", ":six:", ":mushroom:", ":heart:", ":snowflake:"]
        padding_before = [":mushroom:", ":heart:", ":snowflake:"] # padding prevents index errors
        padding_after = [":cherries:", ":cookie:", ":two:"]
        reel = padding_before + reel_pattern + padding_after
        reels = []
        for i in range(0, 3):
            n = randint(3,12)
            reels.append([reel[n - 1], reel[n], reel[n + 1]])
        line = [reels[0][1], reels[1][1], reels[2][1]]

        display_reels = "  " + reels[0][0] + " " + reels[1][0] + " " + reels[2][0] + "\n"
        display_reels += ">" + reels[0][1] + " " + reels[1][1] + " " + reels[2][1] + "\n"
        display_reels += "  " + reels[0][2] + " " + reels[1][2] + " " + reels[2][2] + "\n"

        if line[0] == ":two:" and line[1] == ":two:" and line[2] == ":six:":
            bid = bid * 5000
            await self.bot.send_message(message.channel, "{}{} 226! Your bet is multiplied * 5000! {}! ".format(display_reels, message.author.mention, str(bid)))
        elif line[0] == ":four_leaf_clover:" and line[1] == ":four_leaf_clover:" and line[2] == ":four_leaf_clover:":
            bid += 1000
            await self.bot.send_message(message.channel, "{}{} Three FLC! +1000! ".format(display_reels, message.author.mention))
        elif line[0] == ":cherries:" and line[1] == ":cherries:" and line[2] == ":cherries:":
            bid += 800
            await self.bot.send_message(message.channel, "{}{} Three cherries! +800! ".format(display_reels, message.author.mention))
        elif line[0] == line[1] == line[2]:
            bid += 500
            await self.bot.send_message(message.channel, "{}{} Three symbols! +500! ".format(display_reels, message.author.mention))
        elif line[0] == ":two:" and line[1] == ":six:" or line[1] == ":two:" and line[2] == ":six:":
            bid = bid * 4
            await self.bot.send_message(message.channel, "{}{} 26! Your bet is multiplied * 4! {}! ".format(display_reels, message.author.mention, str(bid)))
        elif line[0] == ":cherries:" and line[1] == ":cherries:" or line[1] == ":cherries:" and line[2] == ":cherries:":
            bid = bid * 3
            await self.bot.send_message(message.channel, "{}{} Two cherries! Your bet is multiplied * 3! {}! ".format(display_reels, message.author.mention, str(bid)))
        elif line[0] == line[1] or line[1] == line[2]:
            bid = bid * 2
            await self.bot.send_message(message.channel, "{}{} Two symbols! Your bet is multiplied * 2! {}! ".format(display_reels, message.author.mention, str(bid)))
        else:
            await self.bot.send_message(message.channel, "{}{} Nothing! Lost bet. ".format(display_reels, message.author.mention))
            self.withdraw_money(message.author.id, bid)
            await self.bot.send_message(message.channel, "Credits left: {}".format(str(self.check_balance(message.author.id))))
            return True
        self.add_money(message.author.id, bid)
        await self.bot.send_message(message.channel, "Current credits: {}".format(str(self.check_balance(message.author.id))))

    @commands.group(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def economyset(self, ctx):
        """Changes economy module settings"""
        if ctx.invoked_subcommand is None:
            msg = ""
            for k, v in self.settings.items():
                msg += str(k) + ": " + str(v) + "\n"
            msg += "\nType help economyset to see the list of commands."
            await self.bot.say(msg)

    @economyset.command()
    async def slotmin(self, bid : int):
        """Minimum slot machine bid"""
        self.settings["SLOT_MIN"] = bid
        await self.bot.say("Minimum bid is now " + str(bid) + " credits.")
        fileIO("data/economy/settings.json", "save", self.settings)

    @economyset.command()
    async def slotmax(self, bid : int):
        """Maximum slot machine bid"""
        self.settings["SLOT_MAX"] = bid
        await self.bot.say("Maximum bid is now " + str(bid) + " credits.")
        fileIO("data/economy/settings.json", "save", self.settings)

    @economyset.command()
    async def paydaytime(self, seconds : int):
        """Seconds between each payday"""
        self.settings["PAYDAY_TIME"] = seconds
        await self.bot.say("Value modified. At least " + str(seconds) + " seconds must pass between each payday.")
        fileIO("data/economy/settings.json", "save", self.settings)

    @economyset.command()
    async def paydaycredits(self, credits : int):
        """Credits earned each payday"""
        self.settings["PAYDAY_CREDITS"] = credits
        await self.bot.say("Every payday will now give " + str(credits) + " credits.")
        fileIO("data/economy/settings.json", "save", self.settings)

    def account_check(self, id):
        if id in self.bank:
            return True
        else:
            return False

    def check_balance(self, id):
        if self.account_check(id):
            return self.bank[id]["balance"]
        else:
            return False

    def add_money(self, id, amount):
        if self.account_check(id):
            self.bank[id]["balance"] = self.bank[id]["balance"] + int(amount)
            fileIO("data/economy/bank.json", "save", self.bank)
        else:
            return False

    def withdraw_money(self, id, amount):
        if self.account_check(id):
            if self.bank[id]["balance"] >= int(amount):
                self.bank[id]["balance"] = self.bank[id]["balance"] - int(amount)
                fileIO("data/economy/bank.json", "save", self.bank)
            else:
                return False
        else:
            return False

    def enough_money(self, id, amount):
        if self.account_check(id):
            if self.bank[id]["balance"] >= int(amount):
                return True
            else:
                return False
        else:
            return False

    def set_money(self, id, amount):
        if self.account_check(id):      
            self.bank[id]["balance"] = amount
            fileIO("data/economy/bank.json", "save", self.bank)
            return True
        else:
            return False

def check_folders():
    if not os.path.exists("data/economy"):
        print("Creating data/economy folder...")
        os.makedirs("data/economy")

def check_files():
    settings = {"PAYDAY_TIME" : 300, "PAYDAY_CREDITS" : 120, "SLOT_MIN" : 5, "SLOT_MAX" : 100}

    f = "data/economy/settings.json"
    if not fileIO(f, "check"):
        print("Creating default economy's settings.json...")
        fileIO(f, "save", settings)

    f = "data/economy/bank.json"
    if not fileIO(f, "check"):
        print("Creating empty bank.json...")
        fileIO(f, "save", {})

def setup(bot):
    global logger
    check_folders()
    check_files()
    logger = logging.getLogger("economy")
    if logger.level == 0: # Prevents the logger from being loaded again in case of module reload
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(filename='data/economy/economy.log', encoding='utf-8', mode='a')
        handler.setFormatter(logging.Formatter('%(asctime)s %(message)s', datefmt="[%d/%m/%Y %H:%M]"))
        logger.addHandler(handler)
    bot.add_cog(Economy(bot))
import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio, os, datetime

# import pymongo

# from box.db_worker import cluster

client = commands.Bot(command_prefix="?")
client.remove_command("help")

token = str(os.environ.get("bot_token"))

#========== Functions ===========
from functions import display_perms, vis_aliases, visual_delta, owner_ids, find_alias, quote_list

#=========== Events ============
@client.event
async def on_ready():
    print(
        f"User: {client.user}\n"
        f"Now: {datetime.datetime.now()}\n"
        "Loading cogs...\n"
    )

#========== Commands ============
@client.command(aliases=["lo"])
async def logout(ctx):
    if ctx.author.id in owner_ids:
        print([c.name for c in client.commands])
        await ctx.send(f"```>>> Logging out...```")
        await client.logout()

@commands.cooldown(1, 1, commands.BucketType.member)
@client.command()
async def help(ctx, *, section=None):
    p = ctx.prefix
    sections = {
        "settings": ["settings", "s", "настройки", "н"],
        "economy": ["economy", "e", "экономика", "э"],
        "games": ["games", "g", "игры", "и", "казино"],
        "forms": ["forms", "f", "формы", "анкеты"],
        "utils": ["utils", "utilities", "утилиты"]
    }
    titles = {
        "settings": "О настройках",
        "economy": "Об экономике",
        "games": "Об играх",
        "forms": "Об анкете сервера",
        "utils": "О полезных командах"
    }
    if section is None:
        reply = discord.Embed(
            title="📖 Меню помощи",
            description=(
                "Введите команду, интересующую Вас:\n\n"
                f"`{p}help settings` - настройка\n"
                f"`{p}help economy` - экономика\n"
                f"`{p}help games` - игры\n"
                f"`{p}help forms` - форма/анкета\n"
                f"`{p}help utils` - утилиты"
            ),
            color=ctx.guild.me.color
        )
        reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
        await ctx.send(embed=reply)
    
    else:
        section = find_alias(sections, section.lower())
        if section is None:
            reply = discord.Embed(
                title="🔎 Раздел не найден",
                description=f"Попробуйте снова с одной из команд, указанных в `{p}help`"
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        
        else:
            text = open(f"box/{section}.txt", "r", encoding="utf8").read()
            text = text.replace("{p}", p)

            reply = discord.Embed(
                title=f"📋 {titles[section]}",
                description=(
                    f"Подробнее о команде: `{p}команда`\n\n"
                    f"{text}"
                ),
                color=ctx.guild.me.color
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)

#========== Errors ============
@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        cool_notify = discord.Embed(
            title='⏳ Перезарядка',
            description = f"Попробуйте снова через {visual_delta(int(error.retry_after))}"
        )
        cool_notify.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
        await ctx.send(embed=cool_notify)

#========== Extensions =========

for file_name in os.listdir("./cogs"):
    if file_name.endswith(".py"):
        client.load_extension(f"cogs.{file_name[:-3]}")

client.run(token)
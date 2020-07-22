import discord
from discord.ext import commands
from discord.ext.commands import Bot
import failures
import asyncio, os, datetime

# import pymongo

# from box.db_worker import cluster

client = commands.Bot(command_prefix="?")
client.remove_command("help")

token = str(os.environ.get("bot_token"))

#========== Functions ===========
from functions import display_perms, vis_aliases, visual_delta, owner_ids, find_alias, quote_list

def has_instance(_list, _class):
    has = False
    for elem in _list:
        if isinstance(elem, _class):
            has = True
            break
    return has

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

@commands.cooldown(1, 1, commands.BucketType.member)
@client.command(aliases=["bot-stats", "bs", "bot-info", "bi"])
async def stats(ctx):
    total_members = 0
    total_servers = 0
    
    for guild in client.guilds:
        total_members += guild.member_count
        total_servers += 1
    
    reply = discord.Embed(
        title="🌍 Статистика бота",
        description=(
            f"**Всего серверов:** {total_servers} 🗂\n\n"
            f"**Всего пользователей:** {total_members} 👥"
        ),
        color=discord.Color.blue()
    )
    reply.set_thumbnail(url=str(client.user.avatar_url))
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
    
    elif isinstance(error, commands.BadArgument):
        kw, search, rest = str(error).split(maxsplit=2)
        kw = kw.lower()
        del rest
        translations = {
            "user": f"По запросу {search} не было найдено пользователей.",
            "member": f"По запросу {search} не было найдено участников.",
            "role": f"По запросу {search} не было найдено ролей.",
            "channel": f"По запросу {search} не было найдено каналов."
        }
        desc = translations.get(kw, f"Введённый аргумент {search} не соответствует требуемому формату.")

        reply = discord.Embed(
            title="❌ Неверный аргумент",
            description=desc,
            color=discord.Color.dark_red()
        )
        reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
        await ctx.send(embed=reply)
    
    elif isinstance(error, commands.CheckAnyFailure):
        if ctx.author.id not in owner_ids:
            if has_instance(error.errors, failures.IsNotModerator):
                reply = discord.Embed(
                    title="❌ Недостаточно прав",
                    description=f"Необходимые права:\n> Модератор",
                    color=discord.Color.dark_red()
                )
                reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
                await ctx.send(embed=reply)
            elif len(error.errors) > 0:
                await on_command_error(ctx, error.errors[0])
            
        else:
            try:
                await ctx.reinvoke()
            except Exception as e:
                await on_command_error(ctx, e)

    elif isinstance(error, commands.MissingPermissions):
        if ctx.author.id not in owner_ids:
            reply = discord.Embed(
                title="❌ Недостаточно прав",
                description=f"Необходимые права:\n{display_perms(error.missing_perms)}",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)
        else:
            try:
                await ctx.reinvoke()
            except Exception as e:
                await on_command_error(ctx, e)

    elif isinstance(error, commands.CommandNotFound):
        pass
    
    elif isinstance(error, commands.MissingRequiredArgument):
        pass

    else:
        print(error)

#========== Extensions =========

for file_name in os.listdir("./cogs"):
    if file_name.endswith(".py"):
        try:
            client.load_extension(f"cogs.{file_name[:-3]}")
        except Exception:
            pass

client.run(token)

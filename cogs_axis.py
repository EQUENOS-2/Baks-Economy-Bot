import discord
from discord.ext import commands
from discord.ext.commands import Bot
import failures
import asyncio, os, datetime

# import pymongo

# from help.db_worker import cluster
started_at = datetime.datetime.utcnow()

def prefix(client, message):
    p = ["?", "!"]
    if client.user.id == 582881093154504734:
        p = ".."
    return p

client = commands.Bot(command_prefix=prefix)
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
        await ctx.send(f"```>>> Logging out...```")
        await client.logout()


@client.command()
async def ping(ctx):
    await ctx.send(f"{ctx.author.mention}, pong")


@commands.cooldown(1, 1, commands.BucketType.member)
@client.command()
async def help(ctx, *, section=None):
    p = ctx.prefix
    sections = {
        "settings": ["настройки"],
        "moderation": ["модерация"],
        "economy": ["экономика"],
        "games": ["игры", "казино"],
        "forms": ["формы", "анкеты"],
        "utils": ["utilities", "утилиты"],
        "brawlstars": ["brawl", "bs", "бравл старс", "бс", "brawl stars"]
    }
    titles = {
        "settings": "О настройках",
        "moderation": "О модерации",
        "economy": "Об экономике",
        "games": "Об играх",
        "forms": "Об анкете сервера",
        "utils": "О полезных командах",
        "brawlstars": "Интеграция Brawl Stars"
    }
    desc = ""
    for sec in titles:
        desc += f"`{p}help {sec}` - {titles[sec]}\n"
    if section is None:
        reply = discord.Embed(
            title="📖 Меню помощи",
            description=f"Введите команду, интересующую Вас:\n\n{desc}",
            color=ctx.guild.me.color
        )
        reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
        await ctx.send(embed=reply)
    
    else:
        section = find_alias(sections, section)
        if section is None:
            reply = discord.Embed(
                title="🔎 Раздел не найден",
                description=f"Попробуйте снова с одной из команд, указанных в `{p}help`"
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        
        else:
            text = open(f"help/{section}.txt", "r", encoding="utf8").read()
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
    uptime = datetime.datetime.utcnow() - started_at
    total_members = 0
    total_servers = 0
    
    for guild in client.guilds:
        total_members += guild.member_count
        total_servers += 1
    
    reply = discord.Embed(
        title="🌍 Статистика бота",
        color=discord.Color.blue()
    )
    reply.add_field(name="🗂 Серверов", value=f"> {total_servers}", inline=False)
    reply.add_field(name="👥 Пользователей", value=f"> {total_members}", inline=False)
    reply.add_field(name="🕑 Аптайм", value=f"> {visual_delta(uptime)}")
    reply.add_field(name="🛰 Пинг", value=f"> {client.latency * 1000:.0f}", inline=False)
    reply.set_thumbnail(url=str(client.user.avatar_url))
    await ctx.send(embed=reply)

#========== Errors ============
@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        cool_notify = discord.Embed(
            title='⏳ Команда перезаряжается',
            description = f"Попробуйте снова через {visual_delta(int(error.retry_after))}"
        )
        cool_notify.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
        await ctx.send(embed=cool_notify)
    
    elif isinstance(error, commands.BadArgument):
        kw, search, rest = str(error).split('"', maxsplit=2)
        kw = kw.lower().strip()
        search = search.strip()
        
        del rest
        if "convert" in kw:
            kw = search
        translations = {
            "user": f"По запросу {search} не было найдено пользователей.",
            "member": f"По запросу {search} не было найдено участников.",
            "role": f"По запросу {search} не было найдено ролей.",
            "channel": f"По запросу {search} не было найдено каналов.",
            "int": f"Пожалуйста, введите целое число."
        }
        desc = translations.get(kw, "Введённый аргумент не соответствует требуемому формату.")

        reply = discord.Embed(
            title="❌ Неверный аргумент",
            description=desc,
            color=discord.Color.dark_red()
        )
        reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
        await ctx.send(embed=reply)

        try:
            ctx.command.reset_cooldown(ctx)
        except Exception:
            pass
    
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
        iw = str(ctx.invoked_with)
        p = ctx.prefix; cmd = ctx.command
        description = "`-`"; usage = "`-`"; brief = "`-`"; aliases = "-"
        if cmd.description != "":
            description = cmd.description
        if cmd.usage is not None:
            usage = "\n> ".join( [f"`{p}{iw} {u}`" for u in cmd.usage.split("\n")] )
        if cmd.brief is not None:
            brief = "\n> ".join( [f"`{p}{iw} {u}`" for u in cmd.brief.split("\n")] )
        if len(cmd.aliases) > 0:
            aliases = ", ".join(cmd.aliases)
        
        reply = discord.Embed(
            title = f"❓ Об аргументах `{p}{iw}`",
            description = (
                f"**Описание:** {description}\n"
                f"**Использование:** {usage}\n"
                f"**Примеры:** {brief}\n\n"
                f"**Синонимы:** `{aliases}`"
            )
        )
        if cmd.help is not None:          # So here I use cmd.help as an optional url holder
            reply.set_image(url=cmd.help) # Ok? So don't forget please
        reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
        await ctx.send(embed=reply)

        try:
            ctx.command.reset_cooldown(ctx)
        except Exception:
            pass

    elif isinstance(error, failures.CooldownResetSignal):
        try:
            ctx.command.reset_cooldown(ctx)
        except Exception:
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
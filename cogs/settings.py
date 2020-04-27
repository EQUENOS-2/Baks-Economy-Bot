import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio, os, datetime, json

import pymongo

from functions import detect, get_field, has_roles, try_int, has_permissions
from box.db_worker import cluster
db = cluster["guilds"]

trigger_file = "msg_triggers.json"

def delete(filename):
    if filename in os.listdir("."):
        os.remove(filename)

def load(filename, default=None):
    if filename in os.listdir("."):
        with open(filename, "r", encoding="utf8") as fff:
            default = json.load(fff)
    return default

def save(data, filename):
    with open(filename, "w", encoding="utf8") as fff:
        json.dump(data, fff)

class settings(commands.Cog):
    def __init__(self, client):
        self.client = client

    #========== Events ===========
    @commands.Cog.listener()
    async def on_ready(self):
        delete(trigger_file)
        print(">> Settings cog is loaded")
    
    # On message
    @commands.Cog.listener()
    async def on_message(self, message):
        trig_data = load(trigger_file, {})
        guild_id = message.guild.id
        
        if f"{guild_id}" not in trig_data:
            collection = db["msg_manip"]
            result = collection.find_one(
                {"_id": guild_id}
            )
            trig = get_field(result, "trigger")
            rep = get_field(result, "reply")
            trig_data.update([(f"{guild_id}", {"trigger": trig, "reply": rep})])

            save(trig_data, trigger_file)
        else:
            trig = trig_data[f"{guild_id}"]["trigger"]
            rep = trig_data[f"{guild_id}"]["reply"]
        
        text = message.content.lower()
        if trig is not None and rep is not None and trig in text:
            reply = discord.Embed(
                description=rep,
                color=message.author.color
            )
            await message.channel.send(embed=reply)

    #========= Commands ===========
    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.command(aliases=["set", "how-set", "hs"])
    async def how_set(self, ctx):
        p = ctx.prefix
        collection = db["money"]
        result = collection.find_one(
            {"_id": ctx.guild.id},
            projection={"cur": True, "work_range": True}
        )
        cur = get_field(result, "cur", default="💰")
        wr = get_field(result, "work_range", default=(100, 300))

        collection = db["msg_manip"]
        result = collection.find_one(
            {"_id": ctx.guild.id}
        )
        trig = get_field(result, "trigger", default="выключен")
        rep = get_field(result, "reply", default="отсутствует")

        reply = discord.Embed(
            title="⚙ Текущие настройки",
            description=(
                f"**Валюта:** {cur}\n"
                f"**Заработок при `{p}work`:** {wr[0]}-{wr[1]} {cur}\n"
                f"**Триггер сообщений:** {trig}\n"
                f"**Ответ на сообщения с триггером:** {rep}\n"
            ),
            color=ctx.guild.me.color
        )
        reply.set_thumbnail(url=f"{ctx.guild.icon_url}")
        await ctx.send(embed=reply)

    #@commands.cooldown(1, 3, commands.BucketType.member)
    #@commands.command(aliases=["master-role", "mr"])
    async def master_role(self, ctx, *, role_s):
        if not has_permissions(ctx.author, ["administrator"]):
            reply = discord.Embed(
                title="❌ Недостаточно прав",
                description=(
                    "**Необходимые права:**\n"
                    f"> Администратор"
                ),
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        
        else:
            correct_role_arg = True
            if role_s.lower() == "delete":
                role = None
                desc = "Мастер-роль удалена"
            else:
                role = detect.role(ctx.guild, role_s)
                if role is None:
                    correct_role_arg = False

                    reply = discord.Embed(
                        title="💢 Упс",
                        description=f"Вы ввели {role_s}, подразумевая роль, но она не была найдена.",
                        color=discord.Color.dark_red()
                    )
                    reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                    await ctx.send(embed=reply)
                else:
                    desc = f"Мастер-роль настроена как <@&{role.id}>"
            
            if correct_role_arg:
                collection = db["money"]
                collection.find_one_and_update(
                    {"_id": ctx.guild.id},
                    {"$set": {"master_role": role.id}},
                    upsert=True
                )
                reply = discord.Embed(
                    title="✅ Выполнено",
                    description=desc,
                    color=discord.Color.dark_green()
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)

    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.command(aliases=["set-currency", "set-cur", "setcur"])
    async def set_currency(self, ctx, string):
        p = ctx.prefix
        if not has_permissions(ctx.author, ["administrator"]):
            reply = discord.Embed(
                title="❌ Недостаточно прав",
                description=(
                    "**Необходимые права:**\n"
                    f"> Администратор"
                ),
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        
        else:
            string = string[:+52]
            collection = db["money"]
            collection.find_one_and_update(
                {"_id": ctx.guild.id},
                {"$set": {"cur": string}},
                upsert=True
            )
            reply = discord.Embed(
                title="✅ Выполнено",
                description=(
                    f"Новый значок валюты: {string}\n\n"
                    f"Текущие настройки: `{p}how-set`"
                ),
                color=discord.Color.dark_green()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
    
    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.command(aliases=["work-range"])
    async def work_range(self, ctx, lower_bound, upper_bound):
        p = ctx.prefix
        if not has_permissions(ctx.author, ["administrator"]):
            reply = discord.Embed(
                title="❌ Недостаточно прав",
                description=(
                    "**Необходимые права:**\n"
                    f"> Администратор"
                ),
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        
        elif not lower_bound.isdigit() or not upper_bound.isdigit():
            reply = discord.Embed(
                title="💢 Ошибка",
                description=(
                    "Минимальный и максимальный заработок должны быть целым числом.\n"
                    f"Пример: `{p}work-range 200 500`"
                ),
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        
        elif int(lower_bound) >= int(upper_bound):
            reply = discord.Embed(
                title="💢 Ошибка",
                description=(
                    "Минимальный заработок должен быть меньше максимального.\n"
                    f"Пример: `{p}work-range 200 500`"
                ),
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)

        else:
            lower_bound, upper_bound = int(lower_bound), int(upper_bound)
            collection = db["money"]
            result = collection.find_one_and_update(
                {"_id": ctx.guild.id},
                {"$set": {"work_range": (lower_bound, upper_bound)}},
                upsert=True,
                projection={"cur": True}
            )
            cur = get_field(result, "cur")
            if cur is None:
                cur = "💰"
            
            reply = discord.Embed(
                title=f"✅ Настроено",
                description=(
                    f"Теперь команда `{p}work` приносит от **{lower_bound}** до **{upper_bound}** {cur}\n\n"
                    f"Текущие настройки: `{p}how-set`"
                ),
                color=discord.Color.dark_green()
            )
            await ctx.send(embed=reply)

    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.command(aliases=["trig", "t"])
    async def trigger(self, ctx, *, string):
        p = ctx.prefix
        if not has_permissions(ctx.author, ["administrator"]):
            reply = discord.Embed(
                title="❌ Недостаточно прав",
                description=(
                    "**Необходимые права:**\n"
                    f"> Администратор"
                ),
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        
        else:
            if string.lower() == "delete":
                desc = "Триггер сообщений удалён"
                string = None
            else:
                string = string[:+500].lower()
                desc = f"Теперь бот отслеживает сообщения с \"{string}\""

            collection = db["msg_manip"]
            collection.find_one_and_update(
                {"_id": ctx.guild.id},
                {"$set": {"trigger": string}},
                upsert=True
            )
            data = load(trigger_file, {})
            if f"{ctx.guild.id}" in data:
                data[f"{ctx.guild.id}"]["trigger"] = string
                save(data, trigger_file)

            reply = discord.Embed(
                title="✅ Выполнено",
                description=(
                    f"{desc}\n\n"
                    f"Текущие настройки: `{p}how-set`"
                ),
                color=discord.Color.dark_green()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)

    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.command(aliases=["trigger-reply", "trig-reply", "tr"])
    async def trigger_reply(self, ctx, *, text):
        p = ctx.prefix
        if not has_permissions(ctx.author, ["administrator"]):
            reply = discord.Embed(
                title="❌ Недостаточно прав",
                description=(
                    "**Необходимые права:**\n"
                    f"> Администратор"
                ),
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        
        else:
            if text.lower() == "delete":
                desc = "Ответ на сообщения с определённым триггером удалён."
                text = None
            else:
                text = text[:+500]
                desc = f"Ответ на сообщения с определённым триггером:\n{text}"

            collection = db["msg_manip"]
            collection.find_one_and_update(
                {"_id": ctx.guild.id},
                {"$set": {"reply": text}},
                upsert=True
            )
            data = load(trigger_file, {})
            if f"{ctx.guild.id}" in data:
                data[f"{ctx.guild.id}"]["reply"] = text
                save(data, trigger_file)

            reply = discord.Embed(
                title="✅ Выполнено",
                description=(
                    f"{desc}\n\n"
                    f"Текущие настройки: `{p}how-set`"
                ),
                color=discord.Color.dark_green()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)

    #======== Errors =========
    #@master_role.error
    async def master_role_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    f"**Описание:** настраивает роль, дающую права на настройку экономики\n"
                    f'**Назначение:** `{p}{cmd} @Роль`\n'
                    f"**Удаление:** `{p}{cmd} delete`\n"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @set_currency.error
    async def set_currency_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    f"**Описание:** настраивает значок валюты\n"
                    f'**Использование:** `{p}{cmd} Значок`\n'
                    f"**Пример:** `{p}{cmd} ✨`\n"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @work_range.error
    async def work_range_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    f"**Описание:** настраивает диапазон заработка с команды `{p}work`\n"
                    f'**Использование:** `{p}{cmd} Мин.заработок Макс.заработок`\n'
                    f"**Пример:** `{p}{cmd} 300 700`\n"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @trigger.error
    async def trigger_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    f"**Описание:** настраивает триггер, провоцирующий ответ бота\n"
                    f'**Использование:** `{p}{cmd} текст`\n'
                    f"**Отключение:** `{p}{cmd} delete`\n"
                    f"**Пример:** `{p}{cmd} привет`\n"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
    
    @trigger_reply.error
    async def trigger_reply_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    f"**Описание:** настраивает ответ бота на сообщения с триггером (подробнее `{p}trigger`)\n"
                    f'**Использование:** `{p}{cmd} текст`\n'
                    f"**Отключение:** `{p}{cmd} delete`\n"
                    f"**Пример:** `{p}{cmd} Здравствуй`\n"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

def setup(client):
    client.add_cog(settings(client))
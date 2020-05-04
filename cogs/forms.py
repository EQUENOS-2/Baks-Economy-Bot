import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio, os

import pymongo
from box.db_worker import cluster

#========== Variables ==========
db = cluster["guilds"]

#========== Functions ==========
from functions import has_permissions, get_field, detect

def attachments_to_links(message, quote=False, header="Вложение"):
    atts = message.attachments
    if atts == []:
        return ""
    else:
        if quote:
            q = "> "
        else:
            q = ""
        out = f"{q}__**Вложения:**__\n"
        pos = 1
        for att in atts:
            out += f"{q}🔹 [{header} {pos}]({att.url})\n"
            pos += 1
        return out

async def read_message(channel, user, t_out, client):
    try:
        msg = await client.wait_for(
            "message",
            check=lambda message: user.id == message.author.id and channel.id == message.channel.id,
            timeout=t_out
        )
    except asyncio.TimeoutError:
        reply=discord.Embed(
            title="🕑 Вы слишком долго не писали",
            description=f"Таймаут: {t_out}",
            color=discord.Color.blurple()
        )
        await channel.send(content=user.mention, embed=reply)
        return None
    else:
        return msg

async def try_send(channel_or_user, content=None, embed=None):
    try:
        return await channel_or_user.send(content=content, embed=embed)
    except Exception:
        return None

class forms(commands.Cog):
    def __init__(self, client):
        self.client = client

    #========== Events ===========
    @commands.Cog.listener()
    async def on_ready(self):
        print(">> Froms cog is loaded")

    #========= Commands ==========
    @commands.command(aliases=["add-field", "add-question", "af"])
    async def add_field(self, ctx, *, name):
        pr = ctx.prefix
        if not has_permissions(ctx.author, ["administrator"]):
            reply = discord.Embed(
                title="❌ Недостаточно прав",
                description=(
                    "**Необходимые права:**\n"
                    f"> Администратор"
                ),
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
            await ctx.send(embed=reply)
        
        else:
            reply = discord.Embed(
                title="💬 Введите вопрос",
                description=f"Ответ на этот вопрос будет отображаться под заголовком **{name}**\nОтмена: `cancel`",
                color=discord.Color.from_rgb(250, 250, 250)
            )
            reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
            await ctx.send(embed=reply)

            message = await read_message(ctx.channel, ctx.author, 120, self.client)
            if message is None:
                pass
            elif message.content.lower() == "cancel" or message.content.startswith(pr):
                await ctx.send("Действие отменено")
            else:
                text = message.content

                collection = db["forms"]
                collection.find_one_and_update(
                    {"_id": ctx.guild.id},
                    {"$set": {f"fields.{name}": text}},
                    upsert=True
                )

                reply = discord.Embed(
                    title="☑ Вопрос добавлен",
                    description=f"**Текст:** {text}",
                    color=discord.Color.dark_blue()
                )
                reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                await ctx.send(embed=reply)

    @commands.command(aliases=["reply-channel", "rc", "redirect", "redirect-channel"])
    async def reply_channel(self, ctx, channel_name):
        pr = ctx.prefix
        if not has_permissions(ctx.author, ["administrator"]):
            reply = discord.Embed(
                title="❌ Недостаточно прав",
                description=(
                    "**Необходимые права:**\n"
                    f"> Администратор"
                ),
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
            await ctx.send(embed=reply)
        
        else:
            correct_arg = True
            if channel_name.lower() == "delete":
                channel = None
                desc = "Канал сбора ответов удалён"
            else:
                channel = detect.channel(ctx.guild, channel_name)
                if channel is None:
                    correct_arg = False
                    reply = discord.Embed(
                        title="💢 Упс",
                        description=f"Вы ввели {channel_name}, подразумевая канал, но он не был найден.",
                        color=discord.Color.dark_red()
                    )
                    reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                    await ctx.send(embed=reply)
                else:
                    desc = f"Канал сбора ответов настроен как <#{channel.id}>"
                    channel = channel.id
            
            if correct_arg:
                collection = db["forms"]
                collection.find_one_and_update(
                    {"_id": ctx.guild.id},
                    {"$set": {"redirect": channel}},
                    upsert=True
                )
                reply = discord.Embed(
                    title="✅ Выполнено",
                    description=f"{desc}\nПосмотреть форму: `{pr}view-form`",
                    color=discord.Color.dark_green()
                )
                reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                await ctx.send(embed=reply)

    @commands.command(aliases=["view-form", "vf"])
    async def view_form(self, ctx):
        pr = ctx.prefix
        collection = db["forms"]
        result = collection.find_one(
            {"_id": ctx.guild.id}
        )
        fields = get_field(result, "fields")
        if fields == {}:
            fields = None
        redirect = get_field(result, "redirect")

        reply = discord.Embed(
            title="📋 Форма",
            color=ctx.guild.me.color
        )
        if redirect is None:
            reply.add_field(name="#️⃣ **Канал для сбора ответов не настроен:**", value=f"`{pr}reply-channel`", inline=False)
        else:
            reply.add_field(name="#️⃣ **Отправлять ответы в:**", value=f"> <#{redirect}>", inline=False)
        
        if fields is None:
            reply.add_field(name="❓ **Вопросы не настроены**", value=f"`{pr}add-field`")
        else:
            for q in fields:
                reply.add_field(name=f"**{q}**", value=f"> {fields[q]}", inline=False)

        await ctx.send(embed=reply)

    @commands.command(aliases=["send-form"])
    async def send_from(self, ctx):
        collection = db["forms"]
        result = collection.find_one(
            {"_id": ctx.guild.id}
        )
        fields = get_field(result, "fields")
        redirect = get_field(result, "redirect")

        if fields is None or redirect is None:
            reply = discord.Embed(
                title="📦 Форма не настроена",
                description="Приходите, когда администрация настроит форму!"
            )
            reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
            await ctx.send(embed=reply)
        
        else:
            completed = True
            answer = discord.Embed(
                color=ctx.author.color
            )
            answer.set_author(name=str(ctx.author), icon_url=str(ctx.author.avatar_url))
            
            talk_channel = None
            for q in fields:
                reply = discord.Embed(
                    title=f"📝 {q}",
                    description=f"{fields[q]}\nДля отмены введите `cancel`",
                    color=ctx.author.color
                )
                reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))

                if talk_channel is None:
                    bot_msg = await try_send(ctx.author, embed=reply)
                    if bot_msg is None:
                        await ctx.send("Не могу написать Вам в личных сообщениях", embed=reply)
                        talk_channel = ctx.channel
                    else:
                        talk_channel = bot_msg.channel
                else:
                    await talk_channel.send(embed=reply)

                msg = await read_message(talk_channel, ctx.author, 300, self.client)
                if msg is None:
                    completed = False
                    break
                elif msg.content.lower() == "cancel" or msg.content.startswith(ctx.prefix):
                    await talk_channel.send("Заполнение формы отменено")
                    completed = False
                    break
                else:
                    await msg.add_reaction("✅")
                    if msg.content == "":
                        msg_desc = ""
                    else:
                        msg_desc = f"> {msg.content}"
                    att_desc = attachments_to_links(msg, True)
                    answer.add_field(name=f"**{q}**", value=f"{msg_desc}\n{att_desc}", inline=False)
            
            if completed:
                channel = ctx.guild.get_channel(redirect)

                reply = discord.Embed(
                    title="✅ Форма заполнена",
                    description="Ваш ответ был записан",
                    color=discord.Color.green()
                )
                reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))

                await talk_channel.send(embed=reply)

                if channel is None:
                    await ctx.send(embed=answer)
                else:
                    await channel.send(embed=answer)

    @commands.command()
    async def rename(self, ctx, *, name):
        pr = ctx.prefix
        if not has_permissions(ctx.author, ["administrator"]):
            reply = discord.Embed(
                title="❌ Недостаточно прав",
                description=(
                    "**Необходимые права:**\n"
                    f"> Администратор"
                ),
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
            await ctx.send(embed=reply)
        
        else:
            collection = db["forms"]
            result = collection.find_one(
                {"_id": ctx.guild.id, f"fields.{name}": {"$exists": True}}
            )
            if result is None:
                reply = discord.Embed(
                    title="❌ Упс",
                    description=(
                        f"Вопроса с заголовком **{name}** не существует\n"
                        f"Просмотреть форму: `{pr}view-form`"
                    ),
                    color=discord.Color.dark_red()
                )
                reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                await ctx.send(embed=reply)

            else:
                reply = discord.Embed(
                    title="💬 Введите новый заголовок",
                    description=f"**{name}** будет переименован.\nОтмена: `cancel`",
                    color=discord.Color.from_rgb(250, 250, 250)
                )
                reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                await ctx.send(embed=reply)

                message = await read_message(ctx.channel, ctx.author, 120, self.client)
                if message is None:
                    pass
                elif message.content.lower() == "cancel" or message.content.startswith(pr):
                    await ctx.send("Действие отменено")
                else:
                    text = message.content

                    collection.find_one_and_update(
                        {"_id": ctx.guild.id},
                        {"$rename": {f"fields.{name}": f"fields.{text}"}},
                        upsert=True
                    )

                    reply = discord.Embed(
                        title="✅ Выполнено",
                        description=f"**{name}** был переименован в **{text}**",
                        color=discord.Color.dark_green()
                    )
                    reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                    await ctx.send(embed=reply)

    @commands.command(aliases=["remove-field", "delete-field", "rf", "df"])
    async def remove_field(self, ctx, *, name):
        pr = ctx.prefix
        if not has_permissions(ctx.author, ["administrator"]):
            reply = discord.Embed(
                title="❌ Недостаточно прав",
                description=(
                    "**Необходимые права:**\n"
                    f"> Администратор"
                ),
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
            await ctx.send(embed=reply)
        
        else:
            collection = db["forms"]
            result = collection.find_one(
                {"_id": ctx.guild.id, f"fields.{name}": {"$exists": True}}
            )
            if result is None:
                reply = discord.Embed(
                    title="❌ Упс",
                    description=(
                        f"Вопроса с заголовком **{name}** не существует\n"
                        f"Просмотреть форму: `{pr}view-form`"
                    ),
                    color=discord.Color.dark_red()
                )
                reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                await ctx.send(embed=reply)

            else:
                collection.find_one_and_update(
                    {"_id": ctx.guild.id},
                    {"$unset": {f"fields.{name}": ""}}
                )
                reply = discord.Embed(
                    title="✅ Выполнено",
                    description=f"Поле **{name}** было удалено",
                    color=discord.Color.dark_green()
                )
                reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                await ctx.send(embed=reply)

    @commands.command(aliases=["clear-form", "cf"])
    async def clear_form(self, ctx):
        pr = ctx.prefix
        if not has_permissions(ctx.author, ["administrator"]):
            reply = discord.Embed(
                title="❌ Недостаточно прав",
                description=(
                    "**Необходимые права:**\n"
                    f"> Администратор"
                ),
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
            await ctx.send(embed=reply)
        
        else:
            collection = db["forms"]
            collection.find_one_and_update(
                {"_id": ctx.guild.id, "fields": {"$exists": True}},
                {"$unset": {"fields": ""}}
            )
            reply = discord.Embed(
                title="🗑 Форма удалена",
                description=f"Добавить новые поля: `{pr}add-field`"
            )
            reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
            await ctx.send(embed=reply)

    #======= Errors =========
    @add_field.error
    async def add_field_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    f"**Описание:** добавляет вопрос в анкету (форму) сервера\n"
                    f'**Использование:** `{p}{cmd} Заголовок`\n'
                    f"**Пример:** `{p}{cmd} Возраст`\n"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
    
    @reply_channel.error
    async def reply_channel_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    f"**Описание:** настраивает канал, в который будут отправляться заоплненные формы (обязателен для работы анкеты)\n"
                    f'**Использование:** `{p}{cmd} #канал`\n'
                    f"**Пример:** `{p}{cmd} #список-заявок`\n"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
    
    @rename.error
    async def rename_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    f"**Описание:** переименовывает заголовок вопроса\n"
                    f'**Использование:** `{p}{cmd} Старый заголовок`\n'
                    f"**Пример:** `{p}{cmd} Возпаст`\n"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
    
    @remove_field.error
    async def remove_field_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    f"**Описание:** удаляет вопрос из формы\n"
                    f'**Использование:** `{p}{cmd} Заголовок`\n'
                    f"**Пример:** `{p}{cmd} Возраст`\n"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

def setup(client):
    client.add_cog(forms(client))

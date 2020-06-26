import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio, os
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

import pymongo
from box.db_worker import cluster

#========== Variables ==========
db = cluster["guilds"]

mass_dm_errors = {}

#========== Functions ==========
from functions import has_permissions, detect, has_any_role, quote_list

def unwrap_isolation(text, s):
    length, wid, i = len(text), len(s), 0
    out = ""
    while i < length:
        if text[i:i + wid] == s:
            i += wid
            while i < length and text[i:i + wid] != s:
                out += text[i]
                i += 1
            out += "\n"
        i += 1
    return out.strip()

def color_from_string(_color):
    Col = discord.Color
    _color = _color.lower()
    if "," in _color:
        rgb = [c.strip() for c in _color.split(",")]
        rgb = [int(c) for c in rgb]
        if len(rgb) < 3 or len(rgb) > 3:
            _color = Col.default()
        else:
            in_range_bools = [(c >= 0 and c < 256) for c in rgb]
            if False in in_range_bools:
                _color = Col.default()
            else:
                _color = Col.from_rgb(*rgb)
    else:
        colors = {
            "green": Col.green(), "dark_green": Col.dark_green(),
            "red": Col.red(), "dark_red": Col.dark_red(),
            "blue": Col.default(), "dark_blue": Col.dark_blue(),
            "magenta": Col.magenta(), "teal": Col.teal(),
            "gold": Col.gold(), "orange": Col.orange(),
            "purple": Col.purple(), "blurple": Col.blurple(),
            "white": Col.from_rgb(255, 255, 255), "black": Col.from_rgb(1, 1, 1)
        }
        if _color not in colors:
            _color = Col.default()
        else:
            _color = colors[_color]
    return _color

def antiformat(text):
    alph = "qwertyuiopasdfghjklzxcvbnm1234567890 \n"
    out = ""
    for s in text:
        if s.lower() not in alph:
            out += "\\" + s
        else:
            out += s
    return out

def embed_from_string(text_input):
    # Carving logical parts
    _title = unwrap_isolation(text_input, "==")
    _desc = unwrap_isolation(text_input, "--")
    _color = unwrap_isolation(text_input, "##")
    _image_url = unwrap_isolation(text_input, "&&")
    _thumb_url = unwrap_isolation(text_input, "++")
    # Interpreting some values
    _color = color_from_string(_color)

    emb = discord.Embed(
        title=_title,
        description=_desc,
        color=_color
    )
    if _image_url != "":
        emb.set_image(url=_image_url)
    if _thumb_url != "":
        emb.set_thumbnail(url=_thumb_url)
    
    return emb

async def get_message(channel, msg_id):
    try:
        return await channel.fetch_message(msg_id)
    except Exception:
        return None

async def try_send_and_count(channel_or_user, message_id, content=None, embed=None, files=None):
    try:
        await channel_or_user.send(content=content, embed=embed, files=files)
    except Exception:
        global mass_dm_errors
        if message_id not in mass_dm_errors:
            mass_dm_errors[message_id] = 1
        else:
            mass_dm_errors[message_id] += 1

class Welcome_card:
    def __init__(self, member):
        self.name = str(member)
        self.count = member.guild.member_count
        self.avatar_url = member.avatar_url
        self.bg = Image.open("images/welcome_card.png")
        self.draw = None
        self.font = None

    def paste_avatar(self, ulc, width):
        r = requests.get(self.avatar_url)
        avatar = Image.open( BytesIO(r.content ) ).resize((width, width))

        mask = Image.new('L', (width, width), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + (width, width), fill=255)

        self.bg.paste(avatar, (*ulc, ulc[0] + width, ulc[1] + width), mask)
    
    def write(self, center, text, font_size, fill=None):
        if self.font is None:
            self.font = ImageFont.truetype("fonts/vida33pro.otf", size=font_size, encoding="utf-8")
        else:
            self.font.size = font_size
        if self.draw is None:
            self.draw = ImageDraw.Draw(self.bg)
        
        tsize = self.draw.textsize(text, font=self.font)
        tulc = (center[0] - tsize[0] // 2, center[1] - tsize[1] // 2)
        self.draw.text(tulc, text, font=self.font, fill=fill)
    
    def save_as(self, path, _format="PNG"):
        self.bg.save(path, _format)


class utilities(commands.Cog):
    def __init__(self, client):
        self.client = client

    #========== Events ===========
    @commands.Cog.listener()
    async def on_ready(self):
        print(">> Utilities cog is loaded")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        collection = db["msg_manip"]
        result = collection.find_one(
            {"_id": member.guild.id},
            projection={
                "welcome_channel": True,
                "welcome_message": True
            }
        )
        if result is None:
            result = {}
        channel = member.guild.get_channel( result.get("welcome_channel", 0) )
        message = result.get("welcome_message")

        if channel is not None:
            path = f"images/{member.id}.png"
            wc = Welcome_card(member)
            wc.paste_avatar((178, 73), 124)
            wc.write((242, 235), wc.name, 37, (255, 108, 0))
            wc.write((240, 233), wc.name, 37)
            wc.write((242, 32), str(wc.count), 37, (255, 108, 0))
            wc.write((240, 30), str(wc.count), 37)
            wc.save_as(path)

            message = message.replace("{member_count}", str(wc.count))
            message = message.replace("{user}", antiformat(wc.name))
            message = message.replace("{server}", str(member.guild.name))
            del wc

            _file = discord.File(path, f"{member.id}.png")
            wemb = discord.Embed(
                description=message,
                color=member.guild.me.color
            )
            wemb.set_image(url=f"attachment://{_file.filename}")
            await channel.send(str(member.mention), embed=wemb, file=_file)
            del _file
            os.remove(path)

    #========= Commands ==========
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases=["dm-role", "mass-send", "role-dm", "dr"])
    async def dm_role(self, ctx, role_search, *, text):
        req_roles = [688313470881759288]
        if not has_any_role(ctx.author, req_roles):
            reply = discord.Embed(
                title="❌ Нет нужной роли",
                description=f"**Требуемые роли:**\n{quote_list([f'<@&{_id}>' for _id in req_roles])}",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)

        else:
            role = detect.role(ctx.guild, role_search)
            if role is None:
                reply = discord.Embed(
                    title="💥 Неверно указана роль",
                    description="Укажите ID или @упоминание роли",
                    color=discord.Color.dark_red()
                )
                reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
                await ctx.send(embed=reply)

            else:
                atts = ctx.message.attachments

                paper = f"📢 **{ctx.guild.name}**\n\n{text}"[:2000]
                files = []
                
                for att in atts:
                    files.append(await att.to_file())

                total_targets = 0
                await ctx.send("🕑 Пожалуйста, подождите...")
                for member in ctx.guild.members:
                    if role in member.roles:
                        total_targets += 1
                        self.client.loop.create_task(try_send_and_count(member, ctx.message.id, paper, files=files))
                
                await ctx.send("🕑 Собираю данные...")

                global mass_dm_errors
                error_targets = mass_dm_errors.get(ctx.message.id, 0)
                if ctx.message.id in mass_dm_errors:
                    mass_dm_errors.pop(ctx.message.id)

                reply = discord.Embed(
                    title="✅ Рассылка завершена",
                    description=(
                        f"**Получатели:** обладатели роли <@&{role.id}>\n"
                        f"**Всего:** {total_targets}\n"
                        f"**Получили:** {total_targets - error_targets}\n"
                    ),
                    color=discord.Color.dark_green()
                )
                reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
                await ctx.send(embed=reply)

    @commands.cooldown(1, 1, commands.BucketType.member)
    @commands.command()
    async def embed(self, ctx, *, text_input):
        req_roles = [688313470881759288]
        if not has_any_role(ctx.author, req_roles):
            reply = discord.Embed(
                title="❌ Нет нужной роли",
                description=f"**Требуемые роли:**\n{quote_list([f'<@&{_id}>' for _id in req_roles])}",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)

        else:
            emb = embed_from_string(text_input)
            
            await ctx.send(embed=emb)
            try:
                await ctx.author.send(f"{ctx.prefix}embed {antiformat(text_input)}")
            except Exception:
                pass
            try:
                await ctx.message.delete()
            except Exception:
                pass

    @commands.cooldown(1, 1, commands.BucketType.member)
    @commands.command()
    async def edit(self, ctx, _id, *, text_input):
        req_roles = [688313470881759288]
        if not has_any_role(ctx.author, req_roles):
            reply = discord.Embed(
                title="❌ Нет нужной роли",
                description=f"**Требуемые роли:**\n{quote_list([f'<@&{_id}>' for _id in req_roles])}",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)

        else:
            if not _id.isdigit():
                reply = discord.Embed(
                    title="❌ Ошибка",
                    description=f"ID должно состоять из цифр.\nВведено: {_id}",
                    color=discord.Color.dark_red()
                )
                reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                await ctx.send(embed=reply)
            
            else:
                message = await get_message(ctx.channel, int(_id))
                if message is None:
                    reply = discord.Embed(
                        title="🔎 Сообщение не найдено",
                        description=f"В этом канале нет сообщения с ID: `{_id}`"
                    )
                    reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                    await ctx.send(embed=reply)
                
                elif message.author.id != self.client.user.id:
                    reply = discord.Embed(
                        title="❌ Это не моё сообщение",
                        description="Я не имею права редактировать чужие сообщения",
                        color=discord.Color.dark_red()
                    )
                    reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                    await ctx.send(embed=reply)
                
                else:
                    emb = embed_from_string(text_input)
                    
                    await message.edit(embed=emb)
                    try:
                        await ctx.author.send(f"{ctx.prefix}edit {_id} {antiformat(text_input)}")
                    except Exception:
                        pass
                    try:
                        await ctx.message.delete()
                    except Exception:
                        pass

    #======== Errors ===========
    @dm_role.error
    async def dm_role_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    f"**Описание:** рассылает сообщения в ЛС обладателям конкретной роли\n"
                    f"**Использование:** `{p}{cmd} @Роль Текст`\n"
                    f"**Пример:** `{p}{cmd} @Member Выпущен новый свод правил`\n"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @embed.error
    async def embed_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Как пользоваться `{p}{cmd}`",
                description = (
                    "**Описание:** создаёт рамку с заголовком, текстом, картинкой и т.п.\n"
                    "Что нужно писать, чтобы создавать разные части рамки:\n"
                    "> `==Заголовок==` - задаёт заголовок\n"
                    "> `--Текст--` - задаёт текстовый блок\n"
                    "> `##цвет##` - задаёт цвет (см. ниже)\n"
                    "> `&&url_картинки&&` - задаёт большую картинку\n"
                    "> `++url_картинки++` - задаёт маленькую картинку\n"
                    "**О цвете:** цвет может быть как из списка, так и из параметров RGB\n"
                    "В RGB формате между `##` должны идти 3 числа через запятую, например `##23, 123, 123##`\n"
                    "Список цветов: `red, dark_red, blue, dark_blue, green, dark_green, gold, teal, magenta, purple, blurple, orange, white, black`\n"
                    "**Пример**\n"
                    f"```{p}{cmd} ==Обновление==\n"
                    "--Мы добавили роль **Помощник**!--\n"
                    "##gold##```"
                ),
                color=discord.Color.from_rgb(0, 57, 84)
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @edit.error
    async def edit_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Как пользоваться `{p}{cmd}`",
                description = (
                    "**Описание:** редактирует мои рамки (эмбеды)\n"
                    f"**Использование:** `{p}{cmd} ID_сообщения Текст_для_эмбеда`\n"
                    f"**Подробнее о тексте для эмбеда:** `{p}embed`"
                ),
                color=discord.Color.from_rgb(0, 57, 84)
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

def setup(client):
    client.add_cog(utilities(client))
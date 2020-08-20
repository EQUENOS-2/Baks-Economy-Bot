import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio, os
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import datetime, timedelta

from pymongo import MongoClient
app_string = str(os.environ.get('cluster_string'))
cluster = MongoClient(app_string)

#----------------------------------------------+
#                 Constants                    |
#----------------------------------------------+
from failures import CooldownResetSignal

db = cluster["guilds"]

mass_dm_errors = {}

reaction_add_timers = {}

#----------------------------------------------+
#                  Functions                   |
#----------------------------------------------+
from functions import detect, quote_list, antiformat, is_moderator, ReactionRolesConfig


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


def embed_from_string(text_input):
    # Carving logical parts
    _title = unwrap_isolation(text_input, "==")
    _desc = unwrap_isolation(text_input, "--")
    _color = unwrap_isolation(text_input, "##")
    _image_url = unwrap_isolation(text_input, "&&")
    _thumb_url = unwrap_isolation(text_input, "++")
    _footer_url = unwrap_isolation(text_input, ";;")
    _footer_text = unwrap_isolation(text_input, "::")
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
    if _footer_text != "" or _footer_url != "":
        emb.set_footer(text=_footer_text, icon_url=_footer_url)
    
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

    def generate(self):
        self.paste_avatar((178, 73), 124)
        self.write((242, 235), self.name, 37, (255, 108, 0))
        self.write((240, 233), self.name, 37)
        self.write((242, 32), str(self.count), 37, (255, 108, 0))
        self.write((240, 30), str(self.count), 37)

        bimg = BytesIO()
        self.bg.save(bimg, format='PNG')
        bimg = bimg.getvalue()
        
        return BytesIO(bimg)


class utilities(commands.Cog):
    def __init__(self, client):
        self.client = client

    #----------------------------------------------+
    #                   Events                     |
    #----------------------------------------------+
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
            wc = Welcome_card(member)
        
            message = message.replace("{member_count}", str(wc.count))
            message = message.replace("{user}", antiformat(wc.name))
            message = message.replace("{server}", str(member.guild.name))

            wemb = discord.Embed(
                description=message,
                color=member.guild.me.color
            )
            wemb.set_image(url=f"attachment://welcome.png")
            await channel.send(str(member.mention), embed=wemb, file=discord.File(wc.generate(), "welcome.png"))

    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        server_rr = ReactionRolesConfig(payload.guild_id)
        emojis = server_rr.get_roles(payload.message_id)
        # If emoji is registered
        if str(payload.emoji) in emojis:
            guild = self.client.get_guild(payload.guild_id)
            role = guild.get_role(emojis[str(payload.emoji)])
            # If the role still exists
            if role is not None:
                member = guild.get_member(payload.user_id)
                if role not in member.roles:
                    try:
                        await member.add_roles(role)

                    except Exception:
                        pass

    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        server_rr = ReactionRolesConfig(payload.guild_id)
        emojis = server_rr.get_roles(payload.message_id)
        # If emoji is registered
        if str(payload.emoji) in emojis:
            guild = self.client.get_guild(payload.guild_id)
            role = guild.get_role(emojis[str(payload.emoji)])
            # If the role still exists
            if role is not None:
                member = guild.get_member(payload.user_id)
                if role in member.roles:
                    try:
                        await member.remove_roles(role)

                    except Exception:
                        pass

    #----------------------------------------------+
    #                  Commands                    |
    #----------------------------------------------+
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.check_any(
        commands.has_permissions(administrator=True),
        is_moderator() )
    @commands.command(
        aliases=["dm-role", "mass-send", "role-dm", "dr"],
        description="рассылает сообщения в ЛС обладателям конкретной роли",
        usage="@Роль Текст",
        brief="@Member Выпущен новый свод правил" )
    async def dm_role(self, ctx, role: discord.Role, *, text):
        atts = ctx.message.attachments

        paper = f"📢 **{ctx.guild.name}**\n\n{text}"[:2000]
        _files = [await att.to_file() for att in atts]

        total_targets = 0
        errors = 0
        progbar = await ctx.send(f"🕑 Идёт рассылка...\nВыслал уже нескольким пользователям...")
        for member in ctx.guild.members:
            if role in member.roles:
                total_targets += 1
                #self.client.loop.create_task(try_send_and_count(member, ctx.message.id, paper, files=_files))
                try:
                    await member.send(paper, files=_files)
                except Exception:
                    errors += 1
                if total_targets % 50 == 0:
                    try:
                        await progbar.edit(content=f"🕑 Идёт рассылка...\nВыслал уже {total_targets}+ пользователям...")
                    except Exception:
                        pass
        
        # await ctx.send("🕑 Собираю данные...")

        # global mass_dm_errors
        # error_targets = mass_dm_errors.get(ctx.message.id, 0)
        # if ctx.message.id in mass_dm_errors:
        #     mass_dm_errors.pop(ctx.message.id)

        reply = discord.Embed(
            title="✅ Рассылка завершена",
            description=(
                f"**Получатели:** обладатели роли <@&{role.id}>\n"
                f"**Всего:** {total_targets}\n"
                f"**Получили:** {total_targets - errors}\n"
            ),
            color=discord.Color.dark_green()
        )
        reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
        await ctx.send(embed=reply)


    @commands.cooldown(1, 1, commands.BucketType.member)
    @commands.check_any(
        commands.has_permissions(administrator=True),
        is_moderator() )
    @commands.command(
        description=(
            "создаёт рамку с заголовком, текстом, картинкой и т.п.\n"
            "Что нужно писать, чтобы создавать разные части рамки:\n"
            "> `==Заголовок==` - заголовок\n"
            "> `--Текст--` - текстовый блок\n"
            "> `##цвет##` - цвет (см. ниже)\n"
            "> `&&url_картинки&&` - большая картинка\n"
            "> `++url_картинки++` - маленькая картинка\n"
            "> `;;url_картинки;;` - иконка футера\n"
            "> `::Текст::` - текст футера\n"
            "**О цвете:** цвет может быть как из списка, так и из параметров RGB\n"
            "В RGB формате между `##` должны идти 3 числа через запятую, например `##23, 123, 123##`\n"
            "Список цветов: `red, dark_red, blue, dark_blue, green, dark_green, gold, teal, magenta, purple, blurple, orange, white, black`"
        ),
        brief="==Обновление== --Мы добавили роль **Помощник**!-- ##gold##" )
    async def embed(self, ctx, *, text_input):
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
    @commands.check_any(
        commands.has_permissions(administrator=True),
        is_moderator() )
    @commands.command(
        description="редактирует мои рамки (эмбеды) (подробнее в команде `embed`)",
        usage="ID_сообщения Текст_для_эмбеда" )
    async def edit(self, ctx, _id, *, text_input):
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


    @commands.cooldown(1, 120, commands.BucketType.member)
    @commands.check_any(
        commands.has_permissions(administrator=True),
        is_moderator() )
    @commands.command(
        aliases=["reaction-role", "rr", "reactionrole", "add-reaction-role"],
        description="добавляет роль за реакцию под сообщением.",
        usage="Роль",
        brief="Minecraft Player" )
    async def reaction_role(self, ctx, *, role: discord.Role):
        if role.position >= ctx.author.top_role.position  and ctx.author.id != ctx.guild.owner_id:
            reply = discord.Embed(
                title="❌ Недостаточно прав",
                description=f"Указанная роль **<@&{role.id}>** выше Вашей, поэтому Вы не имеете права предоставлять её за нажатие на реакцию.",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
            await ctx.send(embed=reply)

        else:
            server_rr = ReactionRolesConfig(ctx.guild.id)

            reply = discord.Embed(
                title="🧸 | Роль за реакцию",
                description=(
                    f"Вы указали **<@&{role.id}>** в качестве роли за реакцию.\n"
                    "Теперь, пожалуйста, под нужным Вам сообщением добавьте реакцию, за которую будет даваться роль."
                ),
                color=role.color
            )
            reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)

            # Waiting for moderator's reaction
            def check(payload):
                return payload.user_id == ctx.author.id and payload.guild_id == ctx.guild.id
            
            cycle = True
            _payload = None
            while cycle:
                try:
                    payload = await self.client.wait_for("raw_reaction_add", check=check, timeout=120)

                except asyncio.TimeoutError:
                    reply = discord.Embed(
                        title="🕑 | Превышено время ожидания",
                        description="Вы не ставили реакцию более 120 секунд",
                        color=discord.Color.blurple()
                    )
                    reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
                    await ctx.send(ctx.author.mention, embed=reply)
                    cycle = False

                else:
                    if server_rr.get_role(payload.message_id, payload.emoji) is not None:
                        reply = discord.Embed(
                            title="⚠ Ошибка",
                            description="За эту реакцию уже даётся роль",
                            color=discord.Color.gold()
                        )
                        reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                        await ctx.send(ctx.author.mention, embed=reply)

                    else:
                        channel = ctx.guild.get_channel(payload.channel_id)
                        message = await channel.fetch_message(payload.message_id)
                        try:
                            await message.add_reaction(payload.emoji)
                            await message.remove_reaction(payload.emoji, ctx.author)
                        except Exception:
                            pass
                        else:
                            cycle = False
                            _payload = payload
            
            # Adding emoji-role pair to database
            if _payload is not None:
                server_rr.add_role(_payload.message_id, _payload.emoji, role.id)

                reply = discord.Embed(
                    title="🧸 | Роль за реакцию",
                    description=f"Теперь в канале <#{_payload.channel_id}> даётся роль **<@&{role.id}>** за реакцию [{_payload.emoji}] под нужным сообщением.",
                    color=role.color
                )
                reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
                await ctx.send(embed=reply)
        
        # Resetting cooldownd
        raise CooldownResetSignal()


    @commands.cooldown(1, 120, commands.BucketType.member)
    @commands.check_any(
        commands.has_permissions(administrator=True),
        is_moderator() )
    @commands.command(
        aliases=["remove-reaction-role", "rrr", "removereactionrole", "reaction-role-remove"] )
    async def remove_reaction_role(self, ctx):
        server_rr = ReactionRolesConfig(ctx.guild.id)

        reply = discord.Embed(
            title="↩ | Сброс роли за реакцию",
            description="Пожалуйста, под нужным Вам сообщением уберите (или поставьте и уберите) реакцию, за которую даётся роль.",
            color=discord.Color.magenta()
        )
        reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
        await ctx.send(embed=reply)

        # Waiting for moderator's reaction
        def check(payload):
            return payload.user_id == ctx.author.id and payload.guild_id == ctx.guild.id
        
        cycle = True
        _payload = None
        role_id = None
        while cycle:
            try:
                payload = await self.client.wait_for("raw_reaction_remove", check=check, timeout=120)

            except asyncio.TimeoutError:
                reply = discord.Embed(
                    title="🕑 | Превышено время ожидания",
                    description="Вы не убирали реакции более 120 секунд",
                    color=discord.Color.blurple()
                )
                reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
                await ctx.send(ctx.author.mention, embed=reply)
                cycle = False

            else:
                role_id = server_rr.get_role(payload.message_id, payload.emoji)
                if role_id is None:
                    reply = discord.Embed(
                        title="⚠ Ошибка",
                        description="За эту реакцию не даётся роль",
                        color=discord.Color.gold()
                    )
                    reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                    await ctx.send(ctx.author.mention, embed=reply)

                else:
                    channel = ctx.guild.get_channel(payload.channel_id)
                    message = await channel.fetch_message(payload.message_id)
                    try:
                        await message.clear_reaction(payload.emoji)
                    except Exception:
                        pass
                    else:
                        cycle = False
                        _payload = payload
        
        # Adding emoji-role pair to database
        if _payload is not None:
            server_rr.remove_reaction(_payload.message_id, _payload.emoji)

            reply = discord.Embed(
                title="🎀 | Сброс роли за реакцию",
                description=f"Теперь, под указанным сообщением, роль **<@&{role_id}>** больше не даётся за реакцию [{_payload.emoji}].",
                color=discord.Color.magenta()
            )
            reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)
        
        # Resetting cooldownd
        raise CooldownResetSignal()


    @commands.cooldown(1, 2, commands.BucketType.member)
    @commands.check_any(
        commands.has_permissions(administrator=True),
        is_moderator() )
    @commands.command(aliases=["preview-welcome", "pw"])
    async def preview_welcome(self, ctx):
        wc = Welcome_card(ctx.author)
        
        collection = db["msg_manip"]
        result = collection.find_one(
            {"_id": ctx.author.guild.id},
            projection={"welcome_message": True}
        )
        if result is None:
            result = {}
        message = result.get("welcome_message")
        message = message.replace("{member_count}", str(wc.count))
        message = message.replace("{user}", antiformat(wc.name))
        message = message.replace("{server}", str(ctx.author.guild.name))

        wemb = discord.Embed(
            description=message,
            color=ctx.guild.me.color
        )
        wemb.set_image(url=f"attachment://welcome.png")
        await ctx.send(str(ctx.author.mention), embed=wemb, file=discord.File(wc.generate(), "welcome.png"))


    
def setup(client):
    client.add_cog(utilities(client))
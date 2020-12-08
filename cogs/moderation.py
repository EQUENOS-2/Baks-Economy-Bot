import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta

#----------------------------------------------+
#                 Functions                    |
#----------------------------------------------+
from functions import is_moderator, visual_delta as vis_delta, antiformat as anf
from  db_models import MuteList, MuteModel, get_saved_mutes
from custom_converters import TimedeltaConverter, IntConverter


class MuteSliceTimer:
    def __init__(self):
        self.last_at = datetime.utcnow()
        self.interval = timedelta(hours=1)
    @property
    def next_in(self):
        next_at = self.last_at + self.interval
        now = datetime.utcnow()
        return next_at - now if next_at > now else timedelta(seconds=0)

    def update(self):
        self.last_at = datetime.utcnow()
MST = MuteSliceTimer()
mute_role_name = "Мут"


async def process_mute_role(server, name):
    role = discord.utils.get(server.roles, name=name)
    if role is None:
        role = await server.create_role(name=name, permissions=discord.Permissions(send_messages=False, speak=False))
        tco = discord.PermissionOverwrite(send_messages=False)
        vco = discord.PermissionOverwrite(speak=False)
        catego = discord.PermissionOverwrite(send_messages=False, speak=False)
        for c in server.channels:
            if isinstance(c, discord.TextChannel):
                ovw = tco
            elif isinstance(c, discord.VoiceChannel):
                ovw = vco
            else:
                ovw = catego
            ovw = {**c.overwrites, role: ovw}
            await c.edit(overwrites=ovw)
    return role


class moderation(commands.Cog):
    def __init__(self, client):
        self.client = client

    #----------------------------------------------+
    #                  Methods                     |
    #----------------------------------------------+
    async def process_unmute(self, mutemodel: MuteModel):
        await asyncio.sleep(mutemodel.time_remaining.total_seconds())
        mutemodel.end()
        # Role manipulations
        guild = self.client.get_guild(mutemodel.server_id)
        role = discord.utils.get(guild.roles, name=mute_role_name)
        member = guild.get_member(mutemodel.id)
        if member is not None and role is not None and role in member.roles:
            try:
                await member.remove_roles(role)
            except:
                pass
        try:
            await member.edit(mute=False)
        except:
            pass
        # Notifications
        reply = discord.Embed(color=0x2b2b2b, description="Время мута истекло, Вы были размучены.")
        reply.set_footer(text=f"Сервер {guild}", icon_url=guild.icon_url )
        try:
            await member.send(embed=reply)
        except:
            pass
        return

    #----------------------------------------------+
    #                   Events                     |
    #----------------------------------------------+
    @commands.Cog.listener()
    async def on_ready(self):
        print(f">> Moderation cog is loaded")
        # Refreshing mutes every X hours
        while True:
            print(f"MuteSlicer: {MST.last_at}")
            for mutelist in get_saved_mutes(MST.last_at + MST.interval): # Gets all closest mutes
                for mm in mutelist.mutes:
                    self.client.loop.create_task(self.process_unmute(mm))
            await asyncio.sleep(MST.next_in.total_seconds())
            MST.update()


    @commands.Cog.listener()
    async def on_member_join(self, member):
        mm = MuteModel(member.guild.id, member.id)
        if mm.time_remaining > timedelta(seconds=0):
            role = discord.utils.get(member.guild.roles, name=mute_role_name)
            if role is not None and role not in member.roles:
                try:
                    await member.add_roles(role)
                except:
                    return
    

    #----------------------------------------------+
    #                  Commands                    |
    #----------------------------------------------+
    @commands.check_any(
        is_moderator(),
        commands.has_permissions(manage_messages=True) )
    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command(
        aliases=["clean"],
        description="",
        usage="",
        brief="" )
    async def clear(self, ctx, amount: int):
        await ctx.channel.purge(limit=amount + 1)
        reply = discord.Embed(
            title="🗑 | Чистка канала",
            description=f"Удалено **{amount}** сообщений",
            color=ctx.guild.me.color
        )
        reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
        await ctx.send(embed=reply, delete_after=3)

    
    @commands.check_any(
        is_moderator(),
        commands.has_permissions(administrator=True) )
    @commands.command(
        description="мутит пользователя во всех чатах",
        usage="@Участник Время Причина(не обязательно)",
        brief="@User#1234 30m Спам в чате" )
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def mute(self, ctx, member: discord.Member, time: TimedeltaConverter, *, reason=None):
        mutelist = MuteList(ctx.guild.id, data={})
        async with ctx.typing():
            try:
                muteRole = await process_mute_role(ctx.guild, mute_role_name)
                await member.add_roles(muteRole)
                mutelist.add(member.id, time, ctx.author.id, reason)
                await member.edit(mute=True)
            except:
                pass
        
        if reason is None:
            reason = "Не указана"

        reply = discord.Embed(colour=0xFFA500)
        reply.description = (
            f"**Длительность:** {vis_delta(time)}\n"
            f"**Причина:** {reason}"
        )
        reply.set_author(name=f" [🔇] {member} был замучен.")
        reply.set_footer(text= f"Выдал: {ctx.author}", icon_url = ctx.author.avatar_url )

        await ctx.send(embed=reply)

        notif = discord.Embed(color=0x2b2b2b, description=f"**[🔇]** Вы были замучены на сервере.")
        notif.set_thumbnail(url=f"{ctx.guild.icon_url}")
        notif.set_footer(text=f"Модератор: {ctx.author}", icon_url=ctx.author.avatar_url )
        notif.add_field(name="Причина:", value=f"{reason}")
        notif.add_field(name="Продолжительность:", value=vis_delta(time))

        try:
            await member.send(embed=notif)
        except:
            pass
        # Mute length classification
        if time >= MST.next_in:
            return # Happens not to collide with mute slicer
        else:
            await asyncio.sleep(time.total_seconds())
            try:
                mutelist.remove(member.id)
                await member.remove_roles(muteRole)
                await member.edit(mute=False)
            except:
                pass

            notif = discord.Embed(color=0x2b2b2b, description="Время мута истекло, Вы были размучены.")
            notif.set_footer(text=f"Сервер {ctx.guild}", icon_url=ctx.guild.icon_url )
            try:
                await member.send(embed=notif)
            except:
                pass
    

    @commands.command(
        description="досрочно снимает мут",
        usage="Участник",
        brief="User#1234" )
    @commands.check_any(
        is_moderator(),
        commands.has_permissions(administrator=True) )
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def unmute(self, ctx, *, member: discord.Member):
        mm = MuteModel(ctx.guild.id, member.id)
        mm.end()
        # Role & mute manipulations
        try:
            await member.edit(mute=False)
        except:
            pass
        role = discord.utils.get(ctx.guild.roles, name=mute_role_name)
        if role in member.roles:
            try:
                await member.remove_roles(role)
            except:
                pass

        elif mm.time_remaining.total_seconds() == 0:
            reply = discord.Embed(color=discord.Color.red())
            reply.title = "❌ | Ошибка"
            reply.description = f"Участник **{anf(member)}** не замьючен."
            reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)
            return #
        
        reply = discord.Embed(color=discord.Color.green())
        reply.title = "🔉 | Участник досрочно размучен"
        reply.description = f"Участник **{anf(member)}** был досрочно размучен."
        reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
        await ctx.send(embed=reply)

        reply = discord.Embed(color=0x2b2b2b, description="Время мута истекло, Вы были размучены.")
        reply.set_footer(text=f"Сервер {ctx.guild}", icon_url=ctx.guild.icon_url )
        try:
            await member.send(embed=reply)
        except:
            pass


    @commands.command()
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def mutes(self, ctx, page: IntConverter=1):
        interval = 10
        mutelist = MuteList(ctx.guild.id)
        mutes = sorted(mutelist.mutes, key=lambda mm: mm.ends_at)
        del mutelist

        total_mutes = len(mutes)
        if total_mutes == 0:
            total_pages = 1
        else:
            total_pages = (total_mutes - 1) // interval +  1
        
        if not (0 < page <= total_pages):
            page = total_pages
        lowerb = (page - 1) * interval
        upperb = min(page * interval, total_mutes)

        reply = discord.Embed(color=discord.Color.blurple())
        reply.title = "📑 | Список людей, находящихся в муте"
        reply.set_footer(text=f"Стр. {page} / {total_pages}")
        for i in range(lowerb, upperb):
            mm = mutes[i]
            member = ctx.guild.get_member(mm.id)
            mod = ctx.guild.get_member(mm.mod_id)
            reply.add_field(name=f"🔒 | {anf(member)}", value=(
                f"> **Осталось:** {vis_delta(mm.time_remaining)}\n"
                f"> **Модератор:** {anf(mod)}\n"
                f"> **Причина:** {mm.reason}"
            )[:256], inline=False)
        if len(reply.fields) == 0:
            reply.description = "Мутов нет, какие молодцы!"
        await ctx.send(embed=reply)


    #----------------------------------------------+
    #                   Errors                     |
    #----------------------------------------------+


def setup(client):
    client.add_cog(moderation(client))

import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio

#----------------------------------------------+
#                 Functions                    |
#----------------------------------------------+
from functions import is_moderator, visual_delta as vis_delta
from custom_converters import TimedeltaConverter


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
            await c.edit(overwrites={role: ovw})
    return role


class moderation(commands.Cog):
    def __init__(self, client):
        self.client = client

    #----------------------------------------------+
    #                   Events                     |
    #----------------------------------------------+
    @commands.Cog.listener()
    async def on_ready(self):
        print(f">> Moderation cog is loaded")

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
    @commands.command()
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def mute(self, ctx, member: discord.Member, time: TimedeltaConverter, *, reason=None):
        if reason is None:
            reason = "Без причины"
        
        async with ctx.typing():
            muteRole = await process_mute_role(ctx.guild, "Мут")
            await member.add_roles(muteRole)

        tempMuteEmbed = discord.Embed(colour=0xFFA500, description=f"**Причина:** {reason}")
        tempMuteEmbed.set_author(name=f" [🔇] {member} был замучен на {vis_delta(time)}")
        tempMuteEmbed.set_footer(text= f"Выдал: {ctx.author}", icon_url = ctx.author.avatar_url )

        await ctx.channel.send(embed=tempMuteEmbed)

        tempMuteDM = discord.Embed(color=0xFFA500, description=f"**[🔇]** Вы были замучены на сервере.")
        tempMuteDM.set_thumbnail(url=f"{ctx.guild.icon_url}"), tempMuteDM.set_footer(text= "Мут был выдан: {} " .format( ctx.author.name  ), icon_url = ctx.author.avatar_url )
        tempMuteDM.add_field(name="Причина:", value=f"{reason}")
        tempMuteDM.add_field(name="Продолжительность:", value=vis_delta(time))

        userToDM = self.client.get_user(member.id)
        await userToDM.send(embed=tempMuteDM)
        await asyncio.sleep(time.total_seconds())
        await member.remove_roles(muteRole)


        unMuteEmbed = discord.Embed(color=0xFFA500, description="Время мута истекло, вы были размучены.")
        #unMuteEmbed.set_author(name=f"🔊UNMUTE] {member}", icon_url=f"{member.avatar_url}")
        #unMuteEmbed.add_field(name="User", value=f"{member.mention}")
        unMuteEmbed.set_footer(text=f"Сервер {ctx.guild}", icon_url=ctx.guild.icon_url )

        await member.send(embed=unMuteEmbed)
    
    #----------------------------------------------+
    #                   Errors                     |
    #----------------------------------------------+


def setup(client):
    client.add_cog(moderation(client))

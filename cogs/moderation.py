import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio

#----------------------------------------------+
#                 Functions                    |
#----------------------------------------------+
from functions import is_moderator

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

      
    #@commands.check_any(
    #commands.has_permissions( mute_members =True) )
    @commands.command()
    @commands.cooldown(1, 2, commands.BucketType.member)
    #@commands.has_any_role(599943309871415317, 708738041824542720, 708938791838154762)
    async def mute(self, ctx, member : discord.Member, time:str=" хуй ", *, reason=None):
        if not member or time == 0 or time == str:
            await ctx.channel.send(embed=EnvironmentError)
            return
        elif reason == None:
            reason = "Без причины"
        
        muteRole = ctx.guild.get_role(780005676461195294)
        await member.add_roles(muteRole)

        tempMuteEmbed = discord.Embed(colour=0xFFA500, description=f"**Причина:** {reason}")
        tempMuteEmbed.set_author(name=f" [🔇] {member} был замучен на {time[:-1]} минут.")
        tempMuteEmbed.set_footer(text= "Мут был выдан: {} " .format( ctx.author.name  ), icon_url = ctx.author.avatar_url )

        await ctx.channel.send(embed=tempMuteEmbed)
        # await ctx.send( embed = tempMuteEmbed )          -  ОТПРАВКА В ЛС
        # await member.send( embed = tempMuteEmbed )         -  ОТПРАВКА В ЛС 

        tempMuteDM = discord.Embed(color=0xFFA500, description=f"**[🔇]** Вы были замучены на сервере.")
        tempMuteDM.set_thumbnail(url=f"{ctx.guild.icon_url}"), tempMuteDM.set_footer(text= "Мут был выдан: {} " .format( ctx.author.name  ), icon_url = ctx.author.avatar_url )
        tempMuteDM.add_field(name="Причина:", value=f"{reason}")
        tempMuteDM.add_field(name="Минуты:", value=f"{time[:-1]}")

        userToDM = self.client.get_user(member.id)
        await userToDM.send(embed=tempMuteDM)
        print ( convert_time_to_minutes (time), type( time ) )
        await asyncio.sleep (int (convert_time_to_minutes (time)))
        await member.remove_roles(muteRole)


        unMuteEmbed = discord.Embed(color=0xFFA500, description="Время мута истекло, вы были размучены.")
        #unMuteEmbed.set_author(name=f"🔊UNMUTE] {member}", icon_url=f"{member.avatar_url}")
        #unMuteEmbed.add_field(name="User", value=f"{member.mention}")
        unMuteEmbed.set_footer(text = "Сервер TEST", icon_url = ctx.guild.icon_url )

        await member.send(embed=unMuteEmbed)
    #----------------------------------------------+
    #                   Errors                     |
    #----------------------------------------------+


def setup(client):
    client.add_cog(moderation(client))

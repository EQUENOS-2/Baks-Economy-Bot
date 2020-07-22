import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio
import brawlstats
import os
from random import choice

#----------------------------------------------+
#       Connecting to Brawl Stars API          |
#----------------------------------------------+
brawl_token = str(os.environ.get("brawl_token"))
brawl = None
try:
    brawl = brawlstats.Client(brawl_token)
except Exception:
    pass

#----------------------------------------------+
#                 Constants                    |
#----------------------------------------------+
from functions import bscolors, antiformat as anf, owner_ids
from custom_emojis import *
emj = Emj()

#----------------------------------------------+
#                 Functions                    |
#----------------------------------------------+
from functions import timeout_embed, BrawlDiscordList, BrawlDiscordUser

class brawlactions(commands.Cog):
    def __init__(self, client):
        self.client = client

    #----------------------------------------------+
    #                   Events                     |
    #----------------------------------------------+
    @commands.Cog.listener()
    async def on_ready(self):
        print(f">> Brawl Actions cog is loaded")

    #----------------------------------------------+
    #                  Commands                    |
    #----------------------------------------------+
    @commands.command()
    async def test(self, ctx):
        if ctx.author.id in owner_ids:
            try:
                brawlstats.Client(brawl_token)
            except Exception as e:
                await ctx.send(str(e))


    @commands.cooldown(1, 360, commands.BucketType.member)
    @commands.command()
    async def verify(self, ctx):
        bdlist = BrawlDiscordList()
        if bdlist.contains_id(ctx.author.id):
            reply2 = discord.Embed(
                title="❌ | Ошибка",
                description=f"Ваша учётная запись Discord уже привязана к другому аккаунту Brawl Stars.",
                color=discord.Color.dark_red()
            )
            reply2.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply2)
        
        else:
            # Introduction
            reply = discord.Embed(
                title="🔗 | Привязка аккаунта Brawl Stars",
                description=(
                    "Сейчас я попрошу Вас написать свой тег в Brawl Stars, после чего у Вас будет ровно 3 минуты, чтобы временно сменить цвет ника в игре.\n"
                    "Это нужно, чтобы подтвердить, что владелец указанного аккаунта - именно Вы.\n\n"
                    "Пожалуйста, укажите тег в бравл старс. Пример - `#ABCDEFGH`\n"
                    "*Для отмены напишите `cancel`*"
                ),
                color=discord.Color.orange()
            )
            reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)

            # Waiting for a valid brawl tag
            cycle = True
            player = None
            while cycle:
                try:
                    msg = await self.client.wait_for(
                        "message",
                        check=lambda m: m.author.id == ctx.author.id and m.channel.id == ctx.channel.id and len(m.content) >= 3,
                        timeout=180
                    )
                except asyncio.TimeoutError:
                    await ctx.send(timeout_embed(180, ctx.author))
                    cycle = False
                else:
                    if msg.content.lower() in ["quit", "cancel", "отмена"]:
                        reply2 = discord.Embed(
                            title="↩ | Отмена",
                            description="Привязка аккаунта отменена.",
                            color=discord.Color.blurple()
                        )
                        reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
                        await ctx.send(embed=reply2)
                        cycle = False
                    
                    else:
                        try:
                            player = brawl.get_player(msg.content)
                        except Exception:
                            pass
                        else:
                            if bdlist.contains_tag(player.tag):
                                reply2 = discord.Embed(
                                    title="❌ | Ошибка",
                                    description=f"Аккаунт **{player.name}** уже привязан к другому Discord-аккаунту.",
                                    color=discord.Color.dark_red()
                                )
                                reply2.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
                                await ctx.send(embed=reply2)
                            
                            else:
                                cycle = False
            
            # Waiting for a color change
            if player is not None:
                col = player.name_color
                req_col = choice([c for c in bscolors if c != col])
                if req_col[4:] == "ffffff":
                    emb_col = discord.Color.from_rgb(254, 254, 254)
                else:
                    emb_col = int(req_col[4:], 16)
                
                reply = discord.Embed(
                    title="🔗 | Привязка аккаунта Brawl Stars",
                    description=(
                        f"Вы указали аккаунт **{player.name}**. Чтобы подтвердить, что он принадлежит Вам, сделайте следующее.\n"
                        f"У Вас есть 3 минуты на то, чтобы сменить цвет своего ника на **{bscolors[req_col]}**\n\n"
                        "Для Вашего удобства, данное сообщение слева подкрашено нужным цветом.\n\n"
                        "Через 3 минуты я скажу результат, после чего Вы сможете вернуть прежний цвет ника в игре."
                    ),
                    color = emb_col
                )
                reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
                await ctx.send(embed=reply)
            
                await asyncio.sleep(180)    # Should be 300?

                player = brawl.get_player(player.tag)
                new_col = player.name_color
                if new_col != req_col:
                    reply = discord.Embed(
                        title="❌ | Верификация не пройдена",
                        description=(
                            f"На аккаунте **{player.name}** стоит не тот цвет, который был запрошен 3 минуты назад ({bscolors[req_col]}). "
                            "Ничего страшного, Вы можете попробовать снова."
                        ),
                        color=discord.Color.dark_red()
                    )
                    reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
                    await ctx.send(content=str(ctx.author.mention), embed=reply)
                
                else:
                    bdlist.link_together(ctx.author.id, player.tag)

                    reply = discord.Embed(
                        title="✅ | Верификация пройдена",
                        description=f"Теперь аккаунт Brawl Stars **{player.name}** привязан к Вашему аккаунту в Discord - **{ctx.author}**",
                        color=discord.Color.dark_green()
                    )
                    reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
                    await ctx.send(content=str(ctx.author.mention), embed=reply)


    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.command()
    async def unverify(self, ctx):
        bdlist = BrawlDiscordList()
        if not bdlist.contains_id(ctx.author.id):
            reply = discord.Embed(
                title="❌ | Ошибка",
                description="Ваша учётная запись Discord не привязана ни к одному аккаунту Brawl Stars.",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)
        
        else:
            reply = discord.Embed(
                title="❓ | Вы уверены",
                description=(
                    "Напишите `да`, чтобы отвязать свой аккаунт Brawl Stars\n"
                    "Напишите `нет`, чтобы отменить действие."
                )
            )
            reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
            botmsg = await ctx.send(embed=reply)

            yes = ["yes", "да"]
            no = ["no", "нет"]
            cycle = True
            msg = None
            while cycle:
                try:
                    msg = await self.client.wait_for(
                        "message",
                        check=lambda m: m.author.id == ctx.author.id and m.channel.id == ctx.channel.id and m.content.lower() in [*yes, *no],
                        timeout=60
                    )
                except asyncio.TimeoutError:
                    await ctx.send(timeout_embed(60, ctx.author))
                    cycle = False
                else:
                    cycle = False
            
            try:
                await botmsg.delete()
            except Exception:
                pass
            if msg is not None and msg.content.lower() in yes:
                bduser = BrawlDiscordUser(ctx.author.id)
                bduser.unlink()

                reply = discord.Embed(
                    title="✅ | Аккаунт отвязан",
                    description="Теперь к Вашему аккаунту Discord не привязано Brawl Stars-аккаунтов",
                    color=discord.Color.dark_green()
                )
                reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
                await ctx.send(content=str(ctx.author.mention), embed=reply)


    @commands.command(aliases=["brawl-profile", "bp"])
    async def brawl_profile(self, ctx, member: discord.Member=None):
        if member is None:
            member = ctx.author
            err_desc = "Ваша учётная запись Discord не привязана ни к одному аккаунту Brawl Stars."
        else:
            err_desc = f"Аккаунт {member} не привязан ни к одному аккаунту Brawl Stars."
        
        bduser = BrawlDiscordUser(member.id)
        if bduser.tag is None:
            reply = discord.Embed(
                title="❌ | Ошибка",
                description=err_desc,
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)
        
        else:
            async with ctx.channel.typing():
                player = brawl.get_player(bduser.tag)
                reply = discord.Embed(
                    title=f"{emj.home} | Профиль {anf(player.name)} `aka` {anf(member)}",
                    description=f"**Lvl:** {emj.xp} {player.exp_level} | **XP:** {player.exp_points}",
                    color=int("3476EF", 16)
                )
                reply.set_footer(text=" - Brawl Stars API")
                reply.add_field(name="**Клуб**", value=f"{emj.club} **{anf(player.club.name)}** ({player.club.tag})", inline=False)
                reply.add_field(name="Максимум трофеев", value=f"{emj.trophy} {player.highest_trophies}")
                reply.add_field(name="Макс. очков в силовой гонке", value=f"{emj.maxrace} {player.highest_power_play_points}")
                # reply.add_field(name="Макс. побед в испытании", value=f"{emj.maxevent} --")
                reply.add_field(name="Побед 3 на 3", value=f"{emj.trio} {player.x3vs3_victories}")
                reply.add_field(name="Одиночных побед", value=f"{emj.solo} {player.solo_victories}")
                reply.add_field(name="Парных побед", value=f"{emj.duo} {player.duo_victories}")
                reply.add_field(name="Уровень роборубки", value=f"{emj.robolevel} {player.best_robo_rumble_time}")
                # reply.add_field(name="Уровень боя с боссом", value=f"{emj.bosslevel} --")
                # reply.add_field(name="Уровень разгрома", value=f"{emj.destructlevel} --")

                await ctx.send(embed=reply)

    #----------------------------------------------+
    #                   Errors                     |
    #----------------------------------------------+


def setup(client):
    client.add_cog(brawlactions(client))
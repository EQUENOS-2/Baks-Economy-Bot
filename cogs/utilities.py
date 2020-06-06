import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio, os

import pymongo
from box.db_worker import cluster

#========== Variables ==========
db = cluster["guilds"]

mass_dm_errors = {}

#========== Functions ==========
from functions import has_permissions, detect

async def try_send_and_count(channel_or_user, message_id, content=None, embed=None):
    try:
        await channel_or_user.send(content=content, embed=embed)
    except Exception:
        global mass_dm_errors
        if message_id not in mass_dm_errors:
            mass_dm_errors[message_id] = 1
        else:
            mass_dm_errors[message_id] += 1

class utilities(commands.Cog):
    def __init__(self, client):
        self.client = client

    #========== Events ===========
    @commands.Cog.listener()
    async def on_ready(self):
        print(">> Utilities cog is loaded")

    #========= Commands ==========
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases=["dm-role", "mass-send", "role-dm", "dr"])
    async def dm_role(self, ctx, role_search, *, text):
        if not has_permissions(ctx.author, ["administrator"]):
            reply = discord.Embed(
                title="❌ Недостаточно прав",
                description=(
                    "**Необходимые права:**\n"
                    f"> Администратор"
                ),
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
                paper = discord.Embed(
                    title=f"📢 Письмо от **{ctx.guild.name}** для **@{role.name}**",
                    description=text,
                    color=discord.Color.from_rgb(92, 249, 131)
                )
                paper.set_thumbnail(url=str(ctx.guild.icon_url))

                total_targets = 0
                await ctx.send("🕑 Пожалуйста, подождите...")
                for member in ctx.guild.members:
                    if role in member.roles:
                        total_targets += 1
                        self.client.loop.create_task(try_send_and_count(member, ctx.message.id, embed=paper))
                
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

def setup(client):
    client.add_cog(utilities(client))
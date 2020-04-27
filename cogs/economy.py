import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio, os, datetime

import pymongo

from functions import detect, get_field, has_roles, try_int, has_permissions
from box.db_worker import cluster
db = cluster["guilds"]

class economy(commands.Cog):
    def __init__(self, client):
        self.client = client

    #========== Events ===========
    @commands.Cog.listener()
    async def on_ready(self):
        print(">> Economy cog is loaded")
    
    #========= Commands ===========
    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.command(aliases=["change-bal", "cb", "change", "add-money", "change-balance"])
    async def change_bal(self, ctx, amount, *, member_s=None):
        collection = db["money"]
        if member_s is None:
            member = ctx.author
        else:
            member = detect.member(ctx.guild, member_s)
        
        result = collection.find_one(
            {"_id": ctx.guild.id},
            projection={"master_role": True}
        )
        mr_id = get_field(result, "master_role")

        if not has_roles(ctx.author, [mr_id]):
            reply = discord.Embed(
                title="❌ Недостаточно прав",
                description=(
                    "**Необходимые права:**\n"
                    "> Администратор\n"
                    "или\n"
                    "> Мастер-роль"
                ),
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        
        elif member is None:
            reply = discord.Embed(
                title="💢 Упс",
                description=f"Вы указали {member_s}, подразумевая участника, но он не был найден",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        
        elif try_int(amount) is None:
            reply = discord.Embed(
                title="💢 Упс",
                description=f"Аргумент \"{amount}\" должен быть целым числом, как `5` или `-5`",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        
        else:
            amount = int(amount)
            amount_desc = f"{amount}"
            if amount_desc[0] != "-":
                amount_desc = f"+{amount_desc}"

            result = collection.find_one_and_update(
                {"_id": ctx.guild.id},
                {"$inc": {f"members.{member.id}": amount}},
                projection={"cur": True},
                upsert=True
            )
            cur = get_field(result, "cur")
            if cur is None:
                cur = "💰"
            reply = discord.Embed(
                title="♻ Выполнено",
                description=f"{amount_desc} {cur} участнику **{member}**",
                color=discord.Color.dark_green()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)

    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.command(aliases=["bal"])
    async def balance(self, ctx, *, member_s=None):
        if member_s is None:
            member = ctx.author
        else:
            member = detect.member(ctx.guild, member_s)
        
        if member is None:
            reply = discord.Embed(
                title="💢 Упс",
                description=f"Вы указали {member_s}, подразумевая участника, но он не был найден",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        
        else:
            collection = db["money"]
            result = collection.find_one(
                {"_id": ctx.guild.id, f"members.{member.id}": {"$exists": True}},
                projection={f"members.{member.id}": True, "cur": True}
            )
            amount = get_field(result, "members", f"{member.id}")
            if amount is None:
                amount = 0
            cur = get_field(result, "cur")
            if cur is None:
                cur = "💰"
            
            reply = discord.Embed(
                title=f"Баланс {member}",
                description=f"**{amount}** {cur}",
                color=member.color
            )
            reply.set_thumbnail(url=f"{member.avatar_url}")
            await ctx.send(embed=reply)

    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.command(aliases=["leaderboard", "leaders", "lb"])
    async def top(self, ctx, page="1"):
        interval = 10

        if not page.isdigit():
            reply = discord.Embed(
                title="💢 Упс",
                description=f"Номер страницы ({page}) должен быть целым числом",
                color=discord.Color.dark_green()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        
        else:
            page = int(page)
            collection = db["money"]
            result = collection.find_one(
                {"_id": ctx.guild.id},
                projection={"members": True, "cur": True}
            )
            cur = get_field(result, "cur")
            if cur is None:
                cur = "💰"
            member_list = get_field(result, "members")

            if member_list is None or member_list == {}:
                reply = discord.Embed(
                    title="📊 Топ участников",
                    description="Пуст",
                    color=ctx.guild.me.color
                )
                reply.set_thumbnail(url=f"{ctx.guild.icon_url}")
                await ctx.send(embed=reply)
            
            else:
                total_pairs = len(member_list)
                total_pages = (total_pairs - 1) // interval + 1
                if page > total_pages or page < 1:
                    reply = discord.Embed(
                        title="📖 Страница не найдена",
                        description=f"Всего страниц: {total_pages}"
                    )
                    reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                    await ctx.send(embed=reply)
                
                else:
                    member_list = [(int(key), member_list[key]) for key in member_list]
                    member_list.sort(reverse=True, key=lambda pair: pair[1])
                    lower_bound = (page - 1) * interval
                    upper_bound = min(page * interval, total_pairs)

                    desc = ""
                    for i in range(lower_bound, upper_bound):
                        pair = member_list[i]
                        member = ctx.guild.get_member(pair[0])
                        desc += f"**{i+1})** {member} • **{pair[1]}** {cur}\n"
                    
                    reply = discord.Embed(
                        title="📊 Топ участников",
                        description=desc,
                        color=ctx.guild.me.color
                    )
                    reply.set_thumbnail(url=f"{ctx.guild.icon_url}")
                    reply.set_footer(text=f"Стр. {page}/{total_pages}")
                    await ctx.send(embed=reply)

    @commands.command()
    async def pay(self, ctx, amount, *, member_s):
        if not amount.isdigit():
            reply = discord.Embed(
                title="💢 Упс",
                description=f"Аргумент \"{amount}\" должен быть целым числом",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        
        else:
            amount = int(amount)
            member = detect.member(ctx.guild, member_s)
            if member is None:
                reply = discord.Embed(
                    title="💢 Упс",
                    description=f"Вы указали {member_s}, подразумевая участника, но он не был найден",
                    color=discord.Color.dark_red()
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)
            
            else:
                collection = db["money"]
                result = collection.find_one(
                    {"_id": ctx.guild.id, f"members.{ctx.author.id}": {"$exists": True}},
                    projection={"cur": True, f"members.{ctx.author.id}": True}
                )
                cur = get_field(result, "cur")
                if cur is None:
                    cur = "💰"
                bal = get_field(result, "members", f"{ctx.author.id}")
                if bal is None:
                    bal = 0
                
                if amount > bal:
                    reply = discord.Embed(
                        title="💢Ошибка",
                        description="На Вашем балансе недостаточно денег.",
                        color=discord.Color.dark_red()
                    )
                    reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                    await ctx.send(embed=reply)
                
                else:
                    collection.find_one_and_update(
                        {"_id": ctx.guild.id},
                        {"$inc": {
                            f"members.{member.id}": amount,
                            f"members.{ctx.author.id}": -amount
                        }},
                        upsert=True
                    )
                    reply = discord.Embed(
                        title="♻ Выполнено",
                        description=f"На баланс {member} переведено {amount} {cur}",
                        color=discord.Color.dark_green()
                    )
                    reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                    await ctx.send(embed=reply)

    #======== Errors =========
    @change_bal.error
    async def change_bal_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    f"**Описание:** изменяет баланс участника\n"
                    f'**Использование:** `{p}{cmd} Кол-во @Участник`\n'
                    f"**Примеры:** `{p}{cmd} -6 @User#1234`\n"
                    f">> `{p}{cmd} +4`"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
    
    @pay.error
    async def pay_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    f"**Описание:** переводит деньги на счёт участника\n"
                    f'**Использование:** `{p}{cmd} Кол-во @Участник`\n'
                    f"**Пример:** `{p}{cmd} 60 @User#1234`\n"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

def setup(client):
    client.add_cog(economy(client))
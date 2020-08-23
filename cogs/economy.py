import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio, os, datetime

#----------------------------------------------+
#                 Constants                    |
#----------------------------------------------+
from functions import timeout_embed, CustomColor
from failures import CooldownResetSignal

colors = CustomColor()
item_limit = 50
case_limit = 50
mkkey_tout = 60
name_limit = 52
edit_item_params = {
    "name": {
        "desc": "изменяет название шмота",
        "usage": "[Старое название] Новое название",
        "example": "[Футболка] Рубашка"
    },
    "price": {
        "desc": "изменяет цену шмотки",
        "usage": "[Название] Число",
        "example": "[Футболка] 100"
    },
    "role": {
        "desc": "привязывает роль к шмотке (при покупке будет даваться роль)",
        "usage": "[Название] Роль",
        "example": "[Футблока] @Покупатель"
    }
}

#----------------------------------------------+
#                 Functions                    |
#----------------------------------------------+
from functions import detect, get_field, try_int, is_moderator, find_alias, antiformat as anf
from functions import CustomerList, Customer, ItemStorage, Item, Case


def isfloat(string: str):
    try:
        float(string)
    except Exception:
        return False
    else:
        return True


def unpack_args(string):
    if isinstance(string, str):
        if string[0] == "[":
            pair = string[1:].rsplit("]", maxsplit=1)
            if len(pair) < 2:
                pair = string.split(maxsplit=1)
        else:
            pair = string.split(maxsplit=1)
        if len(pair) < 2:
            return pair[0].strip(), None
        else:
            return pair[0].strip(), pair[1].strip()
    else:
        return None, None


def unpack_case_args(string):
    if string is None:
        return (None, None)
    else:
        pair = string.split(maxsplit=1)
        if len(pair) < 2:
            return (None, pair[0])
        else:
            pair[0].rstrip("%")
            if not isfloat(pair[0]):
                return (None, pair[1])
            elif float(pair[0]) <= 0:
                return (None, pair[1])
            else:
                return (float(pair[0]), pair[1])


def dupe_dump(array: list):
    out = {}
    for elem in array:
        if elem not in out:
            out[elem] = 1
        else:
            out[elem] += 1
    return out


async def better_add_role(member, role):
    if isinstance(role, int):
        role = member.guild.get_role(role)
    if role is not None and role not in member.roles:
        try:
            await member.add_roles(role)
        except Exception:
            pass


class economy(commands.Cog):
    def __init__(self, client):
        self.client = client

    #----------------------------------------------+
    #                Cog methods                   |
    #----------------------------------------------+
    async def ask_to_choose(self, _choice: list, channel, user):
        """Returns chosen index or None"""
        tout = 60
        desc = ""
        for i, row in enumerate(_choice):
            desc += f"`{i + 1}.` {row}\n"
        emb = discord.Embed(
            title="🔎 | Результаты поиска",
            description=f"Найдено несколько результатов, пожалуйста, напишите **номер** подходящего:\n\n{desc}"
        )
        emb.set_footer(text=f"{user}", icon_url=f"{user.avatar_url}")
        botmsg = await channel.send(embed=emb)

        try:
            msg = await self.client.wait_for(
                "message",
                check=lambda m: m.author.id == user.id and m.channel.id == channel.id and m.content.isdigit() and 0 < int(m.content) <= len(_choice),
                timeout=tout
            )
        except asyncio.TimeoutError:
            await channel.send(embed=timeout_embed(tout, user))
        else:
            try:
                await botmsg.delete()
            except Exception:
                pass
            return int(msg.content) - 1

    #----------------------------------------------+
    #                   Events                     |
    #----------------------------------------------+
    @commands.Cog.listener()
    async def on_ready(self):
        print(">> Economy cog is loaded")
    
    #----------------------------------------------+
    #                  Commands                    |
    #----------------------------------------------+
    # Item related commands
    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.check_any(
        is_moderator(),
        commands.has_permissions(administrator=True) )
    @commands.command(
        aliases=["create-item", "ci", "createitem"],
        description="создаёт новую шмотку на сервере",
        usage="Цена Название",
        brief="100 Фтуболка" )
    async def create_item(self, ctx, price: int, *, name):
        server = ItemStorage(ctx.guild.id, {"items": True, "cy": True})
        if len(server.items) >= item_limit:
            reply = discord.Embed(
                title="❌ | Переполнение",
                description=f"Создано слишком много шмоток - {item_limit}",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        elif price < 0:
            reply = discord.Embed(
                title="❌ | Ошибка",
                description=f"Цена шмотки не может быть отрицательной",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        else:
            server.create_item(ctx.message.id, name[:name_limit], price)
            desc = (
                f"Вы создали новую шмотку - **{name}**.\n"
                f"**Цена:** {price} {server.cy}\n"
                f"**Редактировать:** `{ctx.prefix}edit-item`"
            )
            if len(name) > name_limit:
                desc += f"\n\n*Название превышало {name_limit} символов в длину и было обрезано*"
            reply = discord.Embed(
                title="📦 | Новая вещь",
                description=desc,
                color=discord.Color.blue()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)

    
    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.check_any(
        is_moderator(),
        commands.has_permissions(administrator=True) )
    @commands.command(
        aliases=["edit-item", "ei", "edititem", "edit"],
        description="изменяет некоторые характеристики шмотки. Параметры:\n`name`, `price`, `role`",
        usage="параметр [Название] Новое значние",
        brief=(
            "name [Старое название] Новое название\n"
            "price [Название] Новая цена\n"
            "role [Название] Роль") )
    async def edit_item(self, ctx, param, *, string=None):
        search, value = unpack_args(string)
        p = ctx.prefix; cmd = str(ctx.invoked_with)
        params = {
            "name": ["название"],
            "price": ["цена"],
            "role": ["роль"]
        }
        parameter = find_alias(params, param)
        if parameter is None:
            desc = ""
            for par in params:
                desc += f"> `{p}{cmd} {par}`\n"
            reply = discord.Embed(
                title="❌ | Неверный параметр",
                description=f"Параметра '{param}' не существует, попробуйте эти:\n{desc}",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)

        elif value is None:
            _help_ = edit_item_params[parameter]
            reply = discord.Embed(
                title=f"❓ | О параметре `{p}{cmd} {parameter}`",
                description=(
                    f"**Описание:** {_help_['desc']}\n"
                    f"**Использование:** `{p}{cmd} {parameter} {_help_['usage']}`\n"
                    f"**Пример:** `{p}{cmd} {parameter} {_help_['example']}`"
                )
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)

        else:
            server = ItemStorage(ctx.guild.id, projection={"items"})
            items = server.search_items(search)
            item = None
            if len(items) == 0:
                reply = discord.Embed(
                    title="❌ | Вещь не найдена",
                    description=f"По поиску '{search}' не было найдено шмоток.",
                    color=discord.Color.dark_red()
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)

            elif len(items) < 2:
                item = items[0]
            else:
                ind = await self.ask_to_choose([it.name for it in items], ctx.channel, ctx.author)
                if ind is not None:
                    item = items[ind]
            
            if item is not None:
                updated = True
                if parameter == "name":
                    item.set_name(value[:name_limit])
                    item.name = value[:name_limit]
                elif parameter == "price":
                    if not value.isdigit():
                        updated = False
                        reply = discord.Embed(
                            title="❌ | Неверный аргумент",
                            description=f"Вместо '{value}' введите целое число",
                            color=discord.Color.dark_red()
                        )
                        reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                        await ctx.send(embed=reply)
                    else:
                        item.set_price(int(value))
                elif parameter == "role":
                    role = await commands.RoleConverter().convert(ctx, value)
                    item.set_role(role.id)
                
                if updated:
                    reply = discord.Embed(
                        title="🔁 | Вещь обновлена",
                        description=f"Посмотреть подробнее: `{p}view-item {item.name}`",
                        color=discord.Color.blue()
                    )
                    reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                    await ctx.send(embed=reply)


    @commands.cooldown(1, 2, commands.BucketType.member)
    @commands.check_any(
        is_moderator(),
        commands.has_permissions(administrator=True) )
    @commands.command(
        aliases=["delete-item", "deleteitem", "di"],
        description="удаляет шмотку",
        usage="Название шмотки",
        brief="Футболка" )
    async def delete_item(self, ctx, *, search):
        # Searching item
        server = ItemStorage(ctx.guild.id, {"items": True})
        items = server.search_items(search)
        item = None
        if len(items) == 0:
            reply = discord.Embed(
                title="❌ | Вещь не найдена",
                description=f"По поиску '{search}' не было найдено шмоток.",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        elif len(items) < 2:
            item = items[0]
        else:
            ind = await self.ask_to_choose([it.name for it in items], ctx.channel, ctx.author)
            if ind is not None:
                item = items[ind]
        del items
        # Visualising item
        if item is not None:
            item.delete()
            reply = discord.Embed(
                title="📦 | Удалена вещь",
                description=f"Шмотка {item.name} была удалена с сервера.",
                color=discord.Color.dark_blue()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)


    @commands.cooldown(1, 2, commands.BucketType.member)
    @commands.check_any(
        is_moderator(),
        commands.has_permissions(administrator=True) )
    @commands.command(
        aliases=["give-item", "giveitem", "gi"],
        description="выдаёт шмотку",
        usage="[Название шмотки] @Игрок (себя можно не тегать)",
        brief="[Футболка] @Player#0000" )
    async def give_item(self, ctx, *, string):
        search, member_s = unpack_args(string)
        if member_s is None:
            member = ctx.author
        else:
            member = await commands.MemberConverter().convert(ctx, member_s)
        # Searching item
        server = ItemStorage(ctx.guild.id, {"items": True})
        items = server.search_items(search)
        item = None
        if len(items) == 0:
            reply = discord.Embed(
                title="❌ | Вещь не найдена",
                description=f"По поиску '{search}' не было найдено шмоток.",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        elif len(items) < 2:
            item = items[0]
        else:
            ind = await self.ask_to_choose([it.name for it in items], ctx.channel, ctx.author)
            if ind is not None:
                item = items[ind]
        del items
        # Giving item
        if item is not None:
            customer = Customer(ctx.guild.id, member.id)
            if len(customer.raw_items) >= item_limit:
                reply = discord.Embed(
                    title="❌ | Недостаточно места",
                    description=f"Инвентарь **{member}** переполнен - в нём **{item_limit}** шмоток.",
                    color=discord.Color.dark_red()
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)
            else:
                customer.give_item(item)
                reply = discord.Embed(
                    title="📦 | Выдана шмотка",
                    description=f"Игрок **{member}** получил **{item.name}** себе в инвентарь.",
                    color=discord.Color.dark_blue()
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)


    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.check_any(
        is_moderator(),
        commands.has_permissions(administrator=True) )
    @commands.command(
        aliases=["add-key", "ak", "addkey"],
        description="добавляет к шмотке ключ от кейса",
        usage="[Шмотка] Кейс",
        brief="[Футболка] Кейс с одеждой" )
    async def add_key(self, ctx, *, string):
        # Searching item
        item_search, case_search = unpack_args(string)
        if case_search is None:
            raise commands.MissingRequiredArgument("case_name")

        server = ItemStorage(ctx.guild.id, {"items": True, "cy": True, "cases": True})
        items = server.search_items(item_search)
        item = None
        if len(items) == 0:
            reply = discord.Embed(
                title="❌ | Вещь не найдена",
                description=f"По поиску '{item_search}' не было найдено шмоток.",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        elif len(items) < 2:
            item = items[0]
        else:
            ind = await self.ask_to_choose([it.name for it in items], ctx.channel, ctx.author)
            if ind is not None:
                item = items[ind]
        del items
        # Searching case
        if item is not None:
            cases = server.search_cases(case_search)
            case = None
            if len(cases) == 0:
                reply = discord.Embed(
                    title="❌ | Кейс не найден",
                    description=f"По поиску '{case_search}' не было найдено кейсов.",
                    color=discord.Color.dark_red()
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)
            elif len(cases) < 2:
                case = cases[0]
            else:
                ind = await self.ask_to_choose([c.name for c in cases], ctx.channel, ctx.author)
                if ind is not None:
                    case = cases[ind]
            
            if case is not None:
                item.bind_case(case.id)
                reply = discord.Embed(
                    title="🔑 | Добавлен ключ",
                    description=f"Теперь {item.name} открывает кейс {case.name}",
                    color=colors.cardboard
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)
    
    
    @commands.cooldown(1, case_limit * mkkey_tout, commands.BucketType.member)
    @commands.check_any(
        is_moderator(),
        commands.has_permissions(administrator=True) )
    @commands.command(
        aliases=["remove-key", "remk", "removekey"],
        description="добавляет к шмотке ключ от кейса",
        usage="[Шмотка] Кейс",
        brief="[Футболка] Кейс с одеждой" )
    async def remove_key(self, ctx, *, string):
        # Searching item
        item_search, case_search = unpack_args(string)
        if case_search is None:
            raise commands.MissingRequiredArgument("case_name")

        server = ItemStorage(ctx.guild.id, {"items": True, "cy": True, "cases": True})
        items = server.search_items(item_search)
        item = None
        if len(items) == 0:
            reply = discord.Embed(
                title="❌ | Вещь не найдена",
                description=f"По поиску '{item_search}' не было найдено шмоток.",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        elif len(items) < 2:
            item = items[0]
        else:
            ind = await self.ask_to_choose([it.name for it in items], ctx.channel, ctx.author)
            if ind is not None:
                item = items[ind]
        del items
        # Searching case
        if item is not None:
            cases = server.search_cases(case_search)
            case = None
            if len(cases) == 0:
                reply = discord.Embed(
                    title="❌ | Кейс не найден",
                    description=f"По поиску '{case_search}' не было найдено кейсов.",
                    color=discord.Color.dark_red()
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)
            elif len(cases) < 2:
                case = cases[0]
            else:
                ind = await self.ask_to_choose([c.name for c in cases], ctx.channel, ctx.author)
                if ind is not None:
                    case = cases[ind]
            
            if case is not None:
                if case.id not in item.key_for:
                    reply = discord.Embed(
                        title="❌ | Такой ключ не найден",
                        description=f"{item.name} не является ключом для {case.name}.",
                        color=discord.Color.dark_red()
                    )
                    reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                    await ctx.send(embed=reply)
                else:
                    item.unbind_case(case.id)
                    reply = discord.Embed(
                        title="🔑 | Убран ключ",
                        description=f"Теперь {item.name} не открывает кейс {case.name}",
                        color=colors.cardboard
                    )
                    reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                    await ctx.send(embed=reply)
        
        raise CooldownResetSignal()

    
    @commands.cooldown(1, 2, commands.BucketType.member)
    @commands.command(
        aliases=["view-items", "all-items", "item-list"])
    async def items(self, ctx, page: int=1):
        interval = 10
        server = ItemStorage(ctx.guild.id, {"items": True, "cy": True})
        total_items = len(server.items)
        total_pages = abs(total_items - 1) // interval + 1
        if page > total_pages or page < 1:
            reply = discord.Embed(
                title="❌ | Страница не найдена",
                description=f"Всего страниц: {total_pages}",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)

        else:
            if total_items == 0:
                desc = "Отсутствуют"
            else:
                cy = server.cy
                items = sorted(server.items, key=lambda item: item.price)
                del server
                lb = (page - 1) * interval
                ub = min(page * interval, total_items)

                desc = ""
                for i in range(lb, ub):
                    item = items[i]
                    desc += f"`{i + 1}.` **{item.name}** | {item.price} {cy}\n"
            reply = discord.Embed(
                title=f"📦 | Шмотки сервера",
                description=desc,
                color=discord.Color.blue()
            )
            reply.set_footer(text=f"Стр. {page} / {total_pages} | {ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)


    @commands.cooldown(1, 2, commands.BucketType.member)
    @commands.command(
        aliases=["view-item", "viewitem", "vi", "item"],
        description="показывает информацию о шмотке",
        usage="Название шмотки",
        brief="Футболка" )
    async def view_item(self, ctx, *, search):
        # Searching item
        server = ItemStorage(ctx.guild.id, {"items": True, "cy": True, "cases": True})
        items = server.search_items(search)
        item = None
        if len(items) == 0:
            reply = discord.Embed(
                title="❌ | Вещь не найдена",
                description=f"По поиску '{search}' не было найдено шмоток.",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        elif len(items) < 2:
            item = items[0]
        else:
            ind = await self.ask_to_choose([it.name for it in items], ctx.channel, ctx.author)
            if ind is not None:
                item = items[ind]
        del items
        # Visualising item
        if item is not None:
            reply = discord.Embed(
                title=f"📦 | {item.name}",
                color=discord.Color.blue()
            )
            reply.add_field(name="Цена", value=f"> {item.price} {server.cy}", inline=False)
            if item.role is not None:
                reply.add_field(name="Роль", value=f"> <@&{item.role}>", inline=False)
            if item.key_for != []:
                desc = ""
                for case in server.cases:
                    if case.id in item.key_for:
                        desc += f"> {case.name}\n"
                reply.add_field(name="Ключи", value=desc, inline=False)
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)


    @commands.cooldown(1, 2, commands.BucketType.member)
    @commands.command(
        aliases=["sell-item", "sellitem", "sell"],
        description="продаёт шмотку за пол цены",
        usage="Название шмотки",
        brief="Футболка" )
    async def sell_item(self, ctx, *, search):
        customer = Customer(ctx.guild.id, ctx.author.id)
        items = customer.search_item(search)
        item = None
        if len(items) == 0:
            reply = discord.Embed(
                title="❌ | Вещь не найдена",
                description=f"По запросу '{search}' в Вашем инвентаре не было найдено шмоток.",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        elif len(items) < 2:
            item = items[0]
        else:
            ind = await self.ask_to_choose([it.name for it in items], ctx.channel, ctx.author)
            if ind is not None:
                item = items[ind]
        del items
        # Giving item
        if item is not None:
            customer.sell_item(item)
            reply = discord.Embed(
                title="📦 | Продана шмотка",
                description=f"Вы продали **{item.name}** и стали богаче на **{item.price}**",
                color=discord.Color.dark_blue()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)


    @commands.cooldown(1, 2, commands.BucketType.member)
    @commands.command(
        aliases=["use-item", "useitem", "use"],
        description="Использует шмотку. При этом начисляются прикреплённые к шмотке ключи и выдаётся роль шмотки (при наличии)",
        usage="Название шмотки",
        brief="Футболка" )
    async def use_item(self, ctx, *, search):
        customer = Customer(ctx.guild.id, ctx.author.id)
        items = customer.search_item(search)
        item = None
        if len(items) == 0:
            reply = discord.Embed(
                title="❌ | Вещь не найдена",
                description=f"По запросу '{search}' в Вашем инвентаре не было найдено шмоток.",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        elif len(items) < 2:
            item = items[0]
        else:
            ind = await self.ask_to_choose([it.name for it in items], ctx.channel, ctx.author)
            if ind is not None:
                item = items[ind]
        del items
        # Giving item
        if item is not None:
            if item.key_for == [] and item.role is None:
                reply = discord.Embed(
                    title="❌ | Вещь не имеет свойств",
                    description=f"**{item.name}** не имеет прикреплённых ключей или роли.",
                    color=discord.Color.dark_red()
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)
            else:
                customer.use_item(item)
                await better_add_role(ctx.author, item.role)

                desc = ""
                if item.key_for != []:
                    desc += f"> **Ключей:** {len(item.key_for)} 🔑\n"
                if item.role is not None:
                    desc += f"> **Роль <@&{item.role}>**\n"
                reply = discord.Embed(
                    title="📦 | Использована шмотка",
                    description=(
                        f"Вы использовали **{item.name}** и получили\n"
                        f"{desc}\n"
                        f"*Ваш инвентарь: `{ctx.prefix}inv`*"
                    ),
                    color=discord.Color.dark_blue()
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)

    # Case related commands
    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.check_any(
        is_moderator(),
        commands.has_permissions(administrator=True) )
    @commands.command(
        aliases=["create-case", "cc", "createcase"],
        description="создаёт новый кейс на сервере",
        usage="Название",
        brief="Фтуболка" )
    async def create_case(self, ctx, *, name):
        server = ItemStorage(ctx.guild.id, {"cases": True})
        if len(server.cases) >= case_limit:
            reply = discord.Embed(
                title="❌ | Переполнение",
                description=f"Создано слишком много кейсов - {case_limit}",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        else:
            server.create_case(ctx.message.id, name[:name_limit])
            desc = f"Вы создали новый кейс - {name}.\n**Добавить лут:** `{ctx.prefix}add-loot`\n"
            if len(name) > name_limit:
                desc += f"*Название превышало {name_limit} символов в длину и было обрезано*"
            reply = discord.Embed(
                title="📦 | Новый кейс",
                description=desc,
                color=colors.cardboard
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)


    @commands.cooldown(1, 2, commands.BucketType.member)
    @commands.check_any(
        is_moderator(),
        commands.has_permissions(administrator=True) )
    @commands.command(
        aliases=["delete-case", "deletecase", "delc"],
        description="удаляет кейс",
        usage="Название кейса",
        brief="Кейс Одежды" )
    async def delete_case(self, ctx, *, search):
        # Searching item
        server = ItemStorage(ctx.guild.id, {"cases": True})
        cases = server.search_cases(search)
        case = None
        if len(cases) == 0:
            reply = discord.Embed(
                title="❌ | Кейс не найден",
                description=f"По поиску '{search}' не было найдено кейсов.",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        elif len(cases) < 2:
            case = cases[0]
        else:
            ind = await self.ask_to_choose([c.name for c in cases], ctx.channel, ctx.author)
            if ind is not None:
                case = cases[ind]
        del cases
        # Visualising item
        if case is not None:
            case.delete()
            reply = discord.Embed(
                title="📦 | Удален кейс",
                description=f"Кейс {case.name} был удалён с сервера.",
                color=colors.cardboard
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)


    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.check_any(
        is_moderator(),
        commands.has_permissions(administrator=True) )
    @commands.command(
        aliases=["add-loot", "addloot", "addl"],
        description="Добавляет лут в кейс. Далее `Вес` будет влиять на шанс выпадения. Чем больше вес - тем выше шанс.",
        usage="[Название кейса] Вес Название_шмотки",
        brief="[Кейс Одежды] 50 Футболка\n[Кейс Одежды] 50 Рубашка" )
    async def add_loot(self, ctx, *, string):
        # Unpacking arguments
        case_search, caseargs = unpack_args(string)
        weight, item_search = unpack_case_args(caseargs)
        if None in [weight, item_search]:
            reply = discord.Embed(
                title="❌ | Недостаточно аргументов",
                description=(
                    f"В качестве кейса Вы указали `{case_search}`. После него нужно указать `Вес` и `Шмотку`, прчём `вес` должен быть числом больше нуля.\n"
                    f"Пример: `{ctx.prefix}add-loot [Некий кейс] 10 Некая шмотка`"
                ),
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        
        else:
            # Searching case
            server = ItemStorage(ctx.guild.id, {"items": True, "cases": True})
            _cases = server.search_cases(case_search)
            case = None
            if len(_cases) == 0:
                reply = discord.Embed(
                    title="❌ | Кейс не найден",
                    description=f"По поиску '{case_search}' не было найдено кейсов.",
                    color=discord.Color.dark_red()
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)
            elif len(_cases) < 2:
                case = _cases[0]
            else:
                ind = await self.ask_to_choose([c.name for c in _cases], ctx.channel, ctx.author)
                if ind is not None:
                    case = _cases[ind]
            del _cases
            if case is not None:
                # Searching item
                items = server.search_items(item_search)
                item = None
                if len(items) == 0:
                    reply = discord.Embed(
                        title="❌ | Вещь не найдена",
                        description=f"По поиску '{item_search}' не было найдено шмоток.",
                        color=discord.Color.dark_red()
                    )
                    reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                    await ctx.send(embed=reply)
                elif len(items) < 2:
                    item = items[0]
                else:
                    ind = await self.ask_to_choose([it.name for it in items], ctx.channel, ctx.author)
                    if ind is not None:
                        item = items[ind]
                del items
                # Adding item to the case
                if item is not None:
                    case.add_item(item.id, weight)
                    reply = discord.Embed(
                        title="🔑 | Добавлен лут",
                        description=(
                            f"Теперь **{item.name}** выпадает из кейса **{case.name}** с весом {weight}.\n"
                            f"Просмотреть кейс: `{ctx.prefix}case {case.name}`"
                        ),
                        color=colors.cardboard
                    )
                    reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                    await ctx.send(embed=reply)


    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.check_any(
        is_moderator(),
        commands.has_permissions(administrator=True) )
    @commands.command(
        aliases=["rename-case", "renamecase", "renc"],
        description="изменяет название кейса.",
        usage="[Старое название] Новое название",
        brief="[Кейс Одежды] Кейс с одеждой" )
    async def rename_case(self, ctx, *, string):
        # Unpacking arguments
        case_search, new_name = unpack_args(string)
        if new_name is None:
            reply = discord.Embed(
                title="❌ | Недостаточно аргументов",
                description=(
                    f"В качестве кейса Вы указали `{case_search}`. После него нужно указать новое название.\n"
                    f"Пример: `{ctx.prefix}rename-case [Старое название] Новое название`"
                ),
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        
        else:
            new_name = new_name[:name_limit]
            # Searching case
            server = ItemStorage(ctx.guild.id, {"cases": True})
            _cases = server.search_cases(case_search)
            case = None
            if len(_cases) == 0:
                reply = discord.Embed(
                    title="❌ | Кейс не найден",
                    description=f"По поиску '{case_search}' не было найдено кейсов.",
                    color=discord.Color.dark_red()
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)
            elif len(_cases) < 2:
                case = _cases[0]
            else:
                ind = await self.ask_to_choose([c.name for c in _cases], ctx.channel, ctx.author)
                if ind is not None:
                    case = _cases[ind]
            del _cases
            if case is not None:
                # Renaming case
                case.set_name(new_name)
                reply = discord.Embed(
                    title="📦 | Кейс переименован",
                    description=(
                        f"Теперь **{case.name}** называется **{new_name}**.\n"
                        f"Просмотреть кейс: `{ctx.prefix}case {new_name}`"
                    ),
                    color=colors.cardboard
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)


    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.check_any(
        is_moderator(),
        commands.has_permissions(administrator=True) )
    @commands.command(
        aliases=["remove-loot", "removeloot", "reml"],
        description="Убирает шмотку из кейса.",
        usage="[Название кейса] Название_шмотки",
        brief="[Кейс Одежды] Футболка" )
    async def remove_loot(self, ctx, *, string):
        # Unpacking arguments
        case_search, item_search = unpack_args(string)
        if item_search is None:
            reply = discord.Embed(
                title="❌ | Недостаточно аргументов",
                description=(
                    f"В качестве кейса Вы указали `{case_search}`. После него нужно указать `Шмотку`.\n"
                    f"Пример: `{ctx.prefix}remove-loot [Некий кейс] Некая шмотка`"
                ),
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        
        else:
            # Searching case
            server = ItemStorage(ctx.guild.id, {"items": True, "cases": True})
            _cases = server.search_cases(case_search)
            case = None
            if len(_cases) == 0:
                reply = discord.Embed(
                    title="❌ | Кейс не найден",
                    description=f"По поиску '{case_search}' не было найдено кейсов.",
                    color=discord.Color.dark_red()
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)
            elif len(_cases) < 2:
                case = _cases[0]
            else:
                ind = await self.ask_to_choose([c.name for c in _cases], ctx.channel, ctx.author)
                if ind is not None:
                    case = _cases[ind]
            del _cases
            if case is not None:
                # Searching item
                items = case.search_item(item_search)
                item = None
                if len(items) == 0:
                    reply = discord.Embed(
                        title="❌ | Вещь не найдена",
                        description=f"По запросу '{item_search}' в кейсе **{case.name}** не было найдено шмоток.",
                        color=discord.Color.dark_red()
                    )
                    reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                    await ctx.send(embed=reply)
                elif len(items) < 2:
                    item = items[0]
                else:
                    ind = await self.ask_to_choose([it.name for it in items], ctx.channel, ctx.author)
                    if ind is not None:
                        item = items[ind]
                del items
                # Removing item from the case
                if item is not None:
                    case.remove_item(item.id)
                    reply = discord.Embed(
                        title="🔑 | Убран лут",
                        description=(
                            f"Теперь **{item.name}** больше не выпадает из кейса **{case.name}**.\n"
                            f"Просмотреть кейс: `{ctx.prefix}case {case.name}`"
                        ),
                        color=colors.cardboard
                    )
                    reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                    await ctx.send(embed=reply)


    @commands.cooldown(1, 2, commands.BucketType.member)
    @commands.command(
        aliases=["view-cases", "all-cases", "case-list"])
    async def cases(self, ctx):
        # Searching item
        server = ItemStorage(ctx.guild.id, {"cases": True})
        desc = ""
        for case in server.cases:
            desc += f"• **{case.name}**\n"
        if desc == "":
            desc = "Отсутствуют"
        reply = discord.Embed(
            title=f"📦 | Кейсы сервера",
            description=desc,
            color=colors.cardboard
        )
        reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
        await ctx.send(embed=reply)


    @commands.cooldown(1, 2, commands.BucketType.member)
    @commands.command(
        aliases=["view-case", "viewcase", "vc", "case"],
        description="показывает информацию о кейсе",
        usage="Название кейса",
        brief="Кейс Одежды" )
    async def view_case(self, ctx, *, search):
        # Searching item
        server = ItemStorage(ctx.guild.id, {"items": True, "cy": True, "cases": True})
        cases = server.search_cases(search)
        case = None
        if len(cases) == 0:
            reply = discord.Embed(
                title="❌ | Кейс не найден",
                description=f"По поиску '{search}' не было найдено кейсов.",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        elif len(cases) < 2:
            case = cases[0]
        else:
            ind = await self.ask_to_choose([c.name for c in cases], ctx.channel, ctx.author)
            if ind is not None:
                case = cases[ind]
        del cases
        if case is not None:
            # Visualising item
            percs = case.percentage
            desc = ""
            for i, pair in enumerate(case.loot):
                desc += f"• {pair[0].name} ~ `{percs[i]} %`\n"
            if desc == "":
                desc = "Нет лута"
            if case is not None:
                reply = discord.Embed(
                    title=f"📦 | {case.name}",
                    color=colors.cardboard
                )
                reply.add_field(name="Содержимое", value=desc, inline=False)
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)


    @commands.cooldown(1, 2, commands.BucketType.member)
    @commands.command(
        aliases=["open-case", "opencase", "oc", "open"],
        description="вскрывает кейс, при условии, что у Вас есть ключ",
        usage="Название кейса",
        brief="Кейс Одежды" )
    async def open_case(self, ctx, *, search):
        # Searching item
        server = ItemStorage(ctx.guild.id, {"items": True, "cy": True, "cases": True})

        cases = server.search_cases(search)
        case = None
        if len(cases) == 0:
            reply = discord.Embed(
                title="❌ | Кейс не найден",
                description=f"По поиску '{search}' не было найдено кейсов.",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        elif len(cases) < 2:
            case = cases[0]
        else:
            ind = await self.ask_to_choose([c.name for c in cases], ctx.channel, ctx.author)
            if ind is not None:
                case = cases[ind]
        del cases
        if case is not None:
            # Looking at player's inventory
            customer = Customer(ctx.guild.id, ctx.author.id)
            if case.id not in customer.keys:
                reply = discord.Embed(
                    title="❌ | Нет ключа",
                    description=f"В Вашем инвентаре нет ключа от кейса **{case.name}**.",
                    color=discord.Color.dark_red()
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)
            elif len(case.loot) == 0:
                reply = discord.Embed(
                    title="❌ | Кейс пуст",
                    description=f"Кейс **{case.name}** пока что пуст, его невозможно открыть.",
                    color=discord.Color.dark_red()
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)
            elif len(customer.raw_items) >= item_limit:
                reply = discord.Embed(
                    title="❌ | Недостаточно места",
                    description=f"Ваш инвентарь переполнен - в нём {item_limit} шмоток. Продайте лишнее и попробуйте снова.",
                    color=discord.Color.dark_red()
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)
            else:
                item = customer.open_case(case)
                reply = discord.Embed(
                    title="📦 | Вскрыт кейс",
                    description=f"Шмотка: **{item.name}** • {item.price} {server.cy}",
                    color=colors.cardboard
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)
    
    # Shop related commandы
    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.check_any(
        is_moderator(),
        commands.has_permissions(administrator=True) )
    @commands.command(
        aliases=["shop-add"],
        description="добавляет шмотку в магазин сервера.",
        usage="Название шмотки",
        brief="Футболка" )
    async def shop_add(self, ctx, *, search):
        # Searching item
        server = ItemStorage(ctx.guild.id, {"items": True, "shop": True})
        items = server.search_items(search)
        item = None
        if len(items) == 0:
            reply = discord.Embed(
                title="❌ | Вещь не найдена",
                description=f"По поиску '{search}' не было найдено шмоток.",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        elif len(items) < 2:
            item = items[0]
        else:
            ind = await self.ask_to_choose([it.name for it in items], ctx.channel, ctx.author)
            if ind is not None:
                item = items[ind]
        del items
        # Visualising item
        if item is not None:
            if item.id in server.raw_shop:
                reply = discord.Embed(
                    title="❌ | Вещь уже есть в магазине",
                    description=f"Шмотка **{item.name}** уже продаётся в магазине.",
                    color=discord.Color.dark_red()
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)

            else:
                server.add_to_shop(item.id)
                reply = discord.Embed(
                    title=f"🛒 | Вещь добавлена в магазин",
                    description=f"**{item.name}** теперь продаётся в магазине",
                    color=discord.Color.green()
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)


    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.check_any(
        is_moderator(),
        commands.has_permissions(administrator=True) )
    @commands.command(
        aliases=["shop-remove"],
        description="убирает шмотку из магазина сервера.",
        usage="Название шмотки",
        brief="Футболка" )
    async def shop_remove(self, ctx, *, search):
        # Searching item
        shop = ItemStorage(ctx.guild.id, {"items": True, "shop": True}).shop
        items = shop.search_item(search)
        item = None
        if len(items) == 0:
            reply = discord.Embed(
                title="❌ | Вещь не найдена",
                description=f"По поиску '{search}' в магазине не было найдено шмоток.",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        elif len(items) < 2:
            item = items[0]
        else:
            ind = await self.ask_to_choose([it.name for it in items], ctx.channel, ctx.author)
            if ind is not None:
                item = items[ind]
        del items
        # Visualising item
        if item is not None:
            shop.remove_item(item.id)
            reply = discord.Embed(
                title=f"🛒 | Вещь убрана из магазина",
                description=f"**{item.name}** больше не продаётся в магазине.",
                color=discord.Color.green()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)


    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.check_any(
        is_moderator(),
        commands.has_permissions(administrator=True) )
    @commands.command(
        aliases=["shop-clear"] )
    async def shop_clear(self, ctx):
        # Verifying deletion
        yes = ["да", "yes", "1"]; no = ["нет", "no", "0"]
        tout = 60
        def check(m):
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id and m.content.lower() in [*yes, *no]
        try:
            msg = await self.client.wait_for("message", check=check, timeout=tout)
        except asyncio.TimeoutError:
            await ctx.send(ctx.author.mention, embed=timeout_embed(tout, ctx.author))
        else:
            if msg.content.lower() in no:
                await ctx.send("🛒 Удаление магазина отменено")
            else:
                shop = ItemStorage(ctx.guild.id, {"items": True, "shop": True}).shop
                shop.clear()
                reply = discord.Embed(
                    title=f"🛒 | Магазин очищен",
                    description="Полки и витрины пустуют.",
                    color=discord.Color.green()
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)

    
    @commands.cooldown(1, 2, commands.BucketType.member)
    @commands.command(
        aliases=["buy-item"],
        description="осуществляет покупку шмотки.",
        usage="Название шмотки",
        brief="Футболка" )
    async def buy(self, ctx, *, search):
        # Searching item
        server = ItemStorage(ctx.guild.id, {"items": True, "shop": True, "cy": True})
        shop = server.shop
        cy = server.cy
        p = ctx.prefix
        del server

        items = shop.search_item(search)
        item = None
        if len(items) == 0:
            reply = discord.Embed(
                title="❌ | Вещь не найдена",
                description=f"По поиску '{search}' в магазине не было найдено шмоток.\nМагазин: `{p}shop`",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        elif len(items) < 2:
            item = items[0]
        else:
            ind = await self.ask_to_choose([it.name for it in items], ctx.channel, ctx.author)
            if ind is not None:
                item = items[ind]
        del items
        # Visualising item
        if item is not None:
            del shop
            customer = Customer(ctx.guild.id, ctx.author.id)
            # Checking balance
            if customer.balance < item.price:
                reply = discord.Embed(
                    title="❌ | Недостаточно денег",
                    description=f"**{item.name}** стоит **{item.price}** {cy}, а Ваш баланс - **{customer.balance}** {cy}",
                    color=discord.Color.dark_red()
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)

            else:
                customer.buy(item)
                reply = discord.Embed(
                    title=f"🛒 | Спасибо за покупку!",
                    description=(
                        f"**Приобретено:** {item.name}\n"
                        f"**Цена:** {item.price} {cy}\n\n"
                        f"**Использовать:** `{p}use {item.name}`\n"
                        f"**Ваш профиль:** `{p}inv`"
                    ),
                    color=colors.emerald
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)


    @commands.cooldown(1, 2, commands.BucketType.member)
    @commands.command(
        aliases=["server-shop"] )
    async def shop(self, ctx, page: int=1):
        interval = 10
        server = ItemStorage(ctx.guild.id, {"items": True, "shop": True, "cy": True})
        shop = server.shop
        cy = server.cy
        del server

        total_items = len(shop.items)
        total_pages = abs(total_items - 1) // interval + 1
        if page > total_pages or page < 1:
            reply = discord.Embed(
                title="❌ | Страница не найдена",
                description=f"Всего страниц: {total_pages}",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)
        
        else:
            reply = discord.Embed(
                title=f"🛒 | Магазин сервера",
                description="",
                color=colors.emerald
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            
            lind = (page - 1) * interval
            uind = min(page * interval, total_items)
            for i in range(lind, uind):
                item = shop.items[i]
                reply.add_field(name=f"`{i + 1}.` {item.name}", value=f"> **Цена:** {item.price} {cy}", inline=False)
            if uind == 0:
                reply.description = "Магазин пока что пуст. Приходите позже 🧸"
            
            reply.set_footer(text=f"Стр. {page} / {total_pages} | {ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)


    # Money related commands
    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.check_any(
        is_moderator(),
        commands.has_permissions(administrator=True) )
    @commands.command(
        aliases=["change-bal", "cb", "change", "add-money", "change-balance"],
        description="изменяет баланс участника",
        usage="Кол-во @Участник",
        brief="-6 @User#1234" )
    async def change_bal(self, ctx, amount: int, *, member: discord.Member=None):
        if member is None:
            member = ctx.author
        
        amount_desc = f"{amount}"
        if amount_desc[0] != "-":
            amount_desc = f"+{amount_desc}"

        eco = ItemStorage(ctx.guild.id, {"cy": True})
        customer = Customer(ctx.guild.id, member.id)
        customer.inc_bal(amount)
        reply = discord.Embed(
            title="♻ Выполнено",
            description=f"{amount_desc} {eco.cy} участнику **{member}**",
            color=discord.Color.dark_green()
        )
        reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
        await ctx.send(embed=reply)

    
    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.command(aliases=["bal", "inventory", "inv"])
    async def balance(self, ctx, *, member: discord.Member=None):
        if member is None:
            member = ctx.author
        customer = Customer(ctx.guild.id, member.id)
        eco = ItemStorage(ctx.guild.id, {"cy": True, "cases": True})

        item_desc = ""
        for item, amount in dupe_dump(customer.items).items():
            item_desc += f"> **{item.name}** (x{amount})\n"
        keys = dupe_dump(customer.keys)
        keys_desc = ""
        for case in eco.cases:
            if case.id in keys:
                keys_desc += f"> **{case.name}** (x{keys[case.id]})\n"
        
        reply = discord.Embed(
            title=f"📦 | Инвентарь {member}",
            color=member.color
        )
        reply.add_field(name="Баланс", value=f"> **{customer.balance}** {eco.cy}", inline=False)
        if item_desc != "":
            reply.add_field(name="🧸 Шмотки", value=item_desc)
        if keys_desc != "":
            reply.add_field(name="🔑 Ключи", value=keys_desc)
        reply.set_thumbnail(url=member.avatar_url)
        reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
        await ctx.send(embed=reply)


    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.command(aliases=["leaderboard", "leaders", "lb"])
    async def top(self, ctx, page: int=1):
        interval = 10
        member_list = CustomerList(ctx.guild.id).customers
        cur = ItemStorage(ctx.guild.id, {"cy": True}).cy

        if member_list == []:
            reply = discord.Embed(
                title="📊 Топ участников",
                description="Пуст",
                color=ctx.guild.me.color
            )
            reply.set_thumbnail(url=f"{ctx.guild.icon_url}")
            await ctx.send(embed=reply)
        
        else:
            total_pairs = len(member_list)
            total_pages = abs(total_pairs - 1) // interval + 1
            if page > total_pages or page < 1:
                reply = discord.Embed(
                    title="📖 Страница не найдена",
                    description=f"Всего страниц: {total_pages}"
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)
            
            else:
                member_list.sort(reverse=True, key=lambda cust: cust.balance)
                lower_bound = (page - 1) * interval
                upper_bound = min(page * interval, total_pairs)

                desc = ""
                for i in range(lower_bound, upper_bound):
                    cust = member_list[i]
                    member = ctx.guild.get_member(cust.id)
                    desc += f"**{i + 1}.** {anf(member)} • **{cust.balance}** {cur}\n"
                
                reply = discord.Embed(
                    title="📊 Топ участников",
                    description=desc,
                    color=ctx.guild.me.color
                )
                reply.set_thumbnail(url=f"{ctx.guild.icon_url}")
                reply.set_footer(text=f"Стр. {page} / {total_pages} | {ctx.author}", icon_url=ctx.author.avatar_url)
                await ctx.send(embed=reply)


    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.command(
        description="переводит деньги на счёт участника",
        usage="Кол-во @Участник",
        brief="60 @User#1234" )
    async def pay(self, ctx, amount: int, *, member: discord.Member):
        customer = Customer(ctx.guild.id, ctx.author.id)
        server = ItemStorage(ctx.guild.id, {"cy": True})
        
        if amount > customer.balance or amount < 1:
            reply = discord.Embed(
                title="💢Ошибка",
                description="На Вашем балансе недостаточно денег.",
                color=discord.Color.dark_red()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        
        else:
            customer.pay_to(member.id, amount)
            reply = discord.Embed(
                title="♻ Выполнено",
                description=f"На баланс {member} переведено {amount} {server.cy}",
                color=discord.Color.dark_green()
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)


def setup(client):
    client.add_cog(economy(client))
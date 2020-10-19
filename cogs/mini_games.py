import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio, os, datetime, random

from functions import find_alias, carve_int, get_field

from pymongo import MongoClient
app_string = str(os.environ.get('cluster_string'))
cluster = MongoClient(app_string)
db = cluster["guilds"]

#====== Roulette game rules ========
color_fields = {
    "красный": [1, 3, 7, 12, 16, 18, 21, 23, 25, 27, 32, 36],
    "зеленый": [4, 5, 9, 10, 14, 19, 20, 24, 28, 30, 33, 34]
}
color_aliases = {
    "красный": ["red", "r", "красный", "к"],
    "зеленый": ["green", "g", "зеленый", "зелёный", "з"],
    "черный": ["black", "b", "чёрный", "черный", "ч"]
}
roulette_url = "https://cdn.discordapp.com/attachments/698956854356738168/698957373875814520/roulette_board_upd.png"

roulette_games = {}
lotteries = {}
#======= Work replies=======
work_replies = [
    "Вы провели долгие часы на заводе, заработав {earning}",
    "Поработав 8 часов в офисе, Вы заработали {earning}",
    "За волонтёрскую деятельность Вам заплатили {earning}",
    "Фриланс сегодня принёс Вам {earning}",
    "Вы продали несколько товаров на алиэкспрессе в сумме на {earning}",
    "Вы порылись в карманах зимней куртки. {earning}."
]
#-------- Black jack---------
deck = None

#======= Functions ========
from functions import Customer, ItemStorage, CustomerList

def card_val(name):
    s = name.rsplit("_", maxsplit=1)[1]
    if s in ["j", "q", "k"]:
        return 10
    elif s == "a":
        return 11
    else:
        return int(s)

def get_deck(client):
    sid_1, sid_2 = 698646973347266560, 698992580234444801
    elist_1, elist_2 = client.get_guild(sid_1).emojis, client.get_guild(sid_2).emojis
    out = []
    is_card = lambda name: name.startswith("poke") or name.startswith("club") or name.startswith("diamond") or name.startswith("heart")
    for e in elist_1:
        if is_card(e.name):
            out.append((str(e), card_val(e.name)))
    for e in elist_2:
        if is_card(e.name):
            out.append((str(e), card_val(e.name)))
    return out

def is_command(text, prefix, client):
    out = False
    _1st_word = text.split(maxsplit=1)[0]
    if _1st_word.startswith(prefix):
        _1st_word = _1st_word[len(prefix):]
        for cmd in client.commands:
            if _1st_word == cmd.name or _1st_word in cmd.aliases:
                out = True
                break
    return out

async def read_message(channel, user, t_out, client):
    try:
        msg = await client.wait_for("message", check=lambda message: user.id==message.author.id and channel.id==message.channel.id, timeout=t_out)
    except asyncio.TimeoutError:
        reply=discord.Embed(
            title="🕑 Вы слишком долго не писали",
            description=f"Таймаут: {t_out} сек",
            color=discord.Color.blurple()
        )
        await channel.send(content=user.mention, embed=reply)
        return None
    else:
        return msg

async def do_roulette(channel):
    await asyncio.sleep(30)

    global roulette_games
    players = roulette_games[channel.guild.id]
    players.pop("started_at")
    roulette_games.pop(channel.guild.id)

    win_field = random.randint(1, 36)
    win_line = (win_field - 1) % 3 + 1
    win_col = None
    for color in color_fields:
        if win_field in color_fields[color]:
            win_col = color
            break
    if win_col is None:
        win_col = "черный"

    to_inc_list = []
    mass_ping = ""
    for user_id in players:
        bets = players[user_id]
        summ = 0
        for triplet in bets:
            typ, value, bet = triplet
            if typ == "field" and value == win_field:
                summ += 36 * bet
            elif typ == "line" and value == win_line:
                summ += 3 * bet
            elif typ == "color" and value == win_col:
                summ += 3 * bet
        if summ > 0:
            to_inc_list.append(user_id)
            mass_ping += f"> <@!{user_id}>\n"

    if to_inc_list != []:
        player_base = CustomerList(channel.guild.id, {"_id": True})
        player_base.mass_inc_bal(summ, to_inc_list)
    if mass_ping == "":
        mass_ping = "> Отсутствуют"
    
    msg = discord.Embed(
        title="🎲 Конец рулетки",
        description=(
            f"Шар упал на поле **№{win_field}** (линия {win_line}, {win_col} цвет)\n"
            f"Победители:\n{mass_ping}"
        ),
        color=channel.guild.me.color
    )
    msg.set_thumbnail(url=f"{channel.guild.icon_url}")
    await channel.send(embed=msg)

async def do_lottery(channel):
    await asyncio.sleep(60)

    global lotteries
    guild_id = channel.guild.id
    lot = lotteries[guild_id]
    lot.pop("started_at")
    lotteries.pop(guild_id)

    winner_id = random.choice(lot["ids"])
    winner = channel.guild.get_member(winner_id)

    player = Customer(channel.guild.id, winner_id, {})
    player.inc_bal(lot["pool"])
    
    win_emb = discord.Embed(
        title="🎉 Результаты лотереи",
        description=(
            f"**Призовой фонд:** {lot['pool']}\n"
            f"**Кол-во участников:** {len(lot['ids'])}\n"
            f"**Победитель:** {winner}, получает весь призовой фонд!"
        ),
        color=discord.Color.gold()
    )
    win_emb.set_thumbnail(url=f"{channel.guild.icon_url}")
    await channel.send(embed=win_emb)

class Deck:
    def __init__(self, deck_pairs):
        self.deck = deck_pairs
    
    def take_card(self):
        i = random.randint(0, len(self.deck) - 1)
        card = self.deck[i]
        self.deck.pop(i)
        return card

    def take_specific_card(self, value):
        card = None
        for c in self.deck:
            if c[1] == value:
                card = c
                break
        return card

class Hand:
    def __init__(self):
        self.cards = []
        self.value = 0
        self.values = []
    
    def __str__(self):
        return " ".join(self.cards)
    
    def add_card(self, paired_card):
        self.cards.append(paired_card[0])
        self.values.append(paired_card[1])
        self.value += paired_card[1]
        if self.value > 21:
            for i in range(len(self.values)):
                if self.values[i] == 11:
                    self.values[i] = 1
                    self.value -= 10
                    break

class economy(commands.Cog):
    def __init__(self, client):
        self.client = client

    #========== Events ===========
    @commands.Cog.listener()
    async def on_ready(self):
        print(">> Mini games cog is loaded")

    #========= Commands ==========

    @commands.cooldown(1, 3600, commands.BucketType.member)
    @commands.command(aliases=["w"])
    async def work(self, ctx):
        w_range = (50, 100)
        cur = ItemStorage(ctx.guild.id, {"cy": True}).cy
        player = Customer(ctx.guild.id, ctx.author.id, {})

        summ = random.randint(*w_range)
        text = random.choice(work_replies).replace("{earning}", f"{summ} {cur}")

        player.inc_bal(summ)
        
        reply = discord.Embed(
            title=f"✅ {ctx.author}",
            description=text,
            color=discord.Color.dark_green()
        )
        await ctx.send(embed=reply)


def setup(client):
    client.add_cog(economy(client))

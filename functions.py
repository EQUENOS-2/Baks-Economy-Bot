import failures
import discord
from discord.ext import commands
from pymongo import MongoClient
import os


app_string = str(os.environ.get('cluster_string'))
cluster = MongoClient(app_string)
db = cluster["guilds"]


#-------------------------------------+
#             Constants               |
#-------------------------------------+
owner_ids = [301295716066787332]


perms_tr = {
    "create_instant_invite": "Создавать приглашения",
    "kick_members": "Кикать участников",
    "ban_members": "Банить участников",
    "administrator": "Администратор",
    "manage_channels": "Управлять каналами",
    "manage_guild": "Управлять сервером",
    "add_reactions": "Добавлять реакции",
    "view_audit_log": "Просматривать журнал аудита",
    "priority_speaker": "Приоритетный режим",
    "stream": "Видео",
    "read_messages": "Читать сообщения",
    "view_channel": "Видеть канал",
    "send_messages": "Отправлять сообщения",
    "send_tts_messages": "Отправлять TTS сообщения",
    "manage_messages": "Управлять сообщениями",
    "embed_links": "Встраивать ссылки",
    "attach_files": "Прикреплять файлы",
    "read_message_history": "Просматривать историю сообщений",
    "mention_everyone": "Упоминать everyone / here",
    "external_emojis": "Использовать внешние эмодзи",
    "view_guild_insights": "View server insights",
    "connect": "Подключаться",
    "speak": "Говорить",
    "mute_members": "Выключать микрофон у участников",
    "deafen_members": "Заглушать участников",
    "move_members": "Перемещать участников",
    "use_voice_activation": "Использовать режим рации",
    "change_nickname": "Изменять никнейм",
    "manage_nicknames": "Управлять никнеймами",
    "manage_roles": "Управлять ролями",
    "manage_permissions": "Управлять правами",
    "manage_webhooks": "Управлять вебхуками",
    "manage_emojis": "Управлять эмодзи"
}


bscolors = {
    "0xffffffff": "белый",
    "0xffa2e3fe": "светло-голубой",
    "0xff4ddba2": "изумрудный",
    "0xffff9727": "оранжевый",
    "0xfff9775d": "кремовый красный",
    "0xfff05637": "красный",
    "0xfff9c908": "жёлтый",
    "0xffffce89": "бежевый",
    "0xffa8e132": "зелёный",
    "0xff1ba5f5": "синий",
    "0xffff8afb": "розовый",
    "0xffcb5aff": "фиолетовый"
}


#-------------------------------------+
#           Database Models           |
#-------------------------------------+
class ServerConfig:
    def __init__(self, _id: int, projection=None):
        collection = db["config"]
        result = collection.find_one({"_id": _id}, projection=projection)
        if result is None:
            result = {}
        
        self.id = _id
        self.mod_roles = result.get("mod_roles", [])
        self.log_channel = result.get("log_channel")
    # Moderator role manipulators
    def add_mod_role(self, role_id: int):
        collection = db["config"]
        collection.update_one(
            {"_id": self.id},
            {"$addToSet": {"mod_roles": role_id}},
            upsert=True
        )
    
    def remove_mod_role(self, role_id):
        collection = db["config"]
        collection.update_one(
            {"_id": self.id},
            {"$pull": {"mod_roles": { "$in": [role_id] }}}
        )
    
    def clear_mod_roles(self):
        collection = db["config"]
        collection.update_one(
            {"_id": self.id},
            {"$unset": {"mod_roles": ""}}
        )
    # Log channel manipulators
    def set_log_channel(self, channel_id):
        collection = db["config"]
        collection.update_one(
            {"_id": self.id},
            {"$set": {"log_channel": channel_id}},
            upsert=True
        )

    def unset_log_channel(self):
        collection = db["config"]
        collection.update_one(
            {"_id": self.id},
            {"$unset": {"log_channel": ""}}
        )


class BrawlDiscordList:
    def __init__(self):
        pass

    def contains_tag(self, tag: str):
        collection = db["brawlstars_tags"]
        result = collection.find_one({"tag": tag})
        return False if result is None else True
    
    def contains_id(self, _id: int):
        collection = db["brawlstars_tags"]
        result = collection.find_one({"_id": _id, "tag": {"$exists": True}})
        return False if result is None else True

    def link_together(self, _id: int, tag: str):
        collection = db["brawlstars_tags"]
        collection.update_one(
            {"_id": _id},
            {"$set": {"tag": tag}},
            upsert=True
        )


class BrawlDiscordUser:
    def __init__(self, user_id: int):
        collection = db["brawlstars_tags"]
        result = collection.find_one({"_id": user_id})
        if result is None:
            result = {}
        
        self.id = user_id
        self.tag = result.get("tag")
    
    def link_with(self, tag: str):
        collection = db["brawlstars_tags"]
        collection.update_one(
            {"_id": self.id},
            {"$set": {"tag": tag}},
            upsert=True
        )

    def unlink(self):
        collection = db["brawlstars_tags"]
        collection.update_one(
            {"_id": self.id},
            {"$unset": {"tag": ""}}
        )


class Member:
    def __init__(self, _id: int):
        self.id = _id

#-------------------------------------+
#            Custom Checks            |
#-------------------------------------+
def is_moderator():
    def predicate(ctx):
        server = ServerConfig(ctx.guild.id)
        mod_role_ids = server.mod_roles
        author_role_ids = [r.id for r in ctx.author.roles]
        has = False
        for role_id in mod_role_ids:
            if role_id in author_role_ids:
                has = True
                break
        if has:
            return True
        else:
            raise failures.IsNotModerator()
    return commands.check(predicate)

#-------------------------------------+
#           Other functions           |
#-------------------------------------+
def timeout_embed(timeout, reciever):
    if timeout % 10 == 1:
        timeword = "секунды"
    else:
        timeword = "секунд"
    reply = discord.Embed(
        title="🕑 Истекло время ожидания",
        description=f"{antiformat(reciever)}, Вы не отвечали больше {timeout} {timeword}.",
        color=discord.Color.blurple()
    )
    reply.set_footer(text=str(reciever), icon_url=reciever.avatar_url)
    return reply


def antiformat(text):
    formers = "~`*_|>"
    out = ""
    for s in str(text):
        if s in formers:
            out += "\\" + s
        else:
            out += s
    return out


def quote_list(_list):
    return "\n".join([f"> {elem}" for elem in _list])


def display_perms(missing_perms):
    out = ""
    for perm in missing_perms:
        out += f"> {perms_tr[perm]}\n"
    return out


def vis_aliases(aliases):
    if aliases not in [None, []]:
        out = "**Синонимы:** "
        for a in aliases:
            out += f"`{a}`, "
        return out[:-2]
    else:
        return ""


def visual_delta(delta):
    if "int" in f"{type(delta)}".lower():
        seconds = delta
        t_days = 0
    else:
        seconds = delta.seconds
        t_days = delta.days
    
    expanded_delta = {
        "сек": seconds % 60,
        "мин": seconds // 60 % 60,
        "ч": seconds // 3600 % 24,
        "дн": t_days % 7,
        "нед": t_days // 7
    }

    out = ""
    for key in expanded_delta:
        num = expanded_delta[key]
        if num > 0:
            out = f"{num} {key} " + out
    if out == "":
        out = "0 сек"
    out.strip()
    return out


def rus_timestamp(datetime):
    months = [
        "января", "февраля",
        "марта", "апреля", "мая",
        "июня", "июля", "августа",
        "сентября", "октября", "ноября",
        "декабря"
    ]
    date = f"{datetime.day} {months[datetime.month - 1]} {datetime.year}"
    time = f"{datetime}"[-15:][:+8]
    return f"{date}, {time}"


def get_field(Dict, *key_words, default=None):
    if Dict is not None:
        for key in key_words:
            if key in Dict:
                Dict = Dict[key]
            else:
                Dict = None
                break
    if Dict is None:
        Dict = default
    return Dict


def find_alias(table, value):
    out = None
    for key in table:
        if value in table[key]:
            out = key
            break
    return out


def carve_int(string):
    nums = [str(i) for i in range(10)]
    out = ""
    found = False
    for letter in string:
        if letter in nums:
            found = True
            out += letter
        elif found:
            break
    if out == "":
        out = None
    else:
        out = int(out)
    return out


def try_int(string):
    try:
        return int(string)
    except ValueError:
        return None


def has_permissions(member, perm_array):
    if member.id in owner_ids:
        return True
    else:
        perms_owned = dict(member.guild_permissions)
        total_needed = len(perm_array)
        for perm in perm_array:
            if perms_owned[perm]:
                total_needed -= 1
        return total_needed == 0


def has_roles(member, role_array):
    has_them = True
    if not has_permissions(member, ["administrator"]):
        for role in role_array:
            if isinstance(role, int):
                role = member.guild.get_role(role)
            if role not in member.roles:
                has_them = False
                break
    return has_them


def has_any_role(member, role_array):
    has_them = True
    if not has_permissions(member, ["administrator"]):
        has_them = False
        for role in role_array:
            if isinstance(role, int):
                role = member.guild.get_role(role)
            if role in member.roles:
                has_them = True
                break
    return has_them


def has_role_or_higher(member, role_or_id):
    if has_permissions(member, ["administrator"]):
        return True
    else:
        if "int" in str(type(role_or_id)):
            role_or_id = member.guild.get_role(role_or_id)
        if role_or_id is None:
            return False
        else:
            has = False
            for role in member.roles:
                if role.position >= role_or_id.position:
                    has = True
                    break
            return has


class detect:
    @staticmethod
    def member(guild, search):
        ID = carve_int(search)
        if ID is None:
            ID = 0
        member = guild.get_member(ID)
        if member is None:
            member = guild.get_member_named(search)
        return member
    
    @staticmethod
    def channel(guild, search):
        ID = carve_int(search)
        if ID is None:
            ID = 0
        channel = guild.get_channel(ID)
        if channel is None:
            for c in guild.channels:
                if c.name == search:
                    channel = c
                    break
        return channel
    
    @staticmethod
    def role(guild, search):
        ID = carve_int(search)
        if ID is None:
            ID = 0
        role = guild.get_role(ID)
        if role is None:
            for r in guild.roles:
                if r.name == search:
                    role = r
                    break
        return role
    
    @staticmethod
    def user(search, client):
        ID = carve_int(search)
        user = None
        if ID is not None:
            user = client.get_user(ID)
        return user


class Custom_emoji:
    def __init__(self, client):
        self.server = client.get_guild(698646973347266560)
    
    def __call__(self, emoji_name):
        out = None
        for emoji in self.server.emojis:
            if emoji.name == emoji_name:
                out = emoji
                break
        return out
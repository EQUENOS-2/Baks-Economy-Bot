import failures
import discord
from discord.ext import commands
from pymongo import MongoClient
import os
from datetime import datetime, timedelta
import random


app_string = str(os.environ.get('cluster_string'))
cluster = None; att = 2
while cluster is None:
    try:
        cluster = MongoClient(app_string)
    except Exception as e:
        att += 1
        print(f"--> functions.py: Retrying to connect to MongoDB (attempt {att}): [{e}]")
db = cluster["guilds"]


#-------------------------------------+
#             Constants               |
#-------------------------------------+
inv_capacity = 100
max_club_roles = 20
owner_ids = [
    301295716066787332
]
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
default_cy = "💰"
default_item_icon_url = ""


#-------------------------------------+
#           Database Models           |
#-------------------------------------+
# General server configuration
class ServerConfig:
    def __init__(self, _id: int, projection=None):
        collection = db["config"]
        result = collection.find_one({"_id": _id}, projection=projection)
        if result is None:
            result = {}
        
        self.id = _id
        self.mod_roles = result.get("mod_roles", [])
        self.log_channel = result.get("log_channel")
        self.verified_role = result.get("verified_role")
        self.club_roles = result.get("club_roles", {})
        self.vote_channel = result.get("vote_channel")
    # Moderator role manipulators
    def add_mod_role(self, role_id: int):
        collection = db["config"]
        collection.update_one(
            {"_id": self.id},
            {"$addToSet": {"mod_roles": role_id}},
            upsert=True
        )
    
    def remove_mod_role(self, role_id: int):
        collection = db["config"]
        collection.update_one(
            {"_id": self.id},
            {"$pull": {"mod_roles": { "$in": [role_id] }}}
        )
    
    def clear_outdated_roles(self, server_roles: list):
        server_roles = [r.id for r in server_roles]
        nonexist = []
        for r in self.mod_roles:
            if r not in server_roles:
                self.mod_roles.remove(r)
                nonexist.append(r)
        if nonexist != []:
            collection = db["config"]
            collection.update_one(
                {"_id": self.id},
                {"$pull": {"mod_roles": { "$in": nonexist }}}
            )

    def clear_mod_roles(self):
        collection = db["config"]
        collection.update_one(
            {"_id": self.id},
            {"$unset": {"mod_roles": ""}}
        )
    # Log channel manipulators
    def set_log_channel(self, channel_id: int):
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
    # Verified role
    def set_verified_role(self, role_id: int):
        collection = db["config"]
        collection.update_one(
            {"_id": self.id},
            {"$set": {"verified_role": role_id}},
            upsert=True
        )

    def unset_verified_role(self):
        collection = db["config"]
        collection.update_one(
            {"_id": self.id},
            {"$unset": {"verified_role": ""}}
        )
    # Club role
    def add_club_role(self, role_id: int, club_tag: str):
        collection = db["config"]
        collection.update_one(
            {"_id": self.id},
            {"$set": {f"club_roles.{club_tag}": role_id}},
            upsert=True
        )

    def remove_club_role(self, club_tag: str):
        collection = db["config"]
        collection.update_one(
            {"_id": self.id},
            {"$unset": {f"club_roles.{club_tag}": ""}}
        )
    
    def clear_club_roles(self):
        collection = db["config"]
        collection.update_one(
            {"_id": self.id},
            {"$unset": {"club_roles": ""}}
        )
    # Vote channel
    def set_vote_channel(self, channel_id: int):
        collection = db["config"]
        collection.update_one(
            {"_id": self.id},
            {"$set": {"vote_channel": channel_id}},
            upsert=True
        )

    def unset_vote_channel(self):
        collection = db["config"]
        collection.update_one(
            {"_id": self.id},
            {"$unset": {"vote_channel": ""}}
        )
    
# Brawl Stars: Discord verification
class BrawlDiscordList:
    def __init__(self):
        pass

    def load(self):
        collection = db["brawlstars_tags"]
        result = collection.find({"tag": {"$exists": True}})
        return [] if result is None else [BrawlDiscordUser(doc["_id"], doc["tag"]) for doc in result]

    def contains_tag(self, tag: str):
        collection = db["brawlstars_tags"]
        result = collection.find_one({"tag": tag})
        return False if result is None else True
    
    def contains_id(self, _id: int):
        collection = db["brawlstars_tags"]
        result = collection.find_one({"_id": _id, "tag": {"$exists": True}})
        return False if result is None else True

    def find_matches(self, list_of_ids: list):
        collection = db["brawlstars_tags"]
        result = collection.find({"_id": {"$in": list_of_ids}, "tag": {"$exists": True}})
        return [] if result is None else [BrawlDiscordUser(doc["_id"], doc["tag"]) for doc in result]
    
    def link_together(self, _id: int, tag: str):
        collection = db["brawlstars_tags"]
        collection.update_one(
            {"_id": _id},
            {"$set": {"tag": tag}},
            upsert=True
        )


class BrawlDiscordUser:
    def __init__(self, user_id: int, tag: str=None):
        self.id = user_id

        if tag is None:
            collection = db["brawlstars_tags"]
            result = collection.find_one({"_id": self.id})
            if result is None:
                result = {}
            self.tag = result.get("tag")
        else:
            self.tag = tag
    
    def __str__(self):
        return f"<BDU(id={self.id}, tag={self.tag})>"

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


class BrawlClubLoop:
    def __init__(self, bot_id: int):
        hours = 24
        self.id = bot_id
        collection = db["brawl_loop_data"]
        result = collection.find_one({"_id": self.id})
        if result is None:
            result = {}
        
        now = datetime.utcnow()
        delta = timedelta(hours=hours)
        self.checked_at = result.get("checked_at", now - delta)
        self.next_check_at = self.checked_at + delta
        if self.next_check_at <= now:
            self.time_left = timedelta(seconds=0)
        else:
            self.time_left = self.next_check_at - now

    def get_servers(self):
        collection = db["config"]
        results = collection.find(
            {"club_roles": {"$exists": True}},
            projection={"club_roles": True, "_id": True}
        )
        return [res for res in results if len(res.get("club_roles", {})) > 0]

    def update_timestamp(self):
        collection = db["brawl_loop_data"]
        collection.update_one({"_id": self.id}, {"$set": {"checked_at": datetime.utcnow()}}, upsert=True)


# Reaction Roles manipulator
class ReactionRolesConfig:
    def __init__(self, server_id: int):
        self.id = server_id
    
    def get_role(self, message_id: int, emoji: str):
        collection = db["reaction_roles"]
        result = collection.find_one(
            {"_id": self.id, f"{message_id}.{emoji}": {"$exists": True}},
            projection={str(message_id): True}
        )
        return None if result is None else result.get(f"{message_id}", {}).get(f"{emoji}")
    
    def add_role(self, message_id: int, emoji: str, role_id: int):
        collection = db["reaction_roles"]
        collection.update_one(
            {"_id": self.id, f"{message_id}.{emoji}": {"$exists": False}},
            {"$set": {f"{message_id}.{emoji}": role_id}},
            upsert=True
        )
    
    def remove_reaction(self, message_id: int, emoji: str):
        collection = db["reaction_roles"]
        collection.update_one(
            {"_id": self.id, f"{message_id}.{emoji}": {"$exists": True}},
            {"$unset": {f"{message_id}.{emoji}": ""}}
        )

    def get_roles(self, message_id: int):
        collection = db["reaction_roles"]
        result = collection.find_one(
            {"_id": self.id, f"{message_id}": {"$exists": True}},
            projection={str(message_id): True}
        )
        return {} if result is None else result.get(str(message_id), {})

# Server economy tools
class Item:
    def __init__(self, item_id: int, data: dict, server_id: int):
        self.id = item_id
        self.server_id = server_id
        self.name = data.get("name", "[Удалённый предмет]")
        self.icon_url = data.get("icon_url")
        self.price = data.get("price", 0)
        self.role = data.get("role")
        self.key_for = data.get("key_for", [])

    def set_name(self, name: str):
        collection = db["items"]
        collection.update_one(
            {"_id": self.server_id},
            {"$set": {f"items.{self.id}.name": name}},
            upsert=True
        )
        self.name = name
    
    def set_icon_url(self, url: str):
        collection = db["items"]
        collection.update_one(
            {"_id": self.server_id},
            {"$set": {f"items.{self.id}.icon_url": url}},
            upsert=True
        )
        self.icon_url = url

    def set_price(self, price: int):
        collection = db["items"]
        collection.update_one(
            {"_id": self.server_id},
            {"$set": {f"items.{self.id}.price": price}}
        )
        self.price = price
    
    def set_role(self, role_id: int):
        collection = db["items"]
        collection.update_one(
            {"_id": self.server_id},
            {"$set": {f"items.{self.id}.role": role_id}}
        )
        self.role = role_id
    # case manipulators
    def bind_case(self, case_id: int):
        collection = db["items"]
        collection.update_one(
            {"_id": self.server_id},
            {"$addToSet": {f"items.{self.id}.key_for": case_id}}
        )
        self.key_for.append(case_id)
    
    def unbind_case(self, case_id: int):
        collection = db["items"]
        collection.update_one(
            {"_id": self.server_id},
            {"$pull": {f"items.{self.id}.key_for": {"$in": [case_id]}}}
        )
        self.key_for.remove(case_id)

    def unbind_all(self):
        collection = db["items"]
        collection.update_one(
            {"_id": self.server_id},
            {"$unset": {f"items.{self.id}.key_for": ""}}
        )
        self.key_for = []
    # deletion
    def delete(self):
        collection = db["items"]
        collection.update_one(
            {"_id": self.server_id},
            {"$unset": {f"items.{self.id}": ""}}
        )


class Case:
    def __init__(self, server_id:int, case_id: int, loot: list, data: dict={}):
        self.server_id = server_id
        self.id = case_id
        if "loot" in data:
            data.pop("loot")
        self.name = data.get("name", "???")
        self.icon_url = data.get("icon_url")
        self.loot = sorted(loot, key=lambda p: p[1])
    
    @property
    def percentage(self):
        s = 0
        for item in self.loot:
            s += item[1]
        out = []
        for item in self.loot:
            pr = 100 * item[1] / s
            l = len(str(pr)[2:]) - len(str(pr)[2:].lstrip("0"))
            if l > 0:
                out.append(round(pr, l + 1))
            else:
                out.append(round(pr, 1))
        return out

    def search_item(self, string):
        string = string.lower()
        return [item for item, w in self.loot if string in item.name.lower()]

    def open(self, amount=1):
        try:
            p = []; w = []
            for pair in self.loot:
                p.append(pair[0])
                w.append(pair[1])
            return random.choices(population=p, weights=w, k=amount)
        except Exception:
            return None

    def set_name(self, name: str):
        collection = db["items"]
        collection.update_one(
            {"_id": self.server_id},
            {"$set": {f"cases.{self.id}.name": name}},
            upsert=True
        )

    def set_icon_url(self, url: str):
        collection = db["items"]
        collection.update_one(
            {"_id": self.server_id},
            {"$set": {f"cases.{self.id}.icon_url": url}},
            upsert=True
        )

    def add_item(self, item_id: int, weight: float):
        collection = db["items"]
        collection.update_one(
            {"_id": self.server_id},
            {"$set": {f"cases.{self.id}.loot.{item_id}": weight}}
        )
    
    def remove_item(self, item_id: int):
        collection = db["items"]
        collection.update_one(
            {"_id": self.server_id},
            {"$unset": {f"cases.{self.id}.loot.{item_id}": ""}}
        )
    
    def clear(self):
        collection = db["items"]
        collection.update_one(
            {"_id": self.server_id},
            {"$unset": {f"cases.{self.id}.loot": ""}}
        )

    def delete(self):
        collection = db["items"]
        collection.update_one(
            {"_id": self.server_id},
            {"$unset": {f"cases.{self.id}": ""}}
        )


class Shop:
    def __init__(self, server_id: int, items: list):
        self.id = server_id
        self.items = sorted(items, key=lambda it: it.price)
    
    def search_item(self, string: str):
        string = string.lower()
        return [item for item in self.items if string in item.name.lower()]

    def add_item(self, item_id: int):
        collection = db["items"]
        collection.update_one(
            {"_id": self.id},
            {"$addToSet": {"shop": item_id}}
        )
    
    def remove_item(self, item_id: int):
        collection = db["items"]
        collection.update_one(
            {"_id": self.id},
            {"$pull": {"shop": item_id}}
        )
    
    def clear(self):
        collection = db["items"]
        collection.update_one(
            {"_id": self.id},
            {"$unset": {"shop": ""}}
        )


class ItemStorage:
    def __init__(self, server_id: int, projection=None):
        self.id = server_id
        if "items" in projection:
            self.items_loaded = True
        else:
            self.items_loaded = False
        
        collection = db["items"]
        result = collection.find_one({"_id": self.id}, projection=projection)
        if result is None:
            result = {}
        
        self.cy = result.get("cy", "💰")
        self.items = [ Item(int(_id), data, self.id) for _id, data in result.get("items", {}).items() ]
        self.raw_shop = result.get("shop", [])
        self.raw_cases = result.get("cases", {})
        self._cases = None
        del result
    
    @property
    def shop(self):
        shop_items = []
        nonexist = []
        for item_id in self.raw_shop:
            item = self.get(item_id)
            if item is None:
                nonexist.append(item_id)
            else:
                shop_items.append(item)
        if self.items_loaded:
            collection = db["items"]
            collection.update_one({"_id": self.id}, {"$pull": {"$in": nonexist}})
        return Shop( self.id, shop_items )
    
    @property
    def cases(self):
        if self._cases is None:
            self._cases = []
            nonexist = []
            for cid, data in self.raw_cases.items():
                loot = []
                for _id_, weight in data.get("loot", {}).items():
                    item = self.get(int(_id_))
                    if item is None:
                        nonexist.append((f"cases.{cid}.loot.{_id_}", ""))
                    else:
                        loot.append((item, weight))
                self._cases.append( Case(self.id, int(cid), loot, data) )
            if nonexist != [] and self.items_loaded:
                collection = db["items"]
                collection.update_one({"_id": self.id}, {"$unset": dict(nonexist)})
        return self._cases

    def get(self, item_id: int, result=None):
        for item in self.items:
            if item.id == item_id:
                result = item
                break
        return result

    def get_case(self, case_id: int, result=None):
        for case in self.cases:
            if case.id == case_id:
                result = case
                break
        return result

    def search_items(self, string: str):
        string = string.lower()
        return [item for item in self.items if string in item.name.lower()]

    def search_cases(self, string: str):
        string = string.lower()
        return [case for case in self.cases if string in case.name.lower()]
    # Item creation
    def create_item(self, item_id: int, name: str, price: int=0):
        collection = db["items"]
        collection.update_one(
            {"_id": self.id},
            {"$set": {f"items.{item_id}": {"name": name, "price": price}}},
            upsert=True
        )
    # Case creation
    def create_case(self, case_id: int, name: str):
        collection = db["items"]
        try:
            collection.update_one(
                {"_id": self.id},
                {"$set": {f"cases.{case_id}": {"name": name}}},
                upsert=True
            )
        except Exception:
            pass
    # Add item to shop
    def add_to_shop(self, item_id: int):
        collection = db["items"]
        collection.update_one(
            {"_id": self.id},
            {"$addToSet": {"shop": item_id}}
        )


class Customer:
    def __init__(self, server_id: int, user_id: int, data: dict=None):
        self.server_id = server_id
        self.id = user_id

        if data is None:
            collection = db["customers"]
            result = collection.find_one(
                {"_id": self.server_id, f"{self.id}": {"$exists": True}},
                projection={f"{self.id}": True}
            )
            if result is None:
                data = {}
            else:
                data = result.get(f"{self.id}")
            del result
            
        self.balance = data.get("balance", 0)
        self.raw_items = data.get("items", [])
        self.keys = data.get("keys", [])
        self._items = None
        del data
    
    @property
    def items(self):
        if self._items is None:
            server = ItemStorage(self.server_id, {"items": True})
            self._items = []; outdated = []
            for _id_ in self.raw_items:
                item = server.get(_id_)
                if item is None:
                    outdated.append(_id_)
                else:
                    self._items.append(item)
            if outdated != []:
                self.remove_items(*outdated)
        return self._items

    def search_item(self, string):
        string = string.lower()
        out = []
        for item in self.items:
            if item not in out and string in item.name.lower():
                out.append(item)
        return out

    def pay_to(self, user_id: int, number: int):
        collection = db["customers"]
        collection.update_one(
            {"_id": self.server_id},
            {"$inc": {
                f"{self.id}.balance": -number,
                f"{user_id}.balance": number
            }},
            upsert=True
        )

    def inc_bal(self, number: int):
        collection = db["customers"]
        collection.update_one(
            {"_id": self.server_id},
            {"$inc": {f"{self.id}.balance": number}},
            upsert=True
        )

    def give_item(self, item: Item):
        collection = db["customers"]
        collection.update_one(
            {"_id": self.server_id},
            {"$push": {f"{self.id}.items": item.id}},
            upsert=True
        )

    def remove_items(self, *item_ids: list):
        for item_id in item_ids:
            self.raw_items.remove(item_id)
        collection = db["customers"]
        collection.update_one(
            {"_id": self.server_id},
            {"$set": {f"{self.id}.items": self.raw_items}}
        )
    
    def sell_item(self, item: Item, amount=1):
        earning = 0
        while amount > 0 and item.id in self.raw_items:
            amount -= 1
            self.raw_items.remove(item.id)
            earning += item.price
        collection = db["customers"]
        collection.update_one(
            {"_id": self.server_id},
            {
                "$set": {f"{self.id}.items": self.raw_items},
                "$inc": {f"{self.id}.balance": earning}
            }
        )

    def remove_keys(self, *case_ids: int):
        for case_id in case_ids:
            self.keys.remove(case_id)
        collection = db["customers"]
        collection.update_one(
            {"_id": self.server_id},
            {"$set": {f"{self.id}.keys": self.keys}}
        )

    def open_case(self, case: Case, amount=1):
        x_keys = self.keys.count(case.id)
        inv_weight = len(self.raw_items)
        if amount > x_keys:
            amount = x_keys
        if amount + inv_weight > inv_capacity:
            amount = inv_capacity - inv_weight
        
        if amount > 0:
            items = case.open(amount)
            if items is not None:
                while amount > 0:
                    amount -= 1
                    self.keys.remove(case.id)
                collection = db["customers"]
                collection.update_one(
                    {"_id": self.server_id},
                    {
                        "$push": {f"{self.id}.items": {"$each": [it.id for it in items]}},
                        "$set": {f"{self.id}.keys": self.keys}
                    },
                    upsert=True
                )
            return items

    def buy(self, item: Item, amount=1):
        inv_weight = len(self.raw_items)
        if inv_weight + amount > inv_capacity:
            amount = inv_capacity - inv_weight
        if amount > 0:
            collection = db["customers"]
            collection.update_one(
                {"_id": self.server_id},
                {
                    "$push": {f"{self.id}.items": {"$each": amount * [item.id]}},
                    "$inc": {f"{self.id}.balance": - item.price * amount}
                },
                upsert=True
            )
            return amount

    def use_item(self, item: Item, amount=1):
        """Doesn't add any roles, returns keys earned"""
        if amount < 1:
            amount = 1
        if item.id in self.raw_items:
            new_keys = amount * item.key_for
            while amount > 0 and item.id in self.raw_items:
                amount -= 1
                self.raw_items.remove(item.id)
            
            collection = db["customers"]
            collection.update_one(
                {"_id": self.server_id},
                {
                    "$push": {f"{self.id}.keys": {"$each": new_keys}},
                    "$set": {f"{self.id}.items": self.raw_items}
                },
                upsert=True
            )
            return new_keys


class CustomerList:
    def __init__(self, server_id: int, projection=None):
        self.id = server_id

        collection = db["customers"]
        result = collection.find_one({"_id": self.id}, projection=projection)
        if result is None:
            result = {}
        else:
            try:
                result.pop("_id")
            except Exception:
                pass
        
        self.customers = [Customer(self.id, int(_id_), data ) for _id_, data in result.items()]
        del result

    def get(self, user_id: int, result=None):
        for c in self.customers:
            if c.id == user_id:
                result = c
                break
        return result

    def mass_inc_bal(self, amount: int, user_ids: list):
        collection = db["customers"]
        collection.update_one(
            {"_id": self.id},
            {"$inc": {f"{user_id}.balance": amount for user_id in user_ids}},
            upsert=True
        )

    def reset_money(self):
        """Requires customers loaded"""
        collection = db["customers"]
        collection.update_one(
            {"_id": self.id},
            {"$set": {f"{c.id}.balance": 0 for c in self.customers}}
        )

    def clear_inventories(self):
        """Requires customers loaded"""
        collection = db["customers"]
        collection.update_one(
            {"_id": self.id},
            {"$set": {f"{c.id}.items": [] for c in self.customers}}
        )

    def clear_keys(self):
        """Requires customers loaded"""
        collection = db["customers"]
        collection.update_one(
            {"_id": self.id},
            {"$set": {f"{c.id}.keys": [] for c in self.customers}}
        )

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
    if isinstance(delta, int):
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


def find_alias(table: dict, value):
    out = None
    value = str(value).lower()
    for key in table:
        arr = [key, *table[key]]
        for elem in arr:
            if elem.lower().startswith(value):
                out = key
                break
        if out is not None:
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


def is_command(client, prefix, text):
    out = False
    text = text.split()[0]
    if text.startswith(prefix):
        text = text[len(prefix):]
        for cmd in client.commands:
            if text == cmd.name or text in cmd.aliases:
                out = True
                break
    return out


def carve_cmd(prefix, text):
    text = text.split()[0]
    if text.startswith(prefix):
        return text[len(prefix):]


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


class CustomColor:
    def __init__(self):
        self.cardboard = int("FFCC84", 16)
        self.emerald = int("5DE897", 16)


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
owner_ids = [301295716066787332]


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
            if "int" in f"{type(role)}".lower():
                role = member.guild.get_role(role)
            if not role in member.roles:
                has_them = False
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
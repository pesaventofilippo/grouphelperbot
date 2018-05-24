import telepot, time
from telepot.namedtuple import InlineKeyboardButton, InlineKeyboardMarkup
from tinydb import TinyDB, where
db_users = TinyDB('users.json')


def initialize():
    try:
        f = open("bot_token.txt", "r")
        token = str(f.readline())
        bot = telepot.Bot(token)
        f.close()
    except FileNotFoundError:
        f = open("bot_token.txt", "w")
        token = str(input("Token File not found. Please insert the HTTP API Bot Token: "))
        bot = telepot.Bot(token)
        f.write(token)
        f.close()
    try:
        f = open("group_id.txt", "r")
        group = int(f.readline())
        f.close()
    except FileNotFoundError:
        f = open("group_id.txt", "w")
        group = int(input("Group ID File not found. Please insert the group Chat ID: "))
        f.write(str(group))
        f.close()
    groupAdmins = [x['user']['id'] for x in bot.getChatAdministrators(group) if not x['user']['is_bot']]
    print("Bot started...")
    return bot, group, groupAdmins


def reloadDatabases():
    global groupAdmins
    global groupUserCount
    groupAdmins = [x['user']['id'] for x in bot.getChatAdministrators(group) if not x['user']['is_bot']]
    groupUserCount = int(bot.getChatMembersCount(group))


def updateDatabase(id, firstName, lastName, username):
    if db_users.search(where('chatId') == id):
        db_users.update({'chatId': id, 'firstName': firstName, 'lastName': lastName, 'username': username}, where('chatId') == id)
    else:
        db_users.insert({'chatId': id, 'firstName': firstName, 'lastName': lastName, 'username': username, 'warns': "0"})


def keyboard(type, user, msg_id):
    msg_id = str(msg_id)
    user = str(user)
    data = None
    if type == "warn":
        data = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❎ Unwarn", callback_data="unwarn#"+msg_id+"@"+user)]])
    elif type == "mute":
        data = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔈 Unmute", callback_data="unmute#"+msg_id+"@"+user)]])
    elif type == "ban":
        data = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅️ Unban", callback_data="unban#"+msg_id+"@"+user)]])
    return data


def getUserInfo(msg):
    chatId = int(msg['chat']['id'])
    msgId = int(msg['message_id'])
    from_id = int(msg['from']['id'])
    try:
        text = str(msg['text'])
    except KeyError:
        text = ""
    try:
        from_firstName = str(msg['from']['first_name'])
    except KeyError:
        from_firstName = ""
    try:
        from_lastName = str(msg['from']['last_name'])
    except KeyError:
        from_lastName = ""
    try:
        from_username = str(msg['from']['username'])
    except KeyError:
        from_username = ""

    return chatId, msgId, text, from_id, from_firstName, from_lastName, from_username


def handle(msg):
    chatId, msgId, text, from_id, from_firstName, from_lastName, from_username = getUserInfo(msg)

    if chatId == group:
        updateDatabase(from_id, from_firstName, from_lastName, from_username)
        if (db_users.search(where('chatId') == from_id) == False) and (text == "") and (bot.getChatMembersCount(group) > groupUserCount):
            bot.sendMessage(group, "Hi, <b>"+from_firstName+"</b>!\nWelcome in the "+bot.getChat(group)['title']+" group!", "HTML")

        if text.startswith("/"):
            bot.deleteMessage((group, msgId))

        if from_id in groupAdmins:
            if text.startswith("/warn @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                previousWarns = int(db_users.search(where('chatId') == selectedUserData)[0]['warns'])
                db_users.update({'warns': str(previousWarns + 1)}, where('chatId') == selectedUserData)
                userWarns = int(db_users.search(where('chatId') == selectedUserData)[0]['warns'])
                try:
                    reason = text_split[2]
                    bot.sendMessage(group, str("❗️️ " + selectedUser + " has been warned [" + str(userWarns) + "/3] for <b>" + reason + "</b>."), parse_mode="HTML")
                except IndexError:
                    bot.sendMessage(group, str("❗️️ " + selectedUser + " has been warned [" + str(userWarns) + "/3]."))
                if userWarns >= 3:
                    bot.restrictChatMember(group, selectedUserData, until_date=int(time.time() + 3600))
                    db_users.update({'warns': "0"}, where('chatId') == selectedUserData)
                    bot.sendMessage(group, str("🔇️ " + selectedUser + " has been muted until the next hour."))

            elif text.startswith("/mute @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                bot.restrictChatMember(group, selectedUserData, until_date=int(time.time() + 3600))
                try:
                    reason = text_split[2]
                    bot.sendMessage(group, str("🔇️ " + selectedUser + " has been muted for <b>" + reason + "</b> until the next hour."), parse_mode="HTML")
                except IndexError:
                    bot.sendMessage(group, str("🔇️ " + selectedUser + " has been muted until the next hour."))

            elif text.startswith("/kick @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                bot.kickChatMember(group, selectedUserData)
                time.sleep(0.1)
                bot.unbanChatMember(group, selectedUserData)
                try:
                    reason = text_split[2]
                    bot.sendMessage(group, str("❗️️ "+selectedUser+" has been kicked for <b>"+reason+"</b>."), parse_mode="HTML")
                except IndexError:
                    bot.sendMessage(group, str("❗️️ "+selectedUser+" has been kicked."))

            elif text.startswith("/ban @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                bot.kickChatMember(group, selectedUserData)
                try:
                    reason = text_split[2]
                    bot.sendMessage(group, str("🚷 "+selectedUser+" has been banned for <b>"+reason+"</b>."), parse_mode="HTML")
                except IndexError:
                    bot.sendMessage(group, str("🚷 "+selectedUser+" has been banned."))

            elif text.startswith("/unban @"):
                text_split = text.split(" ", 1)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                bot.unbanChatMember(group, selectedUserData)
                bot.sendMessage(group, "✅️ "+str(selectedUser)+" unbanned.")

            elif text.startswith("/unwarn @"):
                text_split = text.split(" ", 1)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                previousWarns = int(db_users.search(where('chatId') == selectedUserData)[0]['warns'])
                if previousWarns > 0:
                    db_users.update({'warns': str(previousWarns-1)}, where('chatId') == selectedUserData)
                    bot.sendMessage(group, "❎ "+str(selectedUser)+" unwarned.\nHe now has "+str(previousWarns-1)+" warns.")

            elif text.startswith("/unmute @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                bot.restrictChatMember(group, selectedUserData, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
                bot.sendMessage(group, str("🔈 " + selectedUser + " unmuted."))

            elif text.startswith("/tell "):
                text_split = text.split(" ", 1)
                bot.sendMessage(group, text_split[1], parse_mode="HTML")

            elif text == "/reload":
                reloadDatabases()
                bot.sendMessage(group, "✅ <b>Bot reloaded!</b>\nAdmins Found: "+str(groupAdmins.__len__())+".", "HTML")


bot, group, groupAdmins = initialize()
bot.message_loop({'chat': handle})
while 1:
    groupUserCount = bot.getChatMembersCount(group)
    time.sleep(60)
import telepot, time
from tinydb import TinyDB, where
bot = None
group = None
db_users = TinyDB('users.json')
groupAdmins = []


def initialize():
    global bot
    global group
    global groupAdmins
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


def reloadDatabases():
    global groupAdmins
    groupAdmins = [x['user']['id'] for x in bot.getChatAdministrators(group) if not x['user']['is_bot']]


def updateDatabase(id, firstName, lastName, username):
    if db_users.search(where('chatId') == id):
        db_users.update({'firstName': firstName, 'lastName': lastName, 'username': username}, where('chatId') == id)
    else:
        db_users.insert({'chatId': id, 'firstName': firstName, 'lastName': lastName, 'username': username, 'warns': "0"})


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

        if text.startswith("/"):
            bot.deleteMessage((group, msgId))

        if from_id in groupAdmins:
            if text.startswith("/warn @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                previousWarns = int(db_users.search(where('chatId') == selectedUserData)[0]['warns'])
                db_users.update({'warns': str(previousWarns+1)}, where('chatId') == selectedUserData)
                userWarns = int(db_users.search(where('chatId') == selectedUserData)[0]['warns'])
                try:
                    reason = text_split[2]
                    bot.sendMessage(group, str("⚠️ "+selectedUser+" has been warned ["+str(userWarns)+"/3] for <b>"+reason+"</b>."), parse_mode="HTML")
                except IndexError:
                    bot.sendMessage(group, str("⚠️ "+selectedUser+" has been warned ["+str(userWarns)+"/3]."))
                if userWarns >= 3:
                    bot.restrictChatMember(group, selectedUserData, until_date=int(time.time() + 3600))
                    db_users.update({'warns': "0"}, where('chatId') == selectedUserData)
                    bot.sendMessage(group, str("⚠️ "+selectedUser+" has been muted until the next hour."))


            elif text.startswith("/mute @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                bot.restrictChatMember(group, selectedUserData, until_date=int(time.time() + 3600))
                try:
                    reason = text_split[2]
                    bot.sendMessage(group, str("⚠️ "+selectedUser+" has been muted for <b>"+reason+"</b> until the next hour."), parse_mode="HTML")
                except IndexError:
                    bot.sendMessage(group, str("⚠️ "+selectedUser+" has been muted until the next hour."))

            elif text.startswith("/kick @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                bot.kickChatMember(group, selectedUserData)
                time.sleep(0.1)
                bot.unbanChatMember(group, selectedUserData)
                try:
                    reason = text_split[2]
                    bot.sendMessage(group, str("⚠️ "+selectedUser+" has been kicked for <b>"+reason+"</b>."), parse_mode="HTML")
                except IndexError:
                    bot.sendMessage(group, str("⚠️ "+selectedUser+" has been kicked."))

            elif text.startswith("/ban @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                bot.kickChatMember(group, selectedUserData)
                try:
                    reason = text_split[2]
                    bot.sendMessage(group, str("⚠️ "+selectedUser+" has been banned for <b>"+reason+"</b>."), parse_mode="HTML")
                except IndexError:
                    bot.sendMessage(group, str("⚠️ "+selectedUser+" has been banned."))

            elif text.startswith("/tell "):
                text = text.replace("/tell ", "")
                bot.sendMessage(group, text, parse_mode="HTML")

            elif text == "/reload":
                reloadDatabases()
                groupUC = str(bot.getChatMembersCount(group)-1)
                registeredUC = str(db_users.__len__())
                bot.sendMessage(group, "✅ <b>Bot reloaded!</b>\nUsers Found: "+registeredUC+"/"+groupUC+".", "HTML")


initialize()
bot.message_loop({'chat': handle})
while 1:
    time.sleep(1)
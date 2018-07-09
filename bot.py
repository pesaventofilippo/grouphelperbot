import telepot, time, hashlib, requests, os
from tinydb import TinyDB, where
import settings
db_users = TinyDB(settings.Databases.users)
db_admins = TinyDB(settings.Databases.admins)
bot = telepot.Bot(settings.Bot.token)
group = settings.Bot.groupId
myusername = "@" + bot.getMe()['username']


def updateAdminDatabase(id, status):
    if db_admins.search(where('chatId') == id):
        db_admins.update({'status': status}, where('chatId') == id)
    else:
        db_admins.insert({'chatId': id, 'status': status})


def updateUserDatabase(id, firstName, lastName, username):
    if db_users.search(where('chatId') == id):
        db_users.update({'firstName': firstName, 'lastName': lastName, 'username': username}, where('chatId') == id)
    else:
        db_users.insert({'chatId': id, 'firstName': firstName, 'lastName': lastName, 'username': username, 'warns': "0"})


def reloadAdmins():
    for x in bot.getChatAdministrators(group):
        if x['user']['is_bot']:
            updateAdminDatabase(x['user']['id'], "bot")
        elif x['status'] == "administrator":
            updateAdminDatabase(x['user']['id'], "admin")
        elif x['status'] == "creator":
            updateAdminDatabase(x['user']['id'], "creator")


def getUserInfo(msg):
    chatId = msg['chat']['id']
    msgId = msg['message_id']
    from_id = msg['from']['id']
    msgType, x, y = telepot.glance(msg)

    if msgType == "text":
        text = msg['text']
    else:
        text = ""
    try:
        from_firstName = msg['from']['first_name']
    except KeyError:
        from_firstName = ""
    try:
        from_lastName = msg['from']['last_name']
    except KeyError:
        from_lastName = ""
    try:
        from_username = msg['from']['username']
    except KeyError:
        from_username = ""

    try:
        isReply = True
        reply_msgId = msg['reply_to_message']['message_id']
        reply_fromId = msg['reply_to_message']['from']['id']
        try:
            reply_firstName = msg['reply_to_message']['from']['first_name']
        except KeyError:
            reply_firstName = ""
        try:
            reply_lastName = msg['reply_to_message']['from']['last_name']
        except KeyError:
            reply_lastName = ""
        try:
            reply_username = msg['reply_to_message']['from']['username']
        except KeyError:
            reply_username = ""

    except KeyError:
        isReply = False
        reply_msgId = None
        reply_fromId = None
        reply_firstName = None
        reply_lastName = None
        reply_username = None

    return chatId, msgId, msgType, text, from_id, from_firstName, from_lastName, from_username, isReply, reply_msgId, reply_fromId, reply_firstName, reply_lastName, reply_username


def getStatus(chatId):
    try:
        result = db_admins.search(where("chatId") == chatId)[0]['status']
    except IndexError:
        result = "user"
    return result


def handle(msg):
    chatId, msgId, msgType, text,\
    from_id, from_firstName, from_lastName, from_username,\
    isReply, reply_msgId,\
    reply_fromId, reply_firstName, reply_lastName, reply_username = getUserInfo(msg)

    if chatId == group:
        updateUserDatabase(from_id, from_firstName, from_lastName, from_username)

        # Welcoming message
        if msgType == "new_chat_member":
            data = settings.Messages.welcome
            data = data.replace('{{name}}', from_firstName)
            data = data.replace('{{surname}}', from_lastName)
            data = data.replace('{{username}}', from_username)
            data = data.replace('{{id}}', from_id)
            data = data.replace('{{group_name}}', bot.getChat(group)['title'])
            bot.sendMessage(group, data, "HTML")

        elif msgType == "document":
            message = bot.sendMessage(group, "<i>Scanning File...</i>", "HTML")
            bot.download_file(msgId, "file_"+str(msgId))
            file = open("file_"+str(msgId), "rb")
            hash = hashlib.sha256(file.read()).hexdigest()
            data = requests.get(settings.virusTotal.url, params={'apikey': settings.virusTotal.apikey, 'resource': hash}).json()
            file.close()
            os.remove("file_"+str(msgId))
            if data['response_code'] == 1:
                bot.editMessageText((group, message['message_id']), "File Scan:\nAlert " + str(data['positives']) + "/" + str(data['total']))
            else:
                bot.editMessageText((group, message['message_id']), "Could not scan file.")


        # Delete all commands
        if text.startswith("/"):
            bot.deleteMessage((group, msgId))


        # Creator message
        if getStatus(from_id) in ["creator"]:
            if text.startswith("/helper @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if not ((getStatus(selectedUserData) == "creator") or (getStatus(selectedUserData) == "admin")):
                    updateAdminDatabase(selectedUserData, "helper")
                    bot.sendMessage(group, str("⛑ " + selectedUser + " is now <b>Helper</b>."), "HTML")

            elif text.startswith("/unhelper @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if getStatus(selectedUserData) == "helper":
                    db_admins.remove(where('chatId') == selectedUserData)
                    bot.sendMessage(group, str("⛑ " + selectedUser + " removed from <b>Helpers</b>."), "HTML")

            elif text.startswith("/mod @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if not ((getStatus(selectedUserData) == "creator") or (getStatus(selectedUserData) == "admin")):
                    updateAdminDatabase(selectedUserData, "moderator")
                    bot.sendMessage(group, str("👷🏻 " + selectedUser + " is now <b>Moderator</b>."), "HTML")

            elif text.startswith("/unmod @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if getStatus(selectedUserData) == "moderator":
                    db_admins.remove(where('chatId') == selectedUserData)
                    bot.sendMessage(group, str("👷🏻 " + selectedUser + " removed from <b>Moderators</b>."), "HTML")

            elif text.startswith("/manager @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if not ((getStatus(selectedUserData) == "creator") or (getStatus(selectedUserData) == "admin")):
                    updateAdminDatabase(selectedUserData, "manager")
                    bot.sendMessage(group, str("🛃 " + selectedUser + " is now <b>Manager</b>."), "HTML")

            elif text.startswith("/unmanager @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if getStatus(selectedUserData) == "manager":
                    db_admins.remove(where('chatId') == selectedUserData)
                    bot.sendMessage(group, str("🛃 " + selectedUser + " removed from <b>Managers</b>."), "HTML")

            elif isReply:
                if text == "/helper":
                    if not ((getStatus(reply_fromId) == "creator") or (getStatus(reply_fromId) == "admin")):
                        updateAdminDatabase(reply_fromId, "helper")
                        bot.sendMessage(group, str("⛑ " + reply_firstName + " is now <b>Helper</b>."), parse_mode="HTML", reply_to_message_id=reply_msgId)

                elif text == "/unhelper":
                    if getStatus(reply_fromId) == "helper":
                        db_admins.remove(where('chatId') == reply_fromId)
                        bot.sendMessage(group, str("⛑ " + reply_firstName + " removed from <b>Helpers</b>."), parse_mode="HTML", reply_to_message_id=reply_msgId)

                elif text == "/mod":
                    if not ((getStatus(reply_fromId) == "creator") or (getStatus(reply_fromId) == "admin")):
                        updateAdminDatabase(reply_fromId, "moderator")
                        bot.sendMessage(group, str("👷🏻 " + reply_firstName + " is now <b>Moderator</b>."), parse_mode="HTML", reply_to_message_id=reply_msgId)

                elif text == "/unmod":
                    if getStatus(reply_fromId) == "moderator":
                        db_admins.remove(where('chatId') == reply_fromId)
                        bot.sendMessage(group, str("👷🏻 " + reply_firstName + " removed from <b>Moderators</b>."), parse_mode="HTML", reply_to_message_id=reply_msgId)

                elif text == "/manager":
                    if not ((getStatus(reply_fromId) == "creator") or (getStatus(reply_fromId) == "admin")):
                        updateAdminDatabase(reply_fromId, "manager")
                        bot.sendMessage(group, str("🛃 " + reply_firstName + " is now <b>Manager</b>."), parse_mode="HTML", reply_to_message_id=reply_msgId)

                elif text == "/unmanager":
                    if getStatus(reply_fromId) == "manager":
                        db_admins.remove(where('chatId') == reply_fromId)
                        bot.sendMessage(group, str("🛃 " + reply_firstName + " removed from <b>Managers</b>."), parse_mode="HTML", reply_to_message_id=reply_msgId)



        # Creator or Admin message
        if getStatus(from_id) in ["creator", "admin"]:
            if text.startswith("/tell "):
                text_split = text.split(" ", 1)
                bot.sendMessage(group, text_split[1], parse_mode="HTML", reply_to_message_id=reply_msgId)

            elif text == "/reload":
                reloadAdmins()
                bot.sendMessage(group, "✅ <b>Bot reloaded!</b>", "HTML")



        # Creator or Admin or Moderator message
        if getStatus(from_id) in ["creator", "admin", "moderator"]:
            if text.startswith("/warn @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                previousWarns = int(db_users.search(where('chatId') == selectedUserData)[0]['warns'])
                db_users.update({'warns': str(previousWarns + 1)}, where('chatId') == selectedUserData)
                userWarns = int(db_users.search(where('chatId') == selectedUserData)[0]['warns'])
                try:
                    reason = text_split[2]
                    bot.sendMessage(group, str("❗️️ " + selectedUser + " has been warned [" + str(userWarns) + "/" + str(settings.Moderation.maxWarns)+"] for <b>" + reason + "</b>."), parse_mode="HTML")
                except IndexError:
                    bot.sendMessage(group, str("❗️️ " + selectedUser + " has been warned [" + str(userWarns) + "/" + str(settings.Moderation.maxWarns)+"]."))
                if userWarns >= settings.Moderation.maxWarns:
                    bot.kickChatMember(group, selectedUserData)
                    db_users.update({'warns': "0"}, where('chatId') == selectedUserData)
                    bot.sendMessage(group, str("🔇️ " + selectedUser + " has been banned."))

            elif text.startswith("/delwarn @"):
                bot.deleteMessage((group, reply_msgId))
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                previousWarns = int(db_users.search(where('chatId') == selectedUserData)[0]['warns'])
                db_users.update({'warns': str(previousWarns + 1)}, where('chatId') == selectedUserData)
                userWarns = int(db_users.search(where('chatId') == selectedUserData)[0]['warns'])
                try:
                    reason = text_split[2]
                    bot.sendMessage(group, str("❗️️ " + selectedUser + " has been warned [" + str(userWarns) + "/" + str(settings.Moderation.maxWarns)+"] for <b>" + reason + "</b>."), parse_mode="HTML")
                except IndexError:
                    bot.sendMessage(group, str("❗️️ " + selectedUser + " has been warned [" + str(userWarns) + "/" + str(settings.Moderation.maxWarns)+"]."))
                if userWarns >= settings.Moderation.maxWarns:
                    bot.kickChatMember(group, selectedUserData)
                    db_users.update({'warns': "0"}, where('chatId') == selectedUserData)
                    bot.sendMessage(group, str("🔇️ " + selectedUser + " has been banned."))

            elif text.startswith("/mute @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                bot.restrictChatMember(group, selectedUserData, until_date=time.time() + 3600)
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
                time.sleep(0.5)
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
                text_split = text.split(" ", 1)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                bot.restrictChatMember(group, selectedUserData, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
                bot.sendMessage(group, str("🔈 " + selectedUser + " unmuted."))

            elif isReply:
                if text.startswith("/warn"):
                    previousWarns = int(db_users.search(where('chatId') == reply_fromId)[0]['warns'])
                    db_users.update({'warns': str(previousWarns + 1)}, where('chatId') == reply_fromId)
                    userWarns = int(db_users.search(where('chatId') == reply_fromId)[0]['warns'])
                    try:
                        reason = text.split(" ", 1)[1]
                        bot.sendMessage(group, str("❗️️ " + reply_firstName + " has been warned [" + str(userWarns) + "/" + str(settings.Moderation.maxWarns) + "] for <b>" + reason + "</b>."), parse_mode="HTML", reply_to_message_id=reply_msgId)
                    except IndexError:
                        bot.sendMessage(group, str("❗️️ " + reply_firstName + " has been warned [" + str(userWarns) + "/" + str(settings.Moderation.maxWarns) + "]."), reply_to_message_id=reply_msgId)
                    if userWarns >= settings.Moderation.maxWarns:
                        bot.kickChatMember(group, reply_fromId)
                        db_users.update({'warns': "0"}, where('chatId') == reply_fromId)
                        bot.sendMessage(group, str("🔇️ " + reply_firstName + " has been banned."), reply_to_message_id=reply_msgId)

                elif text.startswith("/delwarn"):
                    bot.deleteMessage((group, reply_msgId))
                    previousWarns = int(db_users.search(where('chatId') == reply_fromId)[0]['warns'])
                    db_users.update({'warns': str(previousWarns + 1)}, where('chatId') == reply_fromId)
                    userWarns = int(db_users.search(where('chatId') == reply_fromId)[0]['warns'])
                    try:
                        reason = text.split(" ", 1)[1]
                        bot.sendMessage(group, str("❗️️ " + reply_firstName + " has been warned [" + str(userWarns) + "/" + str(settings.Moderation.maxWarns) + "] for <b>" + reason + "</b>."), parse_mode="HTML")
                    except IndexError:
                        bot.sendMessage(group, str("❗️️ " + reply_firstName + " has been warned [" + str(userWarns) + "/" + str(settings.Moderation.maxWarns) + "]."))
                    if userWarns >= settings.Moderation.maxWarns:
                        bot.kickChatMember(group, reply_fromId)
                        db_users.update({'warns': "0"}, where('chatId') == reply_fromId)
                        bot.sendMessage(group, str("🔇️ " + reply_firstName + " has been banned."))

                elif text.startswith("/mute"):
                    bot.restrictChatMember(group, reply_fromId, until_date=time.time() + 3600)
                    try:
                        reason = text.split(" ", 1)[1]
                        bot.sendMessage(group, str("🔇️ " + reply_firstName + " has been muted for <b>" + reason + "</b> until the next hour."), parse_mode="HTML", reply_to_message_id=reply_msgId)
                    except IndexError:
                        bot.sendMessage(group, str("🔇️ " + reply_firstName + " has been muted until the next hour."), reply_to_message_id=reply_msgId)

                elif text.startswith("/kick"):
                    bot.kickChatMember(group, reply_fromId)
                    time.sleep(0.5)
                    bot.unbanChatMember(group, reply_fromId)
                    try:
                        reason = text.split(" ", 1)[1]
                        bot.sendMessage(group, str("❗️️ "+reply_firstName+" has been kicked for <b>"+reason+"</b>."), parse_mode="HTML", reply_to_message_id=reply_msgId)
                    except IndexError:
                        bot.sendMessage(group, str("❗️️ "+reply_firstName+" has been kicked."), reply_to_message_id=reply_msgId)

                elif text.startswith("/ban"):
                    bot.kickChatMember(group, reply_fromId)
                    try:
                        reason = text.split(" ", 1)[1]
                        bot.sendMessage(group, str("🚷 "+reply_firstName+" has been banned for <b>"+reason+"</b>."), parse_mode="HTML", reply_to_message_id=reply_msgId)
                    except IndexError:
                        bot.sendMessage(group, str("🚷 "+reply_firstName+" has been banned."), reply_to_message_id=reply_msgId)

                elif text.startswith("/unban"):
                    bot.unbanChatMember(group, reply_fromId)
                    bot.sendMessage(group, "✅️ "+str(reply_firstName)+" unbanned.", reply_to_message_id=reply_msgId)

                elif text.startswith("/unwarn"):
                    previousWarns = int(db_users.search(where('chatId') == reply_fromId)[0]['warns'])
                    if previousWarns > 0:
                        db_users.update({'warns': str(previousWarns-1)}, where('chatId') == reply_fromId)
                        bot.sendMessage(group, "❎ "+reply_firstName+" unwarned.\nHe now has "+str(previousWarns-1)+" warns.", reply_to_message_id=reply_msgId)

                elif text.startswith("/unmute"):
                    bot.restrictChatMember(group, reply_fromId, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
                    bot.sendMessage(group, str("🔈 " + reply_firstName + " unmuted."), reply_to_message_id=reply_msgId)



        # Creator or Admin or Moderator or Manager message
        if getStatus(from_id) in ["creator", "admin", "moderator", "manager"]:
            if isReply:
                if text == "/del":
                    bot.deleteMessage((group, reply_msgId))



        # Normal user message
        cmdtext = text.replace(myusername, "")
        if cmdtext == "/staff":
            message = "🔰️ <b>GROUP STAFF</b> 🔰️"

            message += "\n\n  👑 <b>Founder</b>"
            for x in [x["chatId"] for x in db_admins.search(where('status') == "creator")]:
                try:
                    message += "\n        @" + bot.getChatMember(group, x)['user']['username']
                except KeyError:
                    message += "\n        " + bot.getChatMember(group, x)['user']['first_name']

            message += "\n\n  👮🏼 <b>Admins</b>"
            for x in [x["chatId"] for x in db_admins.search(where('status') == "admin")]:
                try:
                    message += "\n        @" + bot.getChatMember(group, x)['user']['username']
                except KeyError:
                    message += "\n        " + bot.getChatMember(group, x)['user']['first_name']

            message += "\n\n  👷🏻 <b>Moderators</b>"
            for x in [x["chatId"] for x in db_admins.search(where('status') == "moderator")]:
                try:
                    message += "\n        @" + bot.getChatMember(group, x)['user']['username']
                except KeyError:
                    message += "\n        " + bot.getChatMember(group, x)['user']['first_name']

            message += "\n\n  🛃 <b>Managers</b>"
            for x in [x["chatId"] for x in db_admins.search(where('status') == "manager")]:
                try:
                    message += "\n        @" + bot.getChatMember(group, x)['user']['username']
                except KeyError:
                    message += "\n        " + bot.getChatMember(group, x)['user']['first_name']

            message += "\n\n  ⛑ <b>Helpers</b>"
            for x in [x["chatId"] for x in db_admins.search(where('status') == "helper")]:
                try:
                    message += "\n        @" + bot.getChatMember(group, x)['user']['username']
                except KeyError:
                    message += "\n        " + bot.getChatMember(group, x)['user']['first_name']

            bot.sendMessage(group, message, parse_mode="HTML")


print("Bot started...")
reloadAdmins()
bot.message_loop({'chat': handle})
while True:
    time.sleep(60)
import telepot, time, hashlib, requests, os
from tinydb import TinyDB, where
from sightengine.client import SightengineClient
import settings

db_users = TinyDB(settings.Databases.users)
db_admins = TinyDB(settings.Databases.admins)
bot = telepot.Bot(settings.Bot.token)
group = settings.Bot.groupId
myusername = "@" + bot.getMe()['username']
imgparse_ai = SightengineClient(settings.sightEngine.user, settings.sightEngine.key)


def updateAdminDatabase(id, status):
    if db_admins.search(where('chatId') == id):
        db_admins.update({'status': status}, where('chatId') == id)
    else:
        db_admins.insert({'chatId': id, 'status': status})


def updateUserDatabase(id, firstName, lastName, username):
    if db_users.search(where('chatId') == id):
        db_users.update({'firstName': firstName, 'lastName': lastName, 'username': username, 'lastMsgDate': int(time.time())}, where('chatId') == id)
    else:
        db_users.insert({'chatId': id, 'firstName': firstName, 'lastName': lastName, 'username': username, 'warns': "0", 'lastMsgDate': int(time.time())})


def reloadAdmins():
    db_admins.remove(where('status') == "admin")
    for x in bot.getChatAdministrators(group):
        if not x['user']['is_bot']:
            if x['status'] == "administrator":
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


def logStaff(message):
    if settings.Bot.useStaffGroup:
        try:
            bot.sendMessage(settings.Bot.staffGroupId, message, "HTML")
        except Exception:
            pass


def handle(msg):
    chatId, msgId, msgType, text,\
    from_id, from_firstName, from_lastName, from_username,\
    isReply, reply_msgId,\
    reply_fromId, reply_firstName, reply_lastName, reply_username = getUserInfo(msg)

    if chatId == group:
        updateUserDatabase(from_id, from_firstName, from_lastName, from_username)


        # Welcoming message
        if msgType == "new_chat_member":
            if settings.Moderation.showWelcomeMessage:
                data = settings.Messages.welcome
                if data != "":
                    data = data.replace('{{name}}', from_firstName)
                    data = data.replace('{{surname}}', from_lastName)
                    data = data.replace('{{username}}', from_username)
                    data = data.replace('{{group_name}}', bot.getChat(group)['title'])
                    bot.sendMessage(group, data, parse_mode="HTML", disable_link_preview=True)
            logStaff('''➕ <b>New User</b>\n-> <a href="tg://user?id='''+str(from_id)+'''">'''+from_firstName+"</a>")


        # Delete all commands
        if text.startswith("/"):
            if settings.Moderation.deleteCommands:
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
                    logStaff("⛑ <b>New Helper</b>\nTo: " + selectedUser+"\nBy: "+from_firstName+" "+from_lastName)

            elif text.startswith("/unhelper @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if getStatus(selectedUserData) == "helper":
                    db_admins.remove(where('chatId') == selectedUserData)
                    bot.sendMessage(group, str("⛑ " + selectedUser + " removed from <b>Helpers</b>."), "HTML")
                    logStaff("⛑ <b>Removed Helper</b>\nTo: " + selectedUser+"\nBy: "+from_firstName+" "+from_lastName)

            elif text.startswith("/mod @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if not ((getStatus(selectedUserData) == "creator") or (getStatus(selectedUserData) == "admin")):
                    updateAdminDatabase(selectedUserData, "moderator")
                    bot.sendMessage(group, str("👷🏻 " + selectedUser + " is now <b>Moderator</b>."), "HTML")
                    logStaff("👷🏻 <b>New Moderator</b>\nTo: " + selectedUser+"\nBy: "+from_firstName+" "+from_lastName)

            elif text.startswith("/unmod @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if getStatus(selectedUserData) == "moderator":
                    db_admins.remove(where('chatId') == selectedUserData)
                    bot.sendMessage(group, str("👷🏻 " + selectedUser + " removed from <b>Moderators</b>."), "HTML")
                    logStaff("👷🏻 <b>Removed Moderator</b>\nTo: " + selectedUser+"\nBy: "+from_firstName+" "+from_lastName)

            elif text.startswith("/manager @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if not ((getStatus(selectedUserData) == "creator") or (getStatus(selectedUserData) == "admin")):
                    updateAdminDatabase(selectedUserData, "manager")
                    bot.sendMessage(group, str("🛃 " + selectedUser + " is now <b>Manager</b>."), "HTML")
                    logStaff("🛃 <b>New Manager</b>\nTo: " + selectedUser+"\nBy: "+from_firstName+" "+from_lastName)

            elif text.startswith("/unmanager @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if getStatus(selectedUserData) == "manager":
                    db_admins.remove(where('chatId') == selectedUserData)
                    bot.sendMessage(group, str("🛃 " + selectedUser + " removed from <b>Managers</b>."), "HTML")
                    logStaff("🛃 <b>Removed Manager</b>\nTo: " + selectedUser+"\nBy: "+from_firstName+" "+from_lastName)

            elif isReply:
                if text == "/helper":
                    if not ((getStatus(reply_fromId) == "creator") or (getStatus(reply_fromId) == "admin")):
                        updateAdminDatabase(reply_fromId, "helper")
                        bot.sendMessage(group, str("⛑ " + reply_firstName + " is now <b>Helper</b>."), parse_mode="HTML", reply_to_message_id=reply_msgId)
                        logStaff('''⛑ <b>New Helper</b>\nTo: <a href="tg://user?id=''' + str(reply_fromId) + '''">''' + reply_firstName + "</a>\nBy: "+from_firstName+" "+from_lastName)

                elif text == "/unhelper":
                    if getStatus(reply_fromId) == "helper":
                        db_admins.remove(where('chatId') == reply_fromId)
                        bot.sendMessage(group, str("⛑ " + reply_firstName + " removed from <b>Helpers</b>."), parse_mode="HTML", reply_to_message_id=reply_msgId)
                        logStaff('''⛑ <b>Removed Helper</b>\nTo: <a href="tg://user?id=''' + str(reply_fromId) + '''">''' + reply_firstName + "</a>\nBy: "+from_firstName+" "+from_lastName)

                elif text == "/mod":
                    if not ((getStatus(reply_fromId) == "creator") or (getStatus(reply_fromId) == "admin")):
                        updateAdminDatabase(reply_fromId, "moderator")
                        bot.sendMessage(group, str("👷🏻 " + reply_firstName + " is now <b>Moderator</b>."), parse_mode="HTML", reply_to_message_id=reply_msgId)
                        logStaff('''👷🏻 <b>New Moderator</b>\nTo: <a href="tg://user?id=''' + str(reply_fromId) + '''">''' + reply_firstName + "</a>\nBy: "+from_firstName+" "+from_lastName)

                elif text == "/unmod":
                    if getStatus(reply_fromId) == "moderator":
                        db_admins.remove(where('chatId') == reply_fromId)
                        bot.sendMessage(group, str("👷🏻 " + reply_firstName + " removed from <b>Moderators</b>."), parse_mode="HTML", reply_to_message_id=reply_msgId)
                        logStaff('''👷🏻 <b>Removed Moderator</b>\nTo: <a href="tg://user?id=''' + str(reply_fromId) + '''">''' + reply_firstName + "</a>\nBy: "+from_firstName+" "+from_lastName)

                elif text == "/manager":
                    if not ((getStatus(reply_fromId) == "creator") or (getStatus(reply_fromId) == "admin")):
                        updateAdminDatabase(reply_fromId, "manager")
                        bot.sendMessage(group, str("🛃 " + reply_firstName + " is now <b>Manager</b>."), parse_mode="HTML", reply_to_message_id=reply_msgId)
                        logStaff('''🛃 <b>New Manager</b>\nTo: <a href="tg://user?id=''' + str(reply_fromId) + '''">''' + reply_firstName + "</a>\nBy: "+from_firstName+" "+from_lastName)

                elif text == "/unmanager":
                    if getStatus(reply_fromId) == "manager":
                        db_admins.remove(where('chatId') == reply_fromId)
                        bot.sendMessage(group, str("🛃 " + reply_firstName + " removed from <b>Managers</b>."), parse_mode="HTML", reply_to_message_id=reply_msgId)
                        logStaff('''🛃 <b>Removed Manager</b>\nTo: <a href="tg://user?id=''' + str(reply_fromId) + '''">''' + reply_firstName + "</a>\nBy: "+from_firstName+" "+from_lastName)



        # Creator or Admin message
        if getStatus(from_id) in ["creator", "admin"]:
            if text.startswith("/tell "):
                text_split = text.split(" ", 1)
                bot.sendMessage(group, text_split[1], parse_mode="HTML", reply_to_message_id=reply_msgId)

            elif text == "/reload":
                reloadAdmins()
                bot.sendMessage(group, "✅ <b>Bot reloaded!</b>", "HTML")
                logStaff("✅ <b>Bot reloaded!</b>\nBy: "+from_firstName+" "+from_lastName)

            elif text.startswith("/kickinactive "):
                text_split = text.split(" ")
                days = int(text_split[1])
                currentTime = int(time.time())
                diffTime = days*24*60*60
                lastTime = currentTime - diffTime
                kick_users = db_users.search(where('lastMsgDate')<lastTime)
                logStaff("☢️ <b>Inactive Users Kick</b>\nStarted by: "+from_firstName+" "+from_lastName+"\nMax. Inactive days: "+days)
                for x in kick_users:
                    try:
                        bot.kickChatMember(group, x['chatId'])
                        time.sleep(0.5)
                        bot.unbanChatMember(group, x['chatId'])
                    except Exception:
                        pass
                logStaff("☢️ <b>Inactive Users Kick terminated!</b>")


        # Creator or Admin or Moderator message
        if getStatus(from_id) in ["creator", "admin", "moderator"]:
            if text.startswith("/warn @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if not ((getStatus(selectedUserData) == "creator") or (getStatus(selectedUserData) == "admin")):
                    previousWarns = int(db_users.search(where('chatId') == selectedUserData)[0]['warns'])
                    db_users.update({'warns': str(previousWarns + 1)}, where('chatId') == selectedUserData)
                    userWarns = int(db_users.search(where('chatId') == selectedUserData)[0]['warns'])
                    try:
                        reason = text_split[2]
                        bot.sendMessage(group, str("❗️️ " + selectedUser + " has been warned [" + str(userWarns) + "/" + str(settings.Moderation.maxWarns)+"] for <b>" + reason + "</b>."), parse_mode="HTML")
                        logStaff("❗️ <b>Warn</b>\nTo: " + selectedUser + "\nBy: " + from_firstName + " " + from_lastName+"\nReason: "+reason+"\nUser Warns Now: "+str(userWarns)+"/"+str(settings.Moderation.maxWarns))
                    except IndexError:
                        bot.sendMessage(group, str("❗️️ " + selectedUser + " has been warned [" + str(userWarns) + "/" + str(settings.Moderation.maxWarns)+"]."))
                        logStaff("❗️ <b>Warn</b>\nTo: " + selectedUser + "\nBy: " + from_firstName + " " + from_lastName + "\nUser Warns Now: " + str(userWarns) + "/" + str(settings.Moderation.maxWarns))
                    if userWarns >= settings.Moderation.maxWarns:
                        bot.kickChatMember(group, selectedUserData)
                        db_users.update({'warns': "0"}, where('chatId') == selectedUserData)
                        bot.sendMessage(group, str("🚷 " + selectedUser + " has been banned."))
                        logStaff("🚷 <b>Ban</b>\nTo: " + selectedUser + "\nBy: Bot\nReason: Exceeded max warns")

            elif text.startswith("/delwarn @"):
                bot.deleteMessage((group, reply_msgId))
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if not ((getStatus(selectedUserData) == "creator") or (getStatus(selectedUserData) == "admin")):
                    previousWarns = int(db_users.search(where('chatId') == selectedUserData)[0]['warns'])
                    db_users.update({'warns': str(previousWarns + 1)}, where('chatId') == selectedUserData)
                    userWarns = int(db_users.search(where('chatId') == selectedUserData)[0]['warns'])
                    try:
                        reason = text_split[2]
                        bot.sendMessage(group, str("❗️ " + selectedUser + " has been warned [" + str(userWarns) + "/" + str(settings.Moderation.maxWarns)+"] for <b>" + reason + "</b>."), parse_mode="HTML")
                        logStaff("❗️ <b>Warn</b>\nTo: " + selectedUser + "\nBy: " + from_firstName + " " + from_lastName + "\nReason: " + reason + "\nUser Warns Now: " + str(userWarns) + "/" + str(settings.Moderation.maxWarns))
                    except IndexError:
                        bot.sendMessage(group, str("❗️ " + selectedUser + " has been warned [" + str(userWarns) + "/" + str(settings.Moderation.maxWarns)+"]."))
                        logStaff("❗️ <b>Warn</b>\nTo: " + selectedUser + "\nBy: " + from_firstName + " " + from_lastName + "\nUser Warns Now: " + str(userWarns) + "/" + str(settings.Moderation.maxWarns))
                    if userWarns >= settings.Moderation.maxWarns:
                        bot.kickChatMember(group, selectedUserData)
                        db_users.update({'warns': "0"}, where('chatId') == selectedUserData)
                        bot.sendMessage(group, str("🚷 " + selectedUser + " has been banned."))
                        logStaff("🚷 <b>Ban</b>\nTo: " + selectedUser + "\nBy: Bot\nReason: Exceeded max warns")

            elif text.startswith("/mute @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if not ((getStatus(selectedUserData) == "creator") or (getStatus(selectedUserData) == "admin")):
                    bot.restrictChatMember(group, selectedUserData, until_date=time.time() + 3600)
                    try:
                        reason = text_split[2]
                        bot.sendMessage(group, str("🔇 " + selectedUser + " has been muted for <b>" + reason + "</b> until the next hour."), parse_mode="HTML")
                        logStaff("🔇 <b>Mute</b>\nTo: " + selectedUser + "\nBy: " + from_firstName + " " + from_lastName + "\nReason: " + reason)
                    except IndexError:
                        bot.sendMessage(group, str("🔇 " + selectedUser + " has been muted until the next hour."))
                        logStaff("🔇 <b>Mute</b>\nTo: " + selectedUser + "\nBy: " + from_firstName + " " + from_lastName)

            elif text.startswith("/kick @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if not ((getStatus(selectedUserData) == "creator") or (getStatus(selectedUserData) == "admin")):
                    try:
                        bot.kickChatMember(group, selectedUserData)
                        time.sleep(0.5)
                        bot.unbanChatMember(group, selectedUserData)
                    except:
                        pass
                    try:
                        reason = text_split[2]
                        bot.sendMessage(group, str("❕ "+selectedUser+" has been kicked for <b>"+reason+"</b>."), parse_mode="HTML")
                        logStaff("❕ <b>Kick</b>\nTo: " + selectedUser + "\nBy: " + from_firstName + " " + from_lastName + "\nReason: " + reason)
                    except IndexError:
                        bot.sendMessage(group, str("❕ "+selectedUser+" has been kicked."))
                        logStaff("❕ <b>Kick</b>\nTo: " + selectedUser + "\nBy: " + from_firstName + " " + from_lastName)

            elif text.startswith("/ban @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if not ((getStatus(selectedUserData) == "creator") or (getStatus(selectedUserData) == "admin")):
                    bot.kickChatMember(group, selectedUserData)
                    db_users.update({'warns': "0"}, where('chatId') == selectedUserData)
                    try:
                        reason = text_split[2]
                        bot.sendMessage(group, str("🚷 "+selectedUser+" has been banned for <b>"+reason+"</b>."), parse_mode="HTML")
                        logStaff("🚷 <b>Ban</b>\nTo: " + selectedUser + "\nBy: " + from_firstName + " " + from_lastName + "\nReason: " + reason)
                    except IndexError:
                        bot.sendMessage(group, str("🚷 "+selectedUser+" has been banned."))
                        logStaff("🚷 <b>Ban</b>\nTo: " + selectedUser + "\nBy: " + from_firstName + " " + from_lastName)

            elif text.startswith("/unban @"):
                text_split = text.split(" ", 1)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                bot.unbanChatMember(group, selectedUserData)
                bot.sendMessage(group, "✅ "+str(selectedUser)+" unbanned.")
                logStaff("✅ <b>Unban</b>\nTo: " + selectedUser + "\nBy: " + from_firstName + " " + from_lastName)

            elif text.startswith("/unwarn @"):
                text_split = text.split(" ", 1)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                previousWarns = int(db_users.search(where('chatId') == selectedUserData)[0]['warns'])
                if previousWarns > 0:
                    db_users.update({'warns': str(previousWarns-1)}, where('chatId') == selectedUserData)
                    bot.sendMessage(group, "❎ "+str(selectedUser)+" unwarned.\nHe now has "+str(previousWarns-1)+" warns.")
                    logStaff("❎ <b>Unwarn</b>\nTo: " + selectedUser + "\nBy: " + from_firstName + " " + from_lastName + "\nUser Warns Now: " + str(previousWarns-1) + "/" + str(settings.Moderation.maxWarns))

            elif text.startswith("/unmute @"):
                text_split = text.split(" ", 1)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                bot.restrictChatMember(group, selectedUserData, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
                bot.sendMessage(group, str("🔊 " + selectedUser + " unmuted."))
                logStaff("🔊 <b>Unmute</b>\nTo: " + selectedUser + "\nBy: " + from_firstName + " " + from_lastName)

            elif text.startswith("/info @"):
                text_split = text.split(" ", 1)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                bot.sendMessage(group, "🙍‍♂️ <b>User Info</b>\nUser: "+selectedUser+"\nChatID: <code>"+str(selectedUserData)+"</code>\nWarns: "+str(db_users.search(where('chatId') == selectedUserData)[0]['warns']), "HTML")

            elif isReply:
                if text.startswith("/warn"):
                    if not ((getStatus(reply_fromId) == "creator") or (getStatus(reply_fromId) == "admin")):
                        previousWarns = int(db_users.search(where('chatId') == reply_fromId)[0]['warns'])
                        db_users.update({'warns': str(previousWarns + 1)}, where('chatId') == reply_fromId)
                        userWarns = int(db_users.search(where('chatId') == reply_fromId)[0]['warns'])
                        try:
                            reason = text.split(" ", 1)[1]
                            bot.sendMessage(group, str("❗️ " + reply_firstName + " has been warned [" + str(userWarns) + "/" + str(settings.Moderation.maxWarns) + "] for <b>" + reason + "</b>."), parse_mode="HTML", reply_to_message_id=reply_msgId)
                            logStaff('''❗️ <b>Warn</b>\nTo: <a href="tg://user?id=''' + str(reply_fromId) + '''">''' + reply_firstName + "</a>\nBy: " + from_firstName + " " + from_lastName+"\nReason: "+reason+"\nUser Warns Now: "+str(userWarns)+"/"+str(settings.Moderation.maxWarns))
                        except IndexError:
                            bot.sendMessage(group, str("❗️️ " + reply_firstName + " has been warned [" + str(userWarns) + "/" + str(settings.Moderation.maxWarns) + "]."), reply_to_message_id=reply_msgId)
                            logStaff('''❗️ <b>Warn</b>\nTo: <a href="tg://user?id=''' + str(reply_fromId) + '''">''' + reply_firstName + "</a>\nBy: " + from_firstName + " " + from_lastName+"\nUser Warns Now: "+str(userWarns)+"/"+str(settings.Moderation.maxWarns))
                        if userWarns >= settings.Moderation.maxWarns:
                            bot.kickChatMember(group, reply_fromId)
                            db_users.update({'warns': "0"}, where('chatId') == reply_fromId)
                            bot.sendMessage(group, str("🚷 " + reply_firstName + " has been banned."), reply_to_message_id=reply_msgId)
                            logStaff('''🚷 <b>Ban</b>\nTo: <a href="tg://user?id=''' + str(reply_fromId) + '''">''' + reply_firstName + "</a>\nBy: Bot\nReason: Exceeded max warns")

                elif text.startswith("/delwarn"):
                    if not ((getStatus(reply_fromId) == "creator") or (getStatus(reply_fromId) == "admin")):
                        bot.deleteMessage((group, reply_msgId))
                        previousWarns = int(db_users.search(where('chatId') == reply_fromId)[0]['warns'])
                        db_users.update({'warns': str(previousWarns + 1)}, where('chatId') == reply_fromId)
                        userWarns = int(db_users.search(where('chatId') == reply_fromId)[0]['warns'])
                        try:
                            reason = text.split(" ", 1)[1]
                            bot.sendMessage(group, str("❗️ " + reply_firstName + " has been warned [" + str(userWarns) + "/" + str(settings.Moderation.maxWarns) + "] for <b>" + reason + "</b>."), parse_mode="HTML")
                            logStaff('''❗️ <b>Warn</b>\nTo: <a href="tg://user?id=''' + str(reply_fromId) + '''">''' + reply_firstName + "</a>\nBy: " + from_firstName + " " + from_lastName+"\nReason: "+reason+"\nUser Warns Now: "+str(userWarns)+"/"+str(settings.Moderation.maxWarns))
                        except IndexError:
                            bot.sendMessage(group, str("❗️ " + reply_firstName + " has been warned [" + str(userWarns) + "/" + str(settings.Moderation.maxWarns) + "]."))
                            logStaff('''❗️ <b>Warn</b>\nTo: <a href="tg://user?id=''' + str(reply_fromId) + '''">''' + reply_firstName + "</a>\nBy: " + from_firstName + " " + from_lastName+"\nUser Warns Now: "+str(userWarns)+"/"+str(settings.Moderation.maxWarns))
                        if userWarns >= settings.Moderation.maxWarns:
                            bot.kickChatMember(group, reply_fromId)
                            db_users.update({'warns': "0"}, where('chatId') == reply_fromId)
                            bot.sendMessage(group, str("🚷 " + reply_firstName + " has been banned."))
                            logStaff('''🚷 <b>Ban</b>\nTo: <a href="tg://user?id=''' + str(reply_fromId) + '''">''' + reply_firstName + "</a>\nBy: Bot\nReason: Exceeded max warns")

                elif text.startswith("/mute"):
                    if not ((getStatus(reply_fromId) == "creator") or (getStatus(reply_fromId) == "admin")):
                        bot.restrictChatMember(group, reply_fromId, until_date=time.time() + 3600)
                        try:
                            reason = text.split(" ", 1)[1]
                            bot.sendMessage(group, str("🔇 " + reply_firstName + " has been muted for <b>" + reason + "</b> until the next hour."), parse_mode="HTML", reply_to_message_id=reply_msgId)
                            logStaff('''🔇 <b>Mute</b>\nTo: <a href="tg://user?id=''' + str(reply_fromId) + '''">''' + reply_firstName + "</a>\nBy: " + from_firstName + " " + from_lastName+"\nReason: "+reason)
                        except IndexError:
                            bot.sendMessage(group, str("🔇 " + reply_firstName + " has been muted until the next hour."), reply_to_message_id=reply_msgId)
                            logStaff('''🔇 <b>Mute</b>\nTo: <a href="tg://user?id=''' + str(reply_fromId) + '''">''' + reply_firstName + "</a>\nBy: " + from_firstName + " " + from_lastName)

                elif text.startswith("/kick"):
                    if not ((getStatus(reply_fromId) == "creator") or (getStatus(reply_fromId) == "admin")):
                        try:
                            bot.kickChatMember(group, reply_fromId)
                            time.sleep(0.5)
                            bot.unbanChatMember(group, reply_fromId)
                        except Exception:
                            pass
                        try:
                            reason = text.split(" ", 1)[1]
                            bot.sendMessage(group, str("❕ "+reply_firstName+" has been kicked for <b>"+reason+"</b>."), parse_mode="HTML", reply_to_message_id=reply_msgId)
                            logStaff('''❕ <b>Kick</b>\nTo: <a href="tg://user?id=''' + str(reply_fromId) + '''">''' + reply_firstName + "</a>\nBy: " + from_firstName + " " + from_lastName+"\nReason: "+reason)
                        except IndexError:
                            bot.sendMessage(group, str("❕ "+reply_firstName+" has been kicked."), reply_to_message_id=reply_msgId)
                            logStaff('''❕ <b>Kick</b>\nTo: <a href="tg://user?id=''' + str(reply_fromId) + '''">''' + reply_firstName + "</a>\nBy: " + from_firstName + " " + from_lastName)

                elif text.startswith("/ban"):
                    if not ((getStatus(reply_fromId) == "creator") or (getStatus(reply_fromId) == "admin")):
                        bot.kickChatMember(group, reply_fromId)
                        db_users.update({'warns': "0"}, where('chatId') == reply_fromId)
                        try:
                            reason = text.split(" ", 1)[1]
                            bot.sendMessage(group, str("🚷 "+reply_firstName+" has been banned for <b>"+reason+"</b>."), parse_mode="HTML", reply_to_message_id=reply_msgId)
                            logStaff('''🚷 <b>Ban</b>\nTo: <a href="tg://user?id=''' + str(reply_fromId) + '''">''' + reply_firstName + "</a>\nBy: " + from_firstName + " " + from_lastName+"\nReason: "+reason)
                        except IndexError:
                            bot.sendMessage(group, str("🚷 "+reply_firstName+" has been banned."), reply_to_message_id=reply_msgId)
                            logStaff('''🚷 <b>Ban</b>\nTo: <a href="tg://user?id=''' + str(reply_fromId) + '''">''' + reply_firstName + "</a>\nBy: " + from_firstName + " " + from_lastName)

                elif text.startswith("/unban"):
                    bot.unbanChatMember(group, reply_fromId)
                    bot.sendMessage(group, "✅ "+str(reply_firstName)+" unbanned.", reply_to_message_id=reply_msgId)
                    logStaff('''✅ <b>Unban</b>\nTo: <a href="tg://user?id=''' + str(reply_fromId) + '''">''' + reply_firstName + "</a>\nBy: " + from_firstName + " " + from_lastName)

                elif text.startswith("/unwarn"):
                    previousWarns = int(db_users.search(where('chatId') == reply_fromId)[0]['warns'])
                    if previousWarns > 0:
                        db_users.update({'warns': str(previousWarns-1)}, where('chatId') == reply_fromId)
                        bot.sendMessage(group, "❎ "+reply_firstName+" unwarned.\nHe now has "+str(previousWarns-1)+" warns.", reply_to_message_id=reply_msgId)
                        logStaff('''❎ <b>Unwarn</b>\nTo: <a href="tg://user?id=''' + str(reply_fromId) + '''">''' + reply_firstName + "</a>\nBy: " + from_firstName + " " + from_lastName)

                elif text.startswith("/unmute"):
                    bot.restrictChatMember(group, reply_fromId, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
                    bot.sendMessage(group, str("🔊 " + reply_firstName + " unmuted."), reply_to_message_id=reply_msgId)
                    logStaff('''🔊 <b>Unmute</b>\nTo: <a href="tg://user?id=''' + str(reply_fromId) + '''">''' + reply_firstName + "</a>\nBy: " + from_firstName + " " + from_lastName)

                elif text.startswith("/info"):
                    bot.sendMessage(group, "🙍‍♂️ <b>User Info</b>\nUser: "+reply_firstName+"\nChatID: <code>"+str(reply_fromId)+"</code>\nWarns: "+str(db_users.search(where('chatId') == reply_fromId)[0]['warns']), "HTML")


        # Creator or Admin or Moderator or Manager message
        if getStatus(from_id) in ["creator", "admin", "moderator", "manager"]:
            if isReply:
                if text == "/del":
                    if not ((getStatus(reply_fromId) == "creator") or (getStatus(reply_fromId) == "admin")):
                        bot.deleteMessage((group, reply_msgId))



        # Any user message
        cmdtext = text.replace(myusername, "")
        if "@admin" in text:
            if settings.Bot.useStaffGroup:
                bot.sendMessage(group, "🆘 <i>Call received.</i>", "HTML")
                if isReply:
                    logStaff('''🆘 <b>Staff Call</b>\nBy: <a href="tg://user?id=''' + str(from_id) + '''">''' + from_firstName + '''</a>\nTo: <a href="tg://user?id=''' + str(reply_fromId) + '''">''' + reply_firstName + "</a>\nMessage: "+text)
                    try:
                        bot.forwardMessage(settings.Bot.staffGroupId, group, reply_msgId)
                    except Exception:
                        pass
                else:
                    logStaff('''🆘 <b>Staff Call</b>\nBy: <a href="tg://user?id=''' + str(from_id) + '''">''' + from_firstName + "</a>\nMessage: " + text)

        elif cmdtext == "/staff":
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

        elif cmdtext == "/rules":
            data = settings.Messages.rules
            if data != "":
                bot.sendMessage(group, data, parse_mode="HTML", disable_web_page_preview=True)


        # Only Normal User Messages
        elif getStatus(from_id) == "user":

            # Control username
            if settings.Moderation.mustHaveUsername:
                if from_username == "":
                    bot.sendMessage(group, "🌐 "+from_firstName+", please, set an <b>username</b> in Telegram Settings", parse_mode="HTML", reply_to_message_id=msgId)

            # Detect spam from a Telegram Link
            if ("t.me/" in text) or ("t.dog/" in text) or ("telegram.me/" in text):
                if settings.Moderation.spamDetect:
                    bot.deleteMessage((group, msgId))
                    previousWarns = int(db_users.search(where('chatId') == from_id)[0]['warns'])
                    db_users.update({'warns': str(previousWarns + 1)}, where('chatId') == from_id)
                    userWarns = int(db_users.search(where('chatId') == from_id)[0]['warns'])
                    bot.sendMessage(group, str("❗️ " + from_firstName + " has been warned [" + str(userWarns) + "/" + str(settings.Moderation.maxWarns) + "] for <b>spam</b>."), parse_mode="HTML")
                    logStaff("❗️ <b>Warn</b>\nTo: " + from_firstName + "\nBy: Bot\nReason: Spam\nUser Warns Now: " + str(userWarns) + "/" + str(settings.Moderation.maxWarns))
                    if userWarns >= settings.Moderation.maxWarns:
                        bot.kickChatMember(group, from_id)
                        db_users.update({'warns': "0"}, where('chatId') == from_id)
                        bot.sendMessage(group, str("🚷 " + from_firstName + " has been banned."))
                        logStaff("🚷 <b>Ban</b>\nTo: " + from_firstName + "\nBy: Bot\nReason: Exceeded max warns")

            # Scan Sended Files
            if msgType == "document":
                if settings.Moderation.scanSendedFiles:
                    message = bot.sendMessage(group, "<i>Scanning File...</i>", parse_mode="HTML", reply_to_message_id=msgId)
                    bot.download_file(msg['document']['file_id'], "file_"+str(msgId))
                    file = open("file_"+str(msgId), "rb")
                    hash = hashlib.sha256(file.read()).hexdigest()
                    data = requests.get(settings.virusTotal.url, params={'apikey': settings.virusTotal.apikey, 'resource': hash}).json()
                    file.close()
                    os.remove("file_"+str(msgId))
                    if data['response_code'] == 1:
                        if data['positives'] == 0:
                            bot.editMessageText((group, message['message_id']), "✅ File Scan: Safe\nAlert " + str(data['positives']) + "/" + str(data['total']))
                        elif data['positives'] < 10:
                            bot.editMessageText((group, message['message_id']), "⚠️ File Scan: Warning\nAlert " + str(data['positives']) + "/" + str(data['total']))
                        else:
                            bot.editMessageText((group, message['message_id']), "🛑️ File Scan: Malware\nAlert " + str(data['positives']) + "/" + str(data['total']))
                    else:
                        bot.deleteMessage((group, message['message_id']))

            # Detect spam from a fowarded message
            if settings.Moderation.forwardSpamDetect:
                try:
                    forwarded_from = msg['forward_from_chat']
                    if forwarded_from['type'] == "channel":
                        if forwarded_from['username'] not in settings.Moderation.channelsWhitelist:
                            bot.deleteMessage((group, msgId))
                            previousWarns = int(db_users.search(where('chatId') == from_id)[0]['warns'])
                            db_users.update({'warns': str(previousWarns + 1)}, where('chatId') == from_id)
                            userWarns = int(db_users.search(where('chatId') == from_id)[0]['warns'])
                            bot.sendMessage(group, str("❗️ " + from_firstName + " has been warned [" + str(userWarns) + "/" + str(settings.Moderation.maxWarns) + "] for <b>forward from a non whitelisted channel</b>."), parse_mode="HTML")
                            logStaff("❗️ <b>Warn</b>\nTo: " + from_firstName + "\nBy: Bot\nReason: Forward from a non whitelisted channel\nUser Warns Now: " + str(userWarns) + "/" + str(settings.Moderation.maxWarns))
                            if userWarns >= settings.Moderation.maxWarns:
                                bot.kickChatMember(group, from_id)
                                db_users.update({'warns': "0"}, where('chatId') == from_id)
                                bot.sendMessage(group, str("🚷 " + from_firstName + " has been banned."))
                                logStaff("🚷 <b>Ban</b>\nTo: " + from_firstName + "\nBy: Bot\nReason: Exceeded max warns")
                except KeyError:
                    pass

            # Porn and violence auto-detect engine
            if msgType == "photo":
                found = False
                bot.download_file(msg['photo'][0]['file_id'], "file_" + str(msgId))

                if settings.Moderation.detectPorn and not found:
                    output = imgparse_ai.check("nudity").set_file("file_" + str(msgId))
                    if output["nudity"]["partial"] > 0.4 or output["nudity"]["raw"] > 0.2:
                        found = True
                        bot.deleteMessage((group, msgId))
                        previousWarns = int(db_users.search(where('chatId') == from_id)[0]['warns'])
                        db_users.update({'warns': str(previousWarns + 1)}, where('chatId') == from_id)
                        userWarns = int(db_users.search(where('chatId') == from_id)[0]['warns'])
                        bot.sendMessage(group, str("❗️ " + from_firstName + " has been warned [" + str(userWarns) + "/" + str(settings.Moderation.maxWarns) + "] for <b>porn media</b>."),parse_mode="HTML")
                        logStaff("❗️ <b>Warn</b>\nTo: " + from_firstName + "\nBy: Bot\nReason: Porn Media\nUser Warns Now: " + str(userWarns) + "/" + str(settings.Moderation.maxWarns))
                        if userWarns >= settings.Moderation.maxWarns:
                            bot.kickChatMember(group, from_id)
                            db_users.update({'warns': "0"}, where('chatId') == from_id)
                            bot.sendMessage(group, str("🚷 " + from_firstName + " has been banned."))
                            logStaff("🚷 <b>Ban</b>\nTo: " + from_firstName + "\nBy: Bot\nReason: Exceeded max warns")

                if settings.Moderation.detectViolence and not found:
                    output = imgparse_ai.check("offensive").set_file("file_" + str(msgId))
                    if output["offensive"]["prob"] > 0.3:
                        found = True
                        bot.deleteMessage((group, msgId))
                        previousWarns = int(db_users.search(where('chatId') == from_id)[0]['warns'])
                        db_users.update({'warns': str(previousWarns + 1)}, where('chatId') == from_id)
                        userWarns = int(db_users.search(where('chatId') == from_id)[0]['warns'])
                        bot.sendMessage(group, str("❗️ " + from_firstName + " has been warned [" + str(userWarns) + "/" + str(settings.Moderation.maxWarns) + "] for <b>offensive media</b>."), parse_mode="HTML")
                        logStaff("❗️ <b>Warn</b>\nTo: " + from_firstName + "\nBy: Bot\nReason: Offensive Media\nUser Warns Now: " + str(userWarns) + "/" + str(settings.Moderation.maxWarns))
                        if userWarns >= settings.Moderation.maxWarns:
                            bot.kickChatMember(group, from_id)
                            db_users.update({'warns': "0"}, where('chatId') == from_id)
                            bot.sendMessage(group, str("🚷 " + from_firstName + " has been banned."))
                            logStaff("🚷 <b>Ban</b>\nTo: " + from_firstName + "\nBy: Bot\nReason: Exceeded max warns")
                os.remove("file_" + str(msgId))

            # Word Blacklist Control
            for x in settings.Moderation.wordBlacklist:
                if x in text.lower():
                    logStaff("🆎 <b>Blacklisted Word</b>\nBy: "+from_firstName)
                    try:
                        bot.forwardMessage(settings.Bot.staffGroupId, group, msgId)
                    except Exception:
                        pass

            # User Name Character Limit
            if settings.Moderation.controlUserName:
                if len(from_firstName+from_lastName) > settings.Moderation.userNameCharacterLimit:
                    bot.sendMessage(group, "🌐 "+from_firstName+", please, set a <b>shorter name</b> in Telegram Settings.", parse_mode="HTML", reply_to_message_id=msgId)



print("Bot started...")
reloadAdmins()
bot.message_loop({'chat': handle})
while True:
    time.sleep(60)

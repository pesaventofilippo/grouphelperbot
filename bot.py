import telepot, time, hashlib, requests, os
from tinydb import TinyDB, where
from sightengine.client import SightengineClient
import settings.settings as settings
from settings.functions import getStr as _

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


def ban(group, selectedUser_id, selectedUser, from_firstName, from_lastName, reason):
    user_data = db_users.search(where('username') == selectedUser.replace("@", ""))[0]
    bot.kickChatMember(group, selectedUser_id)
    db_users.update({'warns': "0"}, where('chatId') == selectedUser_id)
    string = "<a href=\"tg://user?id=" + str(user_data["chatId"]) + "\">" + user_data["firstName"] + " " + user_data["lastName"] + "</a>"
    if reason:
        bot.sendMessage(group, _("grp_ban_reason", [selectedUser, reason]), parse_mode="HTML")
        logStaff(_("log_ban_reason", [string, from_firstName, from_lastName, reason]))
    else:
        bot.sendMessage(group, _("grp_ban_no_reason", [selectedUser]))
        logStaff(_("log_ban_no_reason", [string, from_firstName, from_lastName]))


def warn(group, selectedUser_id, selectedUser, from_firstName, from_lastName, reason):
    user_data = db_users.search(where('username') == selectedUser.replace("@", ""))[0]
    previousWarns = int(db_users.search(where('chatId') == selectedUser_id)[0]['warns'])
    db_users.update({'warns': str(previousWarns + 1)}, where('chatId') == selectedUser_id)
    userWarns = previousWarns + 1
    string = "<a href=\"tg://user?id=" + str(user_data["chatId"]) + "\">" + user_data["firstName"] + " " + user_data["lastName"] + "</a>"
    if reason:
        bot.sendMessage(group, _("grp_warn_reason", [selectedUser, str(userWarns), str(settings.Moderation.maxWarns), reason]), parse_mode="HTML")
        logStaff( _("log_warn_reason", [string, from_firstName, from_lastName, reason, str(userWarns), str(settings.Moderation.maxWarns)]))
    else:
        bot.sendMessage(group, _("grp_warn_no_reason", [selectedUser, str(userWarns), str(settings.Moderation.maxWarns)]))
        logStaff(_("log_warn_no_reason", [string, from_firstName, from_lastName, str(userWarns), str(settings.Moderation.maxWarns)]))
    if userWarns >= settings.Moderation.maxWarns:
        ban(group, selectedUser_id, selectedUser, "Bot", "", _("str_max_warns"))


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
                    bot.sendMessage(group, data, "HTML")
            logStaff(_("log_new_user", [str(from_id), from_firstName]))


        # Delete all commands
        if text.startswith("/"):
            if settings.Moderation.deleteCommands:
                bot.deleteMessage((group, msgId))


        # Creator message
        if getStatus(from_id) in ["creator"]:
            text_split = text.split(" ", 2)
            if isReply:
                selectedUser = reply_username
                selectedUserData = reply_fromId
                selectedUser_firstName = reply_firstName
                selectedUser_lastName = reply_lastName
            else:
                if len(text_split) < 2:
                    return
                selectedUser = text_split[1]
                data = db_users.search(where('username') == selectedUser.replace("@", ""))[0]
                selectedUserData = data['chatId']
                selectedUser_firstName = data['firstName']
                selectedUser_lastName = data['lastName']

            user_link = "<a href=\"tg://user?id=" + str(selectedUserData) + "\">" + selectedUser_firstName + " " + selectedUser_lastName +"</a>"

            if text.startswith("/helper"):
                if not ((getStatus(selectedUserData) == "creator") or (getStatus(selectedUserData) == "admin")):
                    updateAdminDatabase(selectedUserData, "helper")
                    bot.sendMessage(group, _("grp_new_helper", [selectedUser]), "HTML")
                    logStaff(_("log_new_helper", [user_link, from_firstName, from_lastName]))

            elif text.startswith("/unhelper"):
                if getStatus(selectedUserData) == "helper":
                    db_admins.remove(where('chatId') == selectedUserData)
                    bot.sendMessage(group, _("grp_rem_helper", [selectedUser]), "HTML")
                    logStaff(_("log_rem_helper", [user_link, from_firstName, from_lastName]))

            elif text.startswith("/mod"):
                if not ((getStatus(selectedUserData) == "creator") or (getStatus(selectedUserData) == "admin")):
                    updateAdminDatabase(selectedUserData, "moderator")
                    bot.sendMessage(group, _("grp_new_moderator", [selectedUser]), "HTML")
                    logStaff(_("log_new_moderator", [user_link, from_firstName, from_lastName]))

            elif text.startswith("/unmod"):
                if getStatus(selectedUserData) == "moderator":
                    db_admins.remove(where('chatId') == selectedUserData)
                    bot.sendMessage(group, _("grp_rem_moderator", [selectedUser]), "HTML")
                    logStaff(_("log_rem_moderator", [user_link, from_firstName, from_lastName]))

            elif text.startswith("/manager"):
                if not ((getStatus(selectedUserData) == "creator") or (getStatus(selectedUserData) == "admin")):
                    updateAdminDatabase(selectedUserData, "manager")
                    bot.sendMessage(group, _("grp_new_manager", [selectedUser]), "HTML")
                    logStaff(_("log_new_manager", [user_link, from_firstName, from_lastName]))

            elif text.startswith("/unmanager"):
                if getStatus(selectedUserData) == "manager":
                    db_admins.remove(where('chatId') == selectedUserData)
                    bot.sendMessage(group, _("grp_rem_manager", [selectedUser]), "HTML")
                    logStaff(_("log_rem_manager", [user_link, from_firstName, from_lastName]))

        # Creator or Admin message
        if getStatus(from_id) in ["creator", "admin"]:
            if text.startswith("/tell "):
                text_split = text.split(" ", 1)
                bot.sendMessage(group, text_split[1], parse_mode="HTML", reply_to_message_id=reply_msgId)

            elif text == "/reload":
                reloadAdmins()
                bot.sendMessage(group, "✅ <b>Bot reloaded!</b>", "HTML")
                logStaff(_("bot_reload", [from_firstName, from_lastName]))

            elif text.startswith("/kickinactive "):
                text_split = text.split(" ")
                days = int(text_split[1])
                currentTime = int(time.time())
                diffTime = days*24*60*60
                lastTime = currentTime - diffTime
                kick_users = db_users.search(where('lastMsgDate')<lastTime)
                logStaff(_("bot_start_inactive_kick", [from_firstName, from_lastName, str(days)]))
                for x in kick_users:
                    try:
                        bot.kickChatMember(group, x['chatId'])
                        time.sleep(0.5)
                        bot.unbanChatMember(group, x['chatId'])
                    except Exception:
                        pass
                logStaff(_("bot_end_inactive_kick"))


        # Creator or Admin or Moderator message
        if getStatus(from_id) in ["creator", "admin", "moderator"]:
            text_split = text.split(" ", 2)

            if isReply:
                selectedUser = reply_username
                selectedUserData = reply_fromId
                reason = len(text.split(" ", 1)) >= 2 and text.split(" ", 1)[1] or None
            else:
                if len(text_split) < 2:
                    return
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                reason = len(text_split) >= 3 and text_split[2] or None

            if text.startswith("/warn"):
                if not ((getStatus(selectedUserData) == "creator") or (getStatus(selectedUserData) == "admin")):
                    warn(group, selectedUserData, selectedUser, from_firstName, from_lastName, reason)

            elif text.startswith("/delwarn"):
                bot.deleteMessage((group, reply_msgId))
                if not ((getStatus(selectedUserData) == "creator") or (getStatus(selectedUserData) == "admin")):
                    warn(group, selectedUserData, selectedUser, from_firstName, from_lastName, reason)

            elif text.startswith("/mute"):
                if not ((getStatus(selectedUserData) == "creator") or (getStatus(selectedUserData) == "admin")):
                    bot.restrictChatMember(group, selectedUserData, until_date=time.time() + 3600)
                    try:
                        reason = text_split[2]
                        bot.sendMessage(group, _("grp_mute_reason", [selectedUser, reason]), parse_mode="HTML")
                        logStaff(_("grp_mute_reason", [selectedUser, from_firstName, from_lastName, reason]))
                    except IndexError:
                        bot.sendMessage(group, _("grp_mute_no_reason", [selectedUser]))
                        logStaff(_("grp_mute_no_reason", [selectedUser, from_firstName, from_lastName, reason]))

            elif text.startswith("/kick"):
                if not ((getStatus(selectedUserData) == "creator") or (getStatus(selectedUserData) == "admin")):
                    try:
                        bot.kickChatMember(group, selectedUserData)
                        time.sleep(0.5)
                        bot.unbanChatMember(group, selectedUserData)
                    except:
                        pass
                    try:
                        reason = text_split[2]
                        bot.sendMessage(group, _("grp_kick_reason", [selectedUser, reason]), parse_mode="HTML")
                        logStaff(_("log_kick_reason", [selectedUser, from_firstName, from_lastName, reason]))
                    except IndexError:
                        bot.sendMessage(group, _("grp_kick_no_reason", [selectedUser]))
                        logStaff(_("log_kick_no_eason", [selectedUser, from_firstName, from_lastName]))

            elif text.startswith("/ban"):
                if not (getStatus(selectedUserData) in ["creator", "admin"]):
                    ban(group, selectedUserData, selectedUser, from_firstName, from_lastName, reason)

            elif text.startswith("/unban"):
                bot.unbanChatMember(group, selectedUserData)
                bot.sendMessage(group, _("grp_unban", [selectedUser]))
                logStaff(_("log_unban", [selectedUser, from_firstName, from_lastName]))

            elif text.startswith("/unwarn"):
                previousWarns = int(db_users.search(where('chatId') == selectedUserData)[0]['warns'])
                if previousWarns > 0:
                    db_users.update({'warns': str(previousWarns-1)}, where('chatId') == selectedUserData)
                    bot.sendMessage(group, _("grp_unwarn", [selectedUser, str(previousWarns-1)]))
                    logStaff(_("log_unwarn", [selectedUser, from_firstName, from_lastName, str(previousWarns-1), str(settings.Moderation.maxWarns)]))

            elif text.startswith("/unmute"):
                bot.restrictChatMember(group, selectedUserData, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
                bot.sendMessage(group, _("grp_unmute",  [selectedUser]))
                logStaff(_("log_unmute", [selectedUser, from_firstName, from_lastName]))

            elif text.startswith("/info"):
                bot.sendMessage(group, _("grp_info", [selectedUser, str(selectedUserData), str(db_users.search(where('chatId') == selectedUserData)[0]['warns'])]), "HTML")

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
                bot.sendMessage(group, _("grp_staff_call"), "HTML")
                if isReply:
                    logStaff(_("log_staff_call_reply", ["<a href=\"tg://user?id=" + str(from_id) + "\">" + from_firstName + "</a>", "<a href=\"tg://user?id=" + str(reply_fromId) + "\">" + reply_firstName + "</a>", text]))
                    try:
                        bot.forwardMessage(settings.Bot.staffGroupId, group, reply_msgId)
                    except Exception:
                        pass
                else:
                    logStaff(_("log_staff_call_noreply", ["<a href=\"tg://user?id=" + str(from_id) + "\">" + from_firstName + "</a>", text]))

        elif cmdtext == "/staff":
            message = _("grp_staff_title")

            message += _("grp_staff_founder")
            for x in [x["chatId"] for x in db_admins.search(where('status') == "creator")]:
                try:
                    message += "\n        @" + bot.getChatMember(group, x)['user']['username']
                except KeyError:
                    message += "\n        " + bot.getChatMember(group, x)['user']['first_name']

            message += _("grp_staff_admins")
            for x in [x["chatId"] for x in db_admins.search(where('status') == "admin")]:
                try:
                    message += "\n        @" + bot.getChatMember(group, x)['user']['username']
                except KeyError:
                    message += "\n        " + bot.getChatMember(group, x)['user']['first_name']

            message += _("grp_staff_moderators")
            for x in [x["chatId"] for x in db_admins.search(where('status') == "moderator")]:
                try:
                    message += "\n        @" + bot.getChatMember(group, x)['user']['username']
                except KeyError:
                    message += "\n        " + bot.getChatMember(group, x)['user']['first_name']

            message += _("grp_staff_managers")
            for x in [x["chatId"] for x in db_admins.search(where('status') == "manager")]:
                try:
                    message += "\n        @" + bot.getChatMember(group, x)['user']['username']
                except KeyError:
                    message += "\n        " + bot.getChatMember(group, x)['user']['first_name']

            message += _("grp_staff_helpers")
            for x in [x["chatId"] for x in db_admins.search(where('status') == "helper")]:
                try:
                    message += "\n        @" + bot.getChatMember(group, x)['user']['username']
                except KeyError:
                    message += "\n        " + bot.getChatMember(group, x)['user']['first_name']

            bot.sendMessage(group, message, parse_mode="HTML")

        elif cmdtext == "/rules":
            data = settings.Messages.rules
            if data != "":
                bot.sendMessage(group, data, "HTML")


        # Only Normal User Messages
        elif getStatus(from_id) == "user":

            # Control username
            if settings.Moderation.mustHaveUsername:
                if from_username == "":
                    bot.sendMessage(group, _("grp_set_username", [from_firstName]) , parse_mode="HTML", reply_to_message_id=msgId)

            # Detect spam from a Telegram Link
            if ("t.me/" in text) or ("t.dog/" in text) or ("telegram.me/" in text):
                if settings.Moderation.spamDetect:
                    bot.deleteMessage((group, msgId))
                    warn(group, from_id, from_username, "Bot", "", "Spam")

            # Scan Sended Files
            if msgType == "document":
                if settings.Moderation.scanSendedFiles:
                    message = bot.sendMessage(group, _("grp_scan_file"), parse_mode="HTML", reply_to_message_id=msgId)
                    bot.download_file(msg['document']['file_id'], "file_"+str(msgId))
                    file = open("file_"+str(msgId), "rb")
                    hash = hashlib.sha256(file.read()).hexdigest()
                    data = requests.get(settings.virusTotal.url, params={'apikey': settings.virusTotal.apikey, 'resource': hash}).json()
                    file.close()
                    os.remove("file_"+str(msgId))
                    if data['response_code'] == 1:
                        if data['positives'] == 0:
                            bot.editMessageText((group, message['message_id']), _("grp_scanned_safe", [str(data['positives']), str(data['total'])]))
                        elif data['positives'] < 10:
                            bot.editMessageText((group, message['message_id']), _("grp_scanned_warning", [str(data['positives']), str(data['total'])]))
                        else:
                            bot.editMessageText((group, message['message_id']), _("grp_scanned_malware", [str(data['positives']), str(data['total'])]))
                    else:
                        bot.deleteMessage((group, message['message_id']))

            # Detect spam from a fowarded message
            if settings.Moderation.forwardSpamDetect:
                try:
                    forwarded_from = msg['forward_from_chat']
                    if forwarded_from['type'] == "channel":
                        if forwarded_from['username'] not in settings.Moderation.channelsWhitelist:
                            bot.deleteMessage((group, msgId))
                            warn(group, from_id, from_username, "Bot", "", "Spam")
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
                        warn(group, from_id, from_username, "Bot", "", "Spam")

                if settings.Moderation.detectViolence and not found:
                    output = imgparse_ai.check("offensive").set_file("file_" + str(msgId))
                    if output["offensive"]["prob"] > 0.3:
                        found = True
                        bot.deleteMessage((group, msgId))
                        warn(group, from_id, from_username, "Bot", "", "Spam")
                os.remove("file_" + str(msgId))

            # Word Blacklist Control
            for x in settings.Moderation.wordBlacklist:
                if x in text:
                    logStaff("🆎 <b>Blacklisted Word</b>\nBy: "+from_firstName)
                    try:
                        bot.forwardMessage(settings.Bot.staffGroupId, group, msgId)
                    except Exception:
                        pass

            # User Name Character Limit
            if settings.Moderation.controlUserName:
                if len(from_firstName+from_lastName) > settings.Moderation.userNameCharacterLimit:
                    bot.sendMessage(group, _("grp_shorter_name", [from_firstName]), parse_mode="HTML", reply_to_message_id=msgId)

print("Bot started...")
reloadAdmins()
bot.message_loop({'chat': handle})
while True:
    time.sleep(60)

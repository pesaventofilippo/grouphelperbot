import telepot, time, hashlib, requests, os, threading
from tinydb import TinyDB, where
from sightengine.client import SightengineClient
import settings.settings as settings
from settings.functions import getStr as _

db_users = TinyDB(settings.Databases.users)
db_admins = TinyDB(settings.Databases.admins)
bot = telepot.Bot(settings.Bot.token)
group = settings.Bot.groupId
myusername = "@" + bot.getMe()['username']
myname = bot.getMe()['first_name']
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


def forwardStaff(message_id):
    if settings.Bot.useStaffGroup:
        try:
            bot.forwardMessage(settings.Bot.staffGroupId, group, message_id)
        except Exception:
            pass


def kickInactiveUsers(list):
    for x in list:
        if bot.getChatMember(group, x['chatId'])['status'] != "kicked":
            time.sleep(1)
            bot.kickChatMember(group, x['chatId'])
            time.sleep(1)
            bot.unbanChatMember(group, x['chatId'])
            time.sleep(5)
    logStaff(_("bot_end_inactive_kick"))


def createUserString(uid, fname, lname):
    if lname == "":
        string = "<a href=\"tg://user?id=" + str(uid) + "\">" + str(fname) + "</a>"
    else:
        string = "<a href=\"tg://user?id=" + str(uid) + "\">" + str(fname) + " " + str(lname) + "</a>"
    return string


def handle(msg):
    chatId, msgId, msgType, text,\
    from_id, from_firstName, from_lastName, from_username,\
    isReply, reply_msgId,\
    reply_fromId, reply_firstName, reply_lastName, reply_username = getUserInfo(msg)

    if chatId == group:
        updateUserDatabase(from_id, from_firstName, from_lastName, from_username)


        # Welcoming message
        if msgType == "new_chat_member":
            if settings.Moderation.groupClosed:
                bot.kickChatMember(group, from_id)
                time.sleep(0.5)
                bot.unbanChatMember(group, from_id)
                logStaff(_("log_new_user_closed", [createUserString(from_id, from_firstName, from_lastName)]))
            else:
                if settings.Moderation.showWelcomeMessage:
                    data = settings.Messages.welcome
                    if data != "":
                        data = data.replace('{{name}}', from_firstName)
                        data = data.replace('{{surname}}', from_lastName)
                        data = data.replace('{{username}}', from_username)
                        data = data.replace('{{group_name}}', bot.getChat(group)['title'])
                        bot.sendMessage(group, data, parse_mode="HTML", disable_web_page_preview=True)
                logStaff(_("log_new_user", [createUserString(from_id, from_firstName, from_lastName)]))


        # Delete all commands
        if text.startswith("/"):
            if settings.Moderation.deleteCommands:
                bot.deleteMessage((group, msgId))


        # Creator message
        if getStatus(from_id) in ["creator"]:
            if text.startswith(_("cmd_helper") + " @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if not ((getStatus(selectedUserData) == "creator") or (getStatus(selectedUserData) == "admin")):
                    updateAdminDatabase(selectedUserData, "helper")
                    bot.sendMessage(group, _("grp_new_helper", [selectedUser]), "HTML")
                    logStaff(_("log_new_helper", [selectedUser, createUserString(from_id, from_firstName, from_lastName)]))

            elif text.startswith(_("cmd_unhelper") + " @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if getStatus(selectedUserData) == "helper":
                    db_admins.remove(where('chatId') == selectedUserData)
                    bot.sendMessage(group, _("grp_rem_helper", [selectedUser]), "HTML")
                    logStaff(_("log_rem_helper", [selectedUser, createUserString(from_id, from_firstName, from_lastName)]))

            elif text.startswith(_("cmd_mod") + " @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if not ((getStatus(selectedUserData) == "creator") or (getStatus(selectedUserData) == "admin")):
                    updateAdminDatabase(selectedUserData, "moderator")
                    bot.sendMessage(group, _("grp_new_moderator", [selectedUser]), "HTML")
                    logStaff(_("log_new_moderator", [selectedUser, createUserString(from_id, from_firstName, from_lastName)]))

            elif text.startswith(_("cmd_unmod") + " @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if getStatus(selectedUserData) == "moderator":
                    db_admins.remove(where('chatId') == selectedUserData)
                    bot.sendMessage(group, _("grp_rem_moderator", [selectedUser]), "HTML")
                    logStaff(_("log_rem_moderator", [selectedUser, createUserString(from_id, from_firstName, from_lastName)]))

            elif text.startswith(_("cmd_manager") + " @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if not ((getStatus(selectedUserData) == "creator") or (getStatus(selectedUserData) == "admin")):
                    updateAdminDatabase(selectedUserData, "manager")
                    bot.sendMessage(group, _("grp_new_manager", [selectedUser]), "HTML")
                    logStaff(_("log_new_manager", [selectedUser, createUserString(from_id, from_firstName, from_lastName)]))

            elif text.startswith(_("cmd_unmanager") + " @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if getStatus(selectedUserData) == "manager":
                    db_admins.remove(where('chatId') == selectedUserData)
                    bot.sendMessage(group, _("grp_rem_manager", [selectedUser]), "HTML")
                    logStaff(_("log_rem_manager", [selectedUser, createUserString(from_id, from_firstName, from_lastName)]))

            elif isReply:
                if text == _("cmd_helper"):
                    if not ((getStatus(reply_fromId) == "creator") or (getStatus(reply_fromId) == "admin")):
                        updateAdminDatabase(reply_fromId, "helper")
                        bot.sendMessage(group, _("grp_new_helper", [createUserString(reply_fromId, reply_firstName, reply_lastName)]), parse_mode="HTML", reply_to_message_id=reply_msgId)
                        logStaff(_("log_new_helper", [createUserString(reply_fromId, reply_firstName, reply_lastName), createUserString(from_id, from_firstName, from_lastName)]))
                        forwardStaff(reply_msgId)

                elif text == _("cmd_unhelper"):
                    if getStatus(reply_fromId) == "helper":
                        db_admins.remove(where('chatId') == reply_fromId)
                        bot.sendMessage(group, _("grp_rem_helper", [createUserString(reply_fromId, reply_firstName, reply_lastName)]), parse_mode="HTML", reply_to_message_id=reply_msgId)
                        logStaff(_("log_rem_helper", [createUserString(reply_fromId, reply_firstName, reply_lastName), createUserString(from_id, from_firstName, from_lastName)]))
                        forwardStaff(reply_msgId)

                elif text == _("cmd_mod"):
                    if not ((getStatus(reply_fromId) == "creator") or (getStatus(reply_fromId) == "admin")):
                        updateAdminDatabase(reply_fromId, "moderator")
                        bot.sendMessage(group, _("grp_new_moderator", [createUserString(reply_fromId, reply_firstName, reply_lastName)]), parse_mode="HTML", reply_to_message_id=reply_msgId)
                        logStaff(_("log_new_moderator", [createUserString(reply_fromId, reply_firstName, reply_lastName), createUserString(from_id, from_firstName, from_lastName)]))
                        forwardStaff(reply_msgId)

                elif text == _("cmd_unmod"):
                    if getStatus(reply_fromId) == "moderator":
                        db_admins.remove(where('chatId') == reply_fromId)
                        bot.sendMessage(group, _("grp_rem_moderator", [createUserString(reply_fromId, reply_firstName, reply_lastName)]), parse_mode="HTML", reply_to_message_id=reply_msgId)
                        logStaff(_("log_rem_moderator   ", [createUserString(reply_fromId, reply_firstName, reply_lastName), createUserString(from_id, from_firstName, from_lastName)]))
                        forwardStaff(reply_msgId)

                elif text == _("cmd_manager"):
                    if not ((getStatus(reply_fromId) == "creator") or (getStatus(reply_fromId) == "admin")):
                        updateAdminDatabase(reply_fromId, "manager")
                        bot.sendMessage(group, _("grp_new_manager", [createUserString(reply_fromId, reply_firstName, reply_lastName)]), parse_mode="HTML", reply_to_message_id=reply_msgId)
                        logStaff(_("log_new_manager", [createUserString(reply_fromId, reply_firstName, reply_lastName), createUserString(from_id, from_firstName, from_lastName)]))
                        forwardStaff(reply_msgId)

                elif text == _("cmd_unmanager"):
                    if getStatus(reply_fromId) == "manager":
                        db_admins.remove(where('chatId') == createUserString(reply_fromId, reply_firstName, reply_lastName))
                        bot.sendMessage(group, _("grp_rem_manager", [createUserString(reply_fromId, reply_firstName, reply_lastName)]), parse_mode="HTML", reply_to_message_id=reply_msgId)
                        logStaff(_("log_rem_manager", [createUserString(reply_fromId, reply_firstName, reply_lastName), createUserString(from_id, from_firstName, from_lastName)]))
                        forwardStaff(reply_msgId)


        # Creator or Admin message
        if getStatus(from_id) in ["creator", "admin"]:
            if text.startswith(_("cmd_tell") + " "):
                text_split = text.split(" ", 1)
                bot.sendMessage(group, text_split[1], parse_mode="HTML", reply_to_message_id=reply_msgId)

            elif text == _("cmd_reload"):
                reloadAdmins()
                bot.sendMessage(group, _("bot_reload"), parse_mode="HTML")

            elif text.startswith(_("cmd_kickinactive") + " "):
                text_split = text.split(" ")
                days = int(text_split[1])
                currentTime = int(time.time())
                diffTime = days*24*60*60
                lastTime = currentTime - diffTime
                kick_users = db_users.search(where('lastMsgDate')<lastTime)
                logStaff(_("bot_start_inactive_kick", [createUserString(from_id, from_firstName, from_lastName), days]))
                threading.Thread(target=kickInactiveUsers(kick_users), args=kick_users).start()

            elif text == _("cmd_pin"):
                if isReply:
                    bot.pinChatMessage(group, reply_msgId)

            elif text == _("cmd_unpin"):
                bot.unpinChatMessage(group)


        # Creator or Admin or Moderator message
        if getStatus(from_id) in ["creator", "admin", "moderator"]:
            if text.startswith(_("cmd_warn") + " @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if not ((getStatus(selectedUserData) == "creator") or (getStatus(selectedUserData) == "admin")):
                    previousWarns = int(db_users.search(where('chatId') == selectedUserData)[0]['warns'])
                    db_users.update({'warns': str(previousWarns + 1)}, where('chatId') == selectedUserData)
                    userWarns = int(db_users.search(where('chatId') == selectedUserData)[0]['warns'])
                    try:
                        reason = text_split[2]
                        bot.sendMessage(group, _("grp_warn_reason", [selectedUser, str(userWarns), str(settings.Moderation.maxWarns),  reason]), parse_mode="HTML")
                        logStaff(_("log_warn_reason", [selectedUser, createUserString(from_id, from_firstName, from_lastName), reason, str(userWarns), str(settings.Moderation.maxWarns)]))
                    except IndexError:
                        bot.sendMessage(group, _("grp_warn_no_reason", [selectedUser, str(userWarns), str(settings.Moderation.maxWarns)]),  parse_mode="HTML")
                        logStaff(_("log_warn_no_reason", [selectedUser, createUserString(from_id, from_firstName, from_lastName), str(userWarns), str(settings.Moderation.maxWarns)]))
                    if userWarns >= settings.Moderation.maxWarns:
                        bot.kickChatMember(group, selectedUserData)
                        bot.sendMessage(group, _("grp_ban_reason", [selectedUser, _("str_max_warns")]))
                        logStaff(_("log_ban_reason", [selectedUser, createUserString(bot.getMe()['id'], myname, ""), _("str_max_warns")]))

            elif text.startswith(_("cmd_delwarn") + " @"):
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
                        bot.sendMessage(group, _("grp_warn_reason", [selectedUser, str(userWarns), str(settings.Moderation.maxWarns),  reason]), parse_mode="HTML")
                        logStaff(_("log_warn_reason", [selectedUser, createUserString(from_id, from_firstName, from_lastName), reason, str(userWarns), str(settings.Moderation.maxWarns)]))
                    except IndexError:
                        bot.sendMessage(group, _("grp_warn_no_reason", [selectedUser, str(userWarns), str(settings.Moderation.maxWarns)]),  parse_mode="HTML")
                        logStaff(_("log_warn_no_reason", [selectedUser, createUserString(from_id, from_firstName, from_lastName), str(userWarns), str(settings.Moderation.maxWarns)]))
                    if userWarns >= settings.Moderation.maxWarns:
                        bot.kickChatMember(group, selectedUserData)
                        db_users.update({'warns': 0}, where('chatId') == selectedUserData)
                        bot.sendMessage(group, _("grp_ban_reason", [selectedUser, _("str_max_warns")]))
                        logStaff(_("log_ban_reason", [selectedUser, createUserString(bot.getMe()['id'], myname, ""), _("str_max_warns")]))

            elif text.startswith(_("cmd_mute") + " @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if not ((getStatus(selectedUserData) == "creator") or (getStatus(selectedUserData) == "admin")):
                    try:
                        hours = text_split[2]
                        bot.restrictChatMember(group, selectedUserData, until_date=time.time() + (int(hours)*3600))
                        bot.sendMessage(group, _("grp_mute_custom", [selectedUser, hours]))
                        logStaff(_("log_mute_custom", [selectedUser, createUserString(from_id, from_firstName, from_lastName), hours]))
                    except IndexError:
                        bot.restrictChatMember(group, selectedUserData, until_date=time.time() + 3600)
                        bot.sendMessage(group, _("grp_mute_default", [selectedUser]))
                        logStaff(_("log_mute_default", [selectedUser, createUserString(from_id, from_firstName, from_lastName)]))

            elif text.startswith(_("cmd_kick") + " @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if not ((getStatus(selectedUserData) == "creator") or (getStatus(selectedUserData) == "admin")):
                    if bot.getChatMember(group, selectedUserData)['status'] != "kicked":
                        bot.kickChatMember(group, selectedUserData)
                        time.sleep(0.5)
                        bot.unbanChatMember(group, selectedUserData)
                    try:
                        reason = text_split[2]
                        bot.sendMessage(group, _("grp_kick_reason", [selectedUser, reason]), parse_mode="HTML")
                        logStaff(_("log_kick_reason", [selectedUser, createUserString(from_id, from_firstName, from_lastName), reason]))
                    except IndexError:
                        bot.sendMessage(group, _("grp_kick_no_reason", [selectedUser]))
                        logStaff(_("log_kick_no_reason", [selectedUser, createUserString(from_id, from_firstName, from_lastName)]))

            elif text.startswith(_("cmd_ban") + " @"):
                text_split = text.split(" ", 2)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                if not ((getStatus(selectedUserData) == "creator") or (getStatus(selectedUserData) == "admin")):
                    bot.kickChatMember(group, selectedUserData)
                    db_users.update({'warns': 0}, where('chatId') == selectedUserData)
                    try:
                        reason = text_split[2]
                        bot.sendMessage(group, _("grp_ban_reason", [selectedUser, reason]), parse_mode="HTML")
                        logStaff(_("log_ban_reason", [selectedUser, createUserString(from_id, from_firstName, from_lastName), reason]))
                    except IndexError:
                        bot.sendMessage(group, _("grp_ban_no_reason", [selectedUser]))
                        logStaff(_("log_ban_no_reason", [selectedUser, createUserString(from_id, from_firstName, from_lastName)]))

            elif text.startswith(_("cmd_unban") + " @"):
                text_split = text.split(" ", 1)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                bot.unbanChatMember(group, selectedUserData)
                bot.sendMessage(group, _("grp_unban", [selectedUser]))
                logStaff(_("log_unban", [selectedUser, createUserString(from_id, from_firstName, from_lastName)]))

            elif text.startswith(_("cmd_unwarn") + " @"):
                text_split = text.split(" ", 1)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                previousWarns = int(db_users.search(where('chatId') == selectedUserData)[0]['warns'])
                if previousWarns > 0:
                    db_users.update({'warns': str(previousWarns-1)}, where('chatId') == selectedUserData)
                    bot.sendMessage(group, _("grp_unwarn", [selectedUser, str(previousWarns-1)]))
                    logStaff(_("log_unwarn", [selectedUser, createUserString(from_id, from_firstName, from_lastName), str(previousWarns-1), str(settings.Moderation.maxWarns)]))

            elif text.startswith(_("cmd_unmute") + " @"):
                text_split = text.split(" ", 1)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                bot.restrictChatMember(group, selectedUserData, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
                bot.sendMessage(group, _("log_unmute", [selectedUser]))
                logStaff(_("log_unmute", [selectedUser, createUserString(from_id, from_firstName, from_lastName)]))

            elif text.startswith(_("cmd_info") + " @"):
                text_split = text.split(" ", 1)
                selectedUser = text_split[1]
                selectedUserData = db_users.search(where('username') == selectedUser.replace("@", ""))[0]['chatId']
                bot.sendMessage(group, _("grp_info", [selectedUser, str(selectedUserData), str(db_users.search(where('chatId') == selectedUserData)[0]['warns'])]), "HTML")

            elif text == _("cmd_silenceon"):
                settings.Moderation.globalSilenceActive = True
                bot.sendMessage(group, _("grp_global_silence_on"), "HTML")
                logStaff(_("log_global_silence_on", [createUserString(from_id, from_firstName, from_lastName)]))

            elif text == _("cmd_silenceoff"):
                settings.Moderation.globalSilenceActive = False
                bot.sendMessage(group, _("grp_global_silence_off"), "HTML")
                logStaff(_("log_global_silence_off", [createUserString(from_id, from_firstName, from_lastName)]))

            elif text == _("cmd_closegroup"):
                settings.Moderation.groupClosed = True
                bot.sendMessage(group, _("grp_closegroup"), "HTML")
                logStaff(_("log_closegroup", [createUserString(from_id, from_firstName, from_lastName)]))

            elif text == _("cmd_opengroup"):
                settings.Moderation.groupClosed = False
                bot.sendMessage(group, _("grp_opengroup"), "HTML")
                logStaff(_("log_opengroup", [createUserString(from_id, from_firstName, from_lastName)]))


            elif isReply:
                if text.startswith(_("cmd_warn")):
                    if not ((getStatus(reply_fromId) == "creator") or (getStatus(reply_fromId) == "admin")):
                        previousWarns = int(db_users.search(where('chatId') == reply_fromId)[0]['warns'])
                        db_users.update({'warns': str(previousWarns + 1)}, where('chatId') == reply_fromId)
                        userWarns = int(db_users.search(where('chatId') == reply_fromId)[0]['warns'])
                        try:
                            reason = text.split(" ", 1)[1]
                            bot.sendMessage(group, _("grp_warn_reason", [createUserString(reply_fromId, reply_firstName, reply_lastName), str(userWarns), str(settings.Moderation.maxWarns), reason]), parse_mode="HTML", reply_to_message_id=reply_msgId)
                            logStaff(_("log_warn_reason", [createUserString(reply_fromId, reply_firstName, reply_lastName), createUserString(from_id, from_firstName, from_lastName), reason, str(userWarns), str(settings.Moderation.maxWarns)]))
                        except IndexError:
                            bot.sendMessage(group, _("grp_warn_no_reason", [createUserString(reply_fromId, reply_firstName, reply_lastName), str(userWarns), str(settings.Moderation.maxWarns)]), parse_mode="HTML", reply_to_message_id=reply_msgId)
                            logStaff(_("log_warn_no_reason", [createUserString(reply_fromId, reply_firstName, reply_lastName), createUserString(from_id, from_firstName, from_lastName), str(userWarns), str(settings.Moderation.maxWarns)]))
                        forwardStaff(reply_msgId)
                        if userWarns >= settings.Moderation.maxWarns:
                            bot.kickChatMember(group, reply_fromId)
                            db_users.update({'warns': 0}, where('chatId') == reply_fromId)
                            bot.sendMessage(group, _("grp_ban_reason", [createUserString(reply_fromId, reply_firstName, reply_lastName), _("str_max_warns")]))
                            logStaff(_("log_ban_reason", [createUserString(reply_fromId, reply_firstName, reply_lastName), createUserString(bot.getMe()['id'], myname, ""), _("str_max_warns")]))

                elif text.startswith(_("cmd_delwarn")):
                    if not ((getStatus(reply_fromId) == "creator") or (getStatus(reply_fromId) == "admin")):
                        previousWarns = int(db_users.search(where('chatId') == reply_fromId)[0]['warns'])
                        db_users.update({'warns': str(previousWarns + 1)}, where('chatId') == reply_fromId)
                        userWarns = int(db_users.search(where('chatId') == reply_fromId)[0]['warns'])
                        try:
                            reason = text.split(" ", 1)[1]
                            bot.sendMessage(group, _("grp_warn_reason", [createUserString(reply_fromId, reply_firstName, reply_lastName), str(userWarns), str(settings.Moderation.maxWarns), reason]), parse_mode="HTML", reply_to_message_id=reply_msgId)
                            logStaff(_("log_warn_reason", [createUserString(reply_fromId, reply_firstName, reply_lastName), createUserString(from_id, from_firstName, from_lastName), reason, str(userWarns), str(settings.Moderation.maxWarns)]))
                        except IndexError:
                            bot.sendMessage(group, _("grp_warn_no_reason", [createUserString(reply_fromId, reply_firstName, reply_lastName), str(userWarns), str(settings.Moderation.maxWarns)]), parse_mode="HTML", reply_to_message_id=reply_msgId)
                            logStaff(_("log_warn_no_reason", [createUserString(reply_fromId, reply_firstName, reply_lastName), createUserString(from_id, from_firstName, from_lastName), str(userWarns), str(settings.Moderation.maxWarns)]))
                        forwardStaff(reply_msgId)
                        bot.deleteMessage((group, reply_msgId))
                        if userWarns >= settings.Moderation.maxWarns:
                            bot.kickChatMember(group, reply_fromId)
                            db_users.update({'warns': 0}, where('chatId') == reply_fromId)
                            bot.sendMessage(group, _("grp_ban_reason", [createUserString(reply_fromId, reply_firstName, reply_lastName), _("str_max_warns")]))
                            logStaff(_("log_ban_reason", [createUserString(reply_fromId, reply_firstName, reply_lastName), createUserString(bot.getMe()['id'], myname, ""), _("str_max_warns")]))

                elif text.startswith(_("cmd_mute")):
                    if not ((getStatus(reply_fromId) == "creator") or (getStatus(reply_fromId) == "admin")):
                        try:
                            hours = text.split(" ", 1)[1]
                            bot.restrictChatMember(group, reply_fromId, until_date=time.time() + (int(hours)*3600))
                            bot.sendMessage(group, _("grp_mute_custom", [createUserString(reply_fromId, reply_firstName, reply_lastName), hours]), parse_mode="HTML", reply_to_message_id=reply_msgId)
                            logStaff(_("log_mute_custom", [createUserString(reply_fromId, reply_firstName, reply_lastName), createUserString(from_id, from_firstName, from_lastName), hours]))
                        except IndexError:
                            bot.restrictChatMember(group, reply_fromId, until_date=time.time() + 3600)
                            bot.sendMessage(group, _("grp_mute_default", [createUserString(reply_fromId, reply_firstName, reply_lastName)]), parse_mode="HTML", reply_to_message_id=reply_msgId)
                            logStaff(_("log_mute_default", [createUserString(reply_fromId, reply_firstName, reply_lastName), createUserString(from_id, from_firstName, from_lastName)]))
                        forwardStaff(reply_msgId)

                elif text.startswith(_("cmd_kick")):
                    if not ((getStatus(reply_fromId) == "creator") or (getStatus(reply_fromId) == "admin")):
                        if bot.getChatMember(group, reply_fromId)['status'] != "kicked":
                            bot.kickChatMember(group, reply_fromId)
                            time.sleep(0.5)
                            bot.unbanChatMember(group, reply_fromId)
                            try:
                                reason = text.split(" ", 1)[1]
                                bot.sendMessage(group, _("grp_kick_reason", [createUserString(reply_fromId, reply_firstName, reply_lastName), reason]), parse_mode="HTML", reply_to_message_id=reply_msgId)
                                logStaff(_("log_kick_reason", [createUserString(reply_fromId, reply_firstName, reply_lastName), createUserString(from_id, from_firstName, from_lastName), reason]))
                            except IndexError:
                                bot.sendMessage(group, _("grp_kick_no_reason", [createUserString(reply_fromId, reply_firstName, reply_lastName)]), parse_mode="HTML", reply_to_message_id=reply_msgId)
                                logStaff(_("log_kick_no_reason", [createUserString(reply_fromId, reply_firstName, reply_lastName), createUserString(from_id, from_firstName, from_lastName)]))
                            forwardStaff(reply_msgId)

                elif text.startswith(_("cmd_ban")):
                    if not ((getStatus(reply_fromId) == "creator") or (getStatus(reply_fromId) == "admin")):
                        bot.kickChatMember(group, reply_fromId)
                        db_users.update({'warns': 0}, where('chatId') == reply_fromId)
                        try:
                            reason = text.split(" ", 1)[1]
                            bot.sendMessage(group, _("grp_ban_reason", [createUserString(reply_fromId, reply_firstName, reply_lastName), reason]), parse_mode="HTML", reply_to_message_id=reply_msgId)
                            logStaff(_("log_ban_reason", [createUserString(reply_fromId, reply_firstName, reply_lastName), createUserString(from_id, from_firstName, from_lastName), reason]))
                        except IndexError:
                            bot.sendMessage(group, _("grp_ban_no_reason", [createUserString(reply_fromId, reply_firstName, reply_lastName)]), parse_mode="HTML", reply_to_message_id=reply_msgId)
                            logStaff(_("log_ban_no_reason", [createUserString(reply_fromId, reply_firstName, reply_lastName), createUserString(from_id, from_firstName, from_lastName)]))
                        forwardStaff(reply_msgId)

                elif text.startswith(_("cmd_unban")):
                    bot.unbanChatMember(group, reply_fromId)
                    bot.sendMessage(group, _("grp_unban", [createUserString(reply_fromId, reply_firstName, reply_lastName)]), parse_mode="HTML", reply_to_message_id=reply_msgId)
                    logStaff(_("log_unban", [createUserString(reply_fromId, reply_firstName, reply_lastName), createUserString(from_id, from_firstName, from_lastName)]))
                    forwardStaff(reply_msgId)

                elif text.startswith(_("cmd_unwarn")):
                    previousWarns = int(db_users.search(where('chatId') == reply_fromId)[0]['warns'])
                    if previousWarns > 0:
                        db_users.update({'warns': str(previousWarns-1)}, where('chatId') == reply_fromId)
                        bot.sendMessage(group, _("grp_unwarn", [createUserString(reply_fromId, reply_firstName, reply_lastName), str(previousWarns-1)]), parse_mode="HTML", reply_to_message_id=reply_msgId)
                        logStaff(_("log_unwarn", [createUserString(reply_fromId, reply_firstName, reply_lastName), createUserString(from_id, from_firstName, from_lastName)]))
                        forwardStaff(reply_msgId)

                elif text.startswith(_("cmd_unmute")):
                    bot.restrictChatMember(group, reply_fromId, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
                    bot.sendMessage(group, _("grp_unmute", [createUserString(reply_fromId, reply_firstName, reply_lastName)]), parse_mode="HTML", reply_to_message_id=reply_msgId)
                    logStaff(_("log_unmute", [createUserString(reply_fromId, reply_firstName, reply_lastName), createUserString(from_id, from_firstName, from_lastName)]))
                    forwardStaff(reply_msgId)

                elif text.startswith(_("cmd_info")):
                    bot.sendMessage(group, _("grp_info", [createUserString(reply_fromId, reply_firstName, reply_lastName), str(reply_fromId), str(db_users.search(where('chatId') == reply_fromId)[0]['warns'])]), "HTML")


        # Creator or Admin or Moderator or Manager message
        if getStatus(from_id) in ["creator", "admin", "moderator", "manager"]:
            if isReply:
                if text == _("cmd_del"):
                    bot.deleteMessage((group, reply_msgId))


        # Any user message
        cmdtext = text.replace(myusername, "")
        if "@admin" in text:
            if settings.Bot.useStaffGroup:
                bot.sendMessage(group, _("grp_staff_call"), "HTML")
                if isReply:
                    logStaff(_("log_staff_call_reply", [createUserString(from_id, from_firstName, from_lastName), createUserString(reply_fromId, reply_firstName, reply_lastName), text]))
                    forwardStaff(reply_msgId)
                else:
                    logStaff(_("log_staff_call_noreply", [createUserString(from_id, from_firstName, from_lastName), text]))

        elif cmdtext == _("cmd_staff"):
            staff = {"founders": "", "admins": "", "moderators": "", "managers": "", "helpers": ""}

            for x in [x["chatId"] for x in db_admins.search(where('status') == "creator")]:
                try:
                    staff['founders'] += "\n        " + createUserString(x, bot.getChatMember(group, x)['user']['first_name'], bot.getChatMember(group, x)['user']['last_name'])
                except KeyError:
                    staff['founders'] += "\n        " + createUserString(x, bot.getChatMember(group, x)['user']['first_name'], "")

            for x in [x["chatId"] for x in db_admins.search(where('status') == "admin")]:
                try:
                    staff['admins'] += "\n        " + createUserString(x, bot.getChatMember(group, x)['user']['first_name'], bot.getChatMember(group, x)['user']['last_name'])
                except KeyError:
                    staff['admins'] += "\n        " + createUserString(x, bot.getChatMember(group, x)['user']['first_name'], "")

            for x in [x["chatId"] for x in db_admins.search(where('status') == "moderator")]:
                try:
                    staff['moderators'] += "\n        " + createUserString(x, bot.getChatMember(group, x)['user']['first_name'], bot.getChatMember(group, x)['user']['last_name'])
                except KeyError:
                    staff['moderators'] += "\n        " + createUserString(x, bot.getChatMember(group, x)['user']['first_name'], "")

            for x in [x["chatId"] for x in db_admins.search(where('status') == "manager")]:
                try:
                    staff['managers'] += "\n        " + createUserString(x, bot.getChatMember(group, x)['user']['first_name'], bot.getChatMember(group, x)['user']['last_name'])
                except KeyError:
                    staff['managers'] += "\n        " + createUserString(x, bot.getChatMember(group, x)['user']['first_name'], "")

            for x in [x["chatId"] for x in db_admins.search(where('status') == "helper")]:
                try:
                    staff['helpers'] += "\n        " + createUserString(x, bot.getChatMember(group, x)['user']['first_name'], bot.getChatMember(group, x)['user']['last_name'])
                except KeyError:
                    staff['helpers'] += "\n        " + createUserString(x, bot.getChatMember(group, x)['user']['first_name'], "")

            message = _("grp_staff_title")
            if staff['founders'] != "":
                message += _("grp_staff_founder") + staff['founders']
            if staff['admins'] != "":
                message += _("grp_staff_admins") + staff['admins']
            if staff['moderators'] != "":
                message += _("grp_staff_moderators") + staff['moderators']
            if staff['managers'] != "":
                message += _("grp_staff_managers") + staff['managers']
            if staff['helpers'] != "":
                message += _("grp_staff_helpers") + staff['helpers']

            bot.sendMessage(group, message, parse_mode="HTML")

        elif cmdtext == _("cmd_rules"):
            data = settings.Messages.rules
            if data != "":
                bot.sendMessage(group, data, parse_mode="HTML", disable_web_page_preview=True)


        # Only Normal User Messages
        elif getStatus(from_id) == "user":

            # Global Silence Setting
            if settings.Moderation.globalSilenceActive:
                bot.deleteMessage((group, msgId))
                return 0

            # Control username
            if settings.Moderation.mustHaveUsername:
                if from_username == "":
                    bot.sendMessage(group, "🌐 "+from_firstName+", please, set an <b>username</b> in Telegram Settings", parse_mode="HTML", reply_to_message_id=msgId)

            # Detect spam from a Telegram Link
            if ("t.me/" in text) or ("t.dog/" in text) or ("telegram.me/" in text):
                if settings.Moderation.spamDetect:
                    previousWarns = int(db_users.search(where('chatId') == from_id)[0]['warns'])
                    db_users.update({'warns': str(previousWarns + 1)}, where('chatId') == from_id)
                    userWarns = int(db_users.search(where('chatId') == from_id)[0]['warns'])
                    bot.sendMessage(group, _("grp_warn_reason", [createUserString(from_id, from_firstName, from_lastName), str(userWarns), str(settings.Moderation.maxWarns),  "spam"]), parse_mode="HTML")
                    logStaff(_("log_warn_reason", [createUserString(from_id, from_firstName, from_lastName), str(userWarns), str(settings.Moderation.maxWarns)]))
                    forwardStaff(msgId)
                    bot.deleteMessage((group, msgId))
                    if userWarns >= settings.Moderation.maxWarns:
                        bot.kickChatMember(group, from_id)
                        db_users.update({'warns': 0}, where('chatId') == from_id)
                        bot.sendMessage(group, _("grp_ban_reason", [createUserString(from_id, from_firstName, from_lastName), _("str_max_warns")]))
                        logStaff(_("log_ban_reason", [createUserString(from_id, from_firstName, from_lastName),  createUserString(bot.getMe()['id'], myname, ""), _("str_max_warns")]))

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
                            previousWarns = int(db_users.search(where('chatId') == from_id)[0]['warns'])
                            db_users.update({'warns': str(previousWarns + 1)}, where('chatId') == from_id)
                            userWarns = int(db_users.search(where('chatId') == from_id)[0]['warns'])
                            bot.sendMessage(group, _("grp_warn_reason", [createUserString(from_id, from_firstName, from_lastName), str(userWarns), str(settings.Moderation.maxWarns), _("str_forward")]), parse_mode="HTML")
                            logStaff(_("log_warn_reason", [createUserString(from_id, from_firstName, from_lastName), createUserString(bot.getMe()['id'], myname, ""), _("str_forward"), str(userWarns), str(settings.Moderation.maxWarns)]))
                            forwardStaff(msgId)
                            bot.deleteMessage((group, msgId))
                            if userWarns >= settings.Moderation.maxWarns:
                                bot.kickChatMember(group, from_id)
                                db_users.update({'warns': 0}, where('chatId') == from_id)
                                bot.sendMessage(group, _("grp_ban_reason", [createUserString(from_id, from_firstName, from_lastName), _("str_max_warns")]), parse_mode="HTML")
                                logStaff(_("log_ban_reason", [createUserString(from_id, from_firstName, from_lastName), createUserString(bot.getMe()['id'], myname, ""), _("str_max_warns")]))
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
                        previousWarns = int(db_users.search(where('chatId') == from_id)[0]['warns'])
                        db_users.update({'warns': str(previousWarns + 1)}, where('chatId') == from_id)
                        userWarns = int(db_users.search(where('chatId') == from_id)[0]['warns'])
                        bot.sendMessage(group, _("grp_warn_reason", [createUserString(from_id, from_firstName, from_lastName), str(userWarns), str(settings.Moderation.maxWarns), _("str_porn")]), parse_mode="HTML")
                        logStaff(_("log_warn_reason", [createUserString(from_id, from_firstName, from_lastName), createUserString(bot.getMe()['id'], myname, ""), _("str_porn"), str(userWarns), str(settings.Moderation.maxWarns)]))
                        forwardStaff(msgId)
                        bot.deleteMessage((group, msgId))
                        if userWarns >= settings.Moderation.maxWarns:
                            bot.kickChatMember(group, from_id)
                            db_users.update({'warns': 0}, where('chatId') == from_id)
                            bot.sendMessage(group, _("grp_ban_reason", [createUserString(from_id, from_firstName, from_lastName), _("str_max_warns")]), parse_mode="HTML")
                            logStaff(_("log_ban_reason", [createUserString(from_id, from_firstName, from_lastName), _("str_max_warns")]))

                if settings.Moderation.detectViolence and not found:
                    output = imgparse_ai.check("offensive").set_file("file_" + str(msgId))
                    if output["offensive"]["prob"] > 0.3:
                        previousWarns = int(db_users.search(where('chatId') == from_id)[0]['warns'])
                        db_users.update({'warns': str(previousWarns + 1)}, where('chatId') == from_id)
                        userWarns = int(db_users.search(where('chatId') == from_id)[0]['warns'])
                        bot.sendMessage(group, _("grp_warn_reason", [createUserString(from_id, from_firstName, from_lastName), str(userWarns), str(settings.Moderation.maxWarns), _("str_offensive")]), parse_mode="HTML")
                        logStaff(_("log_warn_reason", [createUserString(from_id, from_firstName, from_lastName), createUserString(bot.getMe()['id'], myname, ""), _("str_offensive"), str(userWarns), str(settings.Moderation.maxWarns)]))
                        forwardStaff(msgId)
                        bot.deleteMessage((group, msgId))
                        if userWarns >= settings.Moderation.maxWarns:
                            bot.kickChatMember(group, from_id)
                            db_users.update({'warns': 0}, where('chatId') == from_id)
                            bot.sendMessage(group, _("grp_ban_reason", [createUserString(from_id, from_firstName, from_lastName), _("str_max_warns")]), parse_mode="HTML")
                            logStaff(_("log_ban_reason", [createUserString(from_id, from_firstName, from_lastName), _("str_max_warns")]))
                        os.remove("file_" + str(msgId))

            # Word Blacklist Control
            if any(word in text.lower() for word in settings.Moderation.wordBlacklist):
                logStaff(_("log_blacklist_word", [createUserString(from_id, from_firstName, from_lastName)]))
                forwardStaff(msgId)

            # User Name Character Limit
            if settings.Moderation.controlUserName:
                if len(from_firstName+from_lastName) > settings.Moderation.userNameCharacterLimit:
                    bot.sendMessage(group, _("grp_shorter_name", [createUserString(from_id, from_firstName, from_lastName)]), parse_mode="HTML", reply_to_message_id=msgId)



print("Bot started...")
reloadAdmins()
bot.message_loop({'chat': handle})
while True:
    time.sleep(60)

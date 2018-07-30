class Bot:
    token = '123456789:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    groupId = -1001234567890
    useStaffGroup = True
    staffGroupId = -1001234567890


class Databases:
    admins = 'admins.json'
    users = 'users.json'


class Messages:
    welcome = "Hi, <b>{{name}}</b>!\nWelcome in the {{group_name}} group!"
    rules = ""


class Moderation:
    showWelcomeMessage = True
    deleteCommands = True
    spamDetect = True
    scanSendedFiles = True
    forwardSpamDetect = True
    detectPorn = True
    detectViolence = True
    mustHaveUsername = True
    controlUserName = True
    maxWarns = 3
    userNameCharacterLimit = 32
    channelsWhitelist = ["durov", "telegram"]
    wordBlacklist = ["foo", "bar"]


class virusTotal:
    url = 'https://www.virustotal.com/vtapi/v2/file/report'
    apikey = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'


class sightEngine:
    user = '1234567890'
    key = 'xxxxxxxxxxxxxxxxxxxx'
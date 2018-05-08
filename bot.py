import telepot
bot = None
groupId = None


def initialize():
    global bot
    global groupId
    try:
        tokenFile = open("bot_token.txt", "r")
        token = str(tokenFile.readline())
        bot = telepot.Bot(token)
        tokenFile.close()
    except FileNotFoundError:
        tokenFile = open("bot_token.txt", "w")
        token = str(input("Token File not found. Please insert the HTTP API Bot Token: "))
        bot = telepot.Bot(token)
        tokenFile.write(token)
        tokenFile.close()
    try:
        groupFile = open("group_id.txt", "r")
        groupId = int(groupFile.readline())
        groupFile.close()
    except FileNotFoundError:
        groupFile = open("group_id.txt", "w")
        groupId = int(input("Group ID File not found. Please insert the group Chat ID: "))
        groupFile.write(str(groupId))
        groupFile.close()


initialize()
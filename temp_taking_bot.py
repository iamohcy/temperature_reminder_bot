TOKEN = "1339607682:AAEDlfVwFDigVVDNXFY22wmy7l1R_Xikm5I"

# TODO:
    # 1) don't let /begin work multiple times
    # 1) solve issue with empty entries, use original word instead
    # 2) solve issue with multiple ins
    # 3) solve issue with no past words

# 1) Fixed issue with /begin working multiple times
# 2) Fixed issue where original words could be re-used
# 3) Fixed issue where multiple /in commands would screw things update
# 4) Fixed issue where empty or multi-word entries were allowed
# 5) Added an "/out" command to allow for temporarily leaving the game
# 6) Modified "/help" command to print more useful information
# 7) Added reminder for new players to add the bot at @medium_boardgame_bot
# 8) Game now stops when enough players have left
# 9) No longer need /enter command

import telegram
from telegram.ext import Updater, MessageHandler, CommandHandler, Filters, PicklePersistence
import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

import datetime
import pytz

FIRST_TEMP_MSG = 'First Temperature Logged'
SECOND_TEMP_MSG = 'Second Temperature Logged (> 4 hours later)'

def deregister_user(update, context):
    userId = update.message.from_user.id
    chat_id = update.message.chat_id
    name = update.message.from_user.first_name

    if (chat_id > 0):
        context.bot.send_message(chat_id=chat_id, text="This command can only be sent in a group channel!", parse_mode=telegram.ParseMode.HTML)
        return

    if "membersDict" not in context.chat_data:
        context.bot.send_message(chat_id=update.message.chat_id, text="No one has registered in this chat yet!", parse_mode=telegram.ParseMode.HTML)
    else:
        if userId not in context.chat_data["membersDict"]:
            context.bot.send_message(chat_id=update.message.chat_id, text="<b>%s</b> has not yet registered for temperature reminders!" % name, parse_mode=telegram.ParseMode.HTML)
        else:
            member = context.chat_data["membersDict"][userId]
            if member["remindMe"]:
                member["remindMe"] = False
                context.bot.send_message(chat_id=update.message.chat_id, text="Reminders are now disabled for <b>%s</b>!" % member["name"], parse_mode=telegram.ParseMode.HTML)
            else:
                context.bot.send_message(chat_id=update.message.chat_id, text="Reminders are already disabled for <b>%s</b>!" % member["name"], parse_mode=telegram.ParseMode.HTML)

def register_user(update, context):

    userId = update.message.from_user.id
    name = update.message.from_user.first_name
    chat_id = update.message.chat_id

    if "chat_data" not in context.user_data:
        context.user_data["chat_data"] = {}

    context.user_data["chat_data"][chat_id] = context.chat_data

    if (chat_id > 0):
        context.bot.send_message(chat_id=chat_id, text="This command can only be sent in a group channel!", parse_mode=telegram.ParseMode.HTML)
        return

    # *********************************************
    # BOT INITIALIZATION
    # *********************************************
    if "runningChatIds" not in context.bot_data:
        context.bot_data["runningChatIds"] = set()
        context.bot_data["all_chat_data"] = {}

    if chat_id not in context.bot_data["runningChatIds"]:
        context.bot_data["runningChatIds"].add(chat_id)
        context.bot_data["all_chat_data"][chat_id] = context.chat_data

    if "membersDict" not in context.chat_data:
        context.chat_data["membersDict"] = {}
        context.chat_data["membersArray"] = []
        context.chat_data["chat_id"] = chat_id
        context.chat_data["title"] = update.message.chat.title

    if update.message.chat.title != context.chat_data["title"]:
        context.chat_data["title"] = update.message.chat.title
    # *********************************************

    try:
        context.bot.sendMessage(chat_id=userId, text="You have successfully joined the temperature reminder system", parse_mode=telegram.ParseMode.HTML)

        if userId not in context.chat_data["membersDict"]:
            member = {"id":userId, "name": name, "firstTempTaken": False, "secondTempTaken": False, "remindMe": True}
            context.chat_data["membersDict"][userId] = member
            context.chat_data["membersArray"].append(member)

            context.bot.send_message(chat_id=update.message.chat_id, text="<b>%s</b> has registered for temperature reminders!" % name, parse_mode=telegram.ParseMode.HTML)

            sendTemperatureRequest(member, context.chat_data, context.bot)
        else:
            member = context.chat_data["membersDict"][userId]

            if member["remindMe"]:
                context.bot.send_message(chat_id=update.message.chat_id, text="<b>%s</b> has already registered for temperature reminders!" % name, parse_mode=telegram.ParseMode.HTML)
            else:
                member["remindMe"] = True
                context.bot.send_message(chat_id=update.message.chat_id, text="<b>%s</b> has re-enabled temperature reminders!" % name, parse_mode=telegram.ParseMode.HTML)
    except:
         context.bot.send_message(chat_id=update.message.chat_id, text="%s has to click @temp_taking_reminder_bot and press 'Start' to add the bot before registering. Please do so first, and type /in again." % name)

def sendTemperatureRequest(member, chat_data, chat_bot):
    custom_keyboard  = [
        [ FIRST_TEMP_MSG ],
        [ SECOND_TEMP_MSG ],
    ]
    reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard, selective=True)
    todayStr = datetime.date.today().strftime("%a, %d/%m/%Y")

    reminderStr = ""

    if not member["firstTempTaken"]:
        reminderStr = "Hi %s, you have not logged your <b>morning</b> 🌡️ yet today (%s)" % (member["name"], todayStr)
    elif not member["secondTempTaken"]:
        reminderStr = "Hi %s, you have not logged your <b>afternoon</b> 🌡️ yet today (%s)" % (member["name"], todayStr)

    try:
        if (not member["firstTempTaken"]) or (not member["secondTempTaken"]):
            chat_bot.sendMessage(chat_id=member["id"], text=reminderStr, reply_markup=reply_markup, parse_mode=telegram.ParseMode.HTML)
        else:
            chat_bot.sendMessage(chat_id=member["id"], text="You have logged both temperatures for today, nicely done!", reply_markup=reply_markup)

    except:
        if "firstTry" not in member:
            member["firstTry"] = True
        else:
            chat_bot.send_message(chat_id=chat_data["chat_id"], text="<b>%s</b> needs to add the bot by clicking @wavelength_boardgame_bot first before typing /in again to join the game!" % name, parse_mode=telegram.ParseMode.HTML)

def sendTemperatureRequestToAll(chat_data, chat_id, chat_bot):

    for member in chat_data["membersArray"]:
        if member["remindMe"] and not (member["firstTempTaken"] and member["secondTempTaken"]):
            sendTemperatureRequest(member, chat_data, chat_bot)

def unsubscribe(update, context):
    bot_data = context.bot_data

    name = update.message.from_user.first_name
    chat_data = context.chat_data
    chat_id = update.message.chat_id
    userId = update.message.from_user.id

    if (chat_id > 0):
        context.bot.send_message(chat_id=chat_id, text="This command can only be sent in a group channel!", parse_mode=telegram.ParseMode.HTML)
        return

    if "subscriberIds" not in chat_data:
        chat_data["subscriberIds"] = set()

    if userId in chat_data["subscriberIds"]:
        chat_data["subscriberIds"].remove(userId)
        context.bot.send_message(chat_id=chat_id, text="%s has unsubscribed from the final reminder list" % name, parse_mode=telegram.ParseMode.HTML)
    else:
        context.bot.send_message(chat_id=chat_id, text="%s has not yet subscribed to the final reminder list" % name, parse_mode=telegram.ParseMode.HTML)

def subscribe(update, context):
    bot_data = context.bot_data

    name = update.message.from_user.first_name
    chat_data = context.chat_data
    chat_id = update.message.chat_id
    userId = update.message.from_user.id

    if (chat_id > 0):
        context.bot.send_message(chat_id=chat_id, text="This command can only be sent in a group channel!", parse_mode=telegram.ParseMode.HTML)
        return

    if "subscriberIds" not in chat_data:
        chat_data["subscriberIds"] = set()

    if userId in chat_data["subscriberIds"]:
        context.bot.send_message(chat_id=chat_id, text="%s has already subscribed to the final reminder list" % name, parse_mode=telegram.ParseMode.HTML)
    else:
        chat_data["subscriberIds"].add(userId)
        context.bot.send_message(chat_id=chat_id, text="%s has subscribed to the final reminder list" % name, parse_mode=telegram.ParseMode.HTML)

def remind_all(update, context):
    bot_data = context.bot_data

    chat_data = context.chat_data
    chat_id = update.message.chat_id

    if (chat_id > 0):
        context.bot.send_message(chat_id=chat_id, text="This command can only be sent in a group channel!", parse_mode=telegram.ParseMode.HTML)
        return

    if "membersArray" in chat_data:
        sendTemperatureRequestToAll(chat_data, chat_id, context.bot)

def list_all(update, context):
    bot_data = context.bot_data

    chat_data = context.chat_data
    chat_id = update.message.chat_id

    if (chat_id > 0):
        context.bot.send_message(chat_id=chat_id, text="This command can only be sent in a group channel!", parse_mode=telegram.ParseMode.HTML)
        return

    if "membersArray" in chat_data:
        membersText = "<b>The following individuals are registered for temperature reminders:</b>"
        for member in chat_data["membersArray"]:
            membersText += "%s\n" % member["name"]

        context.bot.send_message(chat_id=chat_id, text=membersText, parse_mode=telegram.ParseMode.HTML)

def clear_temperature_logs(context):
    print("CLEARING DATA")

    bot_data = context.bot_data
    if "runningChatIds" not in bot_data:
        return

    for chat_id in bot_data["runningChatIds"]:
        chat_data = bot_data["all_chat_data"][chat_id]
        for member in chat_data["membersArray"]:
            member["firstTempTaken"] = False
            member["secondTempTaken"] = False

def daily_temperature_checks_subscribers(context):
    check_time = context.job.context["check_time"]
    print("DAILY TEMP CHECKS (Subscribers) - " + check_time)

    bot_data = context.bot_data
    if "runningChatIds" not in bot_data:
        return

    for chat_id in bot_data["runningChatIds"]:
        chat_data = bot_data["all_chat_data"][chat_id]
        checkTemperatureLogs(chat_data, chat_id, context.bot, check_time, sendToUserIds=chat_data["subscriberIds"])

def daily_temperature_reminders(context):
    print("DAILY TEMP REMINDERS")

    bot_data = context.bot_data
    if "runningChatIds" not in bot_data:
        return

    for chat_id in bot_data["runningChatIds"]:
        chat_data = bot_data["all_chat_data"][chat_id]
        sendTemperatureRequestToAll(chat_data, chat_id, context.bot)

def daily_temperature_final_reminders(context):
    finalReminderStartTime = datetime.time(18,30,00,0000)

    timezone = pytz.timezone("Asia/Singapore")
    now = datetime.datetime.now(timezone).time()
    if (now > finalReminderStartTime):
        print("DAILY TEMP FINAL REMINDERS: " + str(now))
        daily_temperature_reminders(context)

def daily_temperature_checks(context):
    check_time = context.job.context["check_time"]
    print("DAILY TEMP CHECKS - " + check_time)

    bot_data = context.bot_data
    if "runningChatIds" not in bot_data:
        return

    for chat_id in bot_data["runningChatIds"]:
        chat_data = bot_data["all_chat_data"][chat_id]
        print(chat_id)
        print(chat_data)
        # checkTemperatureLogs(chat_data, chat_id, context.bot, check_time)

def check_temperature_logs(update, context):

    chat_id = update.message.chat_id
    chat_data = context.chat_data

    checkTemperatureLogs(chat_data, chat_id, context.bot, "afternoon")

def getResultEmoji(result):
    if result:
        return "✔"
    else:
        return "❌"

def checkTemperatureLogs(chat_data, chat_id, chat_bot, check_time, sendToUserIds=None):

    time_emoji = "🌅"
    if check_time != "morning":
        time_emoji = "🌃"

    resultsText = "<b>Temperature log records " + time_emoji + "</b>\n"
    notCompletedBoth = []
    notCompletedFirst = []

    for member in chat_data["membersArray"]:

        if check_time == "morning":
            if (not member["firstTempTaken"]) and (sendToUserIds == None):
                sendTemperatureRequest(member, chat_data, chat_bot)
        else:
            if ((not member["firstTempTaken"]) or (not member["secondTempTaken"])) and (sendToUserIds == None):
                sendTemperatureRequest(member, chat_data, chat_bot)

        if not member["firstTempTaken"]:
            notCompletedFirst.append(member["name"])

        if not (member["firstTempTaken"] and member["secondTempTaken"]):
            notCompletedBoth.append(member["name"])

        if member["remindMe"]:
            resultsText += "%s -> 1st temp. logged (%s), 2nd temp. logged (%s)\n" % (member["name"], getResultEmoji(member["firstTempTaken"]), getResultEmoji(member["secondTempTaken"]))

    if check_time == "morning":
        if len(notCompletedFirst) > 0:
            resultsText += "\n<b>Have not completed morning temperature logging:</b>\n"
            resultsText += ", ".join(notCompletedFirst)
        else:
            resultsText += "\n🏆Everyone has completed the <b>morning</b> temperature logging!🏆\n"
    else:
        if len(notCompletedBoth) > 0:
            resultsText += "\n<b>Have not completed both:</b>\n"
            resultsText += ", ".join(notCompletedBoth)
        else:
            resultsText += "\n<b>🏆Everyone has completed <b>both</b> temperature loggings!🏆</b>\n"

    if sendToUserIds == None:
        chat_bot.send_message(chat_id=chat_id, text=resultsText, parse_mode=telegram.ParseMode.HTML)
    else:
        for userId in sendToUserIds:
            resultsText = ("Final daily update for - <b>%s</b>:\n\n" % chat_data["title"]) + resultsText
            chat_bot.send_message(chat_id=userId, text=resultsText, parse_mode=telegram.ParseMode.HTML)

def help(update, context):
    chat_id = update.message.chat_id

    if (chat_id > 0):
        context.bot.send_message(chat_id=chat_id, text="This command can only be sent in a group channel!", parse_mode=telegram.ParseMode.HTML)
        return

    message = "Welcome to the Telegram Bot for DSO Temperature Reminders!\n\n"
    message += "<b>Instructions:</b>\n"
    message += "1) if you have not already done so, click on @temp_taking_reminder_bot and press 'Start' so the bot can send you reminders.\n"
    message += "2) Type /in in your <b>group chat</b> if you wish to join this temperature reminder system (and /out to leave.)\n"
    message += "3) Go to your private chat with the bot, named 'DSO Temperature Taking Reminder Bot', and use the buttons to record down when you have taken your AM/PM temperatures.\n\n"
    message += "<b>Commands:</b>\n"
    message += "/in - Register yourself in the temperature reminder system\n"
    message += "/out - Stop temperature reminders for yourself\n"
    message += "/check - Check who has finished the temperature reminders for today\n"
    message += "/remind - Remind members who have not finished logging their temperatures for today to do so\n"
    message += "/subscribe - Subscribe to daily summary sent at 1900H\n"
    message += "/unsubscribe - Unsubscribe from daily summary\n"
    message += "/help - Help text\n"

    context.bot.send_message(chat_id=update.message.chat_id, text=message, parse_mode=telegram.ParseMode.HTML)

def admin(update, context):
    bot_data = context.bot_data
    if "runningChatIds" not in bot_data:
        return

    print (bot_data)
    for chat_id in bot_data["runningChatIds"]:
        chat_data = bot_data["all_chat_data"][chat_id]
        print(chat_id)
        print(chat_data)

    print(context.user_data["chat_data"])

def enter(update, context):

    print("*****************************************")
    if (update.message == None):
        return

    og_chat_data = context.chat_data
    print(og_chat_data)
    user_data = context.user_data
    chat_id = update.message.chat_id
    userId = update.message.from_user.id
    msgText = update.message.text



    user_data = context.dispatcher.user_data[id]

    # Guarantees that this is private chat with player, rather than a group chat
    if (chat_id > 0):
        if ("remindMe" not in context.user_data) or (not context.user_data["remindMe"]):
            context.bot.send_message(chat_id=userId, text="You are not in any temperature reminding groups!", parse_mode=telegram.ParseMode.HTML)
            return

        for chat_id in context.user_data["chat_data"]:
            chat_data = context.user_data["chat_data"][chat_id]
            print(chat_data)
            member = chat_data["membersDict"][userId]

            if msgText == FIRST_TEMP_MSG:
                member["firstTempTaken"] = True
            elif msgText == SECOND_TEMP_MSG:
                member["secondTempTaken"] = True

        if msgText == FIRST_TEMP_MSG:
            member["firstTempTaken"] = True
            context.bot.send_message(chat_id=userId, text="First temperature log noted!", parse_mode=telegram.ParseMode.HTML)
        elif msgText == SECOND_TEMP_MSG:
            member["secondTempTaken"] = True
            context.bot.send_message(chat_id=userId, text="Second temperature log noted!", parse_mode=telegram.ParseMode.HTML)

        context.bot.send_message(chat_id=userId, text="Current status: 1st Log - [%s], 2nd Log - [%s]" % (getResultEmoji(member["firstTempTaken"]), getResultEmoji(member["secondTempTaken"])), parse_mode=telegram.ParseMode.HTML)
    print("*****************************************")

def main():
    persistence_pickle = PicklePersistence(filename='persistence_pickle')

    updater = Updater(token=TOKEN, persistence=persistence_pickle, use_context=True)

    job = updater.job_queue

    d = datetime.datetime.now()
    timezone = pytz.timezone("Asia/Singapore")
    d_aware = timezone.localize(d)

    morningReminderTime = datetime.time(10, 00, 00, 000000, tzinfo=d_aware.tzinfo)
    morningReminderJob = job.run_daily(daily_temperature_reminders, morningReminderTime, days=(0,1,2,3,4))

    afternoonReminderTime = datetime.time(17, 30, 00, 000000, tzinfo=d_aware.tzinfo)
    afternoonReminderJob = job.run_daily(daily_temperature_reminders, afternoonReminderTime, days=(0,1,2,3,4))

    morningCheckTime = datetime.time(10, 30, 00, 000000, tzinfo=d_aware.tzinfo)
    morningCheckJob = job.run_daily(daily_temperature_checks, morningCheckTime, days=(0,1,2,3,4), context={"check_time":"morning"})

    afternoonCheckTime = datetime.time(1, 47, 55, 000000, tzinfo=d_aware.tzinfo)
    afternoonCheckJob = job.run_daily(daily_temperature_checks, afternoonCheckTime, days=(0,1,2,3,4,5,6), context={"check_time":"afternoon"})

    dailyResultsTime = datetime.time(19, 00, 00, 000000, tzinfo=d_aware.tzinfo)
    dailyResultsJob = job.run_daily(daily_temperature_checks_subscribers, dailyResultsTime, days=(0,1,2,3,4), context={"check_time":"afternoon"})

    clearTime = datetime.time(00,00,00,000000, tzinfo=d_aware.tzinfo)
    clearJob = job.run_daily(clear_temperature_logs, clearTime, days=(0,1,2,3,4,5,6))

    finalReminderTime = datetime.time(18, 00, 00, 000000, tzinfo=d_aware.tzinfo)
    reminderJob = job.run_repeating(daily_temperature_final_reminders, 1800, first=finalReminderTime) #1800s = 30min

    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('in',register_user))
    dispatcher.add_handler(CommandHandler('out',deregister_user))
    dispatcher.add_handler(CommandHandler('check',check_temperature_logs))
    dispatcher.add_handler(CommandHandler('remind',remind_all))
    dispatcher.add_handler(CommandHandler('subscribe',subscribe))
    dispatcher.add_handler(CommandHandler('unsubscribe',unsubscribe))
    dispatcher.add_handler(CommandHandler('list',list_all))
    dispatcher.add_handler(CommandHandler('admin',admin))
    dispatcher.add_handler(CommandHandler('help',help))

    dispatcher.add_handler(MessageHandler(Filters.text, enter))

    # dispatcher.add_handler(CommandHandler('put', put))
    # dispatcher.add_handler(CommandHandler('get', get))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

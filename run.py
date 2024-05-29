import os
import re
import datetime
import Scheduled
import Functions
import ExcelProcesser
import DateChecker
import ParadeState as ps
from ujson import load, dump
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import filters, ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler

from keep_alive import keep_alive
keep_alive()





# |==================================================================================================|
# |                                                                                                  |
# |                                   !!! RUN THIS FILE !!!                                          |
# |                                                                                                  |
# | 1. Loads in variable API_KEY from .env file                                                      |
# | 2. Runs Scheduled.GetGlobalVariables() once, when file is ran                                    |
# |    --> subsequently runs last day of every month to update global variable for the next month    |
# | 3. Contains all the scheduling of functions in Scheduled.py                                      |
# |    --> can be found under bot.job_queue.(run_repeating/run_daily/run_monthly)                    |
# | 4. Contains all the functions for each command in the bot                                        |
# |    --> can be found under bot.add_handler                                                        |
# | 5. bot.run_polling() - polls telegram to check for command sent                                  |
# |                                                                                                  |
# |==================================================================================================|

async def Start(update, context):
    chatID = update.effective_chat.id
    username = update.effective_chat.username

    with open('data/reference/username_ref.json') as file:
        usernameRef = load(file)
    
    usernameRef[str(chatID)] = {'cos': '', 'username': username}

    with open('data/reference/username_ref.json', 'w') as file:
        dump(usernameRef, file, indent=1)
    
    await context.bot.send_message(chatID, '/help to view commands\n/cos to set rank and name')

async def Help(update, context):
    chatID = update.effective_chat.id

    with open('data/text/help.txt') as file:
        for msg in file.read().split('---SPLIT---'):
            await context.bot.send_message(chatID, msg)

async def TermsOfReference(update, context):
    chatID = update.effective_chat.id

    with open('data/text/terms_of_reference.txt') as file:
        await context.bot.send_message(chatID, file.read(), parse_mode='MarkdownV2', disable_web_page_preview=True)

async def Escort(update, context):
    chatID = update.effective_chat.id

    with open('data/text/escort.txt') as file:
        await context.bot.send_message(chatID, file.read())

async def FullPS(update, context):
    chatID = update.effective_chat.id
    dateDT = DateChecker.SingleDate(context.args)

    if dateDT is not None:
        dataManager = ps.DataManager(chatID)
        await context.bot.send_message(chatID, dataManager.FullPS(dateDT))
        
        if dataManager.categorisedPersonnel['UNKNOWN']:
            await context.bot.send_message(chatID, 'UNKNOWN:\n' + '\n'.join(person.displayFull for person in dataManager.categorisedPersonnel["UNKNOWN"]))
    else:
        await context.bot.send_message(chatID, 'Invalid date')

async def Weekend(update, context):
    chatID = update.effective_chat.id
    startDateDT, endDateDT = DateChecker.DoubleDate(context.args, 9)

    if startDateDT == 'tooFar':
        await context.bot.send_message(chatID, 'Dates are too far apart')
    elif startDateDT is not None:
        dataManager = ps.DataManager()
        await context.bot.send_message(chatID, dataManager.CombinedBottomPS(startDateDT, endDateDT))
    else:
        await context.bot.send_message(chatID, 'Invalid dates')

async def DutyForecast(update, context):
    chatID = update.effective_chat.id
    startDateDT, endDateDT = DateChecker.DoubleDate(context.args, 30, False, False)

    if startDateDT == 'tooFar':
        await context.bot.send_message(chatID, 'Dates are too far apart')
    elif startDateDT is not None:
        ExcelProcesser.ObtainDutyForecastExcel(startDateDT, endDateDT)
        await context.bot.send_document(chatID, open('data/excel files/out/dutyForecast.xlsx', 'rb'))
    else:
        await context.bot.send_message(chatID, 'Invalid dates')

async def OverrideListPrint(update, context):
    chatID = update.effective_chat.id
    overrideList = Functions.OverrideListCategoriser()

    for x in overrideList:
        await context.bot.send_message(chatID, x)

async def OverrideListEdit_FIRST(update, context):
    chatID = update.effective_chat.id
    keyboard = [['ADD STATUS'], ['REMOVE STATUS']]

    await context.bot.send_message(chatID, 'Select what you would like to do\n/exit to exit', reply_markup = ReplyKeyboardMarkup(keyboard))
    return 1

async def OverrideListEdit_SECOND_ADD(update, context):
    chatID = update.effective_chat.id

    with open('data/personnel/alpha.json') as file:
        alphaList = load(file)
    
    keyboard = [[x['displayNoStatus']] for x in alphaList]

    await context.bot.send_message(chatID, 'Select a personnel\n/exit to exit', reply_markup = ReplyKeyboardMarkup(keyboard))
    return 2

async def OverrideListEdit_THIRD_ADD(update, context):
    chatID = update.effective_chat.id
    DisplayToSheet = Functions.ObtainMap('displayNoStatus', 'sheetName')
    context.user_data['sheetName'] = DisplayToSheet[update.message.text]

    keyboard = [['MC', 'OSL', 'OFF'], ['LL', 'MA', 'RSO'], ['CCL', 'PCL', 'HL'], ['UL', 'CL', 'FFI']]

    await context.bot.send_message(
        chatID,
        'Select a status\nFor custom statuses, type using the keyboard\n/exit to exit',
        reply_markup = ReplyKeyboardMarkup(keyboard)
    )

    return 3

async def OverrideListEdit_FOURTH_ADD(update, context):
    chatID = update.effective_chat.id
    context.user_data['sheetStatus'] = re.sub('\s*/\s*', '/', update.message.text.upper().strip())

    await context.bot.send_message(
        chatID,
        'Input: [START DATE] [END DATE]\n/exit to exit',
        reply_markup = ReplyKeyboardRemove()
    )

    return 4

async def OverrideListEdit_FIFTH_ADD(update, context):
    chatID = update.effective_chat.id
    startDateDT, endDateDT = DateChecker.DoubleDate(update.message.text.split(), None, False, False)

    if startDateDT is not None:
        with open('data/override/parade_state_override.json') as file:
            psOverride = load(file)
        
        psOverride.append(
            {
                'sheetName': context.user_data['sheetName'],
                'sheetStatus': context.user_data['sheetStatus'],
                'startDate': Functions.DateConverter(startDateDT),
                'endDate': Functions.DateConverter(endDateDT)
            }
        )

        with open('data/override/parade_state_override.json', 'w') as file:
            dump(psOverride, file, indent = 1)
        
        await context.bot.send_message(chatID, 'Successfully added! Use /ol to view full override list.')
        return ConversationHandler.END
    else:
        await context.bot.send_message(chatID, 'Invalid dates\nRetype dates or /exit to exit')
        return 4

async def OverrideListEdit_SECOND_REMOVE(update, context):
    chatID = update.effective_chat.id
    with open('data/override/parade_state_override.json') as file:
        context.user_data['psOverride'] = load(file)
    
    if not context.user_data['psOverride']:
        await context.bot.send_message(chatID, 'Override list is empty', reply_markup = ReplyKeyboardRemove())
        return ConversationHandler.END
    
    context.user_data['resultDict'] = Functions.ObtainResultDict(Functions.ObtainMap('sheetName', 'displayNoStatus'), context.user_data['psOverride'])

    keyboard = [[x[0]] for x in context.user_data['resultDict'].values()]

    await context.bot.send_message(chatID, Functions.OverrideListCategoriser(False, True)[0])
    await context.bot.send_message(chatID, 'Select personnel whose status you want to remove\n/exit to exit', reply_markup = ReplyKeyboardMarkup(keyboard))
    return 5

async def OverrideListEdit_THIRD_REMOVE(update, context):
    chatID = update.effective_chat.id
    displayToSheet = Functions.ObtainMap('displayNoStatus', 'sheetName')
    context.user_data['sheetNameToRemove'] = displayToSheet[update.message.text]

    keyboard = [[x] for x in context.user_data['resultDict'][context.user_data['sheetNameToRemove']][1:]]

    await context.bot.send_message(chatID, 'Select status which you want to remove\n/exit to exit', reply_markup = ReplyKeyboardMarkup(keyboard))
    return 6

async def OverrideListEdit_FOURTH_REMOVE(update, context):
    chatID = update.effective_chat.id
    messageSplit = update.message.text.split()

    toMatch = {
        'sheetName': context.user_data['sheetNameToRemove'],
        'sheetStatus': re.sub('\(|\)', '', messageSplit[3]),
        'startDate': messageSplit[0],
        'endDate': messageSplit[2]
    }

    context.user_data['psOverride'] = [x for x in context.user_data['psOverride'] if x != toMatch]

    with open('data/override/parade_state_override.json', 'w') as file:
        dump(context.user_data['psOverride'], file, indent=1)
    
    await context.bot.send_message(chatID, 'Successfully removed! Use /ol to view full override list.', reply_markup = ReplyKeyboardRemove())
    return ConversationHandler.END

async def RationsListPrint(update, context):
    chatID = update.effective_chat.id
    await context.bot.send_message(chatID, Functions.RationsListCategoriser())

async def RationsListEdit_FIRST(update, context):
    chatID = update.effective_chat.id
    keyboard = [['EDIT EVERYDAY'], ['EDIT SPECIFIC DAYS'], ['REMOVE SPECIFIC DAYS']]

    await context.bot.send_message(chatID, 'Select one\n/exit to exit', reply_markup = ReplyKeyboardMarkup(keyboard))
    return 1

async def RationsListEdit_SECOND_EVERYDAY(update, context):
    chatID = update.effective_chat.id
    await context.bot.send_message(chatID, 'NOTE: if no rations indented, put 0', reply_markup = ReplyKeyboardRemove())
    await context.bot.send_message(chatID, 'Input: [BREAKFAST PAX] [LUNCH PAX] [DINNER PAX]\n/exit to exit')
    return 2

async def RationsListEdit_THIRD_EVERYDAY(update, context):
    chatID = update.effective_chat.id

    if re.search(r'^[0-9]{1,2} [0-9]{1,2} [0-9]{1,2}$', update.message.text):
        msgSplit = [int(x) for x in update.message.text.split()]

        with open('data/override/rations.json') as file:
            rations = load(file)

        rations['everyday'] = msgSplit

        with open('data/override/rations.json', 'w') as file:
            dump(rations, file, indent = 1)

        await context.bot.send_message(chatID, 'Successfully updated! Use /rl to view full rations list.')
        return ConversationHandler.END
    else:
        await context.bot.send_message(chatID, 'Invalid input\nRetype input or /exit to exit')
        return 2

async def RationsListEdit_SECOND_SPECIFIC(update, context):
    chatID = update.effective_chat.id
    await context.bot.send_message(chatID, 'NOTE: if no rations indented, put 0', reply_markup = ReplyKeyboardRemove())
    await context.bot.send_message(chatID, 'Input: [DATE] [BREAKFAST PAX] [LUNCH PAX] [DINNER PAX]\n/exit to exit')
    return 3

async def RationsListEdit_THIRD_SPECIFIC(update, context):
    chatID = update.effective_chat.id
    
    if re.search(r'^[0-9]{6} [0-9]{1,2} [0-9]{1,2} [0-9]{1,2}$', update.message.text):
        dateRAW = update.message.text[:6]
        dateDT = DateChecker.SingleDate([dateRAW])

        if dateDT is not None:
            msgSplit = [int(x) for x in update.message.text.split()[1:]]

            with open('data/override/rations.json') as file:
                rations = load(file)

            rations[dateRAW] = msgSplit
        
            with open('data/override/rations.json', 'w') as file:
                dump(rations, file, indent = 1)
            
            await context.bot.send_message(chatID, 'Successfully updated! Use /rl to view full rations list.')
            return ConversationHandler.END
    
    await context.bot.send_message(chatID, 'Invalid input\nRetype input or /exit to exit')
    return 3

async def RationsListEdit_SECOND_REMOVE(update, context):
    chatID = update.effective_chat.id

    with open('data/override/rations.json') as file:
        rations = load(file)

    keyboard = [[x] for x in rations if x!= 'everyday']

    if not keyboard:
        await context.bot.send_message(chatID, 'No dates to remove', reply_markup = ReplyKeyboardRemove())
        return ConversationHandler.END

    await context.bot.send_message(chatID, 'Select date to remove\n/exit to exit', reply_markup = ReplyKeyboardMarkup(keyboard))
    return 4

async def RationsListEdit_THIRD_REMOVE(update, context):
    chatID = update.effective_chat.id

    with open('data/override/rations.json') as file:
        rations = load(file)
    
    del rations[update.message.text]

    with open('data/override/rations.json', 'w') as file:
        dump(rations, file, indent = 1)
    
    await context.bot.send_message(chatID, 'Successfully removed! Use /rl to view full rations list.', reply_markup = ReplyKeyboardRemove())
    return ConversationHandler.END

async def PersonnelListPrint(update, context):
    chatID = update.effective_chat.id
    ExcelProcesser.ObtainFlightPersonnelExcel(False)
    await context.bot.send_document(chatID, open('data/excel files/out/flightPersonnel.xlsx', 'rb'))

async def PersonnelListEdit_FIRST(update, context):
    chatID = update.effective_chat.id
    ExcelProcesser.ObtainFlightPersonnelExcel(True)
    await context.bot.send_document(
        chatID,
        open('data/excel files/out/flightPersonnel.xlsx', 'rb'),
        caption = 'Instructions inside\n/exit to exit'
    )
    
    return 1

async def PersonnelListEdit_SECOND(update, context):
    chatID = update.effective_chat.id
    file = await update.message.effective_attachment.get_file()
    await file.download_to_drive('data/excel files/in/flightPersonnel.xlsx')

    ExcelProcesser.EditFlightPersonnelExcel()
    
    await context.bot.send_message(chatID, 'Successfully updated! Use /pl to view all personnel.')
    return ConversationHandler.END

async def StatusReferenceListPrint(update, context):
    chatID = update.effective_chat.id
    ExcelProcesser.ObtainStatusReferenceExcel(False)
    await context.bot.send_document(chatID, open('data/excel files/out/statusReference.xlsx', 'rb'))

async def StatusReferenceListEdit_FIRST(update, context):
    chatID = update.effective_chat.id
    ExcelProcesser.ObtainStatusReferenceExcel(True)
    await context.bot.send_document(
        chatID,
        open('data/excel files/out/statusReference.xlsx', 'rb'),
        caption = 'Instructions inside\n/exit to exit'
    )
    
    return 1

async def StatusReferenceListEdit_SECOND(update, context):
    chatID = update.effective_chat.id
    file = await update.message.effective_attachment.get_file()
    await file.download_to_drive('data/excel files/in/statusReference.xlsx')

    ExcelProcesser.EditStatusReferenceExcel()
    
    await context.bot.send_message(chatID, 'Successfully updated! Use /sl to view all statuses.')
    return ConversationHandler.END

async def Cos_FIRST(update, context):
    chatID = update.effective_chat.id
    await context.bot.send_message(chatID, 'Enter your rank and name (eg. 3sg bob)\n/exit to exit')
    return 1

async def Cos_SECOND(update, context):
    chatID = update.effective_chat.id
    with open('data/reference/username_ref.json') as file:
        usernameRef = load(file)
    
    cos = update.message.text.upper().strip()
    usernameRef[str(chatID)]['cos'] = cos

    with open('data/reference/username_ref.json', 'w') as file:
        dump(usernameRef, file, indent=1)
    
    await context.bot.send_message(chatID, 'Updated successfully! COS: ' + cos)
    return ConversationHandler.END

async def Status(update, context):
    chatID = update.effective_chat.id
    await context.bot.send_message(chatID, Functions.StatusListCategoriser())

async def UpdateAll(update, context):
    chatID = update.effective_chat.id
    message = await context.bot.send_message(chatID, 'Updating... 0% Done')
    messageID = message.message_id
    
    await Scheduled.EveryThirtyMinutes(context, False)
    await context.bot.edit_message_text('Updating... 50% Done', chatID, messageID)
    await Scheduled.EveryDaily(context)
    await context.bot.edit_message_text('Updating... 100% Done', chatID, messageID)
    await Scheduled.EveryMonth(context)
    await context.bot.edit_message_text(Functions.StatusListCategoriser(), chatID, messageID)
    print(chatID)

async def Broadcast_FIRST(update, context):
    chatID = update.effective_chat.id
    await context.bot.send_message(chatID, 'Type the message you want to send out.\n/exit to exit')
    return 1

async def Broadcast_SECOND(update, context):
    chatID = update.effective_chat.id
    context.user_data['message'] = update.message.text
    keyboard = [['YES', 'NO']]
    await context.bot.send_message(chatID, 'Is this the message you would like to broadcast?\n/exit to exit')
    await context.bot.send_message(chatID, context.user_data['message'], reply_markup = ReplyKeyboardMarkup(keyboard))
    return 2

async def Broadcast_THIRD(update, context):
    chatID = update.effective_chat.id
    with open('data/reference/username_ref.json') as file:
        usernameRef = load(file)

    if update.message.text == 'YES':
        await context.bot.send_message(chatID, 'Message Broadcasted.', reply_markup = ReplyKeyboardRemove())
        for x in usernameRef.keys():
            await context.bot.send_message(x, context.user_data['message'])
    else:
        await context.bot.send_message(chatID, 'Message not sent.', reply_markup = ReplyKeyboardRemove())
    return ConversationHandler.END

async def ADWSheetEditHandler_FIRST(update, context):
    chatID = update.effective_chat.id
    ExcelProcesser.ObtainADWExcelSheet()
    await context.bot.send_document(
        chatID,
        open('data/excel files/out/adw.xlsx', 'rb'),
        caption = 'Edit !!!\n/exit to exit'
    )

    return 1

async def ADWSheetEditHandler_SECOND(update, context):
    chatID = update.effective_chat.id
    file = await update.message.effective_attachment.get_file()
    await file.download_to_drive('data/excel files/in/adw.xlsx')

    ExcelProcesser.EditADWExcelSheet()

    await context.bot.send_message(chatID, 'Should have been updated idk')
    return ConversationHandler.END

async def Exit(update, context):
    chatID = update.effective_chat.id
    await context.bot.send_message(chatID, 'Exit ok \U0001F44D', reply_markup = ReplyKeyboardRemove())
    return ConversationHandler.END

if __name__ == "__main__":
    load_dotenv()

    bot = ApplicationBuilder().token(os.getenv('API_KEY')).build()

    # bascially /update (ensures that all stuff is up to date)
    Scheduled.DownloadDatabase()
    Scheduled.ObtainMergedCells()
    Scheduled.RemoveOutdated()
    Scheduled.GetGlobalVariables()
    Scheduled.GetGlobalVariables()

    OverrideListEditHandler = ConversationHandler(
        entry_points = [CommandHandler('oe', OverrideListEdit_FIRST)],
        states = {
            1: [MessageHandler(filters.Regex(r'ADD STATUS'), OverrideListEdit_SECOND_ADD),
                MessageHandler(filters.Regex(r'REMOVE STATUS'), OverrideListEdit_SECOND_REMOVE)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, OverrideListEdit_THIRD_ADD)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, OverrideListEdit_FOURTH_ADD)],
            4: [MessageHandler(filters.TEXT & ~filters.COMMAND, OverrideListEdit_FIFTH_ADD)],
            5: [MessageHandler(filters.TEXT & ~filters.COMMAND, OverrideListEdit_THIRD_REMOVE)],
            6: [MessageHandler(filters.TEXT & ~filters.COMMAND, OverrideListEdit_FOURTH_REMOVE)]
        },
        fallbacks = [CommandHandler('exit', Exit)]
    )

    RationsListEditHandler = ConversationHandler(
        entry_points = [CommandHandler('re', RationsListEdit_FIRST)],
        states = {
            1: [MessageHandler(filters.Regex(r'EDIT EVERYDAY'), RationsListEdit_SECOND_EVERYDAY), 
                MessageHandler(filters.Regex(r'EDIT SPECIFIC DAYS'), RationsListEdit_SECOND_SPECIFIC),
                MessageHandler(filters.Regex(r'REMOVE SPECIFIC DAYS'), RationsListEdit_SECOND_REMOVE)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, RationsListEdit_THIRD_EVERYDAY)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, RationsListEdit_THIRD_SPECIFIC)],
            4: [MessageHandler(filters.TEXT & ~filters.COMMAND, RationsListEdit_THIRD_REMOVE)]
        },
        fallbacks = [CommandHandler('exit', Exit)]
    )

    PersonnelListEditHandler = ConversationHandler(
        entry_points = [CommandHandler('pe', PersonnelListEdit_FIRST)],
        states = {
            1: [MessageHandler(filters.Document.ALL, PersonnelListEdit_SECOND)]
        },
        fallbacks = [CommandHandler('exit', Exit)]
    )

    StatusReferenceListEditHandler = ConversationHandler(
        entry_points = [CommandHandler('se', StatusReferenceListEdit_FIRST)],
        states = {
            1: [MessageHandler(filters.Document.ALL, StatusReferenceListEdit_SECOND)]
        },
        fallbacks = [CommandHandler('exit', Exit)]
    )

    CosHandler = ConversationHandler(
        entry_points = [CommandHandler('cos', Cos_FIRST)],
        states = {
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, Cos_SECOND)]
        },
        fallbacks = [CommandHandler('exit', Exit)]
    )

    BroadcastHandler = ConversationHandler(
        entry_points = [CommandHandler('broadcast', Broadcast_FIRST)],
        states = {
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, Broadcast_SECOND)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, Broadcast_THIRD)]
        },
        fallbacks = [CommandHandler('exit', Exit)]
    )

    ADWSheetHandler = ConversationHandler(
        entry_points = [CommandHandler('ae', ADWSheetEditHandler_FIRST)],
        states = {
            1: [MessageHandler(filters.Document.ALL, ADWSheetEditHandler_SECOND)]
        },
        fallbacks = [CommandHandler('exit', Exit)]
    )

    bot.job_queue.run_repeating(Scheduled.EveryThirtyMinutes, datetime.timedelta(minutes=30), datetime.time(0, 0))
    bot.job_queue.run_daily(Scheduled.EveryDaily, datetime.time(0, 0))
    bot.job_queue.run_monthly(Scheduled.EveryMonth, datetime.time(0, 0), -1)

    bot.add_handler(CommandHandler('start', Start))
    bot.add_handler(CommandHandler('help', Help))
    bot.add_handler(CommandHandler('tor', TermsOfReference))
    bot.add_handler(CommandHandler('escort', Escort))
    bot.add_handler(CommandHandler('f', FullPS))
    bot.add_handler(CommandHandler('we', Weekend))
    bot.add_handler(CommandHandler('df', DutyForecast))
    bot.add_handler(CommandHandler('ol', OverrideListPrint))
    bot.add_handler(OverrideListEditHandler)
    bot.add_handler(CommandHandler('rl', RationsListPrint))
    bot.add_handler(RationsListEditHandler)
    bot.add_handler(CommandHandler('pl', PersonnelListPrint))
    bot.add_handler(PersonnelListEditHandler)
    bot.add_handler(CommandHandler('sl', StatusReferenceListPrint))
    bot.add_handler(StatusReferenceListEditHandler)
    bot.add_handler(CosHandler)
    bot.add_handler(CommandHandler('status', Status))
    bot.add_handler(CommandHandler('update', UpdateAll))
    bot.add_handler(BroadcastHandler)
    bot.add_handler(ADWSheetHandler)

    bot.run_polling()

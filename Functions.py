import datetime
import pandas as pd
from ujson import load
from pytz import timezone

# |==================================================|
# |                                                  |
# | These functions are all used in other .py files  |
# |                                                  |
# |   How ME_df is obtained is explained below ↓↓↓   |
# |                                                  |
# |==================================================|

def CurrentDatetime():
    return datetime.datetime.now(timezone('Asia/Singapore'))

def DateConverter(date):
    if isinstance(date, str):
        return datetime.datetime.strptime(date, '%d%m%y')
    elif isinstance(date, datetime.datetime):
        return datetime.datetime.strftime(date, '%d%m%y')
    else:
        return ValueError

def timedelta_months(month, year, add):
    new_month = ((month - 1) + add) % 12 + 1
    new_year = year + ((month - 1) + add) // 12
    return new_month, new_year

# loads in ME/ADW google sheet and returns it as a dataframe
def csv_to_dataframe(month_num, year, sheet):
    with open('data/reference/meDF_month_ref.json') as file:
        month_alpha_ref = load(file)

    # converts months in numbers to months in aphabets
    month_alpha = month_alpha_ref[month_num - 1]

    # NOTE: ↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓
    # How this URL was created ↓↓↓ (return statement) (this URL gives you a csv file of the sheet you want)
    # Original ME_df link: https://docs.google.com/spreadsheets/d/1rXLXxWMSpb8hU_BRuI87jv7wS04tB6yD/edit#gid=1221436461
    # Spreadsheet ID: 1rXLXxWMSpb8hU_BRuI87jv7wS04tB6yD
    # Format of URL to get csv file: https://docs.google.com/spreadsheets/d/[Spreadsheet ID]/gviz/tq?tqx=out:[csv/html]&sheet=[Sheet Name]
    # More info is found here: https://stackoverflow.com/a/33727897
    try:
        if sheet == 'me':
            return pd.read_csv(f"https://docs.google.com/spreadsheets/d/1rXLXxWMSpb8hU_BRuI87jv7wS04tB6yD/gviz/tq?tqx=out:csv&sheet={month_alpha}%2021{year}").fillna('NIL') 
    except:
        return None
    
    # NOTE: PENDING REMOVAL
    # elif sheet == 'adw':
    #     return pd.read_csv("https://docs.google.com/spreadsheets/d/1TwTIG7XdT1RRWzm8XCtbuWyKcMMdXwGr/gviz/tq?tqx=out:csv&sheet=" + datetime.datetime(year, month_num, 1).strftime('%b').upper() + f"%20{year}").fillna('NIL')

def OpenSheet(dateDT: datetime.datetime, sheet):
    monthINT = int(dateDT.strftime('%#m'))
    yearINT = int(dateDT.strftime('%#y'))

    # tries to open csv sheet in storage
    # if sheet does not exist, download sheet from online and use it
    try:
        if sheet == 'me':
            return pd.read_csv(f'data/database/{sheet}/{sheet}_{monthINT}_{yearINT}.csv')
        elif sheet == 'adw':
            return pd.read_csv('data/database/adw/adw.csv')
    except:
        return csv_to_dataframe(monthINT, yearINT, sheet)

def ObtainMap(key, value):
    resultMap = {}

    for flight in ['alpha', 'bravo', 'others']:
        with open(f'data/personnel/{flight}.json') as flightJson:
            flightList = load(flightJson)
        
        for x in flightList:
            if x[key] != 'NIL':
                resultMap[x[key]] = x[value]
    
    return resultMap

def ObtainResultDict(sheetToDisplay, sheet):
    resultDict = {}

    for x in sheet:
        if not x['sheetName'] in resultDict:
            resultDict[x['sheetName']] = [sheetToDisplay[x['sheetName']]]
        
        resultDict[x['sheetName']].append(f'{x["startDate"]} to {x["endDate"]} ({x["sheetStatus"]})')
    
    return resultDict

def ObtainResultStr(sheetToDisplay, sheet):
    resultStr = ''

    resultDict = ObtainResultDict(sheetToDisplay, sheet)
    
    for x in resultDict.values():
        resultStr += x[0] + ':\n' + '\n'.join(x[1:]) + '\n\n'
    
    return resultStr

def OverrideListCategoriser(mergedCells=True, psOverride=True):
    ref = {'sheetToDisplay': ObtainMap('sheetName', 'displayNoStatus')}
    result = []

    fileName = [
        'mergedCells',
        'psOverride',
        'status'
    ]

    filePath = [
        'data/override/merged_cells.json',
        'data/override/parade_state_override.json',
        'data/status.json'
    ]

    for name, path in zip(fileName, filePath):
        with open(path) as file:
            ref[name] = load(file)
    
    if mergedCells:
        result.append('<<< MERGED CELLS >>>\n')
        result[0] += 'STOPPED UPDATING AS OF ' if ref['status']['merged cells']['stopped'] else 'UPDATED AS OF '
        result[0] += ref['status']['merged cells']['time'] + '\n\n' + ObtainResultStr(ref['sheetToDisplay'], ref['mergedCells'])
    if psOverride and ref['psOverride']:
        result.append('<<< OVERRIDE LIST >>>\n\n' + ObtainResultStr(ref['sheetToDisplay'], ref['psOverride']))
    
    return result

def RationsListCategoriser():
    with open('data/override/rations.json') as file:
        rations = load(file)
    
    resultStr = '<<< RATIONS LIST >>>\n\n'
    for x in rations:
        resultStr += x.upper() + ': ' + f'{rations[x][0]} {rations[x][1]} {rations[x][2]}\n'

        if x == 'everyday':
            resultStr += '\n'
    
    return resultStr

def StatusListCategoriser():
    with open('data/status.json') as file:
        status = load(file)
    
    resultStr = '<<< STATUS LIST >>>\n\n'

    for key, value in status.items():
        resultStr += key.upper() + ':\n'
        resultStr += 'STOPPED UPDATING AS OF ' if value['stopped'] else 'UPDATED AS OF '
        resultStr += value['time'] + '\n\n'
    
    return resultStr

import Global
import re
import datetime
import Functions
import Scheduled
import pandas as pd
import ParadeState as ps
from ujson import load, dump

# |=========================================================================================================|
# |                                                                                                         |
# |                     ALL FOR MAKING EXCEL FILES (/ae, /pl, /pe, /sl, /se, /df)                           |
# |                                                                                                         |
# | Functions that start with:                                                                              |
# | --> Obtain : Generates excel sheet from csv/json files in data folder                                   |
# | --> Edit   : Receives excel sheets sent by user and rewrites into respective csv/json file to be saved  |
# |                                                                                                         |
# |=========================================================================================================|


def ObtainFlightPersonnelExcel(instructions:bool):
    writer = pd.ExcelWriter('data/excel files/out/flightPersonnel.xlsx')
    
    if instructions:
        instructionSheet = writer.book.add_worksheet('INSTRUCTIONS')
        instructionSheet.insert_image(0, 0, 'data/image/personnel_edit_instructions.jpg')

    callsign = pd.read_json('data/reference/callsign_ref.json', orient='index')
    callsign.reset_index(inplace=True)
    callsign.rename(columns={'index': 'callsign', 0: 'sheetName'}, inplace=True)
    callsign.to_excel(writer, sheet_name='CALLSIGN', index=False)
    writer.sheets['CALLSIGN'].autofit()

    for flight in ['alpha', 'bravo', 'others']:
        flightDF = pd.read_json(f'data/personnel/{flight}.json')
        flightDF.drop(columns=['rankINT', 'displayNoStatus'], inplace=True)
        flightDF.to_excel(writer, sheet_name=flight.upper(), index=False)
        writer.sheets[flight.upper()].autofit()

    writer.close()

def EditFlightPersonnelExcel():
    callsignRef = pd.read_excel('data/excel files/in/flightPersonnel.xlsx', sheet_name=['CALLSIGN'])['CALLSIGN'].fillna('NIL')

    result = {}

    for row in range(callsignRef.shape[0]):
        callsign = callsignRef.iloc[row, 0].upper().strip()
        sheetName = callsignRef.iloc[row, 1].upper().strip()
        
        if callsign != 'NIL':
            result[callsign] = sheetName
    
    with open('data/reference/callsign_ref.json', 'w') as file:
        dump(result, file, indent=1)

    with open('data/reference/rank_sorting.json') as file:
        rankSort = load(file)

    flightDF = pd.read_excel('data/excel files/in/flightPersonnel.xlsx', sheet_name=['ALPHA', 'BRAVO', 'OTHERS'])

    for flight, df in flightDF.items():
        df.fillna('NIL', inplace=True)
        result = []
        
        for row in range(df.shape[0]):
            if df.iloc[row, 2] != 'NIL':
                rank = df.iloc[row, 0].upper().strip()
                displayName = df.iloc[row, 1].upper().strip()
                
                result.append(
                    {
                        'rank': rank,
                        'displayName': displayName,
                        'sheetName': df.iloc[row, 2].upper().strip(),
                        'commSec': df.iloc[row, 3].upper().strip(),
                        'nor': df.iloc[row, 4].upper().strip(),
                        'rankINT': rankSort.get(rank, 100),
                        'displayNoStatus': rank + ' ' + displayName if rank != 'NIL' else displayName
                    }
                )
        
        result = sorted(result, key=lambda x: (x.get('rankINT'), x.get('nor')), reverse=True)
        
        with open(f'data/personnel/{flight.lower()}.json', 'w') as file:
            dump(result, file, indent=1)
    
    Scheduled.GetGlobalVariables()

    with open('data/status.json') as file:
        status = load(file)
    
    status['flight personnel files']['time'] = Functions.CurrentDatetime().strftime('%d/%m/%y at %#I:%M %p')

    with open('data/status.json', 'w') as file:
        dump(status, file, indent=1)

def ObtainStatusReferenceExcel(instructions:bool):
    writer = pd.ExcelWriter('data/excel files/out/statusReference.xlsx')

    if instructions:
        instructionSheet = writer.book.add_worksheet('INSTRUCTIONS')
        instructionSheet.insert_image(0, 0, 'data/image/status_edit_instructions.jpg')

    pd.read_json('data/reference/parade_state_categories.json').iloc[:-1].to_excel(writer, sheet_name='PARADE STATE CATEGORIES', index=False, header=['-'])
    pd.read_json('data/reference/more_dominant_status.json').to_excel(writer, sheet_name='MORE DOMINANT STATUS', index=False, header=['-'])

    definiteStatus = pd.read_json('data/reference/definite_status.json', orient='index')
    definiteStatus.reset_index(names='sheetStatus', inplace=True)
    definiteStatus = definiteStatus[:-1]
    definiteStatus.to_excel(writer, sheet_name='DEFINITE STATUS', index=False)

    with open('data/reference/indefinite_status.json') as file:
        indefiniteStatusDict = load(file)

    indefiniteStatus = pd.DataFrame.from_dict(indefiniteStatusDict, orient='index').reset_index(names=['category'])
    indefiniteStatus.to_excel(writer, sheet_name='INDEFINITE STATUS', index=False)
    
    for x in writer.sheets:
        writer.sheets[x].autofit()

    writer.close()

def EditStatusReferenceExcel():
    status = pd.read_excel(
        'data/excel files/in/statusReference.xlsx',
        sheet_name=['PARADE STATE CATEGORIES', 'MORE DOMINANT STATUS', 'DEFINITE STATUS', 'INDEFINITE STATUS']
    )

    for x in status:
        status[x].fillna('NIL', inplace=True)

    result = {'parade_state_categories': [], 'more_dominant_status': [], 'definite_status': {}, 'indefinite_status':{}}

    for x in ['parade_state_categories', 'more_dominant_status']:
        result[x] = [re.sub('\s*/\s*', '/', y.upper().strip()) for y in status[x.upper().replace('_', ' ')]['-'].values.tolist() if y != 'NIL']

        if x == 'parade_state_categories':
            result[x].append('UNKNOWN')

    for row in range(status['DEFINITE STATUS'].shape[0]):
        if status['DEFINITE STATUS'].iloc[row, 2] != 'NIL':
            sheetStatus = re.sub('\s*/\s*', '/', status['DEFINITE STATUS'].iloc[row, 0].upper().strip())
            displayStatus = status['DEFINITE STATUS'].iloc[row, 1].upper().strip()
            category = status['DEFINITE STATUS'].iloc[row, 2].upper().strip()
            
            result['definite_status'][sheetStatus] = {'displayStatus': displayStatus, 'category': category}
    
    result['definite_status']['UNKNOWN'] = {'displayStatus': 'NIL', 'category': 'UNKNOWN'}
    result['definite_status'] = dict(sorted(result['definite_status'].items(), key=lambda item: result['parade_state_categories'].index(item[1].get('category'))))

    for row in range (status['INDEFINITE STATUS'].shape[0]):
        category = status['INDEFINITE STATUS'].iloc[row, 0].upper().strip()
        if category != 'NIL':
            result['indefinite_status'][category] = [
                status['INDEFINITE STATUS'].iloc[row, x].upper().strip() for x in range(1, status['INDEFINITE STATUS'].shape[1]) 
                if status['INDEFINITE STATUS'].iloc[row, x] != 'NIL'
            ]

    for key, value in result.items():
        with open(f'data/reference/{key}.json', 'w') as file:
            dump(value, file, indent=1)
    
    with open('data/status.json') as file:
        status = load(file)
    
    status['status files']['time'] = Functions.CurrentDatetime().strftime('%d/%m/%y at %#I:%M %p')

    with open('data/status.json', 'w') as file:
        dump(status, file, indent=1)

def ObtainDutyForecastExcel(startDateDT, endDateDT):
    writer = pd.ExcelWriter('data/excel files/out/dutyForecast.xlsx')
    format = writer.book.add_format({'bold': True})

    dataManager = ps.DataManager()

    for currentDateRAW, beforeDateRAW, values in dataManager.CombinedDutyForecast(startDateDT, endDateDT):
        dutyME = pd.DataFrame({
            '0' : ['OSC', 'SSM', 'PRI LM', 'SEC LM', '', 'DLS', 'TRANSPORT OPERATOR', 'SITE VCOMM'],
            '1' : [
                values['dutyPersonnel'][0],
                values['dutyPersonnel'][1],
                values['dutyPersonnel'][4],
                values['dutyPersonnel'][2],
                values['dutyPersonnel'][5],
                values['dutyPersonnel'][3],
                '',
                values['siteVcomm']
            ]
        })

        dutyWC = pd.DataFrame({
            '0' : ['A-S COORD (G1)', 'A-S CONT (G2)', 'ASTER WC (G3A)'],
            '1' : [
                values['weaponControllers'][0],
                values['weaponControllers'][1],
                values['weaponControllers'][2]
            ]
        })

        standby = pd.DataFrame({
            '0' : ['OFFICER', 'JUNIOR/SENIOR ADWSS', 'ADWS', 'COMMSEC', 'A-S COORD (G1)', 'A-S CONT (G2)', 'ASTER WC (G3A)', 'SB TO (EQUIPMENT)', 'SB TO (ESCORT)'],
            '1' : [
                values['standbyPersonnel'][0],
                values['standbyPersonnel'][1],
                values['standbyPersonnel'][2],
                values['commSec'],
                values['weaponControllers'][3],
                values['weaponControllers'][4],
                values['weaponControllers'][5],
                '',
                ''
            ]
        })
        
        dutyME.to_excel(writer, sheet_name=currentDateRAW, header=False, index=False, startrow=2)
        dutyWC.to_excel(writer, sheet_name=currentDateRAW, header=False, index=False, startrow=11)
        dutyME.to_excel(writer, sheet_name=beforeDateRAW, header=False, index=False, startcol=3, startrow=2)
        standby.to_excel(writer, sheet_name=currentDateRAW, header=False, index=False, startcol=6, startrow=1)
    
    for x in writer.sheets:
        ws = writer.sheets[x]

        ws.write(0, 0, 'APPT', format)
        ws.write(0, 1, 'NAME', format)
        ws.write(0, 3, 'RVAAC', format)
        ws.write(0, 6, 'STANDBY', format)
        ws.autofit()

    writer.sheets[Functions.DateConverter(startDateDT - datetime.timedelta(days=1))].hide()
    writer.sheets[Functions.DateConverter(endDateDT + datetime.timedelta(days=1))].hide()

    writer.close()

def EditADWExcelSheet():
    adwDF = pd.read_excel('data/excel files/in/adw.xlsx').fillna('NIL')

    for column in adwDF.columns:
        adwDF[column] = adwDF[column].str.upper()
        adwDF[column] = adwDF[column].str.strip()

    adwDF.to_csv('data/database/adw/adw.csv', index=False)

def ObtainADWExcelSheet():
    adwDF = pd.read_csv('data/database/adw/adw.csv')

    writer = pd.ExcelWriter('data/excel files/out/adw.xlsx')
    adwDF.to_excel(writer, sheet_name='ADW', index=False)
    writer.sheets['ADW'].autofit()
    writer.close()
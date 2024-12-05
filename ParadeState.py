import Global
import re
import datetime
import Functions
from ujson import load

# |==================================================================================================================================================|
# |                                                                                                                                                  |
# |                     ALL THE FUNCTIONS IN THIS FILE HELP TO PRODUCE THE WEEKDAY/WEEKEND PARADE STATE (/f, /we, /df)                               |
# |                                                                                                                                                  |
# | CLASSES AND THEIR ATTRIBUTES:                                                                                                                    |
# | 1. DataManager                                                                                                                                   |
# |     --> BOOL fullPS - TRUE: /f | FALSE: /we, /df                                                                                                 |
# |         --> When FALSE personnel are not categorised as only standby crew, duty crew and adw (G1, G2, G3A) are required                          |
# |     --> DATETIME dateDT - date in datetime variable type                                                                                         |
# |     --> STR dateRAW - date in the format DDMMYY (eg. 010124)                                                                                     |
# |     --> INT day - day taken from dateRAW                                                                                                         |
# |     --> LIST WCrange - represents the rows to obtain adw in adwDF                                                                                |
# |         --> G1, G2, G3A: /f and /df                                                                                                              |
# |         --> G1, G2, G3A, G1 SB, G2 SB, G3A SB: /we                                                                                               |
# |     --> DATAFRAME adwDF - file loaded from data/database/adw/adw.csv as a dataframe                                                              |
# |         --> contains callsign of weapon operator doing duty on which day                                                                         |
# |         --> one month for one sheet                                                                                                              |
# |     --> DATAFRAME meDF - file loaded from data/database/me/(file on month based on date given)                                                   |
# |         --> taken from ME_df google sheets directly                                                                                              |
# |     --> LIST personnel - contains multiple person classes                                                                                        |
# |     --> DICT categorisedPersonnel - each person is placed in their respective category                                                           |
# |         --> KEY: CATEGORY (eg. PRESENT, OFF, MC, ...)                                                                                            |
# |         --> VALUE: LIST of person classes with the same category                                                                                 |
# |     --> DICT bottomCategorised - contains personnel required for duty crew, standby crew and adw (G1, G2, G3A)                                   |
# |     --> DICT ref - all files loaded in from data/reference                                                                                       |
# |     --> STR cos - rank + name of personnel generating the parade state, provided in data/reference/username_ref.json                             |
# |                                                                                                                                                  |
# | 2. Person (Inherited from Status class)                                                                                                          |
# |     --> INT rankINT - INT obtained from reference/rank_sorting.json based on person rank                                                         |
# |         --> for sorting of personnel by rank for duty crew and standby crew making                                                               |
# |     --> STR sheetName - name in ME_df                                                                                                            |
# |     --> STR nor - NSF/REGULAR                                                                                                                    |
# |     --> STATUS status - Status (inherited class)                                                                                                 |
# |     --> STR displayNoStatus - person represented in parade state message (eg. 3SG BOB (CPC))                                                     |
# |                                                                                                                                                  |
# | 3. Status                                                                                                                                        |
# |     --> LIST/DICT definiteStatus/indefiniteStatus/moreDominantStatus - reference of respective variable in ref (from DataManager)                |
# |     --> STR sheetStatus - status on ME_df                                                                                                        |
# |         --> trailing and leading whitespaces REMOVED                                                                                             |
# |         --> extra whitespaces between slashes REMOVED (eg. OFF / SB --> OFF/SB)                                                                  |
# |     --> STR displayStatus - status displayed on parade state message (example below)                                                             |
# |         --> 3SG BOB (CPC): CPC is the displayStatus                                                                                              |
# |         --> if displayStatus is NIL no status is displayed (eg. just 3SG BOB)                                                                    |
# |         --> determined in function LoadFUllStatus(self)                                                                                          |
# |     --> STR category - category in parade state message (eg. PRESENT, OFF, MC, ...)                                                              |
# |         --> determined in function LoadFUllStatus(self)                                                                                          |
# |     --> BOOL standby/duty - if TRUE personnel is on standby/duty respectively                                                                    |
# |                                                                                                                                                  |
# |                                                       LOGIC BEHIND HOW IT WORKS                                                                  |
# |                                                                                                                                                  |
# |                         *** def __LoadAll(self, date, WCstandby=False) is the MAIN function !!!!!! ***                                           |
# |                                                                                                                                                  |
# | 1. If /df is ran WCstandby is changed to obtain G1, G2, G3A, G1 SB, G2 SB and G3A SB                                                             |
# |    else if /f or /we is ran WCstandby remains at default to obtain G1, G2 and G3A                                                                |
# |                                                                                                                                                  |
# | 2. def __LoadSheetStatus(self, date)                                                                                                             |
# |     --> DICT nameStatus contents - KEY: sheetName | VALUE: sheetStatus                                                                           |
# |     --> def __LoadME(self, nameStatus) - statuses obtained from ME_df google sheet                                                               |
# |     --> def GetWeaponControllers() - adw obtained and placed in bottomCategorised                                                                |
# |     --> def __LoadADW(self, nameStatus) - def WeaponControllers() runs and sheetStatus of adw assigned                                           |
# |         --> This places adw's on HFD/R (indicating officer is on duty) or \\ (indicating officer is on changeover)                               |
# |             as officers (fit to be weapon controllers) do not put their duty on ME_df but on another sheet !!! ༼ ಠ益ಠ ༽ ╭∩╮                      |
# |         2.1. For the day before dateDT, adw's are taken from adwDF, split and subsequently placed in a list                                      |
# |              For example if G1 is FLARE/GUNDAM, G1 is split into FLARE and GUNDAM and these 2 elements are added to the list                     |
# |         2.2. If any of the callsigns in the list in (1) is present in ref['callsign'],                                                           |
# |              personnel's sheetName will be assigned the sheetStatus "\\" (meaning changeover)                                                    |
# |              (honestly anything can be used but it needs to be added to definite_status.json)                                                    |
# |         2.3. Steps 1 and 2 is repeated but for dateDT. personnel are given the sheetStatus                                                       |
# |              "R" if (R) is placed right beside the callsign and HFD if nothing is present.                                                       |
# |              (eg. FLARE/GUNDAM(R) --> FLARE will be given "HFD" while GUNDAM will be given "R",                                                  |    
# |              provided that these callsigns are in callsign_ref.json)                                                                             |
# |     --> def __LoadOverrideLists(self, nameStatus) - loads in sheetStatus from overrides (merged_cells.json and parade_state_override.json)       |
# |         --> if dateDT is between startDate and endDate a personnel in override files, personnel is given his respective sheetStatus              |
# |                                                                                                                                                  |
# |     *** OverrideList WILL ALWAYS BE THE FINAL SHEETSTATUS OF THE PERSON REGARDLESS OF WHAT SHEETSTATUS THE PERSONNEL HAS IN meDF AND adwDF ***   |
# |                                                                                                                                                  |
# | 3. All files from data/personnel are loaded into a list                                                                                          |
# |                                                                                                                                                  |
# | 4. A person object is initialised for each person in the list created in 3 and added to a personnel list (from DataManager).                     |
# |    During initialisation of a person object, a status object is also initialised. Below shows the steps for initialising a status object:        |
# |     4.1.  If personnel sheetName is present in nameStatus in (2), personnel will have be given their sheetStatus, else it will be "UNKNOWN"      |
# |     4.2a. If fullPS is TRUE (/f is ran):                                                                                                         |
# |         4.2a.1. For personnels' with sheetName present in ref["callsign"] and not present in ME_df,                                              |
# |                 they will be given the sheetStatus of NIL (representing PRESENT)                                                                 |
# |                 (this is so that personnel like OC are marked present if they are not on duty/changeover and not unknown)                        |
# |         4.2a.2. Person.LoadFullStatus(categorisedPersonnel, bottomCategorised), followed by Status.LoadFullStatus(self).                         |
# |                 In Status.LoadFullStatus(), displayStatus, category, duty, and standby are filled in for each person.                            |
# |                 displayStatus and category is determined by steps as shown in the method defined below.                                          |
# |         4.2a.3. displayFull is filled in (displayFull is the string that is to be printed in the final message for each person)                  |
# |         4.2a.4. __CategoriseFull(self, categorisedPersonnel, bottomCategorised) is ran,                                                          |
# |                 which fills in categorisedPersonnel and bottomCategorised (from DataManager).                                                    |
# |                 NOTE: In this step, bottomCategorised["dutyPersonnel"] and bottomCategorised["standbyPersonnel"] are unsorted                    |
# |                       and will be sorted in DataManager.__SortStandbyAndDuty() in (4.3).                                                         |
# |     4.2b. If fullPS is FALSE (/we /df is ran):                                                                                                   |
# |         4.2b.1. Person.LoadStandbyAndDuty() is ran, and only bottomCategorised is filled.                                                        |
# |                 displayStatus and category will NOT be processed as it is not needed.                                                            |
# |                 NOTE: as stated in (4.2a.4)                                                                                                      |
# |                                                                                                                                                  |
# | 5. DataManager.__SortStandbyAndDuty() is ran which sorts bottomCategorised["dutyPersonnel"] and bottomCategorised["standbyPersonnel"].           |
# |    --> In both lists, personnel are sorted in descending order by rank, using RANKINT (ensures that SSM is higher ranking than all minus OSC).   |
# |    --> Then, personnel are sorted again to ensure that their rank matches their role.                                                            |
# |        --> eg. OSC's must have a rank of 2LT and higher, and can be a REGULAR or NSF.                                                            |
# |        --> eg. SSM's must have a rank between SSG and 1WO (could be higher but must be a WOSPEC) inclusive, and can only be a REGULAR.           |
# |        --> eg. ADSS's must have a rank between 3SG and 1WO inclusive, and can only be a regular.                                                 |
# |        --> eg. ADWS's must have a rank between 3SG and 2SG inclusive, and can only be a NSF.                                                     |
# |        --> If personnel does not fit any of the roles, personnel is not sorted in.                                                               |
# |    --> Now both lists are sorted and filtered to ensure that personnel and their role corresponds.                                               |
# |                                                                                                                                                  |
# | 6. The message string (/f, /we) / excel sheet (/df) can now be constructed depending on what command is ran.                                     |
# |     6a. For /f, DataManager.FullPS(date) is ran. which runs DataManager.__psTop() ,DataManager.__psMiddle() and DataManager.__psBottom().        |
# |         6a.1. In DataManager.__psTop()    - top of pararde state is generated (just before rations)                                              |
# |                                             with information from categorisedPersonnel dict and made into a string                               |
# |         6a.2. In DataManager.__psMiddle() - middle of parade state is generated (rations portion)                                                |
# |             6a.2.1. If dateRAW is not a key in data/override/rations.json, "everyday" will be used                                               |
# |                     --> [0] - breakfast pax                                                                                                      |  
# |                     --> [1] - lunch pax                                                                                                          |
# |                     --> [2] - dinner pax                                                                                                         |
# |             6a.2.2. For the lunch section names are obtained through the following logic:                                                        |
# |                     (lowest rank filled in first, NSFs are filled in before REGULARs)                                                            |
# |                     6a.2.2.1. All present palced in a list called lunchPersonnel                                                                 |
# |                     6a.2.2.2. List sorted by NSF/REGULAR and then by rank                                                                        |
# |                     6a.2.2.3. All NSF's taken first from the lowest rank to the highest.                                                         |
# |                               Once all NSFs are exhausted, REGULARs are taken from lowest rank to the highest                                    |
# |                     6a.2.2.4. displayNoStatus taken from each personnel and placed in list in same order as (6a.2.2.3)                           |
# |                               (displayNoStatus - rank + displayName)                                                                             |
# |             6a.2.3. Dinner is not printed for FRIDAYS (taken as 0 pax)                                                                           |
# |         6a.3. In DataManager.__psBottom() - Information from bottomCategorised dict is formatted into a string                                   |
# |     6b. For /we, DataManager.CombinedBottomPS(startDateDT, endDateDT) is ran.                                                                    |
# |         For /df, DataManager.CombinedDutyForecast(startDateDT, endDateDT) is ran.                                                                |
# |         NOTE: fullPS will be set to FALSE                                                                                                        |
# |         6b.1. DataManager.__LoadAll(date) is ran using startDateDT.                                                                              |
# |               If /df, WCstandby is set to TRUE (to get G1 SB, G2 SB and G3A SB) and CommSec is obtained.                                         |
# |         6b.2. For /we, data is parsed into a string, while for /df data is parsed into an excel sheet.                                           |
# |         6b.3. startDateDT is incremented by one day and DataManager.__Update(date) is ran                                                        |
# |               --> DataManager.__Update(date) clears bottomCategorised dict to original and                                                       |
# |                   runs __SortStandbyAndDuty() to obtain next day bottomcategorised.                                                              |
# |         6b.4. Data is parsed according to (6b.2).                                                                                                |
# |         6b.5. Repeat steps (6b.2) to (6b.4) until startDateDT == endDateDT.                                                                      |
# |         6b.6. Message/Excel sheet from startDateDT to endDateDT inclusive is generated.                                                          |
# |                                                                                                                                                  |
# |==================================================================================================================================================|

class Status:
    def __init__ (self, rawSheetStatus, ref):
        self.definiteStatus = ref['definiteStatus']
        self.indefiniteStatus = ref['indefiniteStatus']
        self.moreDominantStatuses = ref['moreDominantStatuses']
        
        self.sheetStatus = re.sub('\s*/\s*', '/', rawSheetStatus.upper().strip())
        self.displayStatus = 'NIL'
        self.category = 'UNKNOWN'
        self.standby = False
        self.duty = False
    
    def Reset(self, rawSheetStatus):
        self.sheetStatus = re.sub('\s*/\s*', '/', rawSheetStatus.upper().strip())
        self.standby = False
        self.duty = False

    def LoadStandbyAndDuty(self):
        if re.search('.{2,}/.{2,}', self.sheetStatus):
            splitSheetStatus = self.sheetStatus.split('/')

            if 'SB' in splitSheetStatus:
                self.standby = True
        else:
            if self.sheetStatus == 'X':
                self.duty = True
            if self.sheetStatus == 'SB':
                self.standby = True

    def LoadFullStatus(self):
        dominantStatus = None

        # if statment is for sheetStatuses with 2 different statuses (eg. COURSE/SB).
        # if statement does the following - examples below:
        # 1. sheetStatus: SB/COURSE                  -> dominantStatus: COURSE                  (sets self.standby = True)
        # 2. sheetStatus: SB/COURSE/MISSILE TRANSFER -> dominantStatus: COURSE/MISSILE TRANSFER (sets self.standby = True)
        # 3. sheetStatus: OFF/COURSE                 -> dominantStatus: OFF                     (NA)
        # 4. sheetStatus: OFF/CCL                    -> dominantStatus: OFF/CCL                 (NA)
        # [does not split U/S and O/S]
        # else statement does the following - examples below:
        # 1. sheetStatus: SB                         -> dominantStatus: SB                      (sets self.standby = True)
        # 2. sheetStatus: X                          -> dominantStatus: X                       (sets self.duty = True)
        # 3. sheetStatus: ANYTHING                   -> dominantStatus: ANYTHING                (NA)
        if re.search('.{2,}/.{2,}', self.sheetStatus):
            splitSheetStatus = self.sheetStatus.split('/')

            if 'SB' in splitSheetStatus:
                self.standby = True
                splitSheetStatus.remove('SB')
            
            moreDominantStatus = [x for x in splitSheetStatus if x in self.moreDominantStatuses]
            if moreDominantStatus:
                dominantStatus = '/'.join(moreDominantStatus)
            else:
                dominantStatus = '/'.join(splitSheetStatus)
        else:
            if self.sheetStatus == 'X':
                self.duty = True
            if self.sheetStatus == 'SB':
                self.standby = True
            if self.sheetStatus == 'OSC SB':
                self.standby = True
                
            dominantStatus = self.sheetStatus
        
        # if   --- dominantStatus in definite_status.json - displayStatus and category are set
        # else --- searches indefinite_status.json
        #    if   --- keywords in indefinite_status.json - displayStatus = dominantStatus and category is set
        #    else --- NA                                 - displayStatus = dominantStatus (category remains as UNKNOWN)
        displayCategory = self.definiteStatus.get(dominantStatus)
        if displayCategory:
            self.displayStatus = displayCategory['displayStatus']
            self.category = displayCategory['category']
        else:
            for category in self.indefiniteStatus:
                if re.search('|'.join(self.indefiniteStatus[category]), dominantStatus):
                    self.displayStatus = dominantStatus
                    self.category = category
                    return
            
            self.displayStatus = dominantStatus

class Person:
    def __init__(self, flight, person, rawSheetStatus, ref):
        self.flight = flight
        self.rankINT = person['rankINT']
        self.sheetName = person['sheetName']
        self.nor = person['nor']
        self.status = Status(rawSheetStatus, ref)
        self.displayNoStatus = person['displayNoStatus']

        self.displayFull = self.displayNoStatus
    
    def __repr__(self):
        return self.displayNoStatus

    def __CategoriseBottom(self, bottomCategorised):
        if self.status.duty:
            bottomCategorised['dutyPersonnel'].append(self)
        if self.status.standby:
            bottomCategorised['standbyPersonnel'].append(self)
        if self.status.sheetStatus == 'SITE VCOMM':
            bottomCategorised['siteVcomm'] = self.displayNoStatus

    def __CategoriseFull(self, categorisedPersonnel, bottomCategorised):
        if self.flight == 'alpha':
            categorisedPersonnel[self.status.category].append(self)
        
        self.__CategoriseBottom(bottomCategorised)

    def LoadStandbyAndDuty(self, bottomCategorised):
        self.status.LoadStandbyAndDuty()

        self.__CategoriseBottom(bottomCategorised)
    
    def LoadFullStatus(self, categorisedPersonnel, bottomCategorised):
        self.status.LoadFullStatus()
        
        if self.status.displayStatus != 'NIL':
            self.displayFull += ' ' + f'({self.status.displayStatus})'
        
        self.__CategoriseFull(categorisedPersonnel, bottomCategorised)

class DataManager:
    def __init__(self, chatID=None):
        self.fullPS = True
        self.dateDT = None
        self.dateRAW = None
        self.day = None
        self.WCrange = [0, 1, 2]
        self.meDF = None
        self.adwDF = None

        self.personnel = []
        self.categorisedPersonnel = {}
        self.bottomCategorised = {'dutyPersonnel': [], 'standbyPersonnel': [], 'siteVcomm': 'UNKNOWN', 'weaponControllers': []}

        self.ref = {}

        fileName = [
            'callsign',
            'definiteStatus',
            'indefiniteStatus',
            'moreDominantStatuses',
            'psCategories',
            'mergedCells',
            'psOverride',
            'rations',
            'username'
        ]

        filePath = [
            'data/reference/callsign_ref.json',
            'data/reference/definite_status.json',
            'data/reference/indefinite_status.json',
            'data/reference/more_dominant_status.json',
            'data/reference/parade_state_categories.json',
            'data/override/merged_cells.json',
            'data/override/parade_state_override.json',
            'data/override/rations.json',
            'data/reference/username_ref.json'
        ]

        for name, path in zip(fileName, filePath):
            with open(path) as file:
                self.ref[name] = load(file)
        
        for category in self.ref['psCategories']:
            self.categorisedPersonnel[category] = []
        
        if self.ref['username'].get(str(chatID)):
            self.cos = self.ref['username'][str(chatID)]['cos']
        else:
            self.cos = ''
    
    def __SetDate(self, date):
        if isinstance(date, str):
            self.dateRAW = date
            self.dateDT = Functions.DateConverter(date)
        elif isinstance(date, datetime.datetime):
            self.dateDT = date
            self.dateRAW = Functions.DateConverter(date)
        else:
            return ValueError

        self.day = int(self.dateDT.strftime('%#d'))
        self.meDF = Functions.OpenSheet(self.dateDT, 'me')
        self.adwDF = Functions.OpenSheet(self.dateDT, 'adw')

    def __LoadME(self, nameStatus):
        for x in range(Global.TOP, Global.MIDDLE):
            if self.meDF.iloc[x, 0] != 'NIL':
                nameStatus[self.meDF.iloc[x, 0].upper().strip()] = self.meDF.iloc[x, self.day]
    
    def __GetCommSec(self):
        csToDisplay = Functions.ObtainMap('commSec', 'displayNoStatus')

        for x in range(Global.MIDDLE, Global.BOTTOM):
            if self.meDF.iloc[x, self.day].upper().strip() == 'C':
                self.bottomCategorised['commSec'] = csToDisplay.get(self.meDF.iloc[x, 0].upper().strip(), 'UNKNOWN')
                return
        
        self.bottomCategorised['commSec'] = 'UNKNOWN'

    def __GetWeaponControllers(self):
        for x in self.WCrange:
            self.bottomCategorised['weaponControllers'].append(self.adwDF.iloc[x, self.day + 1].upper().strip())
    
    def __SplitCallsigns(self, deltaDay: int):
        temp = []

        # places those on duty(A2(D) to G4) the previous day/on the day into a list
        # splitting ones with multiple callsigns into seperate items
        for x in [self.adwDF.iloc[x, self.day + deltaDay].upper().strip() for x in range(3)]:
            if '/' in x:
                temp.extend(x.split('/'))
            else:
                temp.append(x)
        
        return temp

    def __LoadADW(self, nameStatus):
        self.__GetWeaponControllers()

        # places those on duty the day before into a list and splits those with '/'
        adw_daybefore_list = self.__SplitCallsigns(0)

        # putting all those on duty the day before on changeover
        for x in adw_daybefore_list:
            for callsign in self.ref['callsign']:
                if callsign in x:
                    nameStatus[self.ref['callsign'][callsign]] = '\\'
                    break

        # places those on duty into a list and splits those with '/'
        adw_day_list = self.__SplitCallsigns(1)

        # if (R) present, status is R
        # else status is HFD
        for x in adw_day_list:
            for callsign in self.ref['callsign']:
                if callsign in x:
                    if "(R)" in x:
                        nameStatus[self.ref['callsign'][callsign]]  = "R"
                    else:
                        nameStatus[self.ref['callsign'][callsign]]  = "HFD"
                    break
    
    def __LoadOverrideLists(self, nameStatus):
        for x in self.ref['mergedCells'] + self.ref['psOverride']:
            if Functions.DateConverter(x['startDate']) <= self.dateDT <= Functions.DateConverter(x['endDate']):
                nameStatus[x['sheetName']] = x['sheetStatus']

    def __LoadSheetStatus(self, date):
        self.__SetDate(date)

        nameStatus = {}
        self.__LoadME(nameStatus)
        if self.fullPS:
            self.__LoadADW(nameStatus)
        else:
            self.__GetWeaponControllers()
        self.__LoadOverrideLists(nameStatus)

        return nameStatus
    
    def __SortStandbyAndDuty(self):
        self.bottomCategorised['dutyPersonnel'] = sorted(self.bottomCategorised['dutyPersonnel'], key=lambda x: x.rankINT, reverse=True)
        self.bottomCategorised['standbyPersonnel'] = sorted(self.bottomCategorised['standbyPersonnel'], key=lambda x: x.rankINT, reverse=True)

        rankRef = {"duty": [[9, 12], [4, 9], [1, 9], [1, 9], [1, 3], [1, 3]], "standby": [[9, 12], [1, 9], [1, 3]]}

        dutyPersonnelNew = ['UNKNOWN' for x in range(6)]
        dutyOpenSlots = [x for x in range(6)]
        for personnel in self.bottomCategorised['dutyPersonnel']:
            add = False
            for i in dutyOpenSlots:
                if personnel.rankINT in range(rankRef['duty'][i][0], rankRef['duty'][i][1]):
                    if i == 0:
                        add = True
                    if i in [1, 2, 3] and personnel.nor == 'REGULAR':
                        add = True
                    if i in [4, 5] and personnel.nor == 'NSF':
                        add = True

                    if add:
                        dutyOpenSlots.remove(i)
                        dutyPersonnelNew[i] = personnel.displayNoStatus
                        break
        
        self.bottomCategorised['dutyPersonnel'] = dutyPersonnelNew

        standbyPersonnelNew = ['UNKNOWN' for x in range(3)]
        standbyOpenSlots = [x for x in range(3)]
        for personnel in self.bottomCategorised['standbyPersonnel']:
            add = False
            for i in standbyOpenSlots:
                if personnel.rankINT in range(rankRef['standby'][i][0], rankRef['standby'][i][1]):
                    if i == 0:
                        add = True
                    if i == 1 and personnel.nor == 'REGULAR':
                        add = True
                    if i == 2 and personnel.nor == 'NSF':
                        add = True

                    if add:
                        standbyOpenSlots.remove(i)
                        standbyPersonnelNew[i] = personnel.displayNoStatus
                        break
        
        self.bottomCategorised['standbyPersonnel'] = standbyPersonnelNew

    def __LoadAll(self, date, WCstandby=False):
        if WCstandby:
            self.WCrange = [0, 1, 2, 4, 5, 6]
        nameStatus = self.__LoadSheetStatus(date)

        for flight in ['alpha', 'bravo', 'others']:
            with open(f'data/personnel/{flight}.json') as flightJson:
                flightList = load(flightJson)
        
            for person in flightList:
                self.personnel.append(Person(flight, person, nameStatus.get(person['sheetName'], 'UNKNOWN'), self.ref))

                if self.fullPS:
                    if person['sheetName'] in self.ref['callsign'].values() and not person['sheetName'] in nameStatus:
                        self.personnel[-1].status.sheetStatus = 'NIL'
                    
                    self.personnel[-1].LoadFullStatus(self.categorisedPersonnel, self.bottomCategorised)
                
                else:
                    self.personnel[-1].LoadStandbyAndDuty(self.bottomCategorised)

        self.__SortStandbyAndDuty()
    
    def __Update(self, date):
        self.bottomCategorised = {'dutyPersonnel': [], 'standbyPersonnel': [], 'siteVcomm': 'UNKNOWN', 'weaponControllers': []}

        nameStatus = self.__LoadSheetStatus(date)

        for person in self.personnel:
            person.status.Reset(nameStatus.get(person.sheetName, 'UNKNOWN'))
            person.LoadStandbyAndDuty(self.bottomCategorised)
        
        self.__SortStandbyAndDuty()
    
    def __psTop(self):
        psStr = f'Good Day ALPHA, below is the Forecasted Parade State for {self.dateRAW}.\n\n' \
                f'COS: {self.cos}\n\n' \
                f'TOTAL STRENGTH ({len([x for x in self.personnel if x.flight == "alpha"])})\n\n'
        
        for category in self.categorisedPersonnel:
            if category != 'UNKNOWN':
                psStr += f'{category}: ({len(self.categorisedPersonnel[category])})\n' + \
                    '\n'.join(person.displayFull for person in self.categorisedPersonnel[category]) + '\n\n'

        return psStr + '---------------------------------------------------\n\n'
    
    def __psMiddle(self):
        if self.dateRAW in self.ref['rations']:
            rationNum = self.ref['rations'][self.dateRAW]
        else:
            rationNum = self.ref['rations']['everyday']

        midStr = ''

        if rationNum[0] != 0:
            midStr += f'BREAKFAST: [{rationNum[0]} PAX]\n' \
                f'COS WILL SCAN ON BEHALF OF ALPHA\n\n' \
        
        if rationNum[1] != 0:
            lunchPersonnel = [x for x in self.categorisedPersonnel['PRESENT']]
            lunchPersonnel = sorted(lunchPersonnel, key=lambda x: (x.nor, x.rankINT))
            lunchPersonnel = sorted(lunchPersonnel[:rationNum[1]], key=lambda x: x.rankINT, reverse=True)
            lunchPersonnel = [x.displayNoStatus for x in lunchPersonnel]

            midStr += f'LUNCH: [{rationNum[1]} PAX]\n' \
                + '\n'.join(lunchPersonnel) + '\n\n'

        if rationNum[2] != 0:
            midStr += f'DINNER: [{rationNum[2]} PAX]\n' \
                    f'COS WILL SCAN ON BEHALF OF ALPHA\n\n' \

        if midStr == '':
            return ''
        else:
            return '[RATION SCANNERS]\n\n' + midStr + '---------------------------------------------------\n\n'

    def __psBottom(self):
        return f'[DUTY CREW FOR {self.dateRAW}]\n' \
        f'OSC: {self.bottomCategorised["dutyPersonnel"][0]}\n' \
        f'SSM: {self.bottomCategorised["dutyPersonnel"][1]}\n' \
        f'ADSS: {self.bottomCategorised["dutyPersonnel"][2]}\n' \
        f'ADSS: {self.bottomCategorised["dutyPersonnel"][3]}\n' \
        f'ADWS: {self.bottomCategorised["dutyPersonnel"][4]}\n' \
        f'ADWS: {self.bottomCategorised["dutyPersonnel"][5]}\n\n' \
        f'SITE VCOMM: {self.bottomCategorised["siteVcomm"]}\n\n' \
        f'[STANDBY CREW FOR {self.dateRAW}]\n' \
        f'CONVOY CMD: {self.bottomCategorised["standbyPersonnel"][0]}\n' \
        f'ADSS: {self.bottomCategorised["standbyPersonnel"][1]}\n' \
        f'ADWS: {self.bottomCategorised["standbyPersonnel"][2]}\n\n' \
        f'G1: {self.bottomCategorised["weaponControllers"][0]}\n' \
        f'G3A: {self.bottomCategorised["weaponControllers"][2]}'
    
    def FullPS(self, date):
        self.fullPS = True
        self.__LoadAll(date)
        return self.__psTop() + self.__psMiddle() + self.__psBottom()
    
    def CombinedBottomPS(self, startDateDT, endDateDT):
        self.fullPS = False
        self.__LoadAll(startDateDT)
        combStr = self.__psBottom()

        while startDateDT < endDateDT:
            startDateDT += datetime.timedelta(days=1)
            self.__Update(startDateDT)
            combStr += '\n\n---------------------------------------------------\n\n' + self.__psBottom()
        
        return combStr
    
    def CombinedDutyForecast(self, startDateDT, endDateDT):
        self.fullPS = False
        beforeDateRAW = Functions.DateConverter(startDateDT - datetime.timedelta(days=1))
        
        self.__LoadAll(startDateDT, True)
        self.__GetCommSec()
        yield self.dateRAW, beforeDateRAW, self.bottomCategorised

        while startDateDT <= endDateDT:
            beforeDateRAW = Functions.DateConverter(startDateDT)
            startDateDT += datetime.timedelta(days=1)
            self.__Update(startDateDT)
            self.__GetCommSec()
            yield self.dateRAW, beforeDateRAW, self.bottomCategorised

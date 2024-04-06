import datetime
import Functions

# |========================================================================================================================================|
# |                                                                                                                                        |
# |                             CHECKS DATE IS VALID WHEN INPUTTED IN COMMANDS (eg. /f, /df, ...)                                          |
# |                                                                                                                                        |
# |                                      *** dateRAW is int the format DDMMYY ***                                                          |
# |                                                                                                                                        |
# | 1. DateCheck(dateRAW)                                                                                                                  |
# |    --> If dateRAW is 6 digits, dateRAW is passed through Functions.DateConverter                                                       |
# |        to check if it can be converted into a datetime object, and datetime object returned                                            |
# |        (indicated dateRAW is in DDMMYY and is a valid date)                                                                            |
# |                                                                                                                                        |
# | 2. SingleDate(contArgs)                                                                                                                |
# |     --> If no date is provided - contArgs is an empty list, next day datetime object is returned                                       |
# |     --> If one date is provided, date is passed into DateChecker.DateCheck(dateRAW).                                                   |
# |         If date is valid, datetime object is returned, else, none is returned.                                                         |
# |                                                                                                                                        |
# | 3. DoubleDate(contArgs, ...)                                                                                                           |
# |     --> BOOL autofillFirst                                                                                                             |
# |         --> If TRUE : if no date is provided, returns 2 dates (what dates stated below)                                                |
# |         --> If FALSE: if no date is provided, returns none                                                                             |
# |     --> BOOL autofillSecond                                                                                                            |
# |         --> If TRUE : if one date provided, returns 2 dates (what dates stated below)                                                  |
# |         --> If FALSE: if one date provided, returns none                                                                               |
# |                                                                                                                                        |
# |     --> If no dates provided and autoFillFirst is TRUE,                                                                                |
# |         datetime of next day and the day after the next day is returned                                                                |
# |     --> If one date is provided and autoFillSecond is TRUE,                                                                            |
# |         date is passed into DateChecker.DateCheck(dateRAW) to check.                                                                   |
# |         If valid, datetime object is returned and the day after date provided is returned,                                             |
# |         else, none is returned.                                                                                                        |
# |     --> If two dates provided, both dates are checked to be valid.                                                                     |
# |         Then, second date is checked to be larger than the first date.                                                                 |
# |         Lastly, if maxDayDelta provided, checkes whether number of days between startDate and endDate is smaller than maxDayDelta.     |
# |         If it fails at any step, none is returned.                                                                                     |
# |                                                                                                                                        |
# |                                FAILS at rejecting dates very far away from current date                                                |
# |                                        (eg. 010140 will pass and be returned !!!)                                                      |
# |                                                                                                                                        |
# |========================================================================================================================================|

def DateCheck(dateRAW):   
    # checks if date provided is 6 digits
    if len(dateRAW) == 6:
        try:
            return Functions.DateConverter(dateRAW)
        except ValueError:
            return

def SingleDate(contArgs):
    if len(contArgs) == 0:
        # no date provided
        dateDT = Functions.CurrentDatetime() + datetime.timedelta(days=1)
        return datetime.datetime(dateDT.year, dateDT.month, dateDT.day)
    elif len(contArgs) == 1:
        return DateCheck(contArgs[0])
    else:
        return

def DoubleDate(contArgs, maxDayDelta:int=None, autofillFirst = True, autofillSecond = True):
    startDateDT = None
    endDateDT = None

    if len(contArgs) == 0:
        if autofillFirst:
            startDateDT = Functions.CurrentDatetime() + datetime.timedelta(days=1)
            startDateDT = datetime.datetime(startDateDT.year, startDateDT.month, startDateDT.day)
            
            endDateDT = startDateDT + datetime.timedelta(days=1)
            endDateDT = datetime.datetime(endDateDT.year, endDateDT.month, endDateDT.day)
    elif len(contArgs) == 1:
        if autofillSecond:
            startDateDT = DateCheck(contArgs[0])
            
            if startDateDT is not None:
                endDateDT = startDateDT + datetime.timedelta(days=1)
    elif len(contArgs) == 2:
        startDateDT = DateCheck(contArgs[0])
        endDateDT = DateCheck(contArgs[1])

        # check if dates are valid
        if startDateDT is None or endDateDT is None:
            startDateDT = None
            endDateDT = None
        else:
            # check if end date is greater than start date
            if startDateDT > endDateDT:
                startDateDT = None
                endDateDT = None
            else:
                if maxDayDelta is not None and (endDateDT - startDateDT).days > maxDayDelta:
                    startDateDT = 'tooFar'
                    endDateDT = None
    
    return startDateDT, endDateDT
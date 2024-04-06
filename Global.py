# |================================================================================================================================================|
# |                                                                                                                                                |
# | --> These Global variables correspond to the ROWS in ME_df                                                                                     |
# | --> Values are set after function called GetGlobalVariables in Scheduled is ran (runs once when run.py is ran and last day of every month)     |
# | --> sheetName and commSec are found in data/personnel/(alpha/bravo/others).json                                                                |
# |                                                                                                                                                |
# | --> TOP - row of FIRST sheetName detected in ME_df                                                                                             |
# | --> MIDDLE - row of FIRST commSec detected in ME_df                                                                                            |
# | --> BOTTOM - row of LAST commSec detected in ME_df                                                                                             |
# |                                                                                                                                                |
# | --> This ensures that sheetStatus obtained between TOP and MIDDLE is not overridden by sheetStatus obtained from MIDDLE to BOTTOM              |
# |     if commSec and sheetName are the same                                                                                                      |
# |                                                                                                                                                |
# |================================================================================================================================================|

TOP = 0
MIDDLE = 0
BOTTOM = 0
import pandas as pd
data = pd.DataFrame
from io import StringIO
import csv
import numpy as np
import re

pd.options.mode.chained_assignment = None  # default='warn'

'''
Proposito: Pasar un report de unit testing de vectorcast en html y clasificarlo por subsistemas y domains.
''' 

def read_ut_report_html(reporthtmlfile):
    """
    Function: 
    Read VectorCast Unit testing report html file, picks the second df, and renames a column to "name" for later data management.
    
    Params
        reporthtmlfile: String with the address of the VectorCast report html file

    return:
        Dataframe with the vectorcast report data.
    """
    with open(reporthtmlfile, 'r') as file:  # r to open file in READ mode
        html_as_string = file.read() 

    iofile = StringIO(html_as_string) 
    htmlread = pd.read_html(iofile) 
    htmlread[1] = htmlread[1].rename(columns ={"Unnamed: 0":"name"})
    return htmlread[1] # Pick second table of the html


def read_project_directory (fileaddress,testnames) :
    """
    Function:
    Reads the file in the given adress, and reads the last value of each line to find the files that coincide with the names of testnames list,
    these lines are stored in a new .txt file, that is then read to generate a dataframe, and renames a few column for better data management.

        Parameters:
            fileaddress: String with the file address of .txt containing all project addresses.
            testnames: List with the file names used in the report (uppercase, no ".c")

    Return: Dataframe with the data of only the files used in the report, to perform Domain and subsystem classification later
    """

    with open(fileaddress,'r') as fin, open ('writefile1.txt','w',newline='') as fout: 
        file = fin.readlines()[2:]
        writer = csv.writer(fout, delimiter=',')            
        for row in csv.reader(file, delimiter='\\'):
            for i in testnames.index:
                if str.upper(testnames[i])+".C" == str.upper(row[-1]): # Compare with the last value of the file address
                    writer.writerow(row) 
    column_names = [i for i in range(0, 11)]
    
    
    data = pd.DataFrame()
    data = pd.read_csv('writefile1.txt', sep=',', header=None,names=column_names)
    data[10] = data[10].fillna(data[9])
    data["name"] = data[10].str.upper().str[:-2]
    data = data.rename(columns = {5:"Domain"})
    data = data.rename(columns = {6:"Subsystem"})
    return data

def clean_report_data (ut_report_df):
    """
    Function: Read the ut_report dataframe and separate in test passed, and total test for each type of test for each tested file, change data type
    to integer to performs sums later and percentage calculations.

    Params:
        ut_report_df: UT testing report dataframe obtained using the "read_ut_report_html" function.
    """
    #test_types = ['TESTCASES','Statements','Branches','Pairs','Function Calls']
    clean_df = pd.DataFrame()
    clean_df  = ut_report_df
    for i in test_types:

        clean_df[[i+"_NUMBER",i+"_PERCENTREPORT"]] = clean_df[i].str.split(" ",expand = True)
        clean_df[[i+"_PASSED",i+"_TOTAL"]] = clean_df[i+"_NUMBER"].str.split("/",expand = True)
        clean_df[i+"_PERCENT"] = np.nan

        
        #Cambiar informacion a enteros
        clean_df[i+"_PASSED"] =clean_df[i+"_PASSED"].replace('-',np.nan) # Cambiar guiones a cero
        clean_df[i+"_TOTAL"] =clean_df[i+"_TOTAL"].fillna(value=np.nan) # Cambiar Nones a cero

        clean_df[i+"_PASSED"] =clean_df[i+"_PASSED"].astype('Int64') # Cambiar a enteros
        clean_df[i+"_TOTAL"] =clean_df[i+"_TOTAL"].astype('Int64') 
    
        
        clean_df = clean_df.drop([i,i+"_NUMBER",i+"_PERCENTREPORT"], axis=1) 

        #Remover columnas que no se van a utilizar, la origina y la de number (Agregar luego la de porcentajes)
    return clean_df

def fix_time_format (merged_df):
    
    #hh_mm_ss_pattern = r"^\d{1,2}:\d{2}:\d{2}$"
    mm_ss_pattern = r"^\d{1,2}:\d{2}$"
    
    buffer_df = pd.DataFrame()

    buffer_df = merged_df
    
    
    for i in merged_df.index:
        
        if re.match(mm_ss_pattern,buffer_df["Execution Time"].iloc[i]):
            buffer_df["Execution Time"].iloc[i] = "00:"+buffer_df["Execution Time"].iloc[i].str()
            
        if re.match(mm_ss_pattern,buffer_df["Build Time"].iloc[i]):
            buffer_df["Build Time"].iloc[i] = "00:"+buffer_df["Build Time"].iloc[i].str()

    return buffer_df

def check_time_format(value):
    
    hh_mm_ss_pattern = r"^\d{1,2}:\d{2}:\d{2}$"
    mm_ss_pattern = r"^\d{1,2}:\d{2}$"

    if re.match(hh_mm_ss_pattern, value):
        return value
    elif re.match(mm_ss_pattern, value):
        return "00:"+value


def reformat_time (merged_df):
    '''
    Function: Limpiar informacion nula con np.nan, reformatear el tiempo para usarlo en pd.to_timedelta y poder hacer sumas por dominios
    y Subsystem.

    Parameters: 
        merged_df: Merged dataframe entre ut_report_df y source_files_df
    '''
    buffer_df = pd.DataFrame()

    buffer_df = merged_df

    # buffer_df["Execution Time"] =buffer_df["Execution Time"].replace('-',np.nan)

    buffer_df["Execution Time"] = pd.to_timedelta(buffer_df["Execution Time"]) 

    # buffer_df["Build Time"] =buffer_df["Build Time"].replace('-',np.nan)

    buffer_df["Build Time"] = pd.to_timedelta(buffer_df["Build Time"])

    return buffer_df


def summary_reclassified_df (merged_df):
    merged_df=merged_df.set_index("name")

    merged_df = merged_df.set_index(["Domain", "Subsystem"], append=True,drop=True).reorder_levels(
    ["Domain", "Subsystem", "name"] )

    summary_subsistema = ( #Hacer un data frame con sumas por subsistemas.
    merged_df.groupby(["Domain", "Subsystem"])
    .sum()
    .assign(name="AA Summary_Subsystem")
    .set_index("name", append=True)
    )   

    summary_subsistema["Build Status"] = np.nan

    summary_domain = ( #Hacer un data frame con sumas por subsistemas.
    merged_df.groupby(["Domain"])
    .sum()
    .assign(name="AA Summary_Domain")
    .assign(Subsystem="AA Summary_Domain")
    .set_index("Subsystem", append=True)
    .set_index("name", append=True)
    ) 

    summary_domain["Build Status"] = np.nan

    merged_df = pd.concat([merged_df,summary_subsistema,summary_domain]).sort_index(level=["Domain", "Subsystem","name"],axis = 0) 

    return merged_df



def make_clean_df (merged_df):
    '''
    Function: Join the three values of passed tests, total tests, and porcentage into a single string values and remove the days from the time format.


    Parameters: 
        merged_df: Dataframe obtained merging the source_files_df and ut_report_df

    '''

    clean_df = merged_df[base_columns_list]

    for i in test_types: # WARNING fix
        clean_df.loc[:,i] = merged_df.loc[:,i+"_PASSED"].astype(str)+"/"+merged_df.loc[:,i+"_TOTAL"].astype(str)+"("+merged_df.loc[:,i+'_PERCENT'].round(1).astype(str)+")"

    clean_df['Build Time'] = clean_df['Build Time'].astype(str).str.slice(7) # Warning fix
    clean_df['Execution Time'] = clean_df['Execution Time'].astype(str).str.slice(7)

    return clean_df

def make_style_df(merged_df):

    '''
    
    '''

    style_df = merged_df[base_columns_list]

    for i in test_types:
        style_df = pd.concat([style_df,merged_df[i+"_style"]],axis=1)

    style_df.index=clean_df.index
    style_df.columns=clean_df.columns

    return style_df

def make_reclassified_html(clean_df):
    '''
    Function: Join the styles of the report html with the reclasified dataframe html table, output an


    '''
    with open(report_html_file_add,'r') as fin: #
        file = fin.readlines()[:237]
        html_string = file
        
    html_string = "\n".join(html_string)


    reformat_html_file = clean_df.style.set_td_classes(style_df).to_html() # DF reporte


    reformat_html_file = reformat_html_file.split('\n')[2:] #Split into list by \n and read everything but the first two lines
    reformat_html_file = "\n".join(reformat_html_file) # Join again as a single string

    reclassified_html = html_string + reformat_html_file

    with open('reclassified_ut_report.html','w', newline ='\n') as fout:
        fout.write(reclassified_html)

ut_report_df = pd.DataFrame()

'''
Variables with the addresses of the vectorcast html report and a .txt of directory addresses of the project
'''

report_html_file_add = 'SW_Unit_Test_full_status_report_X02_003_000.html'
report_csv_file_add = 'test_results 1.csv'
projectdirectorytxt = 'ALL_SOURCE_FILES.TXT'

# Leer el csv
csv_df = pd.read_csv(report_csv_file_add) 

csv_df = csv_df.drop(["Test Suite"],axis =1)# Quitar la primera columna


csv_df = csv_df.rename(columns ={"Environment (488)":"name"})

csv_df['name'] = csv_df['name'].str.slice(3)

testnames = csv_df['name'] # Extract the names of the tests 


source_files_df= read_project_directory(projectdirectorytxt,testnames) 




# source_files_df["name"] = source_files_df["name"].fillna(source_files_df[9]) # Fill the names where the values are shifted 


merged_df = pd.merge(source_files_df,csv_df,how="left", on = "name")



merged_df.sort_values(by=['Domain','Subsystem'])



test_types = ['Test Cases', 'Expected Values','Statement Coverage', 'Branch Coverage','Pair Coverage', 'Function Call Coverage']

merged_df = clean_report_data(merged_df) # Separate string "1/1" into int data for later calculations


merged_df["Execution Time"] = merged_df["Execution Time"].replace(np.nan,"00:00:00")
merged_df["Build Time"] = merged_df["Build Time"].replace(np.nan,"00:00:00")

merged_df["Execution Time"] = merged_df["Execution Time"].apply(check_time_format)

merged_df["Build Time"] = merged_df["Build Time"].apply(check_time_format)





merged_df = reformat_time(merged_df) # Reformat time string for later use in sums

# 
merged_df = summary_reclassified_df(merged_df)


for i in test_types:
    merged_df[i+'_PERCENT'] = (merged_df[i+"_PASSED"] / merged_df[i+"_TOTAL"]) * 100

# Evaluate style of cells 
for i in test_types: 
    merged_df.loc[merged_df[i+"_PASSED"] == merged_df[i+"_TOTAL"], i+"_style"] = "success"
    merged_df.loc[merged_df[i+"_PASSED"] < merged_df[i+"_TOTAL"], i+"_style"] = "danger"


base_columns_list = ['Build Status', 'Build Time','Execution Time']


clean_df = make_clean_df(merged_df) # Create dataframe with presntation for the final table


# Make dataframe for the styles of the table
style_df = make_style_df(merged_df)

make_reclassified_html(clean_df)
        

# %%

not_present = csv_df["name"][~csv_df["name"].isin(source_files_df["name"])]

print(not_present)
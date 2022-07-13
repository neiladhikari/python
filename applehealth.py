import pandas as pd
import xmltodict
import re
import matplotlib.pyplot as plt
import datetime

#xmltodict will convert the input file to a Python dictionary.
input_path = './na_applehealth_20220624.xml'
with open(input_path, 'r') as xml_file:
    input_data = xmltodict.parse(xml_file.read())

#######################################################

#Variable input_data is a dictionary containing the whole data from the original XML file.
#Actual health records are stored in the Record key of the HealthData dictionary:
records_list = input_data['HealthData']['Record']

#This is a list of dictionaries that can be imported directly into a Pandas data frame:
df = pd.DataFrame(records_list)

# shorter observation names
df['@type'] = df['@type'].str.replace('HKQuantityTypeIdentifier', '')
df['@type'] = df['@type'].str.replace('HKCategoryTypeIdentifier', '')
df['@type'] = df['@type'].str.replace('SDNN', '')
df.to_csv('applealth_20220615.csv', mode='w', index=False) #write entire formatted applehealth dataframe to disk.

#get fat data
#fat = df[df.apply(lambda row: row.astype(str).str.contains('Fat').any(), axis=1)] #find matching word in any row/column. more resource intensive.
fat = df[df['@type'] == "BodyFatPercentage"]
#delete unnecessary/ irrelevant columns
fat.drop(['@sourceName', '@sourceVersion', '@unit', '@startDate', '@endDate', 'MetadataEntry', '@device', 'HeartRateVariabilityMetadataList'], axis=1, inplace=True)

fat['@value'] = fat['@value'].apply(pd.to_numeric) #convert datatype to numeric
fat['@value'] = fat['@value'].apply(lambda x: x*100) #multiply by 100 to get values in percent.
fat.drop(columns=['@type'], inplace=True) #drop unnecessary columns
fat.reset_index(drop=True, inplace=True) #reset index
fat.columns=['Date', 'Fat%'] #rename columns
fat = fat.set_index('Date') #set index to Date column
fat.to_csv('fat_20220615.csv',mode='w', index=False) #write fat data to disk

#calculate fat moving average
fat['SimpleMovingAverage_30_days'] = fat['Fat%'].rolling(30).mean()
fat.dropna(inplace=True)

#plot fat data
fat[['Fat%', 'SimpleMovingAverage_30_days']].plot(label='Total Body Fat %', figsize=(16,8))
plt.xticks(rotation=90)

#get steps data
#steps = df[df.apply(lambda row: row.astype(str).str.contains('StepCount').any(), axis=1)]
steps = df[df['@type'] == "StepCount"]
#drop unwanted columns
steps = steps.drop(columns=['@type', '@sourceName', '@sourceVersion', '@unit', '@startDate', '@endDate', 'MetadataEntry', '@device', 'HeartRateVariabilityMetadataList'])
steps.reset_index(drop=True, inplace=True) #reset index
steps.columns=['CreationDate', 'StepCount'] #rename columns
steps['CreationDate'] = steps['CreationDate'].dt.date #keeps only date and not the time
#convert the value to the specific type for this metric:
steps.loc[:, 'StepCount'] = pd.to_numeric(steps.loc[:, 'StepCount'])
steps = steps.groupby('CreationDate').sum() #group by dates
#calculate 30-day moving average
steps['SMA30'] = steps['StepCount'].rolling(30).mean()
steps.dropna(inplace=True)
steps.to_csv('steps_20220615.csv', mode=w, index=False) #write steps data to disk

#plot steps data
steps[['StepCount', 'SMA30']].plot(label='StepCount', figsize=(16,8))
plt.xticks(rotation=90)
plt.axhline(y = 7000, color = 'r', linestyle = '-')

#get sleep data
sleep = df[df['@type'] == "SleepAnalysis"]
sleep.loc['@sourceName'] = sleep['@sourceName'].astype(str)
#drop unwanted columns
sleep = sleep.drop(columns=['@type', '@sourceName', '@sourceVersion', '@unit', '@value', 'MetadataEntry', '@device', 'HeartRateVariabilityMetadataList'])
sleep['@creationDate'] = pd.to_datetime(sleep['@creationDate']) #convert to datetime
sleep['@startDate'] = pd.to_datetime(sleep['@startDate']) #convert to datetime
sleep['@endDate'] = pd.to_datetime(sleep['@endDate']) #convert to datetime
sleep.reset_index(drop=True, inplace=True)
sleep.columns = ['CreationDate', 'StartDate', 'EndDate'] #rename columns
sleep['TimeAsleep'] = sleep['EndDate'] - sleep['StartDate'] #calculate time asleep

#analyze sleep data
#1REM cycle = 1x 90-minute undisturbed cycle
sleep = sleep.groupby('CreationDate').agg(Total_Time_Asleep=('TimeAsleep', 'sum'),
    BedTime=('StartDate', 'min'), 
    WakeTime=('EndDate', 'max'), 
    SleepCounts=('CreationDate','count'), 
    REM_Cycles=pd.NamedAgg(column='TimeAsleep', aggfunc=lambda x: (x // datetime.timedelta(minutes=90)).sum()))

sleep['Time_in_bed'] = sleep['WakeTime'] - sleep['BedTime']
sleep['Restless_Time'] = sleep['Time_in_bed'] - sleep['Total_Time_Asleep']

#plot sleep data #1
sleep[['Total_Time_Asleep']].plot(label='Total_Time_Asleep', figsize=(16,8))
plt.xticks(rotation=90)

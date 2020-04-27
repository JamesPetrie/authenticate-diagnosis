import secrets
import math
import time
import hmac
import hashlib
import base64
import smtplib
from email.message import EmailMessage

KEY_BYTES = 16 
PERM_DIGITS = 6 
NUM_MONTHS = 1
PERM_NUM_DELAY_MINUTES = 1
MAX_DELAY = 10

healthEmployees = dict()
validatedReports = []

maxId = -1

class HealthEmployee:
  def __init__(self, email, key):
      self.email = email
      self.key = key

# compute the permission number for a given employee ID, employee key, and time
def permissionNumber(id, key, minute):
  permNum = hmac.new(key, (str(minute)).encode(), "SHA256").hexdigest()
  permNum = getLastDigits(permNum, PERM_DIGITS)
  return str(id) + "-" + permNum[0:3] + "-" + permNum[3:PERM_DIGITS]
  

# precompute many permission numbers for a health employee 
def precomputePermissionNumbers(key, id):
  permFile = "permNums_" + str(id) + ".csv"
  f = open(permFile , "w")
  f.write("Minute, PermissionNumber\n")
  currentSec = time.time() # seconds
  currentMin = math.floor(currentSec/60)
  for minute in range(currentMin, currentMin + NUM_MONTHS*30*24*60, PERM_NUM_DELAY_MINUTES): 
    permNum = permissionNumber(id, key, minute)
    f.write(str(minute) + ", " + permNum + "\n")
  return permFile 

# create an employee profile for each submitted email
def createEmployeeProfiles(emails):
  for email in emails:
    id = nextId()
    key = secrets.token_bytes(KEY_BYTES) 
    addHealthEmployee(id, email, key)
    permFile = precomputePermissionNumbers(key, id) 
    emailPermFile(email, permFile)

  
# add a new health employee
def addHealthEmployee(id, email, key):
    newEmployee = HealthEmployee(email, key)
    healthEmployees[id] = newEmployee #todo: use dynamoDB

# email health employee with many permission numbers to be used in the future 
def emailPermFile(email, permFile):
  s = smtplib.SMTP('smtp.gmail.com',587)
  s.ehlo()
  s.starttls()
  s.login("covidwatchtest2", "covid19watch")

  msg = EmailMessage()
  msg.set_content("Test content")
  msg['Subject'] = "Test Email" 
  msg['From'] = "covidwatchtest2@gmail.com"
  msg['To'] = email 

  #todo: attach permFile to email
  s.send_message(msg)
  s.quit()

# send confirmation email to employee who issued permission number that the report was accepted (but with no additional data)
def sendConfirmationEmail(email):
  s = smtplib.SMTP('smtp.gmail.com',587)
  s.ehlo()
  s.starttls()
  s.login("covidwatchtest2", "covid19watch")
  msg = EmailMessage()
  msg.set_content("Report successfully submitted")
  msg['Subject'] = "Test Email" 
  msg['From'] = "covidwatchtest2@gmail.com"
  msg['To'] = email 
  s.send_message(msg)
  s.quit()

# check if the submitted permission number is valid for the current time window
def isPermissionNumberValid(permissionNum, id):
  key = healthEmployees[id].key 
  currentMin = math.floor(time.time()/60)
  for minute in range(currentMin, currentMin - MAX_DELAY, -PERM_NUM_DELAY_MINUTES):
    if permissionNum == permissionNumber(id, key, minute):
      # todo: add check preventing permission number from being reused
      return True
  return False

# function called when client requests to submit a new infection report
def newReport(report, permissionNum):
  print("attempting to submit report")
  id = int(permissionNum.split("-")[0])
  if isPermissionNumberValid(permissionNum, id):
    validatedReports.append(report)
    print("successfully submitted report")
    sendConfirmationEmail(healthEmployees[id].email)
    #todo: mark permissionNum as already used
  else:
    print("report rejected - invalid permission number")
    #todo iterate through keys in report and increase failed attempts counter
    
# gather recently authenticated reports and publish them to a CDN
#todo: make this run every hour
def publishReports():
  #todo: lock DynamoDB 
  global validatedReports
  #todo: shuffle daily keys
  #todo: implement sendToCdn 
  #sendToCdn(validatedReports)
  validatedReports = []

def getLastDigits(num, last_digits_count):
    return str(num)[-last_digits_count:]

# find the next unused employee ID
#todo: use dynamoDB and make this an atomic operation
def nextId():
  global maxId
  maxId = maxId + 1
  return maxId




# create an employee profile then see if reports can be submitted
def runTest():
  createEmployeeProfiles(["james.petrie94@gmail.com"])

  testPermissionNum = "0-000-000" 
  newReport("report", testPermissionNum) # should be rejected since the permission number is made up 

  testPermissionNum = permissionNumber(0, healthEmployees[0].key, math.floor(time.time()/60) - 3)
  newReport("report", testPermissionNum) # should be accepted since the permission number is only 3 minutes old


runTest()


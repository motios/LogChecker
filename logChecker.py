import os
import glob
import datetime
import smtplib,cgi
#import html

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
# Author: Moti Ostrovski - motio@edp.co.il
# Date: 06.12.2018
# Description: This script monitors IDM drivers log status.
#         The script search for all the drivers in a driver folder, and for each one of them,
#         it check if the driver log is changing, or if driver name is in excludedLogsFolders - it's state OK.
#         on driver log is not  changing and not name is in excludedLogsFolders save result in errorsLog file and send mail.
#          before send mail and before save result to errorsLog result checked if not equals to prevision result
#          to prevent send some email more then once.
#          tested in windows and linux( suse 12 sp3 )
# Flags:
#   onErrorAlwaysSendEmail: flag is False - email send only if error is changed. flag is True - email send on any error every scheduled time
#   debugMod: flag is True - data will be collected on execute and will be writed logFile every scheduled time. flag is False - data is not collected and file not write  


#<editor-fold desc=" variables">

# fs section
# logsPath='drive:/folder/logs'
logsPath='D:/Novell/IDM-Logs'
extension = '*.xml'
sizeFileExtention='.txt'

# exclude example:
# excludedLogsFolders =['driverNull','set',]
excludedLogsFolders =['Workday','HealthCheck','Office365']
debugLogPath= 'debug.log'
errorLogPath = 'errorLog.log'
prevFileSizePrefix='_prev'
successLogs=[]
errorLogs=[]
debugMod=True
onErrorAlwaysSendEmail=True
currentTime = datetime.datetime.now()


# stringHelper variables section
constValFile="last="
fileNotValidStr= 'file not valid'
fileNotValidMessage='file not valid style. not contains last='
notFilesMessage="folder is empty"
# fileNotChangedMessage="folder: {}\r\nfile: {} \r\nfile does not changed. Current size is: {}."
fileNotChangedMessage="file {0} does not changed. Current size is: {1}."

#email section
smtpServer='172.16.3.34'
smtpSubject='IDM logfiles monitoring alert!'
smtpFrom='CorporateIT@perion.com'
smtpTo=['idmalerts@edp.co.il','CorporateITGlobal@perion.com']

#</editor-fold>

# for debug
def debugLogger(str):
    if debugMod:
        with open(debugLogPath, 'a') as f:
            f.write(str + '\n')


# read file driver+_prev+.txt. read last size from file.
# if file not exist - create new with start parameters
def getLastSize(prevSizePath):
    debugLogger("getLastSize")
    if not os.path.isfile(prevSizePath):
        debugLogger("file {} not availible".format(prevSizePath))
        file=open(prevSizePath,'w')
        debugLogger("create new file. open for write")
        file.write(constValFile + '0')
        debugLogger("write to file "+constValFile + '0')
        file.close()
        debugLogger("close file")
        return "0"
    else:
        size=fileReader(prevSizePath)
        if not size.startswith(constValFile):
            return fileNotValidStr
        else:
            return size[5:]

# get last modify file: name and size
def get_latest_file(path, *paths):
    debugLogger("get_latest_file")
    fullpath = os.path.join(path, *paths)
    debugLogger("fullpath: "+fullpath)
    files = glob.glob(fullpath)
    debugLogger("get files")
    if not files:
        debugLogger("files is null")
        return None
    debugLogger("files is not null")
    latest_file = max(files, key=os.path.getmtime)
    debugLogger("latest_file: "+latest_file)
    _, filename = os.path.split(latest_file)
    debugLogger("fileName: " + filename)
    fileSize=os.path.getsize(latest_file)
    debugLogger("fileSize: " + str(fileSize))
    return filename,fileSize

# write current file new size to file
def updateNewSize(newSize, filePath):
    debugLogger("updateNewSize")
    file= open(filePath,'w')
    debugLogger("open file to write.")
    file.write(constValFile+str(newSize))
    debugLogger(constValFile+str(newSize))
    file.close()
    debugLogger("file close.")

# validate values size, fileName and check if not equals
def sizeValidate(prevSize,fileSize, fileNameStr,folder):
    debugLogger("sizeValidate")
    if prevSize==fileNotValidStr:
        errorLogs.append('driver= ' + folder + '. status= ' + fileNotValidMessage)
        debugLogger("prev size file not contains valid record. error log append. "+'driver= ' + folder + '. status= ' + fileNotValidMessage)
    elif prevSize == fileSize:
        errorLogs.append('driver= ' + folder + '. status= ' + fileNotChangedMessage.format(fileNameStr,fileSize))
        debugLogger("prev file size = current file size. error log append. "+'driver= ' + folder + '. status= ' + fileNotChangedMessage.format(fileNameStr,fileSize))
    else:
        updateNewSize(fileSize, folder+prevFileSizePrefix+sizeFileExtention)

# send email
def send_email(text, sender, to, subject, smtp_server):
    debugLogger("send_email")
    htmlStr = """\
<html>
  <head></head>
  <body>
   <h1>Perion IDM Logs Monitoring Alert</h1><br><br>
    <p>%s</p>
   <br>
   <br>
   <br>
   <a href=" http://www.edp.co.il/ ">
     <img src="https://www.edp.co.il/wp-content/uploads/2017/02/edp_logo_334x88_nat.png" alt="">
   </a>
  </body>
</html>
""" % cgi.escape(text).replace("\n", "<br>")#html.escape(text).replace("\n", "<br>")
    debugLogger("set html text: "+ htmlStr)
    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    debugLogger("subject: " + subject)
    msg['From'] = sender
    debugLogger("sender: " + sender)
    #debugLogger("To: " + to)
    # Record the MIME types of both parts - text/plain and text/html.
    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(htmlStr, 'html')
    debugLogger("set part")
    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    msg.attach(part1)
    msg.attach(part2)
    debugLogger("attach message")
    # Send the message via local SMTP server.
    s = smtplib.SMTP(smtp_server)
    debugLogger("smtp_server: "+smtp_server)
    # sendmail function takes 3 arguments: sender's address, recipient's address
    # and message to send - here it is sent as one string.
    s.sendmail(sender, to, msg.as_string())
    debugLogger("mail is sended")
    s.quit()
    debugLogger("quit command")

# read file, return data
def fileReader(pathToFile):
    debugLogger("fileReader")
    with open(pathToFile, 'r') as content_file:
        content = content_file.read()
    return content

# if current state(errors) equals prev state(from logfile errorLog) return false - state not changed
# only if condition false, email is to be send
def stateChangeChecker(errors):
    debugLogger("stateChangeChecker")
    prevErrors = fileReader(errorLogPath) if os.path.isfile(errorLogPath) else ""
    # prevErrors =""
    # if os.path.isfile(errorLogPath):
    #     fileReader(errorLogPath)
    debugLogger("prevErrors: " + prevErrors)
    if not onErrorAlwaysSendEmail and errors == prevErrors:
        return False
    return True

debugLogger("\n\n\n{} start program".format(currentTime))
for folder in os.listdir(logsPath):
    debugLogger("folder: "+folder)
    if not folder in excludedLogsFolders and os.path.isdir(logsPath+'/'+folder):
        # driver path not excluded
        prevSize = getLastSize(folder+prevFileSizePrefix+sizeFileExtention)
        debugLogger("prev size: " + prevSize)
        result = get_latest_file(logsPath+'/'+folder,extension)
        debugLogger("result: " + str(result))
        if (result != None and len(result) > 0):
            sizeValidate(prevSize, str(result[1]), result[0],folder)
            debugLogger("result !=null and result count {}".format(len(result)))
        else:
            errorLogs.append('driver= '+folder+'. status= '+notFilesMessage)
            debugLogger("result =null or result count=0. append errorLog file. "+'driver= '+folder+'. status= '+notFilesMessage)
    else:
        debugLogger("folder {} is excluded".format(folder))

message =""
for error in errorLogs:
    message += error + '\n'
debugLogger("message: "+message)
stateChange = stateChangeChecker(message)
debugLogger("stateChange: " + str(stateChange))
#send email and save errors in file only if statechange ==true
if message.__len__() > 0 and stateChange :
    with open(errorLogPath, 'w') as f:
        f.writelines(message)
	debugLogger("sendMail")
    send_email(message,smtpFrom,smtpTo,smtpSubject,smtpServer)
currentTime=datetime.datetime.now()
debugLogger("{} end program\n--------------------------------------".format(str(currentTime)))
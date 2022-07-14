
import os
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
gauth = GoogleAuth()

gauth.LocalWebserverAuth()
drive = GoogleDrive(gauth)

#folder_list = drive.ListFile({'q': "trashed=false"}).GetList()
#for folder in folder_list:
#     print('folder title: %s, id: %s' % (folder['title'], folder['id']))

file1 = drive.CreateFile({'title': 'folder_test', 'mimeType': 'application/vnd.google-apps.folder'})
file1.Upload()
id = file1['id']

file2 = drive.CreateFile({'title': 'testing', "parents": [{"id": id, "kind": "drive#childList"}]})
file2.SetContentFile('road.jpg') #The contents of the file
file2.Upload()

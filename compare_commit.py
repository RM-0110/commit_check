import json
import os
from datetime import datetime, timedelta
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

def authenticate_drive():
    client_secrets_data = json.loads(os.getenv("CLIENT_SECRET"))
    with open("client_secrets_temp.json", "w") as f:
        json.dump(client_secrets_data, f)

    gauth = GoogleAuth()
    scope = ["https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("client_secrets_temp.json", scope)
    gauth.credentials = creds

    os.remove("client_secrets_temp.json")
    return GoogleDrive(gauth)

def get_file_for_date(drive, target_date):
    file_list = drive.ListFile({'q': "title contains 'commit_data_' and trashed=false"}).GetList()
    for file in file_list:
        if target_date in file['title']:
            return file
    return None

drive = authenticate_drive()

today = datetime.now().strftime('%Y-%m-%d')
yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

# Get today's and yesterday's commit files
today_file = get_file_for_date(drive, today)
yesterday_file = get_file_for_date(drive, yesterday)

if not today_file:
    print("No commit data for today.")
    exit()

if not yesterday_file:
    print("No commit data for yesterday. Treating all today's commits as new.")
    today_file.GetContentFile(f"commit_data_{today}.txt")
    exit()

yesterday_file.GetContentFile(f"commit_data_{yesterday}.txt")
today_file.GetContentFile(f"commit_data_{today}.txt")

def compare_commits(today_file, yesterday_file):
    with open(today_file, 'r') as t, open(yesterday_file, 'r') as y:
        today_commits = set(t.readlines())
        yesterday_commits = set(y.readlines())

    new_commits = today_commits - yesterday_commits

    email_body = "List of prod and preprod branches and commit IDs, generated on " + str(today) + "\n\n"

    if new_commits:
        email_body += "Newly changed commits since yesterday:\n"
        for index, commit in enumerate(new_commits):
            email_body += str(index + 1) + ". " + commit.strip() + "\n"
    else:
        email_body += "No new commits found since yesterday.\n"

    send_email(email_body)

def send_email(email_body):
    sender_email = "riddhimann@navyatech.in"
    receiver_emails = ["riddhimann@navyatech.in", "kirana@navyatech.in"]
    password = os.getenv('APP_PASSWORD')

    subject = "Daily Commit List - Preprod and Prod - " + str(today)

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = ", ".join(receiver_emails)
    message["Subject"] = subject
    message.attach(MIMEText(email_body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_emails, message.as_string())
        server.quit()
        print("Email sent successfully.")
    except Exception as e:
        print("Error:", str(e))

compare_commits(f"commit_data_{today}.txt", f"commit_data_{yesterday}.txt")

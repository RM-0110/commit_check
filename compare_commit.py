from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os
import pandas as pd

# Google Drive Authentication
gauth = GoogleAuth()
gauth.LocalWebserverAuth()  # Follow the URL in the console for authentication
drive = GoogleDrive(gauth)

# Folder ID where data will be stored in Google Drive
drive_folder_id = '1fbL73bQ7zyf-D8p74ShCzuTD4oI_lC9f'

# Save commit data to Drive
def save_commit_data(commit_list, filename):
    content = "\n".join(commit_list)
    file_list = drive.ListFile({'q': f"'{drive_folder_id}' in parents and title = '{filename}'"}).GetList()

    if file_list:
        file = file_list[0]  # Update the existing file
        file.SetContentString(content)
        file.Upload()
    else:
        file = drive.CreateFile({'title': filename, 'parents': [{'id': drive_folder_id}]})
        file.SetContentString(content)
        file.Upload()

# Retrieve commit data from Drive
def fetch_commit_data(filename):
    file_list = drive.ListFile({'q': f"'{drive_folder_id}' in parents and title = '{filename}'"}).GetList()
    if file_list:
        file = file_list[0]  # Found file
        content = file.GetContentString()
        return content.strip().split("\n")
    return []

# Compare commit lists
def compare_commits(today_commits, yesterday_commits):
    return list(set(today_commits) - set(yesterday_commits))

# Main Logic
today_date = pd.Timestamp.now('Asia/Kolkata').strftime('%Y-%m-%d')
yesterday_date = (pd.Timestamp.now('Asia/Kolkata') - pd.Timedelta(days=1)).strftime('%Y-%m-%d')

today_filename = f'commit_data_{today_date}.txt'
yesterday_filename = f'commit_data_{yesterday_date}.txt'

commit_list_preprod = main_preprod(username, password, mapping)
commit_list_prod = main_prod(username, password, mapping)

save_commit_data(commit_list_preprod + commit_list_prod, today_filename)
yesterday_commits = fetch_commit_data(yesterday_filename)

changed_commits = compare_commits(commit_list_preprod + commit_list_prod, yesterday_commits)

# Email content update
email_body = "List of prod and preprod branches and commit IDs, generated on " + str(today_date) + "\n\n"
for index, value in enumerate(commit_list_preprod):
    email_body += str(index + 1) + ". " + value + "\n"

diff_section = "\nNewly changed commits since yesterday:\n" if changed_commits else "\nNo new commits found since yesterday.\n"
email_body += diff_section

for index, value in enumerate(changed_commits):
    email_body += str(index + 1) + ". " + value + "\n"

email_body += "\n\nBuild numbers having 'none' value indicates that the latest preprod deployment does not have any upstream project linked to it."

# Email sending logic remains the same
sender_email = "riddhimann@navyatech.in"  # Replace with your email
receiver_emails = ["riddhimann@navyatech.in", "kirana@navyatech.in"]  # Replace with your email
password = os.getenv('APP_PASSWORD')

subject = "Daily Commit List - Preprod and Prod - " + str(formatted_time)

# Create email
message = MIMEMultipart()
message["From"] = sender_email
message["To"] = ", ".join(receiver_emails)
message["Subject"] = subject
message.attach(MIMEText(email_body, "plain"))

# Send email
try:
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender_email, password)
    server.sendmail(sender_email, receiver_emails, message.as_string())
    server.quit()
    print("Email sent successfully.")
except Exception as e:
    print("Error:", str(e))

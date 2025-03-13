import os
import requests
from requests.auth import HTTPBasicAuth
import re
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

username = "riddhimann" # add your jenkins username
password = os.getenv('JENKINS_PASSWORD')
print(password)

def get_branch(repo, url, jsonurl, username, password, branch_name = None):
  response = requests.get(jsonurl, auth=HTTPBasicAuth(username, password))
  if response.status_code == 200:
    build_info = response.json()
    page_text = response.text
    actions = build_info.get('actions', [])
    for action in actions:
      if 'parameters' in action:
          for parameter in action['parameters']:
              if parameter['name'] == 'GIT_BRANCH_NAME':
                  branch_name = parameter['value']
                  break
    if branch_name:
      print(f'Branch Name: {branch_name}')
      return branch_name

    elif not branch_name:
      response2 = requests.get(url, auth=HTTPBasicAuth(username, password))
      page_text = response2.text
      branch_pattern = r'Cloning branch - (\w+)'
      match = re.search(branch_pattern, page_text)
      if match:
        branch_name = match.group(1)  # Extract matched text
        print(branch_name)  # Output: master
        return branch_name
      else:
        print("Branch name not found.")
    else:
      print('GIT_BRANCH_NAME not found in the build parameters or page source')
      return None
  else:
    print("Failed to retrieve the page: "+url+str(response.status_code))

def get_user(url, username, password):
  response = requests.get(url, auth=HTTPBasicAuth(username, password))
  if response.status_code == 200:
    page_text = response.text
    user = r'Started by user (\w+)'
    match_user = re.search(user, page_text)
    if match_user:
        um_user = match_user.group(1)
        print("Deployed by", um_user)
    else:
        print("user not found while trying to send request to "+url)
  else:
    print("Failed to retrieve the page: "+url+str(response.status_code))

def get_commit(repo, url, username, password):
    try:
        response = requests.get(url, auth=HTTPBasicAuth(username, password))
        if response.status_code != 200:
            print(f"Failed to retrieve the page. Status Code: {response.status_code}")
            return None

        page_text = response.text
        commit_patterns = [
            r'COMMIT_ID_IN_TAG = (\w+)',
            r'Commit id - (\w+)',
            r'last commit for alpha apps:(\w+)',
            r'last commit:(\w+)',
            r'ANALYST_APP_COMMIT_ID = (\w+)'
        ]

        for pattern in commit_patterns:
            match_commit = re.search(pattern, page_text)
            if match_commit:
                commit_id = match_commit.group(1)
                print(f"{repo} commit id: {commit_id}")
                return commit_id

        print("Commit ID not found")
        return None

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def get_build_number(repo, url, username, password):
  response = requests.get(url, auth=HTTPBasicAuth(username, password))
  if response.status_code == 200:
    page_text = response.text
    pattern = r'Started by upstream project ".*?/deploy-dev" build number (\d+)'
    match = re.search(pattern, page_text)
    if match:
      build_number = match.group(1)
      print(f"{repo} build number: ", build_number)
      return build_number
    else:
      print("no match")

mapping = {
  "cancerbaba": {
    "job_name_dev": "cancerbaba/job/2.0/job/deploy-dev",
    "job_name_preprod": "cancerbaba/job/2.0/job/deploy-preprod",
    "job_name_prod": "cancerbaba/job/2.0/job/deploy-pri-prod"
  },
  "experts": {
    "job_name_dev": "experts/job/docker/job/deploy-dev",
    "job_name_preprod": "experts/job/docker/job/deploy-preprod",
    "job_name_prod": "experts/job/docker/job/deploy-pri-prod"
  },
  "core": {
    "job_name_dev": "vyas/job/core/job/deploy-dev",
    "job_name_preprod": "vyas/job/core/job/deploy-preprod",
    "job_name_prod": "experts/job/docker/job/deploy-pri-prod"
  },
  "UI": {
    "job_name_dev": "vyas/job/ui/job/deploy-dev",
    "job_name_preprod": "vyas/job/ui/job/deploy-preprod",
    "job_name_prod": "vyas/job/core/job/deploy-pri-prod"
  },
  "user_management": {
    "job_name_dev": "user-management/job/deploy-dev",
    "job_name_preprod": "user-management/job/deploy-preprod",
    "job_name_prod": "user-management/job/deploy-pri-prod"
  },
  "patient_reports": {
    "job_name_dev": "vyas/job/patient-reports/job/deploy-dev",
    "job_name_preprod": "vyas/job/patient-reports/job/deploy-preprod",
    "job_name_prod": "vyas/job/patient-reports/job/deploy-pri-prod"
  },
  "refresh_articles": {
    "job_name_dev": "vyas/job/refresh-articles/job/deploy-dev",
    "job_name_preprod": "vyas/job/refresh-articles/job/deploy-preprod",
    "job_name_prod": "vyas/job/refresh-articles/job/deploy-pri-prod"
  },
  "process": {
    "job_name_dev": "process/job/docker/job/deploy-dev",
    "job_name_preprod": "process/job/docker/job/deploy-preprod",
    "job_name_prod": "process/job/docker/job/deploy-pri-prod"
  },
  "nes": {
    "job_name_dev": "nes/job/deploy-dev",
    "job_name_preprod": "nes/job/deploy-preprod",
    "job_name_prod": "nes/job/deploy-pri-prod"
  },
  "www": {
    "job_name_dev": "www/job/3.0/job/deploy-dev",
    "job_name_preprod": "www/job/3.0/job/deploy-preprod",
    "job_name_prod": "www/job/3.0/job/deploy-pri-prod"
  },
  "napi": {
    "job_name_dev": "navyaapi/job/4.0/job/deploy-dev",
    "job_name_preprod": "navyaapi/job/4.0/job/deploy-preprod",
    "job_name_prod": "navyaapi/job/4.0/job/deploy-pri-prod"
  },
  "ui_user_management": {
    "job_name_dev": "vyas/job/ui-user-management/job/deploy-dev",
    "job_name_preprod": "vyas/job/ui-user-management/job/deploy-preprod",
    "job_name_prod": "vyas/job/ui-user-management/job/deploy-pri-prod"
  },
  "sendmail": {
    "job_name_dev": "utilities/job/sendemail/job/deploy-dev",
    "job_name_preprod": "utilities/job/sendemail/job/deploy-preprod",
    "job_name_prod": "utilities/job/sendemail/job/deploy-pri-prod"
},
  "analyst": {
    "job_name_dev": "vyas/job/analyst/job/deploy-dev",
    "job_name_preprod": "vyas/job/analyst/job/deploy-preprod",
    "job_name_prod": "vyas/job/analyst/job/deploy-pri-prod"
}
}

def main_preprod(username, password, mapping):
  commit_list = []
  repolist = ["user_management", "cancerbaba", "nes", "refresh_articles", "core", "UI", "patient_reports", "www", "ui_user_management", "napi", "process", "experts", "sendmail", "analyst"]
  for index,repo in enumerate(repolist):
    repo_job = mapping[repo]["job_name_preprod"]
    url = f"https://ci.navyanetwork.com/job/{repo_job}/lastSuccessfulBuild/consoleText"
    jsonurl = f"https://ci.navyanetwork.com/job/{repo_job}/lastSuccessfulBuild/api/json"
    print("Checking for: "+repo)
    branch = get_branch(repo, url, jsonurl, username, password)
    if branch == None:
      branch = "develop"
    else:
      branch = branch
    get_user(url, username, password)
    commitid = get_commit(repo, url, username, password)
    build_number = get_build_number(repo, url, username, password)
    commit_string = f"{repo}: {branch}, Commit ID: {commitid}, build_number: {build_number}"
    commit_list.append(commit_string)
    print("---------------------")
  return commit_list

commit_list_preprod = main_preprod(username, password, mapping)
print(commit_list_preprod)

def main_prod(username, password, mapping):
  commit_list = []
  repolist = ["user_management", "cancerbaba", "nes", "refresh_articles", "core", "UI", "patient_reports", "www", "ui_user_management", "napi", "process", "experts", "sendmail", "analyst"]

  for index,repo in enumerate(repolist):
    repo_job = mapping[repo]["job_name_prod"]
    url = f"https://ci.navyanetwork.com/job/{repo_job}/lastSuccessfulBuild/consoleText"
    jsonurl = f"https://ci.navyanetwork.com/job/{repo_job}/lastSuccessfulBuild/api/json"
    print("Checking for: "+repo)
    branch = get_branch(repo, url, jsonurl, username, password)
    if branch == None:
      branch = "develop"
    else:
      branch = branch
    get_user(url, username, password)
    commitid = get_commit(repo, url, username, password)
    build_number = get_build_number(repo, url, username, password)
    commit_string = f"{repo}: {branch}, Commit ID: {commitid}, build_number: {build_number}"
    commit_list.append(commit_string)
    print("---------------------")
  return commit_list

commit_list_prod = main_prod(username, password, mapping)
print(commit_list_prod)

time_ist = pd.Timestamp.now('Asia/Kolkata')
formatted_time = time_ist.strftime("%d/%m/%Y %H:%M")
print("List of preprod branches and commit IDs, generated on "+str(formatted_time)+"\n")
for index, value in enumerate(commit_list_preprod):
  print(str(index+1)+". "+value)

print("List of prod branches and commit IDs, generated on "+str(formatted_time)+"\n")
for index, value in enumerate(commit_list_prod):
  print(str(index+1)+". "+value)

#-----------------------------------------------

email_body = "List of preprod branches and commit IDs, generated on " + str(formatted_time) + "\n\n"
for index, value in enumerate(commit_list_preprod):
    email_body += str(index + 1) + ". " + value + "\n"

email_body += "\nList of prod branches and commit IDs, generated on " + str(formatted_time) + "\n\n"
for index, value in enumerate(commit_list_prod):
    email_body += str(index + 1) + ". " + value + "\n"

email_body += "\n\n\n"
email_body += "Build numbers having 'none' value indicates that the latest preprod deployment does not have any upstream project linked to it."

sender_email = "riddhimann@navyatech.in"  # Replace with your email
receiver_emails = ["riddhimann@navyatech.in", "kirana@navyatech.in", "pushpa@navyatech.in", "armugam@navyatech.in"]  # Replace with your email
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

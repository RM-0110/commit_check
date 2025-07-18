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
repolist = ["user_management", "cancerbaba", "nes", "refresh_articles", "core", "UI", "patient_reports", "www", "ui_user_management", "napi", "process", "experts", "sendmail", "analyst", "DDL", "DML"]

preprod_current_branches = {}
prod_current_branches = {}

expected_branches_preprod = {"user_management": "master", "cancerbaba": "moffitt_cerner", "nes": "develop", "refresh_articles": "master", "core": "master", "UI": "master", "patient_reports": "master", "www": "develop", "ui_user_management": "master", "napi": "develop", "process": "develop", "experts": "develop", "sendmail": "master", "analyst": "master", "DDL": "develop", "DML": "develop"}
expected_branches_prod = {"user_management": "master", "cancerbaba": "develop", "nes": "develop", "refresh_articles": "develop", "core": "master", "UI": "master", "patient_reports": "master", "www": "develop", "ui_user_management": "master", "napi": "develop", "process": "develop", "experts": "develop", "sendmail": "master", "analyst": "master", "DDL": "develop", "DML": "develop"}

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
        return um_user
    else:
        print("user not found while trying to send request to "+url)
  else:
    print("Failed to retrieve the page: "+url+str(response.status_code))

def get_time(repo, url_last_succesful_build, username, password):
  response = requests.get(url_last_succesful_build, auth=HTTPBasicAuth(username, password))
  if response.status_code == 200:
    page_text = response.text
    match = re.search(r"Started\s+(.*)", page_text)
    if match:
        result = match.group(1)  # Extract everything after "Started"
        cleaned_result = re.sub(r"</?div>", "", result)  # Remove <div> and </div>
        result2 = cleaned_result.strip()
        print(result2) 
        return result2
    else:
      print("no match")

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
    "job_name_prod": "vyas/job/core/job/deploy-pri-prod"
  },
  "UI": {
    "job_name_dev": "vyas/job/ui/job/deploy-dev",
    "job_name_preprod": "vyas/job/ui/job/deploy-preprod",
    "job_name_prod": "vyas/job/ui/job/deploy-pri-prod"
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
  },
  "DDL": {
    "job_name_dev": "database/job/rds/job/tmh/job/ddl/job/deploy-dev",
    "job_name_preprod": "database/job/rds/job/tmh/job/ddl/job/deploy-preprod",
    "job_name_prod": "database/job/rds/job/tmh/job/ddl/job/deploy-prod"
  },
  "DML": {
    "job_name_dev": "database/job/rds/job/tmh/job/dml/job/deploy-dev",
    "job_name_preprod": "database/job/rds/job/tmh/job/dml/job/deploy-preprod",
    "job_name_prod": "database/job/rds/job/tmh/job/dml/job/deploy-prod"
  }
}

def main_preprod(username, password, mapping, repolist):
  commit_list = []
  mismatches = {}
  for index, repo in enumerate(repolist):
    repo_job = mapping[repo]["job_name_preprod"]
    url = f"https://ci.navyanetwork.com/job/{repo_job}/lastSuccessfulBuild/consoleText"
    jsonurl = f"https://ci.navyanetwork.com/job/{repo_job}/lastSuccessfulBuild/api/json"
    url_last_succesful_build = f"https://ci.navyanetwork.com/job/{repo_job}/lastSuccessfulBuild"

    print("Checking for: "+repo)
    branch = get_branch(repo, url, jsonurl, username, password)
    if branch is None:
      branch = "develop"
    
    preprod_current_branches[repo] = branch
    expected_branch = expected_branches_preprod.get(repo)
    if expected_branch and expected_branch != branch:
        mismatches[repo] = (expected_branch, branch)

    user = get_user(url, username, password)
    time = get_time(repo, url_last_succesful_build, username, password)
    commitid = get_commit(repo, url, username, password)
    build_number = get_build_number(repo, url, username, password)
    commit_string = f"{repo}: {branch}, Commit ID: {commitid}, build number: {build_number}, {time}"
    commit_list.append(commit_string)
    print("---------------------")
  return commit_list, mismatches


commit_list_preprod, preprod_mismatches = main_preprod(username, password, mapping, repolist)

# print(commit_list_preprod)

def main_prod(username, password, mapping, repolist):
  commit_list = []
  mismatches = {}
  for index, repo in enumerate(repolist):
    repo_job = mapping[repo]["job_name_prod"]
    url = f"https://ci.navyanetwork.com/job/{repo_job}/lastSuccessfulBuild/consoleText"
    jsonurl = f"https://ci.navyanetwork.com/job/{repo_job}/lastSuccessfulBuild/api/json"
    url_last_succesful_build = f"https://ci.navyanetwork.com/job/{repo_job}/lastSuccessfulBuild"

    print("Checking for: "+repo)
    branch = get_branch(repo, url, jsonurl, username, password)
    if branch is None:
      branch = "develop"
    
    prod_current_branches[repo] = branch
    expected_branch = expected_branches_prod.get(repo)
    if expected_branch and expected_branch != branch:
        mismatches[repo] = (expected_branch, branch)

    user = get_user(url, username, password)
    time = get_time(repo, url_last_succesful_build, username, password)
    commitid = get_commit(repo, url, username, password)
    build_number = get_build_number(repo, url, username, password)
    commit_string = f"{repo}: {branch}, Commit ID: {commitid}, build number: {build_number}, {time}"
    commit_list.append(commit_string)
    print("---------------------")
  return commit_list, mismatches


commit_list_prod, prod_mismatches = main_prod(username, password, mapping, repolist)
# print(commit_list_prod)

time_ist = pd.Timestamp.now('Asia/Kolkata')
formatted_time = time_ist.strftime("%d/%m/%Y %H:%M")

# Detect which environments have mismatches
alert_triggered = False
alert_envs = []
alert_body = ""

if preprod_mismatches:
    alert_triggered = True
    alert_envs.append("PREPROD")
    alert_body += "Branch Mismatch Detected in Preprod Environment\n\n"
    for repo, (expected, actual) in preprod_mismatches.items():
        alert_body += f"{repo}: Expected = {expected}, Found = {actual}\n"
    alert_body += "\n"

if prod_mismatches:
    alert_triggered = True
    alert_envs.append("PROD")
    alert_body += "Branch Mismatch Detected in Prod Environment\n\n"
    for repo, (expected, actual) in prod_mismatches.items():
        alert_body += f"{repo}: Expected = {expected}, Found = {actual}\n"
    alert_body += "\n"

# Build subject and content
if alert_triggered:
    env_label = " and ".join(alert_envs)
    subject = f"ALERT: Branch Mismatch for {env_label} - {formatted_time}"
    email_content = alert_body
else:
    subject = f"Daily Commit List - Preprod and Prod - {formatted_time}"
    email_content = ""

# Append commit list regardless of alert
email_content += "------------------------------\n"
email_content += "Full Commit List (Preprod and Prod)\n"
email_content += "------------------------------\n\n"

email_content += "List of preprod branches and commit IDs\n\n"
for index, value in enumerate(commit_list_preprod):
    email_content += f"{index + 1}. {value}\n"

email_content += "\n------------------------------\n"
email_content += "\nList of prod branches and commit IDs\n\n"
for index, value in enumerate(commit_list_prod):
    email_content += f"{index + 1}. {value}\n"

email_content += "\n\nBuild numbers having 'None' value indicates that the latest preprod deployment does not have any upstream project linked to it."

# Email configuration
sender_email = "riddhimann@navyatech.in"
receiver_emails = ["riddhimann@navyatech.in", "pushpa@navyatech.in", "kirana@navyatech.in", "armugam@navyatech.in"]
email_password = os.getenv('APP_PASSWORD')

# Create and send email
message = MIMEMultipart()
message["From"] = sender_email
message["To"] = ", ".join(receiver_emails)
message["Subject"] = subject
message.attach(MIMEText(email_content, "plain"))

try:
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender_email, email_password)
    server.sendmail(sender_email, receiver_emails, message.as_string())
    server.quit()
    print("Email sent successfully.")
except Exception as e:
    print(f"[ERROR] Failed to send email: {e}")

import os
import re
import time
import requests
import pandas as pd
import smtplib
from bs4 import BeautifulSoup
from requests.auth import HTTPBasicAuth
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

username = "riddhimann"  # Jenkins username
password = os.getenv("JENKINS_PASSWORD")
repolist = [
    "user_management-fargate", "cancerbaba-fargate", "nes", "refresh_articles", "core", "UI",
    "patient_reports", "www", "ui_user_management", "napi", "process", "experts-fargate",
    "sendmail", "analyst", "DDL", "DML", "utilities_cancerbaba", "NES_DDL"
]

# -------------------------------------------------------------------------
# 🟡 NEW FUNCTION: Wait until Jenkins finishes active builds
# -------------------------------------------------------------------------
def wait_for_active_builds(username, password, max_retries=3, interval=30):
    """
    Checks Jenkins UI for active builds and waits until all builds complete.
    Looks for 'app-progress-bar' element which indicates an active deployment.
    """
    jenkins_url = "https://ci.navyanetwork.com/"
    retry_count = 0

    print("🔍 Checking for active Jenkins deployments...")

    while retry_count < max_retries:
        try:
            response = requests.get(jenkins_url, auth=HTTPBasicAuth(username, password))
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                active_build = soup.find("div", class_="app-progress-bar")

                if active_build:
                    retry_count += 1
                    print(f"⚠️  Active deployment detected (Attempt {retry_count}/{max_retries}). Waiting {interval} seconds...")
                    time.sleep(interval)
                    continue
                else:
                    print("✅ No active deployments found. Proceeding with script...\n")
                    return True
            else:
                print(f"[ERROR] Failed to access Jenkins UI. Status Code: {response.status_code}")
                return False
        except Exception as e:
            print(f"[ERROR] Exception while checking for active builds: {e}")
            return False

    print("🕓 Waited for all retries but deployment is still ongoing. Proceeding anyway.\n")
    return True


# -------------------------------------------------------------------------
# 🔧 Helper Functions
# -------------------------------------------------------------------------
def get_branch(repo, url, jsonurl, username, password, branch_name=None):
    response = requests.get(jsonurl, auth=HTTPBasicAuth(username, password))
    if response.status_code == 200:
        build_info = response.json()
        actions = build_info.get("actions", [])
        for action in actions:
            if "parameters" in action:
                for parameter in action["parameters"]:
                    if parameter["name"] == "GIT_BRANCH_NAME":
                        branch_name = parameter["value"]
                        break

        if branch_name:
            print(f"Branch Name: {branch_name}")
            return branch_name

        response2 = requests.get(url, auth=HTTPBasicAuth(username, password))
        page_text = response2.text
        branch_pattern = r"Cloning branch - (\w+)"
        match = re.search(branch_pattern, page_text)
        if match:
            branch_name = match.group(1)
            print(branch_name)
            return branch_name
        else:
            print("Branch name not found.")
            return None
    else:
        print("Failed to retrieve the page:", url, response.status_code)


def get_user(url, username, password):
    response = requests.get(url, auth=HTTPBasicAuth(username, password))
    if response.status_code == 200:
        page_text = response.text
        match_user = re.search(r"Started by user (\w+)", page_text)
        if match_user:
            um_user = match_user.group(1)
            print("Deployed by", um_user)
            return um_user
        else:
            print("User not found in:", url)
    else:
        print("Failed to retrieve user:", url, response.status_code)


def get_time(repo, url_last_succesful_build, username, password):
    response = requests.get(url_last_succesful_build, auth=HTTPBasicAuth(username, password))
    if response.status_code == 200:
        page_text = response.text
        match = re.search(r"Started\s+(.*)", page_text)
        if match:
            result = match.group(1)
            cleaned_result = re.sub(r"</?div>", "", result)
            result2 = cleaned_result.strip()
            print(result2)
            return result2
        else:
            print("No time match found for", repo)


def get_commit(repo, url, username, password):
    try:
        response = requests.get(url, auth=HTTPBasicAuth(username, password))
        if response.status_code != 200:
            print(f"Failed to retrieve page. Status Code: {response.status_code}")
            return None

        page_text = response.text
        commit_patterns = [
            r"COMMIT_ID_IN_TAG = (\w+)",
            r"Commit id - (\w+)",
            r"last commit for alpha apps:(\w+)",
            r"last commit:(\w+)",
            r"ANALYST_APP_COMMIT_ID = (\w+)",
        ]

        for pattern in commit_patterns:
            match_commit = re.search(pattern, page_text)
            if match_commit:
                commit_id = match_commit.group(1)
                print(f"{repo} commit id: {commit_id}")
                return commit_id

        print("Commit ID not found for", repo)
        return None

    except Exception as e:
        print(f"Error in get_commit for {repo}: {e}")
        return None


def get_build_number(repo, url, repo_job, username, password):
    response = requests.get(url, auth=HTTPBasicAuth(username, password))
    if response.status_code == 200:
        page_text = response.text

        # First try: old pattern (console text style)
        match = re.search(r'Started by upstream project ".*?/deploy-dev" build number (\d+)', page_text)
        if match:
            build_number = match.group(1)
            print(f"{repo} build number: {build_number}")
            return build_number

        # Fallback: check HTML source for "deploy-dev #4711" pattern
        url = f"https://ci.navyanetwork.com/job/{repo_job}/lastSuccessfulBuild"
        response = requests.get(url, auth=HTTPBasicAuth(username, password))
        if response.status_code == 200:
            page_text = response.text
        match = re.search(r'deploy-dev.*?\s+#(\d+)', page_text)
        if match:
            build_number = match.group(1)
            print(f"{repo} build number (from page source): {build_number}")
            return build_number

        print(f"No build number found for {repo}")
    else:
        print(f"Failed to fetch {repo}: {response.status_code}")


# -------------------------------------------------------------------------
# 🔁 Jenkins Job Mapping
# -------------------------------------------------------------------------
mapping = {
    "cancerbaba-fargate": {"job_name_dev": "cancerbaba/job/2.0/job/deploy-dev-fargate"},
    "experts-fargate": {"job_name_dev": "experts/job/docker/job/deploy-dev-fargate"},
    "core": {"job_name_dev": "vyas/job/core/job/deploy-dev"},
    "UI": {"job_name_dev": "vyas/job/ui/job/deploy-dev"},
    "user_management-fargate": {"job_name_dev": "user-management/job/deploy-dev-fargate"},
    "patient_reports": {"job_name_dev": "vyas/job/patient-reports/job/deploy-dev"},
    "refresh_articles": {"job_name_dev": "vyas/job/refresh-articles/job/deploy-dev"},
    "process": {"job_name_dev": "process/job/docker/job/deploy-dev"},
    "nes": {"job_name_dev": "nes/job/deploy-dev"},
    "www": {"job_name_dev": "www/job/3.0/job/deploy-dev"},
    "napi": {"job_name_dev": "navyaapi/job/4.0/job/deploy-dev"},
    "ui_user_management": {"job_name_dev": "vyas/job/ui-user-management/job/deploy-dev"},
    "sendmail": {"job_name_dev": "utilities/job/sendemail/job/deploy-dev"},
    "analyst": {"job_name_dev": "vyas/job/analyst/job/deploy-dev"},
    "DDL": {"job_name_dev": "database/job/rds/job/tmh/job/ddl/job/deploy-dev"},
    "DML": {"job_name_dev": "database/job/rds/job/tmh/job/dml/job/deploy-dev"},
    "utilities_cancerbaba": {"job_name_dev": "utilities/job/cancerbaba/job/deploy-dev"},
    "NES_DDL": {"job_name_dev": "database/job/rds/job/nes/job/ddl/job/deploy-dev"},
}


# -------------------------------------------------------------------------
# 🚀 Main Function
# -------------------------------------------------------------------------
def main_dev(username, password, mapping, repolist):
    commit_list = []
    for repo in repolist:
        repo_job = mapping[repo]["job_name_dev"]
        url = f"https://ci.navyanetwork.com/job/{repo_job}/lastSuccessfulBuild/consoleText"
        jsonurl = f"https://ci.navyanetwork.com/job/{repo_job}/lastSuccessfulBuild/api/json"
        url_last_succesful_build = f"https://ci.navyanetwork.com/job/{repo_job}/lastSuccessfulBuild"

        print(f"\n🔹 Checking for: {repo}")
        branch = get_branch(repo, url, jsonurl, username, password) or "develop"
        user = get_user(url, username, password)
        time_ = get_time(repo, url_last_succesful_build, username, password)
        commitid = get_commit(repo, url, username, password)
        build_number = get_build_number(repo, url, repo_job, username, password)

        commit_string = f"{repo}: {branch}, Commit ID: {commitid}, Build number: {build_number}, {time_}"
        commit_list.append(commit_string)
        print("---------------------")
    return commit_list


# -------------------------------------------------------------------------
# ✉️ Email Sending
# -------------------------------------------------------------------------
def send_email(commit_list_dev):
    time_ist = pd.Timestamp.now("Asia/Kolkata")
    formatted_time = time_ist.strftime("%d/%m/%Y %H:%M")

    email_content = f"List of dev branches and commit IDs, generated on {formatted_time}.\n\n"
    for index, value in enumerate(commit_list_dev):
        email_content += f"{index + 1}. {value}\n"

    print(email_content)

    subject = f"Commit List - Dev - {formatted_time}"
    sender_email = "riddhimann@navyatech.in"
    receiver_emails = [
        "riddhimann@navyatech.in",
        "armugam@navyatech.in",
        "pushpa@navyatech.in",
        "kirana@navyatech.in",
    ]
    # receiver_emails = ["riddhimann@navyatech.in"]
    email_password = os.getenv("APP_PASSWORD")

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
        print("✅ Email sent successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")


# -------------------------------------------------------------------------
# 🏁 Main Entry Point
# -------------------------------------------------------------------------
if __name__ == "__main__":
    if wait_for_active_builds(username, password):
        commit_list_dev = main_dev(username, password, mapping, repolist)
        send_email(commit_list_dev)
    else:
        print("[ERROR] Skipping commit check due to failed Jenkins access.")

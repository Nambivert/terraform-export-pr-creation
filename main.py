import os
import json
from flask import Flask
from flask import request
from flask import jsonify
import functions_framework
from slack.signature import SignatureVerifier
import requests
from jinja2 import Environment, FileSystemLoader
import subprocess
import pandas as pd
import glob
from pandas.errors import EmptyDataError
import csv
from sys import stdout
import argparse
from subprocess import run, PIPE
from datetime import datetime
import sys

app = Flask(__name__)

# [END functions_verify_webhook]
token = os.environ['GH_TOKEN']

def policy_exporter():
  resource_name = "google_compute_security_policy"
  resource_instance = "ip_ban"
  inside_block = False
  cfinstall = subprocess.check_output(
      [f'yes | gcloud config set project devops-test'], shell=True, encoding='utf-8')
  print(cfinstall)
  output = subprocess.check_output(
      [f'yes | gcloud services enable cloudasset.googleapis.com'], shell=True, encoding='utf-8')
  print(output)
  secexport = subprocess.check_output(
      [f'gcloud beta resource-config bulk-export  --resource-types=ComputeSecurityPolicy --project=devops-test --resource-format=terraform'], shell=True, encoding='utf-8')
  #print(secexport)
  filename = "sec-prod.txt"
  file = open(filename, "w")
  file.write(secexport)
  file.close()
  output_file = "ip-ban.tf"
  with open("sec-prod.txt", "r") as file, open(output_file, "w") as output:
    for line in file:
      if f'resource "{resource_name}" "{resource_instance}"' in line:
        inside_block = True
        brace_count = 1
        output.write(line)
      # print(line, end="")
      elif inside_block:
        # print(line, end="")
        output.write(line)
        brace_count += line.count("{") - line.count("}")
        if brace_count == 0:
          inside_block = False
    final_text = subprocess.check_output(
        [f'head -n -1 sec-prod.txt > ip-ban.txt'], shell=True, encoding='utf-8')
    #print(final_text)  
    with open('ip-ban.tf', 'r') as f:
          contents = f.read()
     #     print("The extracted IP-Ban Terraform file is: \n", contents)

def pr_creator(token):
    gh_login = subprocess.check_output(
        [f'echo {token} | gh auth login --with-token'], shell=True, encoding='utf-8')
    print(gh_login)
    gh_clone = subprocess.check_output(
        [f'gh repo clone nambivert/terraform && pwd'], shell=True, encoding='utf-8')
    print(gh_clone)
    date_format = "%Y-%m-%d"
    current_date = datetime.now().strftime(date_format)
    branch = f"sec-updater-{current_date}"
    gh_checkout = subprocess.check_output(
        [f'cd terraform && git checkout -b {branch}'], shell=True, encoding='utf-8')
    print(gh_checkout)
    copy_files = subprocess.check_output(
        [f'cp ip-ban.tf terraform/gcp/devops-test/gcp-prod-network/cloud-armor/ip-ban.tf'], shell=True, encoding='utf-8')
    print(copy_files)
    set_origin = subprocess.check_output(
            [f'cd terraform && git remote set-url origin  https://nsrinivasan:{token}@github.com/nambivert/terraform.git'], shell=True, encoding='utf-8')
    print(set_origin)
    create_branch = subprocess.check_output(
     [f"cd terraform && git config --global user.email 'nsrinivasan@nambivert.com' && git config --global user.name 'nsrinivasan' && git add . && git status && git commit -m '{branch}: IP Ban policy latest' && git push --set-upstream origin {branch}"], shell=True, encoding='utf-8')
    print(create_branch)
    pr_title = f"{branch}: Scheduled Task to update IP Ban Cloud Armor Policy"
    pr_body = "This is an automated PR indented to sync changes in Cloud Armor policy of IP Ban which was added manually"
    raise_pr  = subprocess.check_output(
      [f"cd terraform && gh pr create --base main --head {branch} --title '{pr_title}' --body '{pr_body}'"], shell=True, encoding='utf-8')
    print(raise_pr)

@app.route("/")
def home():
  return "It Works!"

@app.route("/policyupdater", methods=["POST"])
def secpolicy_updater():
  # Your code here
  if request.method != 'POST':
        return 'Only POST requests are accepted', 405

  policy_exporter()
  pr_creator(token)

  # Return an HTTP response
  return jsonify(res)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
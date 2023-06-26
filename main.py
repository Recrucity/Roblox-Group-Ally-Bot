import requests
import json
import random
import time
import os
from colorama import Fore, init
init()

# Some functions for printing pretty messages
def info(msg): print(f"{Fore.LIGHTBLUE_EX}INFO{Fore.RESET} {msg}")
def success(msg): print(f"{Fore.LIGHTGREEN_EX}SUCCESS{Fore.RESET} {msg}")
def error(msg): print(f"{Fore.RED}ERROR{Fore.RESET} {msg}")


# Load the config, get cookie, group id, webhook etc
with open("config.json") as f:
    config = json.load(f)
    cookie = config["auth"]["cookie"]
    yourId = config["ally"]["yourGroupId"]
    webhook = config["ally"]["webhook"]

# Load the proxies into a list
with open("proxies.txt") as f:
    proxies = f.readlines()

# Make a requests session with the cookie and define some variables
s = requests.Session()
s.cookies[".ROBLOSECURITY"] = cookie
xcsrfToken = ""
sentGroups = []
scrapedGroups = []


with open("sent.txt") as f:
    for sent in f.readlines():
        sentGroups.append(sent.strip("\n"))


# Scraping groups. Gets the allies from a group and put it in a list.
def scrapegroups(id):
    nextRow = 1
    info("Scraping groups...")

    while True:
        proxyChoice = {"https": "http://" + random.choice(proxies).strip("\n")}
        allyRequest = requests.get(f"https://groups.roblox.com/v1/groups/{id}/relationships/allies?maxRows=10000&sortOrder=Asc&startRowIndex={nextRow}", proxies=proxyChoice)
        if allyRequest.status_code == 200:
            data = allyRequest.json()
            if data["relatedGroups"]:
                for ally in data["relatedGroups"]:
                    if ally["id"] not in sentGroups:
                        scrapedGroups.append(ally["id"])

                if data["nextRowIndex"] and data["nextRowIndex"] > 901:
                    nextRow = data["nextRowIndex"]
                else:
                    break
            else:
                break
        break

    success("Scraped Groups!")


def getxcsrf():
    return s.post("https://auth.roblox.com/v2/logout").headers["X-CSRF-TOKEN"]


xcsrfToken = getxcsrf()


# Send an ally request.
def sendrequest(id):
    global xcsrfToken
    sendheaders = {
        "X-CSRF-TOKEN": xcsrfToken
    }

    proxychoice = {"https": "http://" + random.choice(proxies).strip("\n")}
    r = s.post(f"https://groups.roblox.com/v1/groups/{yourId}/relationships/allies/{id}", headers=sendheaders, proxies=proxychoice)

    if r.status_code == 200:
        success(f"Successfully sent ally request to {id}")

        with open("sent.txt", "a") as f:
            f.write(f"{id}\n")
        f.close()

        groupRequest = requests.get(f"https://groups.roblox.com/v1/groups/{id}")
        if groupRequest.status_code == 200:

            # Gets some info about the group such as name, members, thumbnail and post it on discord
            groupInfo = groupRequest.json()

            groupThumbnail = requests.get(f"https://thumbnails.roblox.com/v1/groups/icons?groupIds={id}&size=420x420&format=Png&isCircular=false").json()["data"][0]["imageUrl"]

            webhookData = {
                "content": None,
                "embeds": [
                    {
                        "title": "Ally Request Sent",
                        "url": f"https://roblox.com/groups/{id}",
                        "description": f"Name: {groupInfo['name']}\nMembers: {groupInfo['memberCount']}",
                        "color": 5814783,
                        "thumbnail": {
                            "url": groupThumbnail
                        },
                        "footer": {
                            "text": "Made by Recrucity#3575"
                        }
                    }
                ],
                "attachments": []
            }

            requests.post(webhook, json=webhookData)

    elif r.status_code == 403:
        error("Unauthorized error. Getting new x-csrf-token")
        xcsrfToken = getxcsrf()
    elif r.status_code == 429:
        error("Rate Limited. Waiting 1 minute.")
        time.sleep(60)
    elif r.status_code == 400:
        error("Bad Request. Most likely due to this group already having an ally request sent.")
    else:
        error(f"Unknown error. ({r.status_code})")


firstGroup = input("Please input a group ID for the scraping starting point.\nThe more allies the better: ")
scrapegroups(firstGroup)

# Main loop. Loops through all the groups in the scrapedGroups list.
# When it's run out of groups it will pick a random group it has sent to and scrape new groups from that.
while True:
    try:
        for group in scrapedGroups:
            if group not in sentGroups:
                sendrequest(group)
                scrapedGroups.remove(group)
                sentGroups.append(group)

        randomSentGroup = random.choice(sentGroups)
        sentGroups.remove(randomSentGroup)
        scrapegroups(randomSentGroup)
    except Exception as e:
        print(f"Error {e}")

#!/usr/bin/env python3
import re
import dotenv
import requests
from datetime import datetime

config = dotenv.dotenv_values(".twilio_env")
API_BASE = "https://api.twilio.com"
MSG_URL = f"{API_BASE}/2010-04-01/Accounts/{config['TWILIO_ACCOUNT_SID']}/Messages.json"
auth = (config["TWILIO_API_KEY"], config["TWILIO_API_SECRET"])


# GET all msgs
def all_messages(all_pages=False):
    """Get all Twilio messages ever"""
    msgs = []
    # init with default url.
    all_msgs_json = {"next_page_uri": MSG_URL}
    while msg_url := all_msgs_json["next_page_uri"]:
        all_msgs = requests.get(
            msg_url, params={"PageSize": 1000}, auth=auth, timeout=30
        )
        if all_msgs.status_code != 200:
            # all_msgs.raise_for_status()
            raise Exception(
                f"Could not get all messages. {msg_url} failed with {all_msgs.status_code}"
            )
        # TODO: accumlate more. while all_pages
        all_msgs_json = all_msgs.json()
        msgs.extend(all_msgs_json.get("messages", []))
        if not all_pages:
            break

    return msgs


def send_msg(to, msg="sms_appointment_reminders"):
    """Send a message using Twilio's API"""
    sent = requests.post(
        MSG_URL,
        auth=auth,
        data={"To": to, "From": config["TWILIO_FROM"], "Body": msg},
        timeout=30,
    )
    return sent


# x_sent.text '"Invalid template name. Trial accounts can only use predefined...'
# x_sent = send_msg('+13152479200', 'hi from python')
# x_sent = send_msg('+13152479200', 'sms_appointment_reminders')
# alt: 'sms_internal_alerts' 'sms_marketing_promotions'

def number_harmonize(phone):
    """
    US centric parsing. must have 10 digits. drops anyting before that.
    >>> number_harmonize("123) 456- 7890")
    +11234567890
    """
    if m := re.search(r'\d{10}$', re.sub('[^0-9]', '', phone)):
        return "+1" + m.group()
    else:
        return None


def habit_json_extract(redcap_json):
    """Redcap json response to list of dicts"""
    contacts = {}
    numbers = {}
    for j in redcap_json:
        ins = []
        lunaid = j["redcap_id"]
        # recruit (one) and contact update (behave 1 to 3)j
        # in reverse importance. last one is final for 'numberes'
        if phone := number_harmonize(j.get("contact_alt_phone")):
            source = "habit_alt_" + j["redcap_event_name"]
            ins.append(
                {
                    "phone": phone,
                    "source": source,
                    "contact": j["contact_alt_name"],
                }
            )
            numbers[phone] = {'lunaid': lunaid, 'name': j["contact_alt_name"], "source": source}

        if phone := number_harmonize(j.get("recruit_phone")):
            source = "habit_" + j["redcap_event_name"]
            ins.append(
                {
                    "phone": phone,
                    "source": source,
                    "contact": j["recruit_contact_who"],
                }
            )
            numbers[phone] = {'lunaid': lunaid, 'name': j["contact_alt_name"], "source": source}

        if phone := number_harmonize(j.get("contact_phonenumber")):
            source ="habit_" + j["redcap_event_name"];
            ins.append(
                {
                    "phone": phone,
                    "source": source,
                    "contact": j["contact_fullname"],
                }
            )
            numbers[phone] = {'lunaid': lunaid, "source": source, 'name': j["contact_alt_name"]}

        if not ins:
            continue

        if lunaid in contacts:
            contacts[lunaid].extend(ins)
        else:
            contacts[lunaid] = ins

    return (contacts, numbers)


def redcap_contact_db_habit():
    req = {
        "token": config["RC_API_HABIT"],
        "content": "record",
        "action": "export",
        "format": "json",
        "type": "flat",
        "csvDelimiter": "",
        "forms[0]": "prerecruit",
        "forms[1]": "contact_information_address_update",
        "rawOrLabel": "raw",
        "rawOrLabelHeaders": "raw",
        "exportCheckboxLabel": "false",
        "exportSurveyFields": "false",
        "exportDataAccessGroups": "false",
        "returnFormat": "json",
    }

    redcap = requests.post(config["RC_URL"], data=req)
    redcap_json = redcap.json()
    return redcap_json


def redcap_twilio():
    redcap_json = redcap_contact_db_habit()
    (contacts, numbers) = habit_json_extract(redcap_json)

    twilio_log = all_messages(True)
    log = []
    per_id = {}
    for t in twilio_log:
        subset = {k: t.get(k)
                  for k in ['date_sent', 'to', 'from', 'body', 'direction']}

        # sortable date
        subset['epoch'] = datetime.strptime(t['date_sent'], '%a, %d %b %Y %H:%M:%S %z').timestamp()

        # lookup lunaid from number
        subj_num = t['from'] if t['direction'] == 'inbound' else t['to']
        subset['subj_num'] = subj_num
        subset.update(numbers.get(subj_num))

        log.append(subset)

        if lunaid := subset.get('lunaid'):
            if lunaid in per_id:
                per_id[lunaid].append(subset)
            else:
                per_id[lunaid] = [subset]

    import jinja2
    templateLoader = jinja2.FileSystemLoader(searchpath="./")
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template("template.html")
    outputText = template.render(per_id=per_id, numbers=numbers)
    print(outputText)

# contacts['1']
# [{'phone': '+14125305175', 'source': 'habit_alt_behavioral_arm_1', 'contact': "Will's Guardian"}, {'phone': '+13152479200', 'source': 'habit_behavioral_arm_1', 'contact': 'Will, W, Foran'}]
# >>> numbers['+14125305175']
# {'lunaid': '1', 'name': "Will's Guardian"}

if __name__ == "__main__":
    print("Content-type: text/html\n\n")
    redcap_twilio()

import base64
import os.path
import sys
from datetime import datetime, timezone
import bs4

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from model import EmailStructure

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
MAX_EMAILS = 20


def get_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def list_message_ids(service, query, limit):
    # list() returns one page of IDs at a time; keep following nextPageToken
    ids = []
    page_token = None
    while len(ids) < limit:
        results = service.users().messages().list(
            userId="me", q=query, pageToken=page_token, maxResults=min(limit - len(ids), 500)
        ).execute()
        ids += [message["id"] for message in results.get("messages", [])]
        page_token = results.get("nextPageToken")
        if not page_token:
            break
    return ids


def find_part(payload, mime_type):
    # Parts can be nested (multipart/mixed -> multipart/alternative -> text/plain),
    # so search depth-first. Containers and attachments have no body data.
    if payload["mimeType"] == mime_type and "data" in payload.get("body", {}):
        return payload["body"]["data"]
    for part in payload.get("parts", []):
        data = find_part(part, mime_type)
        if data:
            return data
    return None

def get_text_from_html(htmldata):
    soup = bs4.BeautifulSoup(htmldata, "html.parser")
    nrtags = soup.find_all(["style","script","head"])

    for tag in nrtags:
        tag.decompose()

    return soup.get_text(separator="\n", strip=True)


def find_body(payload):
    data = find_part(payload, "text/plain") or find_part(payload, "text/html")
    if data is None:
        return ""
    return get_text_from_html(base64.urlsafe_b64decode(data).decode("utf-8", errors="replace"))


def fetch_email(service, message_id):
    email = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    payload = email["payload"]
    headers = {header["name"]: header["value"] for header in payload["headers"]}
    return EmailStructure(
        message_id=message_id,
        sender=headers.get("From", ""),
        subject=headers.get("Subject", ""),
        # internalDate is Gmail's receive time in ms since epoch; the Date header is sender-controlled
        date=datetime.fromtimestamp(int(email["internalDate"]) / 1000, tz=timezone.utc),
        body=find_body(payload),
    )


def email_list():
    unix_timestamp = int(datetime.strptime(input("Enter date for starting point: "), "%d/%m/%Y").timestamp())
    service = get_service()
    emails = []

    try:
        message_ids = list_message_ids(service, "after:{}, category:primary or category:updates".format(unix_timestamp), MAX_EMAILS)
    except HttpError as error:
        print(f"Could not list messages: {error}", file=sys.stderr)
        return

    for message_id in message_ids:
        try:
            email = fetch_email(service, message_id)
            emails.append(email)
        except HttpError as error:
            print(f"Gmail API error for message {message_id}: {error}", file=sys.stderr)
            continue
        except (KeyError, ValueError) as error:
            print(f"Could not parse message {message_id}: {error!r}", file=sys.stderr)
            continue

    return emails
if __name__ == "__main__":
    emails = email_list()
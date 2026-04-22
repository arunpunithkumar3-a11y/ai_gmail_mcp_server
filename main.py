from fastmcp import FastMCP
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from auth import get_gmail_service
import os


mcp = FastMCP(name="gmail_tool")



def extract_body(payload):
    """Recursively extract plain text body from email payload."""
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body'].get('data', '')
                return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            elif 'parts' in part:
                return extract_body(part)
    else:
        data = payload.get('body', {}).get('data', '')
        if data:
            return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
    return ''


def get_or_create_label(service, label_name: str):
    labels = service.users().labels().list(userId="me").execute().get("labels", [])

    for label in labels:
        if label["name"].lower() == label_name.lower():
            return label["id"]

    new_label = service.users().labels().create(
        userId="me",
        body={"name": label_name}
    ).execute()

    return new_label["id"]




@mcp.tool
def read_emails(user_data: dict, max_results=10, query=''):
    service = get_gmail_service(user_data)

    results = service.users().messages().list(
        userId='me',
        maxResults=max_results,
        q=query
    ).execute()

    messages = results.get('messages', [])
    emails = []

    for msg in messages:
        email_data = service.users().messages().get(
            userId='me',
            id=msg['id'],
            format='full'
        ).execute()

        headers = email_data['payload']['headers']

        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender  = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
        date    = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')

        body = extract_body(email_data['payload'])

        emails.append({
            'id': msg['id'],
            'subject': subject,
            'from': sender,
            'date': date,
            'body': body,
            'snippet': email_data.get('snippet', ''),
        })

    return emails


@mcp.tool
def send_email(user_data: dict, to, subject, body, cc=None, bcc=None, attachment_path=None):
    service = get_gmail_service(user_data)

    msg = MIMEMultipart()
    msg['To'] = to
    msg['Subject'] = subject

    if cc:
        msg['Cc'] = cc
    if bcc:
        msg['Bcc'] = bcc

    msg.attach(MIMEText(body, 'plain'))

    if attachment_path:
        with open(attachment_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())

        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{attachment_path}"')
        msg.attach(part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    result = service.users().messages().send(
        userId='me',
        body={'raw': raw}
    ).execute()

    return result




@mcp.tool
def reply_to_email(user_data: dict, message_id, reply_body):
    service = get_gmail_service(user_data)

    original = service.users().messages().get(
        userId='me',
        id=message_id,
        format='full'
    ).execute()

    headers = original['payload']['headers']

    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
    reply_to = next((h['value'] for h in headers if h['name'] == 'From'), '')
    thread_id = original['threadId']
    msg_id_header = next((h['value'] for h in headers if h['name'] == 'Message-ID'), '')

    reply = MIMEText(reply_body, 'plain')
    reply['To'] = reply_to
    reply['Subject'] = f"Re: {subject}" if not subject.startswith('Re:') else subject
    reply['In-Reply-To'] = msg_id_header
    reply['References'] = msg_id_header

    raw = base64.urlsafe_b64encode(reply.as_bytes()).decode()

    result = service.users().messages().send(
        userId='me',
        body={'raw': raw, 'threadId': thread_id}
    ).execute()

    return result


@mcp.tool
def mark_as_read(user_data: dict, message_id):
    service = get_gmail_service(user_data)

    service.users().messages().modify(
        userId='me',
        id=message_id,
        body={'removeLabelIds': ['UNREAD']}
    ).execute()

    return {"message": "Marked as read"}


@mcp.tool
def mark_as_unread(user_data: dict, message_id):
    service = get_gmail_service(user_data)

    service.users().messages().modify(
        userId='me',
        id=message_id,
        body={'addLabelIds': ['UNREAD']}
    ).execute()

    return {"message": "Marked as unread"}


@mcp.tool
def archive_email(user_data: dict, message_id):
    service = get_gmail_service(user_data)

    service.users().messages().modify(
        userId='me',
        id=message_id,
        body={'removeLabelIds': ['INBOX']}
    ).execute()

    return {"message": "Archived email"}


@mcp.tool
def trash_email(user_data: dict, message_id):
    service = get_gmail_service(user_data)

    service.users().messages().trash(
        userId='me',
        id=message_id
    ).execute()

    return {"message": "Email moved to trash"}




@mcp.tool
def add_label(user_data: dict, message_id: str, label_name: str):
    service = get_gmail_service(user_data)

    label_id = get_or_create_label(service, label_name)

    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"addLabelIds": [label_id]}
    ).execute()

    return {"message": f"Label '{label_name}' added"}


@mcp.tool
def remove_label(user_data: dict, message_id: str, label_name: str):
    service = get_gmail_service(user_data)

    label_id = get_or_create_label(service, label_name)

    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"removeLabelIds": [label_id]}
    ).execute()

    return {"message": f"Label '{label_name}' removed"}


@mcp.tool
def list_labels(user_data: dict):
    service = get_gmail_service(user_data)

    resp = service.users().labels().list(userId="me").execute()
    labels = resp.get("labels", [])

    return {
        "labels": [l["name"] for l in labels]
    }



@mcp.tool
def create_draft(user_data: dict, to: str, subject: str, body: str, cc: str = "", bcc: str = ""):
    service = get_gmail_service(user_data)

    msg = MIMEMultipart()
    msg["To"] = to
    msg["Subject"] = subject

    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc

    msg.attach(MIMEText(body, "plain"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    draft = service.users().drafts().create(
        userId="me",
        body={"message": {"raw": raw}}
    ).execute()

    return {
        "message": "Draft created",
        "draft_id": draft["id"]
    }


@mcp.tool
def get_email_stats(user_data: dict):
    service = get_gmail_service(user_data)

    profile = service.users().getProfile(userId="me").execute()

    counts = {}
    for label in ["INBOX", "UNREAD", "SENT", "DRAFT", "SPAM", "STARRED"]:
        try:
            resp = service.users().messages().list(
                userId="me",
                labelIds=[label],
                maxResults=1
            ).execute()

            counts[label] = resp.get("resultSizeEstimate", 0)
        except:
            counts[label] = 0

    return {
        "email": profile.get("emailAddress"),
        "total_messages": profile.get("messagesTotal"),
        "total_threads": profile.get("threadsTotal"),
        "counts": counts
    }



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="http", host="0.0.0.0", port=port)

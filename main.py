from fastmcp import FastMCP
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from  auth import get_gmail_service
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


@mcp.tool
def read_emails(user_data: dict, max_results=10, query=''):
    """
    query examples:
      'is:unread'           → unread emails
      'from:someone@x.com'  → from specific sender
      'subject:invoice'     → by subject
      'is:unread label:inbox' → unread inbox
    """
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
            'id':      msg['id'],
            'subject': subject,
            'from':    sender,
            'date':    date,
            'body':    body,
            'snippet': email_data.get('snippet', ''),
        })

    return emails


@mcp.tool
def send_email(user_data: dict, to, subject, body, cc=None, bcc=None, attachment_path=None):
    service = get_gmail_service(user_data)

    msg = MIMEMultipart()
    msg['To']      = to
    msg['Subject'] = subject
    if cc:  msg['Cc']  = cc
    if bcc: msg['Bcc'] = bcc

    msg.attach(MIMEText(body, 'plain'))


    if attachment_path:
        with open(attachment_path, 'rb') as f:
            part = MIMEBase('application', 'octet-dicteam')
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{attachment_path}"')
        msg.attach(part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(
        userId='me',
        body={'raw': raw}
    ).execute()

    print(f"Email sent! Message ID: {result['id']}")
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
    subject  = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
    reply_to = next((h['value'] for h in headers if h['name'] == 'From'), '')
    thread_id = original['threadId']
    msg_id_header = next((h['value'] for h in headers if h['name'] == 'Message-ID'), '')


    reply = MIMEText(reply_body, 'plain')
    reply['To']         = reply_to
    reply['Subject']    = f"Re: {subject}" if not subject.startswith('Re:') else subject
    reply['In-Reply-To'] = msg_id_header
    reply['References']  = msg_id_header

    raw = base64.urlsafe_b64encode(reply.as_bytes()).decode()
    result = service.users().messages().send(
        userId='me',
        body={'raw': raw, 'threadId': thread_id}
    ).execute()

    print(f"Reply sent! Message ID: {result['id']}")
    return result    

@mcp.tool
def mark_as_read(user_data: dict, message_id):
    service = get_gmail_service(user_data)
    service.users().messages().modify(
        userId='me', id=message_id,
        body={'removeLabelIds': ['UNREAD']}
    ).execute()
    print(f"Marked as read: {message_id}")

@mcp.tool
def archive_email(user_data: dict, message_id):
    service = get_gmail_service(user_data)
    service.users().messages().modify(
        userId='me', id=message_id,
        body={'removeLabelIds': ['INBOX']}
    ).execute()
    print(f"Archived: {message_id}")

@mcp.tool
def trash_email(user_data: dict, message_id):
    service = get_gmail_service(user_data)
    service.users().messages().trash(userId='me', id=message_id).execute()
    print(f"Trashed: {message_id}")



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="http", host="0.0.0.0", port=port)
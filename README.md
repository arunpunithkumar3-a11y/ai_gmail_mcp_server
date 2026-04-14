Gmail MCP Server

This project is a FastMCP-based server that exposes Gmail functionalities as MCP tools. It allows AI agents or MCP clients to interact with a user's Gmail account to read, send, reply, and manage emails.

What This Project Does

The server provides the following tools:

read_emails → Fetch emails (supports filters like unread, sender, subject)
send_email → Send emails with optional CC, BCC, attachments
reply_to_email → Reply to an existing email thread
mark_as_read → Mark an email as read
archive_email → Archive an email
trash_email → Delete an email
How to Run on Your Machine
1. Install dependencies
pip install -r requirements.txt
2. Setup Gmail Authentication
Create a Google Cloud project
Enable Gmail API
Create OAuth credentials
Add your authentication logic in auth.py
Make sure get_gmail_service(user_id) returns a valid Gmail service
3. Run the server
python main.py

Server will start at:

http://localhost:8000

MCP endpoint:

http://localhost:8000/sse
How to Use (MCP Client)

Use an MCP client to connect and call tools:

from mcp import ClientSession
from mcp.client.sse import SSEClientTransport
import asyncio

async def main():
    transport = SSEClientTransport(
        url="http://localhost:8000/sse"
    )

    async with ClientSession(transport) as session:
        await session.initialize()

        result = await session.call_tool(
            name="read_emails",
            arguments={
                "user_id": "user_1",
                "max_results": 5,
                "query": "is:unread"
            }
        )

        print(result)

asyncio.run(main())

"""A2A Client — calls the remote Reviewer agent via the A2A protocol.

Prerequisites:  Start the server first — python -m a2a_demo.server
Run:            python -m a2a_demo.client
"""

from __future__ import annotations

import asyncio
import sys

from agent_framework.a2a import A2AAgent

SERVER_URL = "http://localhost:9000"

SAMPLE_DRAFT = """\
# Getting Started with Azure Functions

Azure Functions is a servless compute service that lets you run code without managing servers.

## Key Features
- Event-driven execution
- Multiple language support (Python, C#, JavaScript, Java)  
- Pay only for compute time consumed
- Integrates with Azure services and third-party tools

## Quick Start
To create your first function:
```python
import azure.functions as func

app = func.FunctionApp()

@app.route(route="hello")
def hello(req: func.HttpRequest) -> func.HttpResponse:
    name = req.params.get("name", "World")
    return func.HttpResponse(f"Hello, {name}!")
```

Deploy using the Azure CLI:
```bash
func azure functionapp publish <app-name>
```

## Conclusion
Azure Functions makes it easy to build event-driven applications in the cloud.
"""


async def main() -> None:
    print(f"{'=' * 50}")
    print("A2A Client — sending draft to remote Reviewer agent")
    print(f"{'=' * 50}\n")
    print(f"Connecting to: {SERVER_URL}")

    # Create an A2A agent that points to our server
    # This works exactly like a local agent — same interface, remote execution
    reviewer = A2AAgent(
        name="RemoteReviewer",
        description="Remote Reviewer agent accessed via A2A protocol",
        url=SERVER_URL,
    )

    print("Sending draft article for review...\n")

    async with reviewer:
        response = await reviewer.run(
            f"Please review and polish this article:\n\n{SAMPLE_DRAFT}",
        )

    print(f"\n{'─' * 50}")
    print("Reviewed article:\n")
    print(response.text)
    print(f"\n{'=' * 50}")
    print("Done! The remote agent reviewed the article via A2A protocol.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)

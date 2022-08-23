from typing import Dict

import click
from dynaconf import loaders
from rich import markdown, prompt  # type: ignore
from rich.console import Console  # type: ignore

from kaprien.cli.admin import admin
from kaprien.helpers.api_client import URL, Methods, is_logged, request_server

console = Console()


def _login(server: str, data: Dict[str, str]):

    token_response = request_server(
        server, URL.token.value, Methods.post, data=data
    )
    if token_response.status_code != 200:
        raise click.ClickException(token_response.json()["detail"])

    return token_response.json()


def _run_login(context):
    settings = context.obj.get("settings")
    console.print(
        markdown.Markdown(
            f"""# Login to Kaprien Server\n
            The server and token will generate a token and it will be
            stored in {context.obj.get('config')}
            """
        ),
        width=100,
    )
    while True:
        server = prompt.Prompt.ask("\nServer Address")
        if server.startswith("http") is False:
            console.print(
                f"Please use 'http://{server}' or 'https://{server}'"
            )
        else:
            break
    username = prompt.Prompt.ask(
        "Username", default="admin", show_default=True
    )
    password = click.prompt("Password", hide_input=True)
    expires = prompt.IntPrompt.ask(
        "Expire (in hours)", default=24, show_default=False
    )

    data = {
        "username": username,
        "password": password,
        "scope": (
            "write:targets "
            "read:targets "
            "write:bootstrap "
            "read:bootstrap "
            "read:settings "
            "read:token "
        ),
        "expires": expires,
    }

    token = _login(server, data)
    settings.SERVER = server
    settings.TOKEN = token["access_token"]
    loaders.write(context.obj.get("config"), settings.to_dict())

    console.print(f"Token stored in {context.obj.get('config')}\n")
    console.print("Login successfuly.")


@admin.command()
@click.option(
    "-f", "--force", "force", help="Force login/Renew token", is_flag=True
)
@click.pass_context
def login(context, force):
    """
    Login to Kaprien Server (API).
    """
    settings = context.obj.get("settings")
    server = settings.get("SERVER")
    token = settings.get("TOKEN")

    if force is False and server is not None and token is not None:
        response = is_logged(server, token)
        if response.state is False:
            _run_login(context)

        else:
            data = response.data
            if response.data.get("expired") is False:
                console.print(
                    f"Already logged. Valid until '{data['expiration']}'"
                )

    else:
        _run_login(context)

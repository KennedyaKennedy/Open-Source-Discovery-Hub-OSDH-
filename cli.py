#!/usr/bin/env python3
"""
Open-Source Discovery Hub CLI
Full feature parity with web UI.
"""

import click
import httpx
import json
import sys

BASE_URL = "http://localhost:8080/api"


def api_get(path, params=None):
    url = f"{BASE_URL}{path}"
    try:
        resp = httpx.get(url, params=params, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def api_post(path, data=None):
    url = f"{BASE_URL}{path}"
    try:
        resp = httpx.post(url, json=data, timeout=120)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@click.group()
def cli():
    """Open-Source Discovery Hub CLI"""
    pass


@cli.command()
@click.option("-q", "--query", help="Search query")
@click.option("-l", "--language", help="Filter by language")
@click.option("--license", "license_", help="Filter by license")
@click.option("-s", "--source-type", help="Filter by source type")
@click.option("-m", "--maintenance-status", help="Filter by maintenance status")
@click.option("--tags", help="Filter by comma-separated tags")
@click.option(
    "--sort",
    default="last_updated",
    type=click.Choice(["name", "stars", "last_updated", "created_at"]),
)
@click.option("--order", default="desc", type=click.Choice(["asc", "desc"]))
@click.option("--limit", default=20, type=int)
@click.option("--offset", default=0, type=int)
@click.option("--json-output", is_flag=True, help="Output as JSON")
def search(
    query,
    language,
    license_,
    source_type,
    maintenance_status,
    tags,
    sort,
    order,
    limit,
    offset,
    json_output,
):
    """Search and filter resources"""
    params = {
        "q": query,
        "language": language,
        "license": license_,
        "source_type": source_type,
        "maintenance_status": maintenance_status,
        "tags": tags,
        "sort": sort,
        "order": order,
        "limit": limit,
        "offset": offset,
    }
    params = {k: v for k, v in params.items() if v is not None}

    data = api_get("/resources", params)

    if json_output:
        click.echo(json.dumps(data, indent=2, default=str))
        return

    if not data["resources"]:
        click.echo("No resources found.")
        return

    click.echo(f"Found {data['total']} resources (showing {len(data['resources'])})\n")

    for r in data["resources"]:
        status = r["maintenance_status"]
        status_color = {
            "active": "green",
            "maintained": "blue",
            "stale": "yellow",
            "archived": "red",
        }.get(status, "white")
        click.echo(f"  {click.style(r['name'], fg='cyan')}")
        click.echo(f"    {r.get('description', 'No description')[:100]}")
        click.echo(
            f"    {click.style(status, fg=status_color)} | ★ {r['stars']} | ⑂ {r['forks']} | {r.get('language', 'N/A')} | {r.get('license', 'N/A')}"
        )
        if r.get("ai_tags"):
            click.echo(f"    Tags: {', '.join(r['ai_tags'][:5])}")
        click.echo(f"    {r['url']}")
        click.echo()


@cli.command()
@click.argument("resource_id")
def info(resource_id):
    """Show detailed info for a resource"""
    data = api_get(f"/resources/{resource_id}")

    click.echo(f"  {click.style(data['name'], fg='cyan', bold=True)}")
    click.echo(f"  URL: {data['url']}")
    click.echo(f"  Description: {data.get('description', 'N/A')}")
    click.echo(f"  Source: {data['source_type']}")
    click.echo(f"  Language: {data.get('language', 'N/A')}")
    click.echo(f"  License: {data.get('license', 'N/A')}")
    click.echo(f"  Stars: {data['stars']} | Forks: {data['forks']}")
    click.echo(f"  Status: {data['maintenance_status']}")
    click.echo(f"  Archived: {data['is_archived']}")

    if data.get("readme_summary"):
        click.echo(f"\n  AI Summary:\n    {data['readme_summary']}")

    if data.get("ai_tags"):
        click.echo(f"\n  AI Tags: {', '.join(data['ai_tags'])}")

    if data.get("topics"):
        click.echo(f"\n  Topics: {', '.join(data['topics'])}")


@cli.command()
@click.option(
    "-s",
    "--source",
    default="github",
    type=click.Choice(["github", "awesome", "educational", "all"]),
)
@click.option("-q", "--query", help="Search query (GitHub only)")
@click.option("-l", "--language", help="Language filter (GitHub only)")
@click.option("-t", "--topic", multiple=True, help="Topic filter (GitHub only)")
@click.option("--no-ai", is_flag=True, help="Skip AI processing")
def aggregate(source, query, language, topic, no_ai):
    """Run aggregation from sources"""
    topics = list(topic) if topic else None

    click.echo(f"Starting aggregation from {source}...")
    data = api_post(
        "/aggregate/run",
        {
            "source": source,
            "query": query,
            "language": language,
            "topics": topics,
            "run_ai": not no_ai,
        },
    )

    click.echo(f"  Found: {data['resources_found']}")
    click.echo(f"  Added: {data['resources_added']}")
    click.echo(f"  Updated: {data['resources_updated']}")
    click.echo(f"  Log ID: {data['log_id']}")


@cli.command()
def ai_process():
    """Run AI processing on unprocessed resources"""
    click.echo("Starting AI processing...")
    api_post("/aggregate/ai-process")
    click.echo("AI processing started in background.")


@cli.command()
@click.option(
    "-f",
    "--format",
    "format_",
    default="json",
    type=click.Choice(["json", "csv", "sqlite", "all"]),
)
def snapshot(format_):
    """Create a snapshot export"""
    click.echo(f"Creating snapshot (format: {format_})...")
    data = api_post(f"/snapshots/create?format={format_}")
    click.echo(f"  Version: {data['version']}")
    click.echo(f"  Resources: {data['resource_count']}")
    click.echo(f"  Files: {', '.join(data['file_paths'])}")


@cli.command()
def snapshots_list():
    """List available snapshots"""
    data = api_get("/snapshots/list")
    if not data:
        click.echo("No snapshots found.")
        return

    for s in data:
        click.echo(
            f"  {s['version']} | {s['resource_count']} resources | {s['created_at']}"
        )


@cli.command()
def stats():
    """Show database statistics"""
    data = api_get("/stats")

    click.echo(
        f"  Total resources: {click.style(str(data['total']), fg='cyan', bold=True)}"
    )
    click.echo(f"  Active: {click.style(str(data['by_status']['active']), fg='green')}")
    click.echo(
        f"  Maintained: {click.style(str(data['by_status']['maintained']), fg='blue')}"
    )
    click.echo(f"  Stale: {click.style(str(data['by_status']['stale']), fg='yellow')}")
    click.echo(
        f"  Archived: {click.style(str(data['by_status']['archived']), fg='red')}"
    )

    click.echo(f"\n  Languages: {len(data['languages'])}")
    click.echo(f"  Licenses: {len(data['licenses'])}")

    if data.get("top_tags"):
        click.echo(f"\n  Top tags:")
        for tag, count in list(data["top_tags"].items())[:10]:
            click.echo(f"    {tag}: {count}")


@cli.command()
def logs():
    """Show aggregation logs"""
    data = api_get("/aggregate/logs")
    if not data:
        click.echo("No logs found.")
        return

    for log in data[:10]:
        status_color = {"completed": "green", "running": "yellow", "failed": "red"}.get(
            log["status"], "white"
        )
        click.echo(
            f"  {click.style(log['source'], fg='cyan')} | {click.style(log['status'], fg=status_color)} | Found: {log['resources_found']} | Added: {log['resources_added']} | {log['started_at']}"
        )


if __name__ == "__main__":
    cli()

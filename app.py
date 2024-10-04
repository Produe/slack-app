import logging
import os


logging.basicConfig(level=logging.DEBUG)

from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
import requests

from dotenv import load_dotenv

from service_functions import get_team_id_from_command, is_workspace_authenticated, get_user_by_team_id, fetch_all_tasks, fetch_github_commits


load_dotenv("TOKENS.env")
app = App(signing_secret=os.environ["SLACK_SIGNING_SECRET"])

@app.middleware  # or app.use(log_request)
def log_request(logger, body, next):
    logger.debug(body)
    return next()


@app.event("app_mention")
def event_test(body, say, logger):
    logger.info(body)
    say("What's up?")


@app.event("message")
def handle_message():
    pass


@app.command("/clickup_tasks")
def filter_tasks_by_assignee(ack, command, say):
    ack()

    team_id = get_team_id_from_command(command)
    if not is_workspace_authenticated(team_id):
        say(f"Workspace for team {team_id} is not authenticated. Please contact your administrator.")
        return

    try:
        user_data = get_user_by_team_id(team_id) 
        tasks_list = fetch_all_tasks(user_data)
        username = command['text']
        filtered_tasks = [task for task in tasks_list if username in task['assignees']]

        if filtered_tasks:
            response_text = f"Here are the tasks assigned to *{username}*:\n"
            for task in filtered_tasks:
                response_text += (f"• *Task ID:* {task['task_id']} | "
                                  f"*Name:* {task['task_name']} | "
                                  f"*Team:* {task['team_name']} | "
                                  f"*Status:* {task['task_status']}\n")
            say(response_text)
        else:
            say(f"No tasks found for user {username}.")
    except requests.exceptions.RequestException as e:
        say(f"Error fetching data: {str(e)}")

@app.command("/github_commits")
def fetch_github_commits_command(ack, command, say):
    ack()

    team_id = get_team_id_from_command(command)
    if not is_workspace_authenticated(team_id):
        say(f"Workspace for team {team_id} is not authenticated. Please contact your administrator.")
        return

    try:
        user_data = get_user_by_team_id(team_id)  
        commits_list = fetch_github_commits(user_data)

        if commits_list:
            response_text = "Here are the latest commits:\n"
            for commit in commits_list[:5]: 
                response_text += (f"• *SHA:* {commit['sha']} | "
                                  f"*Message:* {commit['commit']['message']} | "
                                  f"*Author:* {commit['commit']['author']['name']} | "
                                  f"*Date:* {commit['commit']['author']['date']}\n")
            say(response_text)
        else:
            say(f"No commits found for user {team_id}.")
    except requests.exceptions.RequestException as e:
        say(f"Error fetching GitHub commits: {str(e)}")

from flask import Flask, request

flask_app = Flask(__name__)
handler = SlackRequestHandler(app)


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    flask_app.run(debug=True)

# pip install -r requirements.txt
# export SLACK_SIGNING_SECRET=***
# export SLACK_BOT_TOKEN=xoxb-***
# FLASK_APP=app.py FLASK_ENV=development flask run -p 3000
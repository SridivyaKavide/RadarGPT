import requests
import json
import os
from flask import url_for
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntegrationManager:
    """Manages integrations with external tools"""
    
    def __init__(self):
        # Load API keys from environment variables
        self.jira_api_key = os.getenv("JIRA_API_KEY")
        self.jira_domain = os.getenv("JIRA_DOMAIN")
        self.jira_email = os.getenv("JIRA_EMAIL")
        
        self.trello_api_key = os.getenv("TRELLO_API_KEY")
        self.trello_token = os.getenv("TRELLO_TOKEN")
        
        self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        
        self.notion_api_key = os.getenv("NOTION_API_KEY")
        
    def create_jira_issue(self, project_key, summary, description, issue_type="Task"):
        """Create a Jira issue from radar findings"""
        if not self.jira_api_key or not self.jira_domain:
            return {"error": "Jira integration not configured"}, 400
            
        url = f"https://{self.jira_domain}.atlassian.net/rest/api/3/issue"
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Format description for Jira markdown
        description = description.replace("<h2>", "h2. ").replace("</h2>", "\n\n")
        description = description.replace("<h3>", "h3. ").replace("</h3>", "\n\n")
        description = description.replace("<ul>", "").replace("</ul>", "")
        description = description.replace("<li>", "* ").replace("</li>", "")
        description = description.replace("<br>", "\n")
        
        payload = {
            "fields": {
                "project": {
                    "key": project_key
                },
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": description
                                }
                            ]
                        }
                    ]
                },
                "issuetype": {
                    "name": issue_type
                }
            }
        }
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                auth=(self.jira_email, self.jira_api_key)
            )
            
            if response.status_code == 201:
                data = response.json()
                return {
                    "success": True,
                    "issue_key": data["key"],
                    "issue_url": f"https://{self.jira_domain}.atlassian.net/browse/{data['key']}"
                }, 201
            else:
                return {"error": f"Failed to create Jira issue: {response.text}"}, 400
        except Exception as e:
            logger.error(f"Error creating Jira issue: {e}")
            return {"error": f"Error creating Jira issue: {str(e)}"}, 500
    
    def create_trello_card(self, board_id, list_id, name, description):
        """Create a Trello card from radar findings"""
        if not self.trello_api_key or not self.trello_token:
            return {"error": "Trello integration not configured"}, 400
            
        url = "https://api.trello.com/1/cards"
        
        # Format description for Trello markdown
        description = description.replace("<h2>", "## ").replace("</h2>", "\n\n")
        description = description.replace("<h3>", "### ").replace("</h3>", "\n\n")
        description = description.replace("<ul>", "").replace("</ul>", "")
        description = description.replace("<li>", "- ").replace("</li>", "")
        description = description.replace("<br>", "\n")
        
        query = {
            "key": self.trello_api_key,
            "token": self.trello_token,
            "idList": list_id,
            "name": name,
            "desc": description
        }
        
        try:
            response = requests.post(url, params=query)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "card_id": data["id"],
                    "card_url": data["shortUrl"]
                }, 201
            else:
                return {"error": f"Failed to create Trello card: {response.text}"}, 400
        except Exception as e:
            logger.error(f"Error creating Trello card: {e}")
            return {"error": f"Error creating Trello card: {str(e)}"}, 500
    
    def send_to_slack(self, channel, summary, details_url):
        """Send radar findings to Slack"""
        if not self.slack_webhook_url:
            return {"error": "Slack integration not configured"}, 400
            
        payload = {
            "channel": channel,
            "text": "New PainRadar Insight",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "New PainRadar Insight"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{summary}*"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View Details"
                            },
                            "url": details_url
                        }
                    ]
                }
            ]
        }
        
        try:
            response = requests.post(
                self.slack_webhook_url,
                json=payload
            )
            
            if response.status_code == 200:
                return {"success": True}, 200
            else:
                return {"error": f"Failed to send to Slack: {response.text}"}, 400
        except Exception as e:
            logger.error(f"Error sending to Slack: {e}")
            return {"error": f"Error sending to Slack: {str(e)}"}, 500
    
    def create_notion_page(self, database_id, title, content):
        """Create a Notion page from radar findings"""
        if not self.notion_api_key:
            return {"error": "Notion integration not configured"}, 400
            
        url = "https://api.notion.com/v1/pages"
        
        headers = {
            "Authorization": f"Bearer {self.notion_api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        # Format content for Notion blocks
        # This is a simplified version - Notion API requires specific block structure
        blocks = []
        
        # Add heading
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": title}}]
            }
        })
        
        # Add content as paragraph
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": content}}]
            }
        })
        
        payload = {
            "parent": {"database_id": database_id},
            "properties": {
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                }
            },
            "children": blocks
        }
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "page_id": data["id"],
                    "page_url": f"https://notion.so/{data['id'].replace('-', '')}"
                }, 201
            else:
                return {"error": f"Failed to create Notion page: {response.text}"}, 400
        except Exception as e:
            logger.error(f"Error creating Notion page: {e}")
            return {"error": f"Error creating Notion page: {str(e)}"}, 500

# Singleton instance
integration_manager = IntegrationManager()
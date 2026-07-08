import requests
from config import NOTION_TOKEN, NOTION_DATABASE_ID, NOTION_VERSION

def create_notion_task(task_text, tag, sender_name, image_url=None):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }
    
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": task_text}}]},
            "Status": {"status": {"name": "Вхідні"}},
            "Priority": {"select": {"name": "⚡ Середній"}},
            "Tags": {"multi_select": [{"name": tag}]},
            "Від кого": {"rich_text": [{"text": {"content": sender_name}}]}
        }
    }
    
    if image_url:
        data["children"] = [{"object": "block", "type": "image", "image": {"type": "external", "external": {"url": image_url}}}]
        
    try:
        response = requests.post(url, headers=headers, json=data)
        return response.status_code == 200, response.text if response.status_code != 200 else "OK"
    except Exception as e:
        return False, str(e)

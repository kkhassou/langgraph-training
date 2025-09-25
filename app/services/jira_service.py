from typing import List, Dict, Any, Optional
from jira import JIRA
from jira.exceptions import JIRAError

from app.core.dependencies import validate_jira_config


class JiraService:
    """Service for Jira API interactions"""

    def __init__(self):
        self.config = validate_jira_config()
        self.client = JIRA(
            server=self.config["server"],
            basic_auth=(self.config["email"], self.config["token"])
        )

    async def get_projects(self) -> List[Dict[str, Any]]:
        """Get list of projects"""
        try:
            projects = self.client.projects()
            return [
                {
                    "key": project.key,
                    "name": project.name,
                    "id": project.id,
                    "description": getattr(project, "description", "")
                }
                for project in projects
            ]
        except JIRAError as e:
            raise Exception(f"Jira API error: {str(e)}")

    async def search_issues(
        self,
        jql: str,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """Search issues using JQL"""
        try:
            issues = self.client.search_issues(jql, maxResults=max_results)

            result = []
            for issue in issues:
                result.append({
                    "key": issue.key,
                    "summary": issue.fields.summary,
                    "status": issue.fields.status.name,
                    "assignee": issue.fields.assignee.displayName if issue.fields.assignee else None,
                    "reporter": issue.fields.reporter.displayName if issue.fields.reporter else None,
                    "priority": issue.fields.priority.name if issue.fields.priority else None,
                    "created": str(issue.fields.created),
                    "updated": str(issue.fields.updated),
                    "description": issue.fields.description or "",
                })

            return result

        except JIRAError as e:
            raise Exception(f"Jira API error: {str(e)}")

    async def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: str = "Task",
        assignee: Optional[str] = None,
        priority: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new issue"""
        try:
            issue_dict = {
                'project': {'key': project_key},
                'summary': summary,
                'description': description,
                'issuetype': {'name': issue_type},
            }

            if assignee:
                issue_dict['assignee'] = {'name': assignee}

            if priority:
                issue_dict['priority'] = {'name': priority}

            new_issue = self.client.create_issue(fields=issue_dict)

            return {
                "key": new_issue.key,
                "id": new_issue.id,
                "url": f"{self.config['server']}/browse/{new_issue.key}"
            }

        except JIRAError as e:
            raise Exception(f"Jira API error: {str(e)}")

    async def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """Get issue details"""
        try:
            issue = self.client.issue(issue_key)

            return {
                "key": issue.key,
                "summary": issue.fields.summary,
                "status": issue.fields.status.name,
                "assignee": issue.fields.assignee.displayName if issue.fields.assignee else None,
                "reporter": issue.fields.reporter.displayName if issue.fields.reporter else None,
                "priority": issue.fields.priority.name if issue.fields.priority else None,
                "created": str(issue.fields.created),
                "updated": str(issue.fields.updated),
                "description": issue.fields.description or "",
                "url": f"{self.config['server']}/browse/{issue.key}"
            }

        except JIRAError as e:
            raise Exception(f"Jira API error: {str(e)}")

    async def update_issue(
        self,
        issue_key: str,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        assignee: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update an existing issue"""
        try:
            issue = self.client.issue(issue_key)
            update_fields = {}

            if summary:
                update_fields['summary'] = summary
            if description:
                update_fields['description'] = description
            if assignee:
                update_fields['assignee'] = {'name': assignee}

            if update_fields:
                issue.update(fields=update_fields)

            if status:
                transitions = self.client.transitions(issue)
                transition_id = None
                for transition in transitions:
                    if transition['name'].lower() == status.lower():
                        transition_id = transition['id']
                        break

                if transition_id:
                    self.client.transition_issue(issue, transition_id)

            return {
                "key": issue.key,
                "updated": True,
                "url": f"{self.config['server']}/browse/{issue.key}"
            }

        except JIRAError as e:
            raise Exception(f"Jira API error: {str(e)}")
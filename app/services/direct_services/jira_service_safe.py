from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

try:
    from jira import JIRA
    from jira.exceptions import JIRAError
    JIRA_AVAILABLE = True
except ImportError:
    JIRA_AVAILABLE = False
    JIRAError = Exception

from app.core.dependencies import validate_jira_config_safe


class JiraServiceSafe:
    """Safe service for Jira API interactions with dependency checking"""

    def __init__(self):
        if not JIRA_AVAILABLE:
            raise ImportError("jira is not installed. Please run: pip install jira")

        self.config = validate_jira_config_safe()
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


class JiraServiceMock:
    """Mock service for when Jira is not available"""

    def __init__(self):
        logger.warning("Using mock Jira service - jira not installed")

    async def get_projects(self) -> List[Dict[str, Any]]:
        return [
            {"key": "PROJ", "name": "Test Project", "id": "10000", "description": "A mock project"},
            {"key": "DEV", "name": "Development", "id": "10001", "description": "Development project"},
        ]

    async def search_issues(self, jql: str, max_results: int = 50) -> List[Dict[str, Any]]:
        return [
            {
                "key": "PROJ-1",
                "summary": "Mock issue for testing",
                "status": "To Do",
                "assignee": "john.doe",
                "reporter": "jane.smith",
                "priority": "Medium",
                "created": "2023-01-01T10:00:00.000+0000",
                "updated": "2023-01-01T10:00:00.000+0000",
                "description": "This is a mock issue"
            }
        ]

    async def create_issue(self, project_key: str, summary: str, description: str,
                          issue_type: str = "Task", assignee: Optional[str] = None,
                          priority: Optional[str] = None) -> Dict[str, Any]:
        return {
            "key": f"{project_key}-999",
            "id": "999999",
            "url": f"https://mock.atlassian.net/browse/{project_key}-999"
        }

    async def get_issue(self, issue_key: str) -> Dict[str, Any]:
        return {
            "key": issue_key,
            "summary": "Mock issue",
            "status": "In Progress",
            "assignee": "john.doe",
            "reporter": "jane.smith",
            "priority": "High",
            "created": "2023-01-01T10:00:00.000+0000",
            "updated": "2023-01-01T10:00:00.000+0000",
            "description": "This is a mock issue description",
            "url": f"https://mock.atlassian.net/browse/{issue_key}"
        }


def get_jira_service():
    """Get Jira service instance (real or mock)"""
    if JIRA_AVAILABLE:
        try:
            return JiraServiceSafe()
        except Exception:
            logger.warning("Failed to initialize real Jira service, using mock")
            return JiraServiceMock()
    else:
        return JiraServiceMock()
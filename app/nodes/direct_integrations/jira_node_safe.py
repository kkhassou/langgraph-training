from typing import List, Dict, Any, Optional
from enum import Enum

from app.nodes.base_node import BaseNode, NodeState, NodeInput, NodeOutput
from app.services.direct_services.jira_service_safe import get_jira_service


class JiraActionType(str, Enum):
    GET_PROJECTS = "get_projects"
    SEARCH_ISSUES = "search_issues"
    CREATE_ISSUE = "create_issue"
    GET_ISSUE = "get_issue"


class JiraNodeSafe(BaseNode):
    """Safe node for Jira operations with dependency checking"""

    def __init__(self):
        super().__init__(
            name="jira_node_safe",
            description="Interact with Jira API for issue management (safe version)"
        )
        self.service = None

    def _get_service(self):
        """Get or create Jira service instance"""
        if self.service is None:
            self.service = get_jira_service()
        return self.service

    async def execute(self, state: NodeState) -> NodeState:
        """Execute Jira operation"""
        try:
            service = self._get_service()
            action = state.data.get("action", JiraActionType.GET_PROJECTS)

            if action == JiraActionType.GET_PROJECTS:
                projects = await service.get_projects()
                state.data["projects"] = projects
                state.messages.append(f"Retrieved {len(projects)} projects")

            elif action == JiraActionType.SEARCH_ISSUES:
                jql = state.data.get("jql")
                if not jql:
                    raise ValueError("jql is required for search_issues action")

                max_results = state.data.get("max_results", 50)
                issues = await service.search_issues(jql, max_results)
                state.data["issues"] = issues
                state.messages.append(f"Found {len(issues)} issues matching JQL query")

            elif action == JiraActionType.CREATE_ISSUE:
                required_fields = ["project_key", "summary", "description"]
                for field in required_fields:
                    if not state.data.get(field):
                        raise ValueError(f"{field} is required for create_issue action")

                result = await service.create_issue(
                    project_key=state.data["project_key"],
                    summary=state.data["summary"],
                    description=state.data["description"],
                    issue_type=state.data.get("issue_type", "Task"),
                    assignee=state.data.get("assignee"),
                    priority=state.data.get("priority")
                )
                state.data["created_issue"] = result
                state.messages.append(f"Created issue {result['key']}")

            elif action == JiraActionType.GET_ISSUE:
                issue_key = state.data.get("issue_key")
                if not issue_key:
                    raise ValueError("issue_key is required for get_issue action")

                issue = await service.get_issue(issue_key)
                state.data["issue"] = issue
                state.messages.append(f"Retrieved issue {issue_key}")

            state.metadata["node"] = self.name
            return state

        except Exception as e:
            state.data["error"] = str(e)
            state.metadata["error_node"] = self.name
            return state


class JiraInputSafe(NodeInput):
    """Input model for safe Jira node"""
    action: JiraActionType
    jql: Optional[str] = None
    issue_key: Optional[str] = None
    project_key: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    issue_type: str = "Task"
    assignee: Optional[str] = None
    priority: Optional[str] = None
    max_results: int = 50


class JiraOutputSafe(NodeOutput):
    """Output model for safe Jira node"""
    projects: List[Dict[str, Any]] = []
    issues: List[Dict[str, Any]] = []
    issue: Optional[Dict[str, Any]] = None
    created_issue: Optional[Dict[str, Any]] = None


async def jira_node_safe_handler(input_data: JiraInputSafe) -> JiraOutputSafe:
    """Standalone handler for safe Jira node API endpoint"""
    try:
        node = JiraNodeSafe()
        state = NodeState()
        state.data.update({
            "action": input_data.action,
            "jql": input_data.jql,
            "issue_key": input_data.issue_key,
            "project_key": input_data.project_key,
            "summary": input_data.summary,
            "description": input_data.description,
            "issue_type": input_data.issue_type,
            "assignee": input_data.assignee,
            "priority": input_data.priority,
            "max_results": input_data.max_results,
        })

        result_state = await node.execute(state)

        if "error" in result_state.data:
            return JiraOutputSafe(
                output_text="",
                success=False,
                error_message=result_state.data["error"]
            )

        # Format output based on action
        output_text = ""
        if result_state.messages:
            output_text = result_state.messages[-1]

        return JiraOutputSafe(
            output_text=output_text,
            projects=result_state.data.get("projects", []),
            issues=result_state.data.get("issues", []),
            issue=result_state.data.get("issue"),
            created_issue=result_state.data.get("created_issue"),
            data=result_state.data
        )

    except Exception as e:
        return JiraOutputSafe(
            output_text="",
            success=False,
            error_message=str(e)
        )
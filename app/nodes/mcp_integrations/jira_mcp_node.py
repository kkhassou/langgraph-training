from typing import Dict, Any, List, Optional
from enum import Enum

from app.nodes.mcp_integrations.mcp_base import MCPBaseNode
from app.nodes.base_node import NodeState, NodeInput, NodeOutput


class JiraMCPActionType(str, Enum):
    GET_PROJECTS = "get_projects"
    SEARCH_ISSUES = "search_issues"
    CREATE_ISSUE = "create_issue"
    GET_ISSUE = "get_issue"
    UPDATE_ISSUE = "update_issue"
    ADD_COMMENT = "add_comment"
    GET_TRANSITIONS = "get_transitions"
    TRANSITION_ISSUE = "transition_issue"
    GET_USER = "get_user"


class JiraMCPNode(MCPBaseNode):
    """Node for Jira operations using MCP server"""

    def __init__(self):
        super().__init__(
            name="jira_mcp_node",
            mcp_server_name="jira",
            description="Interact with Jira API via MCP server"
        )

    async def execute_mcp(self, state: NodeState) -> NodeState:
        """Execute Jira MCP operation"""
        action = state.data.get("action", JiraMCPActionType.GET_PROJECTS)

        if action == JiraMCPActionType.GET_PROJECTS:
            result = await self.call_mcp_tool("list_projects", {})
            if not result.get("isError"):
                projects_data = result.get("content", {})
                if isinstance(projects_data, str):
                    import ast
                    projects_data = ast.literal_eval(projects_data)

                projects = projects_data.get("projects", [])
                state.data["projects"] = projects
                state.messages.append(f"Retrieved {len(projects)} projects via MCP")

        elif action == JiraMCPActionType.SEARCH_ISSUES:
            jql = state.data.get("jql")
            if not jql:
                raise ValueError("jql is required for search_issues action")

            arguments = {
                "jql": jql,
                "max_results": state.data.get("max_results", 50)
            }

            result = await self.call_mcp_tool("search_issues", arguments)
            if not result.get("isError"):
                issues_data = result.get("content", {})
                if isinstance(issues_data, str):
                    import ast
                    issues_data = ast.literal_eval(issues_data)

                issues = issues_data.get("issues", [])
                state.data["issues"] = issues
                state.messages.append(f"Found {len(issues)} issues matching JQL query via MCP")

        elif action == JiraMCPActionType.CREATE_ISSUE:
            required_fields = ["project_key", "summary", "description"]
            for field in required_fields:
                if not state.data.get(field):
                    raise ValueError(f"{field} is required for create_issue action")

            arguments = {
                "project_key": state.data["project_key"],
                "summary": state.data["summary"],
                "description": state.data["description"],
                "issue_type": state.data.get("issue_type", "Task")
            }

            # Optional fields
            for field in ["assignee", "priority", "labels"]:
                if state.data.get(field):
                    arguments[field] = state.data[field]

            result = await self.call_mcp_tool("create_issue", arguments)
            if not result.get("isError"):
                issue_data = result.get("content", {})
                if isinstance(issue_data, str):
                    import ast
                    issue_data = ast.literal_eval(issue_data)

                state.data["created_issue"] = issue_data
                state.messages.append(f"Created issue {issue_data.get('key', 'unknown')} via MCP")

        elif action == JiraMCPActionType.GET_ISSUE:
            issue_key = state.data.get("issue_key")
            if not issue_key:
                raise ValueError("issue_key is required for get_issue action")

            result = await self.call_mcp_tool("get_issue", {"issue_key": issue_key})
            if not result.get("isError"):
                issue_data = result.get("content", {})
                if isinstance(issue_data, str):
                    import ast
                    issue_data = ast.literal_eval(issue_data)

                state.data["issue"] = issue_data
                state.messages.append(f"Retrieved issue {issue_key} via MCP")

        elif action == JiraMCPActionType.UPDATE_ISSUE:
            issue_key = state.data.get("issue_key")
            if not issue_key:
                raise ValueError("issue_key is required for update_issue action")

            arguments = {"issue_key": issue_key}

            # Optional update fields
            for field in ["summary", "description", "assignee", "priority", "labels"]:
                if state.data.get(field):
                    arguments[field] = state.data[field]

            result = await self.call_mcp_tool("update_issue", arguments)
            if not result.get("isError"):
                update_data = result.get("content", {})
                if isinstance(update_data, str):
                    import ast
                    update_data = ast.literal_eval(update_data)

                state.data["update_result"] = update_data
                state.messages.append(f"Updated issue {issue_key} via MCP")

        elif action == JiraMCPActionType.ADD_COMMENT:
            issue_key = state.data.get("issue_key")
            comment = state.data.get("comment")
            if not issue_key or not comment:
                raise ValueError("issue_key and comment are required for add_comment action")

            arguments = {
                "issue_key": issue_key,
                "comment": comment
            }

            result = await self.call_mcp_tool("add_comment", arguments)
            if not result.get("isError"):
                comment_data = result.get("content", {})
                if isinstance(comment_data, str):
                    import ast
                    comment_data = ast.literal_eval(comment_data)

                state.data["comment_result"] = comment_data
                state.messages.append(f"Added comment to issue {issue_key} via MCP")

        elif action == JiraMCPActionType.GET_TRANSITIONS:
            issue_key = state.data.get("issue_key")
            if not issue_key:
                raise ValueError("issue_key is required for get_transitions action")

            result = await self.call_mcp_tool("get_transitions", {"issue_key": issue_key})
            if not result.get("isError"):
                transitions_data = result.get("content", {})
                if isinstance(transitions_data, str):
                    import ast
                    transitions_data = ast.literal_eval(transitions_data)

                transitions = transitions_data.get("transitions", [])
                state.data["transitions"] = transitions
                state.messages.append(f"Retrieved {len(transitions)} transitions for issue {issue_key} via MCP")

        elif action == JiraMCPActionType.TRANSITION_ISSUE:
            issue_key = state.data.get("issue_key")
            transition_id = state.data.get("transition_id")
            if not issue_key or not transition_id:
                raise ValueError("issue_key and transition_id are required for transition_issue action")

            arguments = {
                "issue_key": issue_key,
                "transition_id": transition_id
            }

            result = await self.call_mcp_tool("transition_issue", arguments)
            if not result.get("isError"):
                transition_data = result.get("content", {})
                if isinstance(transition_data, str):
                    import ast
                    transition_data = ast.literal_eval(transition_data)

                state.data["transition_result"] = transition_data
                state.messages.append(f"Transitioned issue {issue_key} via MCP")

        elif action == JiraMCPActionType.GET_USER:
            user_id = state.data.get("user_id")
            if not user_id:
                raise ValueError("user_id is required for get_user action")

            result = await self.call_mcp_tool("get_user", {"user_id": user_id})
            if not result.get("isError"):
                user_data = result.get("content", {})
                if isinstance(user_data, str):
                    import ast
                    user_data = ast.literal_eval(user_data)

                state.data["user_info"] = user_data
                state.messages.append(f"Retrieved user info for {user_id} via MCP")

        # Handle MCP errors
        if result.get("isError"):
            error_content = result.get("content", "Unknown MCP error")
            state.data["error"] = f"MCP Jira error: {error_content}"

        state.metadata["node"] = self.name
        state.metadata["mcp_server"] = self.mcp_server_name
        return state


class JiraMCPInput(NodeInput):
    """Input model for Jira MCP node"""
    action: JiraMCPActionType
    jql: Optional[str] = None
    issue_key: Optional[str] = None
    project_key: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    issue_type: str = "Task"
    assignee: Optional[str] = None
    priority: Optional[str] = None
    labels: Optional[List[str]] = None
    comment: Optional[str] = None
    transition_id: Optional[str] = None
    user_id: Optional[str] = None
    max_results: int = 50


class JiraMCPOutput(NodeOutput):
    """Output model for Jira MCP node"""
    projects: List[Dict[str, Any]] = []
    issues: List[Dict[str, Any]] = []
    issue: Optional[Dict[str, Any]] = None
    created_issue: Optional[Dict[str, Any]] = None
    update_result: Optional[Dict[str, Any]] = None
    comment_result: Optional[Dict[str, Any]] = None
    transitions: List[Dict[str, Any]] = []
    transition_result: Optional[Dict[str, Any]] = None
    user_info: Optional[Dict[str, Any]] = None


async def jira_mcp_node_handler(input_data: JiraMCPInput) -> JiraMCPOutput:
    """Standalone handler for Jira MCP node API endpoint"""
    try:
        node = JiraMCPNode()
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
            "labels": input_data.labels,
            "comment": input_data.comment,
            "transition_id": input_data.transition_id,
            "user_id": input_data.user_id,
            "max_results": input_data.max_results,
        })

        result_state = await node.execute(state)

        if "error" in result_state.data:
            return JiraMCPOutput(
                output_text="",
                success=False,
                error_message=result_state.data["error"]
            )

        # Format output based on action
        output_text = ""
        if result_state.messages:
            output_text = result_state.messages[-1]

        return JiraMCPOutput(
            output_text=output_text,
            projects=result_state.data.get("projects", []),
            issues=result_state.data.get("issues", []),
            issue=result_state.data.get("issue"),
            created_issue=result_state.data.get("created_issue"),
            update_result=result_state.data.get("update_result"),
            comment_result=result_state.data.get("comment_result"),
            transitions=result_state.data.get("transitions", []),
            transition_result=result_state.data.get("transition_result"),
            user_info=result_state.data.get("user_info"),
            data=result_state.data
        )

    except Exception as e:
        return JiraMCPOutput(
            output_text="",
            success=False,
            error_message=str(e)
        )
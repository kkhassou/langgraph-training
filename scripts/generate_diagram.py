#!/usr/bin/env python3
"""
Script to generate Mermaid diagrams for all LangGraph workflows
"""
import os
import sys
from pathlib import Path

# Add the parent directory to the Python path to import modules
sys.path.append(str(Path(__file__).parent.parent))

from src.workflows.basic import SimpleChatGraph, PPTSummaryGraph, SlackReportGraph
from src.workflows.patterns import ReflectionGraph, ChainOfThoughtGraph


def generate_diagrams():
    """Generate Mermaid diagrams for all workflows"""

    # Create diagrams directory
    diagrams_dir = Path(__file__).parent.parent / "docs" / "diagrams"
    diagrams_dir.mkdir(parents=True, exist_ok=True)

    # Initialize all graphs
    graphs = {
        "simple_chat": SimpleChatGraph(),
        "ppt_summary": PPTSummaryGraph(),
        "slack_report": SlackReportGraph(),
        "reflection": ReflectionGraph(),
        "chain_of_thought": ChainOfThoughtGraph()
    }

    print("🎨 Generating Mermaid diagrams for all workflows...\n")

    # Generate diagram files
    for name, graph in graphs.items():
        try:
            diagram_content = graph.get_mermaid_diagram()

            # Write to .mmd file
            mmd_file = diagrams_dir / f"{name}.mmd"
            with open(mmd_file, "w", encoding="utf-8") as f:
                f.write(diagram_content.strip())

            # Generate HTML file for viewing
            html_file = diagrams_dir / f"{name}.html"
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{name.replace('_', ' ').title()} Workflow</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        h1 {{ color: #333; text-align: center; }}
        .diagram {{ text-align: center; margin: 20px 0; }}
        .description {{ background: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{name.replace('_', ' ').title()} Workflow</h1>

        <div class="description">
            <p><strong>Workflow Description:</strong> {_get_workflow_description(name)}</p>
        </div>

        <div class="diagram">
            <div class="mermaid">
{diagram_content}
            </div>
        </div>

        <div class="description">
            <h3>Usage:</h3>
            <p>This diagram shows the flow of the {name.replace('_', ' ')} workflow. Each node represents a processing step, and arrows show the data flow between steps.</p>
        </div>
    </div>

    <script>
        mermaid.initialize({{startOnLoad: true, theme: 'default'}});
    </script>
</body>
</html>"""

            with open(html_file, "w", encoding="utf-8") as f:
                f.write(html_content)

            print(f"✅ Generated diagrams for {name}")
            print(f"   📄 Mermaid file: {mmd_file}")
            print(f"   🌐 HTML file: {html_file}")
            print()

        except Exception as e:
            print(f"❌ Error generating diagram for {name}: {str(e)}")
            print()

    # Generate index.html
    generate_index_html(diagrams_dir, list(graphs.keys()))

    print("🎉 All diagrams generated successfully!")
    print(f"\n📁 Output directory: {diagrams_dir}")
    print("🌐 Open docs/diagrams/index.html to view all diagrams")


def _get_workflow_description(name: str) -> str:
    """Get description for a workflow"""
    descriptions = {
        "simple_chat": "A basic chat workflow using Gemini LLM for text generation",
        "ppt_summary": "PowerPoint processing workflow that extracts text and generates summaries",
        "slack_report": "Slack integration workflow for collecting messages and generating reports",
        "reflection": "Iterative improvement pattern using self-reflection and feedback",
        "chain_of_thought": "Step-by-step reasoning pattern for complex problem solving"
    }
    return descriptions.get(name, "Advanced workflow pattern")


def generate_index_html(diagrams_dir: Path, workflow_names: list):
    """Generate index HTML file listing all diagrams"""

    index_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>LangGraph Training - Workflow Diagrams</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }}
        h1 {{ color: #333; text-align: center; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
        .workflow-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-top: 30px; }}
        .workflow-card {{ background: #f9f9f9; padding: 20px; border-radius: 8px; border-left: 4px solid #4CAF50; }}
        .workflow-card h3 {{ margin-top: 0; color: #333; }}
        .workflow-card p {{ color: #666; margin: 10px 0; }}
        .workflow-card a {{ color: #4CAF50; text-decoration: none; font-weight: bold; }}
        .workflow-card a:hover {{ text-decoration: underline; }}
        .footer {{ text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎨 LangGraph Training - Workflow Diagrams</h1>

        <p style="text-align: center; color: #666; font-size: 18px;">
            Visual representations of all workshop workflows and patterns
        </p>

        <div class="workflow-grid">
"""

    for name in workflow_names:
        title = name.replace('_', ' ').title()
        description = _get_workflow_description(name)

        index_content += f"""
            <div class="workflow-card">
                <h3>{title}</h3>
                <p>{description}</p>
                <p>
                    <a href="{name}.html">View Diagram</a> |
                    <a href="{name}.mmd">Download Mermaid</a>
                </p>
            </div>
"""

    index_content += f"""
        </div>

        <div class="footer">
            <p><strong>LangGraph Training Workshop</strong><br>
               Generated on {os.popen('date').read().strip()}</p>
        </div>
    </div>
</body>
</html>"""

    index_file = diagrams_dir / "index.html"
    with open(index_file, "w", encoding="utf-8") as f:
        f.write(index_content)

    print(f"📝 Generated index file: {index_file}")


if __name__ == "__main__":
    try:
        generate_diagrams()
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

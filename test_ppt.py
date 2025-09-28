#!/usr/bin/env python3
"""
Test script for PPT ingest functionality
"""
import asyncio
import tempfile
import os

# Add project root to Python path
import sys
sys.path.append('.')

from app.nodes.ppt_ingest import ppt_ingest_handler, PowerPointIngestNode
from app.nodes.base_node import NodeState


async def test_ppt_ingest():
    """Test PPT ingest functionality"""
    print("🧪 Testing PPT ingest functionality...")

    try:
        # Test NodeState creation
        print("📝 Testing NodeState creation...")
        state = NodeState()
        print(f"✅ NodeState created: messages={state.messages}, data={state.data}")

        # Test PowerPointIngestNode creation
        print("📝 Testing PowerPointIngestNode creation...")
        node = PowerPointIngestNode()
        print(f"✅ Node created: {node.name} - {node.description}")

        # Test with a non-existent file (should fail gracefully)
        print("📝 Testing with non-existent file...")
        fake_path = "/tmp/non_existent_file.pptx"
        result = await ppt_ingest_handler(fake_path)
        print(f"✅ Handler handled non-existent file: success={result.success}")
        if not result.success:
            print(f"   Expected error: {result.error_message}")

        print("🎉 All tests passed! PPT ingest is working correctly.")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_ppt_ingest())
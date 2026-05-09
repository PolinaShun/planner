import asyncio
import httpx
import json

async def check_subtasks():
    base_url = "http://127.0.0.1:8000/api"
    
    async with httpx.AsyncClient() as client:
        print("1. Creating parent task...")
        res = await client.post(f"{base_url}/tasks", json={
            "name": "Родительская задача",
            "priority": "p1"
        })
        parent = res.json()
        parent_id = parent["id"]
        print(f"Parent created: ID {parent_id}")
        
        print("\n2. Creating subtask...")
        res = await client.post(f"{base_url}/tasks", json={
            "name": "Моя подзадача",
            "parent_id": parent_id,
            "priority": "p2"
        })
        subtask = res.json()
        print(f"Subtask created: ID {subtask['id']}, Parent ID: {subtask['parent_id']}")
        
        print("\n3. Fetching all tasks to check hierarchy...")
        res = await client.get(f"{base_url}/tasks")
        tasks = res.json()
        
        found_parent = next((t for t in tasks if t["id"] == parent_id), None)
        if found_parent and "subtasks" in found_parent:
            subtasks = found_parent["subtasks"]
            print(f"Success! Parent ID {parent_id} has {len(subtasks)} subtasks.")
            for st in subtasks:
                print(f" - Found subtask: {st['name']} (ID {st['id']})")
        else:
            print("Error: Subtask not found in parent's hierarchy.")

        # Cleanup (optional but good)
        # await client.post(f"{base_url}/tasks/{parent_id}/archive")

if __name__ == "__main__":
    try:
        asyncio.run(check_subtasks())
    except Exception as e:
        print(f"Server is likely not running: {e}")

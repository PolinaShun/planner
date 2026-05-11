import asyncio
import httpx

async def force_delete_tasks():
    base_url = "http://127.0.0.1:8000/api"
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(f"{base_url}/tasks")
            if res.status_code != 200:
                print("Error fetching tasks.")
                return
            all_tasks = res.json()

            def flatten_tasks(tasks):
                flat_list = []
                for task in tasks:
                    flat_list.append(task)
                    if task.get('subtasks'):
                        flat_list.extend(flatten_tasks(task['subtasks']))
                return flat_list

            flat_task_list = flatten_tasks(all_tasks)

        except Exception as e:
            print(f"Could not connect to server: {e}")
            return

        tasks_to_delete = []
        for task in flat_task_list:
            if "????" in task["name"]:
                tasks_to_delete.append(task)
        
        if not tasks_to_delete:
            print("No tasks with '????' found.")
            return

        print(f"Found {len(tasks_to_delete)} tasks to delete. Deleting now...")
        
        for task in tasks_to_delete:
            task_id = task["id"]
            print(f"  > Deleting ID: {task_id}")
            await client.delete(f"{base_url}/tasks/{task_id}")
    
    print("Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(force_delete_tasks())

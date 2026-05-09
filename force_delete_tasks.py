import asyncio
import httpx

async def force_delete_tasks():
    base_url = "http://127.0.0.1:8000/api"
    
    async with httpx.AsyncClient() as client:
        print("1. Fetching all tasks to find garbage...")
        try:
            res = await client.get(f"{base_url}/tasks")
            if res.status_code != 200:
                print(f"Error fetching tasks: {res.status_code}")
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
        garbage_names = ["Родительская задача", "????", "Тест без родителя", "Подзадача к", "Задача на удаление", "Финальная проверка"]
        
        for task in flat_task_list:
            if any(garbage in task["name"] for garbage in garbage_names):
                tasks_to_delete.append(task)
        
        unique_tasks_to_delete = list({t['id']: t for t in tasks_to_delete}.values())

        if not unique_tasks_to_delete:
            print("No garbage tasks found to delete.")
            return

        print(f"Found {len(unique_tasks_to_delete)} unique tasks to delete. Deleting now...")
        
        sorted_tasks = sorted(unique_tasks_to_delete, key=lambda x: x.get('parent_id') is not None, reverse=True)

        for task in sorted_tasks:
            task_id = task["id"]
            print(f"  > Deleting task ID: {task_id} ('{task['name']}')")
            try:
                delete_res = await client.delete(f"{base_url}/tasks/{task_id}")
                if delete_res.status_code == 200:
                    print("    - Success.")
                else:
                    print(f"    - Failed with status: {delete_res.status_code}")
            except Exception as e:
                print(f"    - Error deleting task {task_id}: {e}")
    
    print("
Cleanup complete.")

if __name__ == "__main__":
    try:
        asyncio.run(force_delete_tasks())
    except httpx.ConnectError as e:
        print(f"Connection error. Is the server running on http://127.0.0.1:8000?
Details: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

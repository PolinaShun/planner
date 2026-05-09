import asyncio
import httpx

async def force_delete_tasks():
    base_url = "http://127.0.0.1:8000/api"
    
    async with httpx.AsyncClient() as client:
        print("1. Fetching all tasks to find garbage...")
        try:
            # Сначала получим все задачи, включая архивные, чтобы ничего не пропустить
            res_active = await client.get(f"{base_url}/tasks")
            res_archived = await client.get(f"{base_url}/tasks/archived")
            
            if res_active.status_code != 200 or res_archived.status_code != 200:
                print("Error fetching tasks.")
                return

            all_tasks = res_active.json()
            # Добавляем подзадачи в общий список для проверки
            for task in all_tasks:
                if task.get('subtasks'):
                    all_tasks.extend(task['subtasks'])
            all_tasks.extend(res_archived.json())

        except Exception as e:
            print(f"Could not connect to server: {e}")
            return

        tasks_to_delete = []
        for task in all_tasks:
            if "Родительская задача" in task["name"] or "????" in task["name"] or "Тест без родителя" in task["name"] or "Подзадача к" in task["name"]:
                if task not in tasks_to_delete:
                    tasks_to_delete.append(task)
        
        if not tasks_to_delete:
            print("No garbage tasks found to delete.")
            return

        print(f"Found {len(tasks_to_delete)} tasks to delete. Deleting now...")
        
        # Сортируем, чтобы сначала удалять подзадачи (хотя cascade должен справляться)
        tasks_to_delete.sort(key=lambda x: x.get('parent_id') is not None, reverse=True)

        for task in tasks_to_delete:
            task_id = task["id"]
            print(f"  > Deleting task ID: {task_id} ('{task['name']}')")
            try:
                delete_res = await client.delete(f"{base_url}/tasks/{task_id}")
                if delete_res.status_code == 200:
                    print(f"    - Success.")
                else:
                    print(f"    - Failed with status: {delete_res.status_code}")
            except Exception as e:
                print(f"    - Error deleting task {task_id}: {e}")
    
    print("
Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(force_delete_tasks())

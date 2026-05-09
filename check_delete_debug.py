import asyncio
import httpx

async def check_delete():
    base_url = "http://127.0.0.1:8000/api"
    headers = {"Content-Type": "application/json"}
    
    async with httpx.AsyncClient() as client:
        # 1. Создаем родительскую задачу
        print("1. Creating a parent task...")
        parent_res = await client.post(f"{base_url}/tasks", json={"name": "Родитель для удаления"}, headers=headers)
        if parent_res.status_code != 200:
            if parent_res.status_code != 200:
                print(f"Error creating parent task: {parent_res.status_code}\n{parent_res.text}")
                return
            parent_task = parent_res.json()
            parent_id = parent_task["id"]
            print(f"  > Parent task created with ID: {parent_id}")

            # 2. Создаем подзадачу
            print("\\n2. Creating a subtask for it...")
            sub_res = await client.post(f"{base_url}/tasks", json={"name": "Подзадача для удаления", "parent_id": parent_id}, headers=headers)
            if sub_res.status_code != 200:
                print(f"Error creating subtask: {sub_res.status_code}\\n{sub_res.text}")
                return

{sub_res.text}")
            return
        sub_task = sub_res.json()
        print(f"  > Subtask created with ID: {sub_task['id']}")

        # 3. Удаляем родительскую задачу (каскадное удаление должно сработать)
        print(f"
3. Deleting parent task with ID: {parent_id}...")
        delete_res = await client.delete(f"{base_url}/tasks/{parent_id}")
        
        print(f"  > Delete response status: {delete_res.status_code}")
        
        if delete_res.status_code == 200:
            print("  > Delete request successful.")
        else:
            print(f"  > Error during delete request:
{delete_res.text}")
            return

        # 4. Проверяем, что обе задачи удалены
        print("
4. Verifying both tasks are deleted...")
        all_tasks_res = await client.get(f"{base_url}/tasks")
        all_tasks = all_tasks_res.json()
        
        parent_found = any(t["id"] == parent_id for t in all_tasks)
        
        subtask_found_in_any_parent = False
        for task in all_tasks:
            if "subtasks" in task and any(st["id"] == sub_task["id"] for st in task["subtasks"]):
                subtask_found_in_any_parent = True
                break

        if not parent_found and not subtask_found_in_any_parent:
            print("  > Success! Parent and subtask are no longer present.")
        else:
            print("  > Error! One or both tasks were not deleted.")

if __name__ == "__main__":
    try:
        asyncio.run(check_delete())
    except httpx.ConnectError as e:
        print(f"Connection error. Is the server running on http://127.0.0.1:8000?
Details: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

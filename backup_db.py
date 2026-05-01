import shutil
import os
from datetime import datetime

def make_backup():
    db_path = "planner.db"
    backup_dir = "backups"
    
    if not os.path.exists(db_path):
        return
        
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = f"{backup_dir}/planner_{timestamp}.db"
    
    shutil.copy2(db_path, backup_path)
    print(f"📦 Бэкап создан: {backup_path}")
    
    # Удаляем старые бэкапы (оставляем только 7 последних)
    backups = sorted([f for f in os.listdir(backup_dir) if f.endswith(".db")])
    while len(backups) > 7:
        os.remove(os.path.join(backup_dir, backups.pop(0)))

if __name__ == "__main__":
    make_backup()

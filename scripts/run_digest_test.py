from modules.email_digest import run_digest
from modules.discord_notifier import send_email_digest

print("Connecting to Outlook...")
results = run_digest(hours=48)
total = sum(len(v) for v in results.values())
print(f"Found: Urgent={len(results['urgent'])}, Normal={len(results['normal'])}, FYI={len(results['fyi'])}, Total={total}")
send_email_digest(results)
print("Done!")

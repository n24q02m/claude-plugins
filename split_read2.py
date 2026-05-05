with open("scripts/test_check_version_freshness.py") as f:
    lines = f.readlines()
for i in range(11, 14):
    start = i * 20
    end = start + 20
    print(f"--- CHUNK {i} ({start} to {end}) ---")
    print("".join(lines[start:end]))

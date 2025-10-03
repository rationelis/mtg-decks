import os

directory_path = "decks"

for deck in os.listdir(directory_path):
    with open(os.path.join(directory_path, deck), "r") as f:
        count = sum(
            int(parts[0])
            for line in f
            if (parts := line.split()) and parts[0].isdigit()
        )

    status = "✅" if count == 100 else "❌"
    print(f"{status} {deck} has {count} cards.")

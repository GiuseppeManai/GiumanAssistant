from giuman_assistant.ainote_importer import import_new_notes, validate_inbox


def choose_category():
    categories = [
        "personal",
        "family",
        "professional",
        "confidential",
        "health",
        "finance",
        "learning",
        "ideas",
    ]

    print("\nCategory:")
    for i, category in enumerate(categories, start=1):
        print(f"{i}. {category}")

    choice = input("Choose category [default professional]: ").strip()

    if not choice:
        return "professional"

    return categories[int(choice) - 1]


def choose_knowledge_type():
    types = [
        "Source only",
        "Idea",
        "Concept",
        "Framework",
        "Project",
        "Client",
        "Decision",
        "Pattern",
        "Profile",
        "Action",
    ]

    print("\nKnowledge type:")
    for i, item in enumerate(types, start=1):
        print(f"{i}. {item}")

    choice = input("Choose type [default Source only]: ").strip()

    if not choice:
        return "Source only"

    return types[int(choice) - 1]


def main():
    validation = validate_inbox()
    files = validation["new"]

    if not files:
        print(validation["message"])
        return

    print("\nFound new files:")
    for i, item in enumerate(files, start=1):
        print(f"{i}. {item['name']}")

    selected = input("\nImport all files? [y/N]: ").strip().lower()

    if selected != "y":
        print("Cancelled.")
        return

    category = choose_category()
    knowledge_type = choose_knowledge_type()
    result = import_new_notes(category, knowledge_type)

    for item in result["processed"]:
        print(f"\nImported: {item['file']}")
        print(f"Saved raw source: {item['raw_txt_path']}")
        print(f"Updated wiki files: {item['updated_files']}")
        print("Marked as processed")

    for item in result["failed"]:
        print(f"\nFailed to import {item['file']}: {item['error']}")
        print(f"Moved to: {item['failed_path']}")

    print(f"\n{result['message']}")


if __name__ == "__main__":
    main()

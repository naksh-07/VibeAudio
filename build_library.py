import os
import json

# --- SETTINGS ---
INPUT_FOLDER = "books_data"  # Yahan choti files rahengi
OUTPUT_FILE = "books.json"   # Ye website use karegi

def merge_books():
    if not os.path.exists(INPUT_FOLDER):
        print(f"❌ Bhai '{INPUT_FOLDER}' folder hi nahi hai!")
        os.makedirs(INPUT_FOLDER)
        print(f"✅ Maine bana diya. Ab usme apni book files daal.")
        return

    all_books = []
    files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith(".json")]

    if not files:
        print("⚠️ Folder khali hai bhai! Kuch .json files to daal.")
        return

    print(f"📚 Found {len(files)} books. Merging them...")

    existing_ids = [] # Duplicate check karne ke liye

    # Har file ko padho aur list mein jodo
    for file_name in files:
        file_path = os.path.join(INPUT_FOLDER, file_name)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                book_data = json.load(f)
                
                # Validation: Check kar lo zaroori cheezein hain ya nahi
                if "id" in book_data and "title" in book_data and "chapters" in book_data:
                    
                    # Duplicate ID Check (Bhai ki madad ke liye)
                    if book_data['id'] in existing_ids:
                        print(f"⚠️ WARNING: ID {book_data['id']} do baar aa gaya hai! ({file_name})")
                    else:
                        existing_ids.append(book_data['id'])
                    
                    all_books.append(book_data)
                else:
                    print(f"⚠️ Skipping {file_name}: 'id', 'title' ya 'chapters' missing hai.")
                    
        except Exception as e:
            print(f"❌ Error reading {file_name}: {e}")

    # 🛑 YAHAN THI GALTI: Wo loop hata diya jo ID change kar raha tha.
    
    # ✅ NEW FEATURE: Books ko unki ID ke hisab se sort kar diya
    # Taaki file name kuch bhi ho (a.json, z.json), lekin list ID 1, 2, 3 ke hisab se bane.
    all_books.sort(key=lambda x: x['id'])

    # Master File Save Karo
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_books, f, indent=2, ensure_ascii=False)

    print(f"🎉 Success! '{OUTPUT_FILE}' update ho gayi hai with {len(all_books)} books.")

if __name__ == "__main__":
    merge_books()
def load_all_profiles(user_ids, db):
    profiles = []
    for uid in user_ids:
        profile = db.query(f"SELECT * FROM profiles WHERE id = {uid}")
        profiles.append(profile)
    return profiles


def fetch_avatars(urls, client):
    avatars = []
    for url in urls:
        avatars.append(client.get(url))
    return avatars

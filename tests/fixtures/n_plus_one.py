def load_all_profiles(user_ids, db):
    profiles = []
    for uid in user_ids:
        profile = db.query(f"SELECT * FROM profiles WHERE id = {uid}")
        profiles.append(profile)
    return profiles

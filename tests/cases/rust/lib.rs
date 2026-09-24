use std::collections::HashSet;

fn matches(users: &[User], orders: &[Order]) {
    for u in users {
        for o in orders { // expect: nested-loop
            println!("{:?} {:?}", u, o);
        }
    }
}

fn contains(names: &[String], banned: &Vec<String>) {
    for n in names {
        if banned.contains(n) { // expect: membership-in-loop
            println!("{}", n);
        }
    }
}

fn hashed(names: &[String], banned: &HashSet<String>) {
    for n in names {
        if banned.contains(n) {
            println!("{}", n);
        }
    }
}

fn regex_in_loop(lines: &[String]) {
    for l in lines {
        let re = Regex::new(r"\d+").unwrap(); // expect: regex-compile-in-loop
        re.is_match(l);
    }
}

fn front_removal(mut jobs: Vec<Job>) {
    while !jobs.is_empty() {
        let job = jobs.remove(0); // expect: list-shift-in-loop
    }
}

fun match(users: List<User>, orders: List<Order>) {
    users.forEach { u ->
        orders.forEach { o -> // expect: nested-loop
            println(o)
        }
    }
}

fun build(parts: List<String>): String {
    var s = ""
    for (p in parts) {
        s += p // expect: string-concat-in-loop
    }
    return s
}

fun walk(groups: List<List<Int>>) {
    groups.forEach { g ->
        g.forEach { println(it) }
    }
}

fun implicit(groups: List<Group>) {
    groups.forEach {
        it.items.forEach { item -> println(item) }
    }
}

fun hashed(names: List<String>, banned: Set<String>) {
    for (n in names) {
        if (banned.contains(n)) println(n)
    }
}

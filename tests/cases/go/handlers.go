package handlers

func Match(users []User, orders []Order) {
	for _, u := range users {
		for _, o := range orders { // expect: nested-loop
			if o.UserID == u.ID {
				println(o.ID)
			}
		}
	}
}

func Walk(groups [][]int) int {
	total := 0
	for _, g := range groups {
		for _, v := range g {
			total += v
		}
	}
	return total
}

func Build(parts []string) string {
	s := ""
	for _, p := range parts {
		s += p // expect: string-concat-in-loop
	}
	return s
}

func BuildFast(parts []string) string {
	var b strings.Builder
	for _, p := range parts {
		b.WriteString(p)
	}
	return b.String()
}

func Compile(lines []string) {
	for _, l := range lines {
		re := regexp.MustCompile(`\d+`) // expect: regex-compile-in-loop
		re.MatchString(l)
	}
}

func Load(ids []int, db *sql.DB) {
	for _, id := range ids {
		db.Query("SELECT * FROM t WHERE id = ?", id) // expect: io-or-query-in-loop
	}
}

func Leaders(rounds [][]int, scores []int) {
	for _, r := range rounds {
		scores = append(scores, r...)
		slices.Sort(scores) // expect: sort-in-loop
	}
}

func Lookup(ids []int, index map[int]User) {
	for _, id := range ids {
		if _, ok := index[id]; ok {
			println(id)
		}
	}
}

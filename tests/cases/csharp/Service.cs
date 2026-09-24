using System.Collections.Generic;
using System.Linq;

class Service
{
    string Render(List<Row> rows) {
        string output = "";
        foreach (var row in rows) {
            output += row.Name; // expect: string-concat-in-loop
        }
        return output;
    }

    void Match(List<User> users, List<Order> orders) {
        foreach (var u in users) {
            var match = orders.FirstOrDefault(o => o.UserId == u.Id); // expect: nested-loop
        }
    }

    void Lookup(List<string> names, HashSet<string> banned) {
        foreach (var n in names) {
            if (banned.Contains(n)) { }
        }
    }

    void ListLookup(List<string> names, List<string> banned) {
        foreach (var n in names) {
            if (banned.Contains(n)) { } // expect: membership-in-loop
        }
    }
}

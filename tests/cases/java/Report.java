import java.util.List;
import java.util.Set;
import java.util.regex.Pattern;

class Report {
    String render(List<Row> rows) {
        String out = "";
        for (Row row : rows) {
            out += row.name(); // expect: string-concat-in-loop
        }
        return out;
    }

    String renderFast(List<Row> rows) {
        StringBuilder sb = new StringBuilder();
        for (Row row : rows) {
            sb.append(row.name());
        }
        return sb.toString();
    }

    void match(List<User> users, List<Order> orders) {
        for (User u : users) {
            for (Order o : orders) { // expect: nested-loop
                System.out.println(o);
            }
        }
    }

    void listContains(List<String> names, List<String> banned) {
        for (String n : names) {
            if (banned.contains(n)) { // expect: membership-in-loop
                System.out.println(n);
            }
        }
    }

    void setContains(List<String> names, Set<String> banned) {
        for (String n : names) {
            if (banned.contains(n)) {
                System.out.println(n);
            }
        }
    }

    void pattern(List<String> lines) {
        for (String line : lines) {
            Pattern p = Pattern.compile("\\d+"); // expect: regex-compile-in-loop
            p.matcher(line);
        }
    }

    void drain(List<Job> jobs) {
        while (!jobs.isEmpty()) {
            Job job = jobs.remove(0); // expect: list-shift-in-loop
        }
    }
}

import { useMemo } from "react";

export function UserTable({ users, filter }) {
  const visible = users.filter((u) => u.name.includes(filter)); // expect: render-derived-work
  const sorted = useMemo(() => [...visible].sort(byName), [visible]);
  const total = useMemo(() => {
    return visible.reduce((sum, u) => sum + u.score, 0);
  }, [visible]);
  return (
    <ul>
      {sorted.map((u) => (
        <li key={u.id}>
          {u.name} {total}
        </li>
      ))}
    </ul>
  );
}

export function byName(a, b) {
  return a.name.localeCompare(b.name);
}

export function topScores(users) {
  return users.filter((u) => u.score > 10);
}

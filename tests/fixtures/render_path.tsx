function UserList({ users }) {
  const active = users.filter(u => u.active).map(u => u.name);
  return <ul>{active.map(name => <li key={name}>{name}</li>)}</ul>;
}

export function toLabels(items) {
  return items.map((i) => i.label);
}
